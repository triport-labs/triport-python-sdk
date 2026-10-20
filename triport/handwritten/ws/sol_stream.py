"""Solana Yellowstone-like stream WS client (atomic filter replacement).

Python mirror of sdk/typescript/src/handwritten/ws/sol-stream.ts.
"""

from __future__ import annotations

import time
from typing import Any, Literal, TypedDict

from .base import WSClient, WSClientOptions

SolStreamCommitment = Literal["processed", "confirmed", "finalized"]


class SolStreamAccountFilter(TypedDict, total=False):
    account: list[str]
    owner: list[str]
    filters: list[dict[str, Any]]


class SolStreamTransactionsFilter(TypedDict, total=False):
    vote: bool
    failed: bool
    signature: str
    accountInclude: list[str]
    accountExclude: list[str]
    accountRequired: list[str]


class SolStreamSlotsFilter(TypedDict, total=False):
    filterByCommitment: bool


class SolStreamBlocksFilter(TypedDict, total=False):
    accountInclude: list[str]
    includeTransactions: bool
    includeAccounts: bool
    includeEntries: bool


class SolStreamSubscribeRequest(TypedDict, total=False):
    accounts: dict[str, SolStreamAccountFilter]
    slots: dict[str, SolStreamSlotsFilter]
    transactions: dict[str, SolStreamTransactionsFilter]
    transactionsStatus: dict[str, SolStreamTransactionsFilter]
    blocks: dict[str, SolStreamBlocksFilter]
    blocksMeta: dict[str, dict[str, Any]]
    entry: dict[str, dict[str, Any]]
    commitment: SolStreamCommitment
    accountsDataSlice: list[dict[str, int]]
    ping: dict[str, int]


class SolStreamClient(WSClient):
    """Solana Yellowstone-style stream client."""

    def __init__(self, options: WSClientOptions) -> None:
        super().__init__(options)
        self._active_filters: SolStreamSubscribeRequest | None = None

    async def subscribe(self, request: SolStreamSubscribeRequest) -> None:
        """Subscribe / replace the active filter set (atomic on the server)."""
        self._active_filters = request
        await self.send(request)

    async def ping(self, ping_id: int | None = None) -> None:
        """Send a keepalive Ping (matches Yellowstone proto)."""
        pid = ping_id if ping_id is not None else int(time.time()) & 0x7FFFFFFF
        await self.send({"ping": {"id": pid}})

    def current_filters(self) -> SolStreamSubscribeRequest | None:
        return self._active_filters
