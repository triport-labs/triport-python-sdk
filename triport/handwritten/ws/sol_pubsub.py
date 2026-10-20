"""Solana JSON-RPC Pub/Sub WS client (9 subscribe methods).

Python mirror of sdk/typescript/src/handwritten/ws/sol-pubsub.ts.
"""

from __future__ import annotations

from itertools import count
from typing import Any, Literal

from .base import WSClient, WSClientOptions

SolSubscribeMethod = Literal[
    "accountSubscribe",
    "signatureSubscribe",
    "logsSubscribe",
    "programSubscribe",
    "slotSubscribe",
    "rootSubscribe",
    "blockSubscribe",
    "voteSubscribe",
    "slotsUpdatesSubscribe",
]


class SolPubsubClient(WSClient):
    """Solana Pub/Sub WS client."""

    def __init__(self, options: WSClientOptions) -> None:
        super().__init__(options)
        self._next_id = count(1)
        self._subscription_methods: dict[int, SolSubscribeMethod] = {}

    async def subscribe(self, method: SolSubscribeMethod, params: list[Any]) -> int:
        """Send <method>Subscribe; return the server-assigned subscription id."""
        req_id = next(self._next_id)
        await self.send({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        async for frame in self:
            if not isinstance(frame, dict) or frame.get("id") != req_id:
                continue
            result = frame.get("result")
            # bool is a subclass of int — exclude it so a `result: true`
            # ack is never mistaken for subscription id 1.
            if isinstance(result, int) and not isinstance(result, bool):
                self._subscription_methods[result] = method
                return result
        raise RuntimeError("WS closed before subscribe ack")

    async def unsubscribe(self, subscription_id: int) -> bool:
        """Send <method>Unsubscribe for a previously-acked subscription id."""
        method = self._subscription_methods.get(subscription_id)
        if method is None:
            return False
        unsub_method = method.replace("Subscribe", "Unsubscribe")
        req_id = next(self._next_id)
        await self.send(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": unsub_method,
                "params": [subscription_id],
            }
        )
        async for frame in self:
            if not isinstance(frame, dict) or frame.get("id") != req_id:
                continue
            result = frame.get("result")
            if isinstance(result, bool):
                self._subscription_methods.pop(subscription_id, None)
                return result
        return False
