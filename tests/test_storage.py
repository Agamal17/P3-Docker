import os
import sys
import os.path
# Ensure generated protobufs are importable when running tests locally
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'proto', 'src')))

from storage.storage import _row_to_item, StorageService
import market_pb2


def test_row_to_item_basic():
    row = {
        "seller_id": "seller1",
        "title": "Test item",
        "category": "cat",
        "description": "desc",
        "starting_price": 5.0,
        "current_price": 5.0,
        "quantity": 3,
        "status": "AVAILABLE",
        "version": 1,
    }
    item = _row_to_item("item-1", row)
    assert item.item_id == "item-1"
    assert item.seller_id == "seller1"
    assert item.title == "Test item"
    assert item.category == "cat"
    assert item.description == "desc"
    assert item.starting_price == 5.0
    assert item.current_price == 5.0
    assert item.quantity == 3
    assert item.status == "AVAILABLE"
    assert item.version == 1


def test_create_and_get_item():
    # ensure deterministic node id for test
    os.environ.pop("HOSTNAME", None)
    s = StorageService()
    item = market_pb2.MarketplaceItem(
        item_id="i-1",
        seller_id="seller1",
        title="T",
        category="cat",
        description="d",
        starting_price=10.0,
        current_price=10.0,
        quantity=1,
        status="AVAILABLE",
        version=1,
    )
    req = market_pb2.CreateItemRequest(item=item, primary_store_id="some-other-node")
    resp = s.CreateItem(req, None)
    assert resp.success
    get_req = market_pb2.GetItemRequest(item_id="i-1")
    got = s.GetItem(get_req, None)
    assert got.item_id == "i-1"
    assert got.title == "T"
    assert got.seller_id == "seller1"
