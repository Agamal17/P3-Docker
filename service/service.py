from concurrent import futures
import os
import random
import threading
import grpc
import market_pb2
import market_pb2_grpc
from utils.config import NODE_PORT


class MarketplaceService(market_pb2_grpc.MarketplaceServiceServicer):
    def __init__(self):
        super().__init__()
        self.node_id = os.environ.get("HOSTNAME", "unknown-service-node")
        self.controller_url = os.environ.get("CONTROLLER_ADDR", "controller:50050")
        self.storage_targets = os.environ.get("STORAGE_TARGETS", "").split(",") if os.environ.get("STORAGE_TARGETS") else []

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
                        type=market_pb2.Ping.SERVICE
                    )
                    stub.Heartbeat(ping)
                except grpc.RpcError as e:
                    print(f"[{self.node_id}] Failed to heartbeat Controller: {e.code()}")
                
                # Sleep for a interval shorter than the Controller's timeout
                threading.Event().wait(3)

    def _get_random_storage_node(self):
        if not self.storage_targets:
            raise ValueError("No storage targets available")
        return random.choice(self.storage_targets)

    def CreateItem(self, request, context):
        target = request.primary_store_id
        with grpc.insecure_channel(target) as channel:
            stub = market_pb2_grpc.MarketplaceStorageStub(channel)
            try:
                resp = stub.CreateItem(request)
                return resp
            except grpc.RpcError as e:
                context.set_code(e.code())
                context.set_details(e.details())
                return market_pb2.ActionResponse(success=False, message=str(e), new_version=0)

    def GetItem(self, request, context):
        target = self._get_random_storage_node()
        with grpc.insecure_channel(target) as channel:
            stub = market_pb2_grpc.MarketplaceStorageStub(channel)
            try:
                resp = stub.GetItem(request)
                return resp
            except grpc.RpcError as e:
                context.set_code(e.code())
                context.set_details(e.details())
                return market_pb2.MarketplaceItem()

    def SearchItems(self, request, context):
        target = self._get_random_storage_node()
        with grpc.insecure_channel(target) as channel:
            stub = market_pb2_grpc.MarketplaceStorageStub(channel)
            try:
                resp = stub.SearchItems(request)
                return resp
            except grpc.RpcError as e:
                context.set_code(e.code())
                context.set_details(e.details())
                return market_pb2.SearchResponse(items=[])

    def UpdateItem(self, request, context):
        target = request.primary_store_id
        with grpc.insecure_channel(target) as channel:
            stub = market_pb2_grpc.MarketplaceStorageStub(channel)
            try:
                resp = stub.UpdateItem(request)
                return resp
            except grpc.RpcError as e:
                context.set_code(e.code())
                context.set_details(e.details())
                return market_pb2.ActionResponse(success=False, message=str(e), new_version=0)

    def PlaceBid(self, request, context):
        target = request.primary_store_id
        with grpc.insecure_channel(target) as channel:
            stub = market_pb2_grpc.MarketplaceStorageStub(channel)
            try:
                resp = stub.PlaceBid(request)
                return resp
            except grpc.RpcError as e:
                context.set_code(e.code())
                context.set_details(e.details())
                return market_pb2.ActionResponse(success=False, message=str(e), new_version=0)
            
    def JoinAuction(self, request, context):
        target = self._get_random_storage_node()
        with grpc.insecure_channel(target) as channel:
            stub = market_pb2_grpc.MarketplaceStorageStub(channel)
            try:
                auction_stream = stub.JoinAuction(request)
                for event in auction_stream:
                    yield event
            except grpc.RpcError as e:
                context.set_code(e.code())
                context.set_details(e.details())
                return

def serve():
    # 1. Get configuration from Environment Variables (set in docker-compose)
    node_id = os.environ.get("HOSTNAME", "unknown-service-node")
    controller_url = os.environ.get("CONTROLLER_URL", "controller:50050")
    port = os.environ.get("PORT", "50051")

    # 2. Initialize the Service Logic
    service_impl = MarketplaceService()

    # 3. Start Heartbeat Thread
    heartbeat_thread = threading.Thread(target=service_impl._send_heartbeats, daemon=True)
    heartbeat_thread.start()

    # 4. Start gRPC Server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    market_pb2_grpc.add_MarketplaceServiceServicer_to_server(service_impl, server)
    
    server.add_insecure_port(f'[::]:{port}')
    print(f"[{node_id}] Service Node listening on port {port}...")
    
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
