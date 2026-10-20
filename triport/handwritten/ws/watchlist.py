"""Triport watchlist push WS client.

Python mirror of sdk/typescript/src/handwritten/ws/watchlist.ts.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from .base import WSClient, WSClientOptions

WatchChangeKind = Literal[
    "account_data", "lamports", "owner_change", "executable_change", "rent_epoch"
]


class WatchSubscribeFrame(TypedDict):
    action: Literal["watchlist.subscribe"]
    entries: list[str]


class WatchEventFrame(TypedDict, total=False):
    action: Literal["watchlist.event"]
    entry_id: str
    pubkey: str
    slot: int
    change_kind: WatchChangeKind
    before: dict[str, Any]
    after: dict[str, Any]
    signature: str | None
    timestamp: str


class WatchEntryRevokedFrame(TypedDict):
    action: Literal["watchlist.revoked"]
    entry_id: str
    reason: Literal["deleted", "tier_downgrade", "tenant_suspended"]


class WatchHeartbeatFrame(TypedDict, total=False):
    action: Literal["watchlist.heartbeat"]
    ts: str
    active_entries: int


class WatchlistClient(WSClient):
    """Triport watchlist push channel client."""

    def __init__(self, options: WSClientOptions) -> None:
        super().__init__(options)
        self._active_entries: list[str] = []

    async def subscribe(self, entries: list[str]) -> None:
        """Subscribe to a set of watchlist entry-ids (or ['*'] for all tenant-owned)."""
        if not entries:
            raise ValueError("WatchlistClient.subscribe requires at least one entry id")
        self._active_entries = list(entries)
        frame: WatchSubscribeFrame = {"action": "watchlist.subscribe", "entries": entries}
        await self.send(frame)

    def current_entries(self) -> tuple[str, ...]:
        return tuple(self._active_entries)
