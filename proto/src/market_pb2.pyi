from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MarketplaceItem(_message.Message):
    __slots__ = ("item_id", "seller_id", "title", "category", "description", "starting_price", "current_price", "quantity", "status", "version")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    SELLER_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    STARTING_PRICE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_PRICE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    seller_id: str
    title: str
    category: str
    description: str
    starting_price: float
    current_price: float
    quantity: int
    status: str
    version: int
    def __init__(self, item_id: _Optional[str] = ..., seller_id: _Optional[str] = ..., title: _Optional[str] = ..., category: _Optional[str] = ..., description: _Optional[str] = ..., starting_price: _Optional[float] = ..., current_price: _Optional[float] = ..., quantity: _Optional[int] = ..., status: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class CreateItemRequest(_message.Message):
    __slots__ = ("item", "primary_store_id")
    ITEM_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_STORE_ID_FIELD_NUMBER: _ClassVar[int]
    item: MarketplaceItem
    primary_store_id: str
    def __init__(self, item: _Optional[_Union[MarketplaceItem, _Mapping]] = ..., primary_store_id: _Optional[str] = ...) -> None: ...

class GetItemRequest(_message.Message):
    __slots__ = ("item_id",)
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    def __init__(self, item_id: _Optional[str] = ...) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ("query", "category")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    query: str
    category: str
    def __init__(self, query: _Optional[str] = ..., category: _Optional[str] = ...) -> None: ...

class SearchResponse(_message.Message):
    __slots__ = ("items",)
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[MarketplaceItem]
    def __init__(self, items: _Optional[_Iterable[_Union[MarketplaceItem, _Mapping]]] = ...) -> None: ...

class UpdateItemRequest(_message.Message):
    __slots__ = ("item_id", "description", "quantity", "status", "expected_version", "primary_store_id")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_VERSION_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_STORE_ID_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    description: str
    quantity: int
    status: str
    expected_version: int
    primary_store_id: str
    def __init__(self, item_id: _Optional[str] = ..., description: _Optional[str] = ..., quantity: _Optional[int] = ..., status: _Optional[str] = ..., expected_version: _Optional[int] = ..., primary_store_id: _Optional[str] = ...) -> None: ...

class BidRequest(_message.Message):
    __slots__ = ("item_id", "bidder_id", "bid_amount", "primary_store_id")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    BIDDER_ID_FIELD_NUMBER: _ClassVar[int]
    BID_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_STORE_ID_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    bidder_id: str
    bid_amount: float
    primary_store_id: str
    def __init__(self, item_id: _Optional[str] = ..., bidder_id: _Optional[str] = ..., bid_amount: _Optional[float] = ..., primary_store_id: _Optional[str] = ...) -> None: ...

class ActionResponse(_message.Message):
    __slots__ = ("success", "message", "new_version")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    NEW_VERSION_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    new_version: int
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., new_version: _Optional[int] = ...) -> None: ...

class AuctionRequest(_message.Message):
    __slots__ = ("item_id", "user_id")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    user_id: str
    def __init__(self, item_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class AuctionEvent(_message.Message):
    __slots__ = ("type", "item_snapshot", "event_description")
    class EventType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        NEW_BID: _ClassVar[AuctionEvent.EventType]
        STATUS_CHANGE: _ClassVar[AuctionEvent.EventType]
        AUCTION_CLOSED: _ClassVar[AuctionEvent.EventType]
    NEW_BID: AuctionEvent.EventType
    STATUS_CHANGE: AuctionEvent.EventType
    AUCTION_CLOSED: AuctionEvent.EventType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ITEM_SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    EVENT_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    type: AuctionEvent.EventType
    item_snapshot: MarketplaceItem
    event_description: str
    def __init__(self, type: _Optional[_Union[AuctionEvent.EventType, str]] = ..., item_snapshot: _Optional[_Union[MarketplaceItem, _Mapping]] = ..., event_description: _Optional[str] = ...) -> None: ...

class ReplicationRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Ping(_message.Message):
    __slots__ = ("node_id", "node_address", "type")
    class NodeType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SERVICE: _ClassVar[Ping.NodeType]
        STORAGE: _ClassVar[Ping.NodeType]
    SERVICE: Ping.NodeType
    STORAGE: Ping.NodeType
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    node_address: str
    type: Ping.NodeType
    def __init__(self, node_id: _Optional[str] = ..., node_address: _Optional[str] = ..., type: _Optional[_Union[Ping.NodeType, str]] = ...) -> None: ...

class Pong(_message.Message):
    __slots__ = ("healthy",)
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    def __init__(self, healthy: bool = ...) -> None: ...

class GetPrimaryStorageRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetPrimaryStorageResponse(_message.Message):
    __slots__ = ("primary_storage_target",)
    PRIMARY_STORAGE_TARGET_FIELD_NUMBER: _ClassVar[int]
    primary_storage_target: str
    def __init__(self, primary_storage_target: _Optional[str] = ...) -> None: ...

class DeleteItemRequest(_message.Message):
    __slots__ = ("item_id", "version")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    version: int
    def __init__(self, item_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...
