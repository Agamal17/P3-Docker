import sys
import os
import grpc

import market_pb2
import market_pb2_grpc

# If running in devcontainer use host.docker.internal
# If running on host machine use localhost
TARGET = "host.docker.internal:50050"
# TARGET = "localhost:50050"

def main():
    if len(sys.argv) < 3:
        print("put <key> <value>")
        print("get <key>")
        return
    
    key=sys.argv[2]
    if sys.argv[1] != "get":
        value=sys.argv[3]
    
    with grpc.insecure_channel(TARGET) as channel:
        stub = market_pb2_grpc.MarketplaceControllerStub(channel)
        mit = market_pb2.MarketplaceItem()
        mit.item_id = key
        mit.seller_id = "435"
        mit.title = "hey"
        mit.category = "a"
        mit.description = "category"
        mit.starting_price = 6
        mit.current_price = 7
        mit.quantity = 8
        mit.status = "AVAILABLE"
        mit.version = 0

        if sys.argv[1] == "get":
            response = stub.GetItem(market_pb2.GetItemRequest(item_id=key))
            print({"key": key, "value": response.title})
            return
        
        response = stub.CreateItem(market_pb2.CreateItemRequest(item=mit))
        print({"key": key, "ok": response.success, "message": response.message})


if __name__ == "__main__":
    main()
