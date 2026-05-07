import grpc
import market_pb2
import market_pb2_grpc

class ClientWrapper:
    def __init__(self, target, env_type="k8s"):
        self.target = target
        self.env_type = env_type
        self.channel = grpc.insecure_channel(target)
        if env_type == "k8s":
            self.stub = market_pb2_grpc.MarketplaceServiceStub(self.channel)
        else:
            self.stub = market_pb2_grpc.MarketplaceControllerStub(self.channel)
            
    def get_item(self, item_id, timeout=5):
        return self.stub.GetItem(market_pb2.GetItemRequest(item_id=item_id), timeout=timeout)
        
    def create_item(self, item, timeout=5):
        return self.stub.CreateItem(market_pb2.CreateItemRequest(item=item), timeout=timeout)
        
    def place_bid(self, item_id, bidder_id, bid_amount, timeout=5):
        return self.stub.PlaceBid(market_pb2.BidRequest(item_id=item_id, bidder_id=bidder_id, bid_amount=bid_amount), timeout=timeout)

    def search_items(self, query, category, timeout=5):
        return self.stub.SearchItems(market_pb2.SearchRequest(query=query, category=category), timeout=timeout)

    def join_auction(self, item_id, user_id, timeout=None):
        return self.stub.JoinAuction(market_pb2.AuctionRequest(item_id=item_id, user_id=user_id), timeout=timeout)
