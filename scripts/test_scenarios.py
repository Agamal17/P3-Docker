#!/usr/bin/env python3
import os
import sys
import time
import grpc

# Make generated proto modules importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto', 'src'))
import market_pb2
import market_pb2_grpc

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
    try:
        resp = stub.CreateItem(req)
    except grpc.RpcError as e:
        print("CreateItem rpc error:", e)
        return None
    print("CreateItem ->", resp)
    return resp

def get_item(stub, key):
    try:
        resp = stub.GetItem(market_pb2.GetItemRequest(item_id=key))
    except grpc.RpcError as e:
        print("GetItem rpc error:", e)
        return None
    print("GetItem repr:\n", resp)
    print("item_id:", repr(resp.item_id))
    print("title:", repr(resp.title))
    print("current_price:", resp.current_price)
    return resp

def search_items(stub, query, category=''):
    try:
        resp = stub.SearchItems(market_pb2.SearchRequest(query=query, category=category))
    except grpc.RpcError as e:
        print("SearchItems rpc error:", e)
        return None
    print("SearchItems -> count:", len(resp.items))
    for item in resp.items:
        print("-", item.item_id, item.title, item.current_price)
    return resp

def update_item(stub, key, description=None, status=None, quantity=None, expected_version=None):
    kwargs = { 'item_id': key }
    if description is not None:
        kwargs['description'] = description
    if status is not None:
        kwargs['status'] = status
    if quantity is not None:
        kwargs['quantity'] = quantity
    if expected_version is not None:
        kwargs['expected_version'] = expected_version
    req = market_pb2.UpdateItemRequest(**kwargs)
    try:
        resp = stub.UpdateItem(req)
    except grpc.RpcError as e:
        print("UpdateItem rpc error:", e)
        return None
    print("UpdateItem ->", resp)
    return resp

def place_bid(stub, key, bidder_id, amount):
    req = market_pb2.BidRequest(item_id=key, bidder_id=bidder_id, bid_amount=amount)
    try:
        resp = stub.PlaceBid(req)
    except grpc.RpcError as e:
        print("PlaceBid rpc error:", e)
        return None
    print("PlaceBid ->", resp)
    return resp

def main():
    key = 'test123'
    channel = grpc.insecure_channel(TARGET)
    try:
        grpc.channel_ready_future(channel).result(timeout=5)
    except Exception as e:
        print("Channel not ready to", TARGET, ":", e)
        return
    stub = market_pb2_grpc.MarketplaceControllerStub(channel)

    print("=== CreateItem ===")
    create_item(stub, key)
    time.sleep(0.3)

    print("\n=== GetItem ===")
    get_item(stub, key)

    print("\n=== SearchItems (query='test') ===")
    search_items(stub, 'test')

    print("\n=== UpdateItem -> set AUCTION_ACTIVE ===")
    update_item(stub, key, description='updated description', status='AUCTION_ACTIVE', expected_version=1)
    time.sleep(0.3)

    print("\n=== PlaceBid (valid) ===")
    place_bid(stub, key, 'bidder1', 20.0)

    print("\n=== GetItem after bid ===")
    get_item(stub, key)

    print("\n=== PlaceBid (too low) ===")
    place_bid(stub, key, 'bidder2', 5.0)

    print("\n=== Final SearchItems ===")
    search_items(stub, 'test')

    channel.close()

if __name__ == '__main__':
    main()
