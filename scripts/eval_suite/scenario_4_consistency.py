import threading
import time
import market_pb2

def run_consistency_scenario(wrapper, workers=50):
    print(f"--- Running Scenario 4: Consistency ({workers} concurrent writes) ---")
    print("Waiting for cluster to fully recover from previous downtime tests...")
    
    # Wait until the system responds successfully before proceeding
    for _ in range(30):
        try:
            wrapper.search_items("ping", "test", timeout=2)
            break
        except Exception:
            time.sleep(2)
    else:
        print("Warning: Cluster did not seem to recover before starting Scenario 4.")
    
    item_id = "consistency-item-1"
    item = market_pb2.MarketplaceItem(
        item_id=item_id,
        seller_id="seller-1",
        title="Consistency Test Item",
        category="test",
        description="Testing concurrency",
        starting_price=1.0,
        current_price=1.0,
        quantity=1,
        status="AUCTION_ACTIVE",
        version=1
    )
    
    try:
        wrapper.create_item(item)
    except Exception as e:
        print(f"Setup failed: {e}")

    # Launch concurrent bids
    success_count = [0]
    lock = threading.Lock()
    
    def bid_worker(bid_amount):
        try:
            resp = wrapper.place_bid(item_id, f"bidder-{bid_amount}", bid_amount)
            if resp.success:
                with lock:
                    success_count[0] += 1
        except Exception:
            pass

    threads = []
    # All threads will bid slightly different amounts, the highest should win.
    bid_amounts = [10.0 + i for i in range(workers)]
    
    # Use a barrier to try and start them as simultaneously as possible
    barrier = threading.Barrier(workers)
    
    def synced_worker(amt):
        barrier.wait()
        bid_worker(amt)

    for amt in bid_amounts:
        t = threading.Thread(target=synced_worker, args=(amt,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Verify final state
    try:
        final_item = wrapper.get_item(item_id, timeout=15)
        print(f"Expected Final Price: {max(bid_amounts)}")
        print(f"Actual Final Price: {final_item.current_price}")
        print(f"Successful bids processed: {success_count[0]}/{workers}")
        
        if final_item.current_price == max(bid_amounts):
            print("Consistency Check: PASS")
        else:
            print("Consistency Check: FAIL (Lost Updates or Incorrect Highest Bid)")
    except Exception as e:
        print(f"Failed to retrieve final state: {e}")
    print("\n")
