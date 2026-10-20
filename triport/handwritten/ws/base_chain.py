"""Base-chain WS helpers derived from the accepted Base AsyncAPI contracts."""

from __future__ import annotations

import re
from typing import Literal, TypedDict, cast

from triport.endpoints import ws_path

from .base import WSClient, WSClientOptions

BaseSubscriptionKind = Literal[
    "newHeads",
    "logs",
    "newPendingTransactions",
    "newFlashblockTransactions",
    "pendingLogs",
    "newFlashblocks",
]
BaseWSChannel = Literal["pubsub", "feed"]


def base_chain_ws_url(
    channel: BaseWSChannel,
    *,
    base_url: str = "wss://triport.io",
    api_key: str | None = None,
) -> str:
    """Resolve the documented Base Pub/Sub or feed endpoint."""
    path = ws_path("base" if channel == "pubsub" else "base-feed", api_key)
    return base_url.rstrip("/") + path


class BasePubSubClient(WSClient):
    def __init__(
        self,
        *,
        base_url: str = "wss://triport.io",
        api_key: str | None = None,
        bearer_token: str | None = None,
        reconnect: bool = True,
    ) -> None:
        super().__init__(
            WSClientOptions(
                url=base_chain_ws_url(
                    "pubsub", base_url=base_url, api_key=None if bearer_token else api_key
                ),
                bearer_token=bearer_token,
                reconnect=reconnect,
            )
        )
        self._request_id = 1

    async def subscribe(self, kind: BaseSubscriptionKind, options: object | None = None) -> int:
        request_id = self._request_id
        self._request_id += 1
        params = [kind] if options is None else [kind, options]
        await self.send(
            {"jsonrpc": "2.0", "id": request_id, "method": "eth_subscribe", "params": params}
        )
        return request_id

    async def unsubscribe(self, subscription_id: str) -> int:
        request_id = self._request_id
        self._request_id += 1
        await self.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "eth_unsubscribe",
                "params": [subscription_id],
            }
        )
        return request_id


class BaseFlashblockDiff(TypedDict):
    state_root: str
    receipts_root: str
    gas_used: str
    block_hash: str
    transactions: list[str]


class BaseFlashblockEvent(TypedDict, total=False):
    payload_id: str
    index: int
    base: dict[str, object]
    diff: BaseFlashblockDiff
    metadata: object
    provenance: Literal["raw_flashblocks_primary"]
    finality: Literal["preconfirmed"]


class BaseFeedControlEvent(TypedDict, total=False):
    type: Literal["control"]
    control: Literal["gap", "reorg", "degraded", "recovered"]
    provenance: Literal["raw_flashblocks_primary"]
    payload_id: str
    expected_index: int
    received_index: int
    reason: str


BaseFeedEvent = BaseFlashblockEvent | BaseFeedControlEvent


def parse_base_feed_frame(value: object) -> BaseFeedEvent:
    if not isinstance(value, dict):
        raise TypeError("Base feed frame must be an object")
    if value.get("type") == "control":
        if value.get("control") not in {"gap", "reorg", "degraded", "recovered"}:
            raise TypeError("Base feed control lane has an unknown control value")
        if value.get("provenance") != "raw_flashblocks_primary":
            raise TypeError("Base feed control lane lost provenance")
        return value  # type: ignore[return-value]
    payload_id = value.get("payload_id")
    index = value.get("index")
    diff = value.get("diff")
    if not isinstance(payload_id, str) or re.fullmatch(r"0x[0-9a-fA-F]{16}", payload_id) is None:
        raise TypeError("Base feed payload_id is invalid")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise TypeError("Base feed index must be a non-negative integer")
    if not isinstance(diff, dict) or not isinstance(diff.get("transactions"), list):
        raise TypeError("Base feed diff/transactions are invalid")
    if any(
        not isinstance(diff.get(field), str)
        for field in ("state_root", "receipts_root", "gas_used", "block_hash")
    ):
        raise TypeError("Base feed diff fields are invalid")
    if any(
        not isinstance(tx, str) or re.fullmatch(r"0x[0-9a-fA-F]*", tx) is None
        for tx in diff["transactions"]
    ):
        raise TypeError("Base feed transaction bytes must be hex strings")
    if (
        value.get("provenance") != "raw_flashblocks_primary"
        or value.get("finality") != "preconfirmed"
    ):
        raise TypeError("Base feed provenance/finality mismatch")
    return value  # type: ignore[return-value]


class BaseFeedClient(WSClient):
    def __init__(
        self,
        *,
        base_url: str = "wss://triport.io",
        api_key: str | None = None,
        bearer_token: str | None = None,
        reconnect: bool = True,
    ) -> None:
        super().__init__(
            WSClientOptions(
                url=base_chain_ws_url(
                    "feed", base_url=base_url, api_key=None if bearer_token else api_key
                ),
                bearer_token=bearer_token,
                reconnect=reconnect,
            )
        )
        self._payload_id: str | None = None
        self._last_index: int | None = None

    def ingest(self, value: object) -> list[BaseFeedEvent]:
        event = parse_base_feed_frame(value)
        if event.get("type") == "control":
            return [event]
        event = cast(BaseFlashblockEvent, event)
        payload_id = event["payload_id"]
        index = event["index"]
        expected_index = (
            self._last_index + 1
            if self._payload_id == payload_id and self._last_index is not None
            else 0
        )
        emitted: list[BaseFeedEvent] = []
        if index != expected_index:
            emitted.append(
                {
                    "type": "control",
                    "control": "gap",
                    "provenance": "raw_flashblocks_primary",
                    "payload_id": payload_id,
                    "expected_index": expected_index,
                    "received_index": index,
                }
            )
        self._payload_id = payload_id
        self._last_index = index
        emitted.append(event)
        return emitted


BASE_AUCTION_STATUS = {
    "availability": "key_required",
    "wire_enabled": False,
    "minimum_tier": "business",
    "scope": "base:auction",
}
