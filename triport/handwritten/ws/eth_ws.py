"""Ethereum + Polygon JSON-RPC Pub/Sub WS client (eth_subscribe family).

Python mirror of sdk/typescript/src/handwritten/ws/eth-ws.ts. Polygon
reuses EthWSClient (alias PolyWSClient) — wire shape is identical
eth-base; only the channel URL differs.
"""

from __future__ import annotations

from itertools import count
from typing import Any, Literal, TypedDict

from .base import WSClient, WSClientOptions

EthSubscriptionKind = Literal["newHeads", "logs", "newPendingTransactions", "syncing"]


class EthLogsFilter(TypedDict, total=False):
    address: str | list[str]
    topics: list[str | list[str] | None]


class EthNewPendingTxOpts(TypedDict, total=False):
    includeFullTx: bool


class EthWSClient(WSClient):
    """Ethereum WS pubsub client (eth_subscribe / eth_unsubscribe)."""

    def __init__(self, options: WSClientOptions) -> None:
        super().__init__(options)
        self._next_id = count(1)
        self._subscriptions: set[str] = set()

    async def subscribe(
        self,
        kind: EthSubscriptionKind,
        arg: EthLogsFilter | EthNewPendingTxOpts | None = None,
    ) -> str:
        """eth_subscribe. Returns the hex subscription id."""
        req_id = next(self._next_id)
        params: list[Any] = [kind] if arg is None else [kind, arg]
        await self.send(
            {"jsonrpc": "2.0", "id": req_id, "method": "eth_subscribe", "params": params}
        )
        async for frame in self:
            if not isinstance(frame, dict) or frame.get("id") != req_id:
                continue
            result = frame.get("result")
            if isinstance(result, str):
                self._subscriptions.add(result)
                return result
        raise RuntimeError("WS closed before subscribe ack")

    async def unsubscribe(self, subscription_id: str) -> bool:
        """eth_unsubscribe for a hex subscription id."""
        req_id = next(self._next_id)
        await self.send(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "eth_unsubscribe",
                "params": [subscription_id],
            }
        )
        async for frame in self:
            if not isinstance(frame, dict) or frame.get("id") != req_id:
                continue
            result = frame.get("result")
            if isinstance(result, bool):
                self._subscriptions.discard(subscription_id)
                return result
        return False


class PolyWSClient(EthWSClient):
    """Polygon WS pubsub — wire shape identical to Ethereum (eth-base)."""
