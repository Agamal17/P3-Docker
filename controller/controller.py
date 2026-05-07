import random
import grpc
from concurrent import futures
import time
import threading
import sys
import os
from utils.config import CONTROLLER_PORT, NODE_PORT
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../proto/src')))
import market_pb2
import market_pb2_grpc
from utils.utils import create_service_node, create_storage_node
import functools

NUMBER_OF_STORAGE_NODES = 2  # number of storage nodes

# decorator to monitor gRPC method calls for logging and scaling decisions
def monitor_request(func):
    @functools.wraps(func)
    def wrapper(self, request, context):
        # 1. Logic BEFORE the function starts
        self.request_count += 1
        try:
            # 2. Execute the actual gRPC method
            result = func(self, request, context)
            return result
        finally:
            # 3. Logic AFTER the function ends
            self.request_count -= 1
            
    return wrapper

class MarketplaceController(market_pb2_grpc.MarketplaceControllerServicer):
    def __init__(self):
        # Metadata storage
        self.nodes = {}  # node_id -> {"type": type, "stub": stub}
        self.health_map = {}  # node_id -> last_timestamp
        self.primary_storage_id = None
        self.lock = threading.Lock()

        # a counter to detect number of requests for scaling service nodes accordingly
        # doesn't need to be thread-safe since it's only used for logging and scaling decisions, not critical to be perfectly accurate
        self.request_count = 0
        
        # Start failure detection thread
        threading.Thread(target=self._monitor_nodes, daemon=True).start()

    def GetPrimaryStorage(self, request, context):
        with self.lock:
            if self.primary_storage_id and self.primary_storage_id in self.health_map:
                return market_pb2.GetPrimaryStorageResponse(primary_storage_target=f"{self.primary_storage_id}:{NODE_PORT}")
            else:
                return None

    def _get_random_service_node(self):
        with self.lock:
            service_nodes = [(node_id, v) for node_id, v in self.nodes.items() if v["type"] == market_pb2.Ping.SERVICE and node_id in self.health_map]
            if not service_nodes:
                return None
            return random.choice(service_nodes)

    @monitor_request
    def CreateItem(self, request, context):
        service_node = self._get_random_service_node()
        if not service_node:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            return market_pb2.ActionResponse(success=False, message="No service nodes available")
        
        # Route the request to the Service Node
        request.primary_store_id = f"{self.primary_storage_id}:{NODE_PORT}"  # Attach primary storage info for the service node to route to storage
        return service_node[1]["stub"].CreateItem(request)

    @monitor_request
    def GetItem(self, request, context):
        self.request_count += 1
        service_node = self._get_random_service_node()
        if not service_node:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            return market_pb2.MarketplaceItem()
        
        return service_node[1]["stub"].GetItem(request)
    
    @monitor_request
    def SearchItems(self, request, context):
        service_node = self._get_random_service_node()
        if not service_node:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            return market_pb2.SearchResponse()
        return service_node[1]["stub"].SearchItems(request)
    
    @monitor_request
    def UpdateItem(self, request, context):
        service_node = self._get_random_service_node()
        if not service_node:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            return market_pb2.ActionResponse(success=False, message="No service nodes available")

        request.primary_store_id = f"{self.primary_storage_id}:{NODE_PORT}"  # Attach primary storage info for the service node to route to storage
        return service_node[1]["stub"].UpdateItem(request)
    
    @monitor_request
    def PlaceBid(self, request, context):
        service_node = self._get_random_service_node()
        if not service_node:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            return market_pb2.ActionResponse(success=False, message="No service nodes available")
        
        request.primary_store_id = f"{self.primary_storage_id}:{NODE_PORT}"  # Attach primary storage info for the service node to route to storage
        return service_node[1]["stub"].PlaceBid(request)
    
    @monitor_request
    def JoinAuction(self, request, context):
        service_node = self._get_random_service_node()
        if not service_node:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            return market_pb2.ActionResponse(success=False, message="No service nodes available")
        auction_stream = service_node[1]["stub"].JoinAuction(request)
        for event in auction_stream:
            yield event

    def Heartbeat(self, request, context):
        with self.lock:
            node_id = request.node_id
            self.health_map[node_id] = time.time()
            
            # Register new nodes on the fly
            if node_id not in self.nodes:
                self.nodes[node_id] = {"type": request.type}
                target = request.node_address
                channel = grpc.insecure_channel(target)
                if request.type == market_pb2.Ping.SERVICE:
                    stub = market_pb2_grpc.MarketplaceServiceStub(channel)
                elif request.type == market_pb2.Ping.STORAGE:
                    stub = market_pb2_grpc.MarketplaceStorageStub(channel)

                self.nodes[node_id]["stub"] = stub
                print(f"Registered Type {request.type} node: {node_id}")
                
                # If it's the first storage node, make it Primary
                if request.type == market_pb2.Ping.STORAGE and self.primary_storage_id is None:
                    self.primary_storage_id = node_id
                    print(f"Elected Primary: {node_id}")

        return market_pb2.Pong(healthy=True)

    def _monitor_nodes(self):
        """Background thread to detect crashes and scale service nodes based on request load"""
        while True:
            threading.Event().wait(3)
            now = time.time()
            with self.lock:
                dead_nodes = [id for id, t in self.health_map.items() if now - t > 15]  # 15 seconds timeout for node failure
                for node_id in dead_nodes:
                    print(f"Node failure detected: {node_id}")
                    self._handle_failure(node_id)

                print(f"Current request count: {self.request_count}, Active service nodes: {len([n for n in self.nodes.values() if n['type'] == market_pb2.Ping.SERVICE and n['stub'] is not None])}")
                if self.request_count > 10 * len([n for n in self.nodes.values() if n["type"] == market_pb2.Ping.SERVICE]):  #threshold for scaling up
                    print("High load detected, consider scaling up service nodes")
                    create_service_node(len(self.nodes), [node_id for node_id, v in self.nodes.items() if v["type"] == market_pb2.Ping.STORAGE])
                    self.request_count = 0  # Reset counter after scaling decision

    def _handle_failure(self, node_id):
        """Logic to promote a new primary if the current one dies"""
        del self.health_map[node_id]
        if node_id == self.primary_storage_id:
            self.primary_storage_id = None
            # Find a new storage node to promote
            for nid, info in self.nodes.items():
                if nid in self.health_map and info["type"] == market_pb2.Ping.STORAGE:
                    self.primary_storage_id = nid
                    print(f"New Primary elected: {self.primary_storage_id}")
                    break
        del self.nodes[node_id]

        # Replica Replenishment: If a storage node dies, create a new one to maintain replication factor
        if len([n for n in self.nodes.values() if n["type"] == market_pb2.Ping.STORAGE]) < NUMBER_OF_STORAGE_NODES:
            print("Storage node count below threshold, creating new storage node")
            create_storage_node(len(self.nodes), [node_id for node_id, v in self.nodes.items() if v["type"] == market_pb2.Ping.STORAGE])

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    market_pb2_grpc.add_MarketplaceControllerServicer_to_server(MarketplaceController(), server)
    server.add_insecure_port(f'[::]:{CONTROLLER_PORT}')
    print(f"Controller started on port {CONTROLLER_PORT}...")

    server.start()

    # Create initial storage and service nodes
    storage_nodes = [f"storage-{i}:{NODE_PORT}" for i in range(NUMBER_OF_STORAGE_NODES)]
    for i in range(NUMBER_OF_STORAGE_NODES):
        create_storage_node(i, storage_nodes)
    
    for i in range(1):
        create_service_node(i, storage_nodes)

    server.wait_for_termination()

if __name__ == "__main__":
    serve()