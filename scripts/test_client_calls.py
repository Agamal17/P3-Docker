#!/usr/bin/env python3
import os
import sys
import time
import grpc

# Ensure generated proto modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto', 'src'))
import market_pb2
import market_pb2_grpc

# Default to localhost:50050, can be overridden with env var TARGET
TARGET = os.environ.get('TARGET', 'localhost:50050')

def create_item(stub, key):
    mit = market_pb2.MarketplaceItem()
    mit.item_id = key
    mit.seller_id = "435"
    mit.title = "test-item"
    mit.category = "test"
    mit.description = "test description"
    mit.starting_price = 6.0
    mit.current_price = 7.0
    mit.quantity = 1
    mit.status = "AVAILABLE"
    mit.version = 0

    req = market_pb2.CreateItemRequest(item=mit)
    resp = stub.CreateItem(req)
    print("CreateItem response:", resp)

def get_item(stub, key):
    resp = stub.GetItem(market_pb2.GetItemRequest(item_id=key))
    print("GetItem response repr:", repr(resp))
    # Print individual fields for easier debugging
    print("item_id:", repr(resp.item_id))
    print("title:", repr(resp.title))
    print("current_price:", resp.current_price)

def main():
    key = "test123"
    with grpc.insecure_channel(TARGET) as channel:
        stub = market_pb2_grpc.MarketplaceControllerStub(channel)
        create_item(stub, key)
        time.sleep(0.5)
        get_item(stub, key)

if __name__ == '__main__':
    main()
