import grpc
import market_pb2
import market_pb2_grpc
import threading
import time
import random
from concurrent import futures

TARGET = "host.docker.internal:50050"
# TARGET = "localhost:50050"

class MarketplaceClient:
    def __init__(self):
        self.channel = grpc.insecure_channel(TARGET)
        self.stub = market_pb2_grpc.MarketplaceControllerStub(self.channel)

    def read_heavy_scenario(self, duration_sec=10):
        """Simulates constant browsing (Search/GetItem)."""
        print("--- Starting Read-Heavy Scenario ---")
        end_time = time.time() + duration_sec
        while time.time() < end_time:
            try:
                # Simulating a search for items
                self.stub.SearchItems(market_pb2.SearchRequest(query="a", category="a"))
                time.sleep(0.1)  # High frequency reads
            except Exception as e:
                print(f"Read error: {e}")

    def occasional_writes(self, count=5):
        """Simulates item updates or new listings."""
        print("--- Starting Occasional Writes ---")
        for i in range(count):
            item_id = f"item_{random.randint(100, 999)}"
            mit = market_pb2.MarketplaceItem(
                item_id=item_id,
                seller_id="435",
                title=f"Update_{i}",
                starting_price=6.0,
                current_price=7.0,
                quantity=8,
                status="AVAILABLE",
                category="a",
                version=1,
                description="An updated item for testing",
            )
            try:
                self.stub.CreateItem(market_pb2.CreateItemRequest(item=mit))
                print(f"Created/Updated {item_id}")
                time.sleep(1) # Occasional, not a burst
            except Exception as e:
                print(f"Write error: {e}")

    def active_auction(self, item_id="bid_item_1"):
        """Scenario: Multiple bids on a single item (Contention)."""
        print(f"--- Participating in Auction for {item_id} ---")
        for i in range(5):
            bid_amount = 10.0 + i
            try:
                # Assuming your proto has a PlaceBid or UpdateItem for bids
                self.stub.PlaceBid(market_pb2.BidRequest(item_id=item_id, bidder_id=" bidder_id", bid_amount=bid_amount))
                print(f"Placed bid: {bid_amount}")
                time.sleep(0.5)
            except Exception as e:
                print(f"Auction error: {e}")

def burst_demand(client_count=20):
    """Scenario: Bursts of demand using multiple threads."""
    print(f"--- Triggering Burst Demand: {client_count} concurrent clients ---")
    
    def task():
        client = MarketplaceClient()
        client.stub.GetItem(market_pb2.GetItemRequest(item_id="item_123"))
    
    threads = []
    for _ in range(client_count):
        t = threading.Thread(target=task)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    

def main():
    client = MarketplaceClient()

    # # 1. Occasional Writes
    # client.occasional_writes(count=1)

    # # 2. Read-Heavy
    # client.read_heavy_scenario(duration_sec=5)

    # # 3. Active Auction
    # client.active_auction("item_123")

    # 4. Burst Demand (Stress test for your autoscaler!)
    # burst_demand(client_count=100)

if __name__ == "__main__":
    main()