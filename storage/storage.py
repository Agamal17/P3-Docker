import os
from concurrent import futures
import threading
import grpc
import pandas as pd
import market_pb2
import market_pb2_grpc
from utils.config import NODE_PORT


def _row_to_item(item_id, row) -> market_pb2.MarketplaceItem:
    item = market_pb2.MarketplaceItem()
    item.item_id = item_id
    item.seller_id = str(row.get("seller_id", ""))
    item.title = str(row.get("title", ""))
    item.category = str(row.get("category", ""))
    item.description = str(row.get("description", ""))
    item.starting_price = float(row.get("starting_price", 0.0) or 0.0)
    item.current_price = float(row.get("current_price", 0.0) or 0.0)
    item.quantity = int(row.get("quantity", 0) or 0)
    item.status = str(row.get("status", ""))
    item.version = int(row.get("version", 0) or 0)
    return item


class StorageService(market_pb2_grpc.MarketplaceStorageServicer):
    def __init__(self):
        self.node_id = os.environ.get("HOSTNAME", "unknown-storage-node")
        self.controller_url = os.environ.get("CONTROLLER_ADDR", "controller:50050")
        storage_env = os.environ.get("STORAGE_NODES") or os.environ.get("STORAGE_TARGETS") or ""
        self.storage_nodes = [s for s in storage_env.split(",") if s]

        # Use a pandas DataFrame for item storage. This is an in-memory DataFrame
        # representing the storage layer; in a production deployment this would be
        # backed by a durable, replicated store.
        DF_COLUMNS = [
            "item_id",
            "seller_id",
            "title",
            "category",
            "description",
            "starting_price",
            "current_price",
            "quantity",
            "status",
            "version",
        ]

        self.DATA_DF = pd.DataFrame(columns=DF_COLUMNS).set_index("item_id")
        self.DATA_LOCK = threading.Lock()

    def _send_heartbeats(self):
        """Background thread to keep the node registered with the Controller"""
        print(f"[{self.node_id}] Heartbeat thread started.")
        # Create a dedicated channel for heartbeats
        with grpc.insecure_channel(self.controller_url) as channel:
            stub = market_pb2_grpc.MarketplaceControllerStub(channel)
            while True:
                try:
                    # Construct the Ping message
                    ping = market_pb2.Ping(
                        node_id=self.node_id, 
                        node_address=f"{self.node_id}:{NODE_PORT}",
                        type=market_pb2.Ping.STORAGE
                    )
                    stub.Heartbeat(ping)
                except grpc.RpcError as e:
                    print(f"[{self.node_id}] Failed to heartbeat Controller: {e.code()}")
                
                # Sleep for a interval shorter than the Controller's timeout
                threading.Event().wait(3)

    # replicate state from primary to self
    def send_replicate_request(self):
        controller_stub = market_pb2_grpc.MarketplaceControllerStub(grpc.insecure_channel(self.controller_url))
        try:
            # get primary storage node
            resp = controller_stub.GetPrimaryStorage(market_pb2.GetPrimaryStorageRequest())
            primary_target = resp.primary_storage_target
            if primary_target == f"{self.node_id}:{NODE_PORT}":
                print(f"[{self.node_id}] I am the primary storage, no need to replicate")
                return
            print(f"[{self.node_id}] Replicating state from primary storage {primary_target}")
            with grpc.insecure_channel(primary_target) as channel:
                stub = market_pb2_grpc.MarketplaceStorageStub(channel)
                replicate_stream = stub.ReplicateState(market_pb2.ReplicationRequest())
                data_list = []
                for item in replicate_stream:
                    data_list.append({
                        "item_id": item.item_id, # We'll move this to the index later
                        "seller_id": item.seller_id,
                        "title": item.title,
                        "category": item.category,
                        "description": item.description,
                        "starting_price": float(item.starting_price),
                        "current_price": float(item.current_price),
                        "quantity": int(item.quantity),
                        "status": item.status,
                        "version": int(item.version),
                    })

                # 2. Create the DataFrame in one shot
                new_df = pd.DataFrame(data_list)
                
                if not new_df.empty:
                    new_df.set_index("item_id", inplace=True)

                # apply replicated state to self
                with self.DATA_LOCK:
                    self.DATA_DF = new_df

                print(f"[{self.node_id}] Replication complete, {len(new_df)} items replicated")
        except grpc.RpcError as e:
            print(f"[{self.node_id}] Failed to replicate state from primary: {e.code()}")


    def ReplicateState(self, request, context):
        """Handle replication requests to primary storage to synchronize replicas"""
        print(f"[{self.node_id}] Received replication request from requester")
        for item_id, row in self.DATA_DF.iterrows():
            yield _row_to_item(item_id, row)

    def propagate_to_replicas(self, item: market_pb2.MarketplaceItem, version: int):
        """Propagate item changes to replica storage nodes for redundancy"""
        written_replicas = []
        for target in self.storage_nodes:
            if target == f"{self.node_id}:{NODE_PORT}":
                continue  # Skip self
            try:
                with grpc.insecure_channel(target) as channel:
                    stub = market_pb2_grpc.MarketplaceStorageStub(channel)
                    request = market_pb2.CreateItemRequest(item=item)
                    stub.CreateItem(request)
                    written_replicas.append(target)
            except grpc.RpcError as e:
                print(f"[{self.node_id}] Failed to propagate to replica {target}: {e.code()}")
                # handle write failure (Atomic Consistency) - in a real system we might want to retry, mark the replica as unhealthy, etc.
                for target in written_replicas:
                    try:
                        with grpc.insecure_channel(target) as channel:
                            stub = market_pb2_grpc.MarketplaceStorageStub(channel)
                            stub.DeleteItem(market_pb2.DeleteItemRequest(item_id=item.item_id, version=version))
                    except grpc.RpcError as e:
                        print(f"[{self.node_id}] Failed to rollback replica {target}: {e.code()}")
                return None
            
        print(f"[{self.node_id}] Successfully propagated item {item.item_id} v{version} to replicas")
        return market_pb2.ActionResponse(success=True, message="updated", new_version=version)

    def CreateItem(self, request, context):
        item = request.item
        with self.DATA_LOCK:
            if item.item_id in self.DATA_DF.index:
                existing = self.DATA_DF.loc[item.item_id]
                return market_pb2.ActionResponse(success=False, message="item exists", new_version=int(existing.get("version", 0) or 0))
            version = int(item.version or 0) or 1
            row = {
                "seller_id": item.seller_id,
                "title": item.title,
                "category": item.category,
                "description": item.description,
                "starting_price": float(item.starting_price or 0.0),
                "current_price": float(item.current_price or item.starting_price or 0.0),
                "quantity": int(item.quantity or 0),
                "status": item.status,
                "version": version,
            }
            self.DATA_DF.loc[item.item_id] = row
        
        # Determine if this node is the primary for the incoming request.
        primary_store = getattr(request, 'primary_store_id', '') or ''
        primary_host = primary_store.split(':')[0] if primary_store else ''
        if primary_host == self.node_id or primary_store == f"{self.node_id}:{NODE_PORT}":
            # Only propagate if this node is the primary store for the item
            res = self.propagate_to_replicas(item, version)
            if not res:
                self.DATA_DF.drop(item.item_id, inplace=True)  # rollback local write
                return market_pb2.ActionResponse(success=False, message="failed to propagate", new_version=version)

        return market_pb2.ActionResponse(success=True, message="created", new_version=version)

    def GetItem(self, request, context):
        item_id = request.item_id
        with self.DATA_LOCK:
            if item_id not in self.DATA_DF.index:
                return market_pb2.MarketplaceItem()
            row = self.DATA_DF.loc[item_id]
            return _row_to_item(item_id, row)
        
    def DeleteItem(self, request, context):
        item_id = request.item_id
        version = request.version
        with self.DATA_LOCK:
            if item_id not in self.DATA_DF.index:
                return market_pb2.ActionResponse(success=False, message="not found", new_version=0)
            row = self.DATA_DF.loc[item_id]
            current_version = int(row.get("version", 0) or 0)
            if version and version != current_version:
                return market_pb2.ActionResponse(success=False, message="version mismatch", new_version=current_version)
            self.DATA_DF.drop(item_id, inplace=True)
        print(f"{self.node_id} Deleted item {item_id} v{version}", flush=True)
        return market_pb2.ActionResponse(success=True, message="deleted", new_version=version)

    def SearchItems(self, request, context):
        q = (request.query or "").lower()
        cat = (request.category or "").lower()
        results = []
        with self.DATA_LOCK:
            df = self.DATA_DF.copy()
        if q:
            mask = df["title"].fillna("").str.lower().str.contains(q) | df["description"].fillna("").str.lower().str.contains(q)
            df = df[mask]
        if cat:
            mask = df["category"].fillna("").str.lower() == cat
            df = df[mask]
        for item_id, row in df.iterrows():
            results.append(_row_to_item(item_id, row))
        return market_pb2.SearchResponse(items=results)

    def UpdateItem(self, request, context):
        item_id = request.item_id
        with self.DATA_LOCK:
            if item_id not in self.DATA_DF.index:
                return market_pb2.ActionResponse(success=False, message="not found", new_version=0)
            row = self.DATA_DF.loc[item_id].to_dict()
            # optional checks
            try:
                has_desc = request.HasField('description')
            except Exception:
                has_desc = bool(request.description)
            try:
                has_qty = request.HasField('quantity')
            except Exception:
                has_qty = request.quantity != 0
            try:
                has_status = request.HasField('status')
            except Exception:
                has_status = bool(request.status)
            current_version = int(row.get("version", 0) or 0)
            if request.expected_version and request.expected_version != current_version:
                return market_pb2.ActionResponse(success=False, message="version mismatch", new_version=current_version)
            if has_desc:
                row["description"] = request.description
            if has_qty:
                row["quantity"] = int(request.quantity)
            if has_status:
                row["status"] = request.status
            row["version"] = current_version + 1
            self.DATA_DF.loc[item_id] = row
            new_version = row["version"]
        print(f"{self.node_id} UpdateItem {item_id} -> v{new_version}", flush=True)
        return market_pb2.ActionResponse(success=True, message="updated", new_version=new_version)

    def PlaceBid(self, request, context):
        item_id = request.item_id
        with self.DATA_LOCK:
            if item_id not in self.DATA_DF.index:
                return market_pb2.ActionResponse(success=False, message="not found", new_version=0)
            row = self.DATA_DF.loc[item_id].to_dict()
            status = str(row.get("status", ""))
            current_price = float(row.get("current_price", 0.0) or 0.0)
            starting_price = float(row.get("starting_price", 0.0) or 0.0)
            version = int(row.get("version", 0) or 0)
            if status != "AUCTION_ACTIVE":
                return market_pb2.ActionResponse(success=False, message="auction not active", new_version=version)
            min_price = current_price or starting_price
            if request.bid_amount <= min_price:
                return market_pb2.ActionResponse(success=False, message="bid too low", new_version=version)
            row["current_price"] = float(request.bid_amount)
            row["version"] = version + 1
            self.DATA_DF.loc[item_id] = row
            new_version = row["version"]
        print(f"{self.node_id} PlaceBid {item_id} bid={request.bid_amount} by {request.bidder_id}", flush=True)
        return market_pb2.ActionResponse(success=True, message="bid accepted", new_version=new_version)

    def AuctionPoll(self, request, context):
        item_id = request.item_id
        last_version = None
        while True:
            with self.DATA_LOCK:
                if item_id not in self.DATA_DF.index:
                    yield market_pb2.AuctionEvent(type=market_pb2.AuctionEvent.AUCTION_CLOSED, item_snapshot=market_pb2.MarketplaceItem(), event_description="item not found or auction closed")
                    return
                row = self.DATA_DF.loc[item_id]
                current_version = int(row.get("version", 0) or 0)
                if current_version != last_version:
                    item = _row_to_item(item_id, row)
                    event_type = market_pb2.AuctionEvent.BID_PLACED if last_version is not None else market_pb2.AuctionEvent.STATUS_CHANGE
                    yield market_pb2.AuctionEvent(type=event_type, item_snapshot=item, event_description="polled")
                    last_version = current_version

            threading.Event().wait(1)


def serve():
    storage_service = StorageService()
    port = int(os.environ.get("PORT", "50051"))
    heartbeat_thread = threading.Thread(target=storage_service._send_heartbeats, daemon=True)
    heartbeat_thread.start()

    # wait a moment to ensure heartbeat thread has registered the node with the Controller and primary storage is elected before attempting replication
    time.sleep(5)
    
    storage_service.send_replicate_request()  # synchronize state from primary on startup

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    market_pb2_grpc.add_MarketplaceStorageServicer_to_server(storage_service, server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"storage {storage_service.node_id} listening on {port}", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    import time
    serve()
