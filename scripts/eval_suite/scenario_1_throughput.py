import time
import threading
import random
import market_pb2
import grpc

def run_throughput_scenario(wrapper, num_items=5, workers=20, duration=10):
    print("--- Running Scenario 1: Throughput (Reads, Bids, Polling) ---")
    
    # 1. Setup Items
    item_ids = [f"bench-item-{i}" for i in range(num_items)]
    for item_id in item_ids:
        item = market_pb2.MarketplaceItem(
            item_id=item_id,
            seller_id="bench-seller",
            title=f"Benchmark {item_id}",
            category="bench",
            description="A benchmark item",
            starting_price=10.0,
            current_price=10.0,
            quantity=1,
            status="AUCTION_ACTIVE",
            version=1
        )
        try:
            wrapper.create_item(item)
        except Exception as e:
            print(f"Warn: Setup failed for {item_id}: {e}")

    stop_event = threading.Event()
    requests_completed = [0]
    lock = threading.Lock()

    def polling_worker(item_id):
        try:
            # Join auction and stream events until stopped
            stream = wrapper.join_auction(item_id, f"poller-{random.randint(100,999)}")
            for event in stream:
                if stop_event.is_set():
                    break
                with lock:
                    requests_completed[0] += 1
        except grpc.RpcError as e:
            # Stream closed or cancelled
            pass
        except Exception:
            pass

    def action_worker():
        while not stop_event.is_set():
            item_id = random.choice(item_ids)
            try:
                if random.random() < 0.2: # 20% writes
                    wrapper.place_bid(item_id, f"bidder-{random.randint(100,999)}", round(random.uniform(10, 500), 2))
                else: # 80% reads
                    wrapper.get_item(item_id)
                
                with lock:
                    requests_completed[0] += 1
            except grpc.RpcError:
                pass
            except Exception:
                pass

    threads = []
    
    # Start Polling threads (1 per item)
    for item_id in item_ids:
        t = threading.Thread(target=polling_worker, args=(item_id,))
        t.start()
        threads.append(t)

    # Start Action threads
    for _ in range(workers):
        t = threading.Thread(target=action_worker)
        t.start()
        threads.append(t)

    start_time = time.time()
    time.sleep(duration)
    stop_event.set()
    
    # Since join_auction is a blocking stream generator, we might need to forcefully cancel 
    # the underlying channel to join threads cleanly if they are stuck waiting for a message.
    # We will just give it a short timeout and proceed.
    for t in threads:
        t.join(timeout=1.0)

    actual_duration = time.time() - start_time
    rps = requests_completed[0] / actual_duration
    
    print(f"Total Requests (Reads + Bids + Stream Events): {requests_completed[0]}")
    print(f"Duration: {actual_duration:.2f}s")
    print(f"RPS: {rps:.2f} req/s\n")
    return rps
