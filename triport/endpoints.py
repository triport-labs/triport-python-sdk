"""Public endpoint templates. Resolved URLs contain credentials; do not log them."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import quote

Chain = Literal["sol", "eth", "polygon", "bsc", "base", "tron", "robinhood", "stellar", "ton"]
CHAINS: tuple[Chain, ...] = (
    "sol",
    "eth",
    "polygon",
    "bsc",
    "base",
    "tron",
    "robinhood",
    "stellar",
    "ton",
)
WS_CHAINS = frozenset({"sol", "eth", "polygon", "base", "robinhood"})
GRPC_TARGET = "grpc.triport.io:443"


def rpc_path(chain: Chain, api_key: str | None = None) -> str:
    """Keyed HTTPS route, or the documented header-auth route without a key."""
    if chain not in CHAINS:
        raise ValueError(f"Unknown chain: {chain}")
    if api_key:
        suffix = "rpc/base" if chain == "base" else chain
        return f"/r/{quote(api_key, safe='')}/{suffix}"
    return f"/{chain}" if chain in {"sol", "eth", "polygon"} else f"/rpc/{chain}"


def ws_path(channel: str, api_key: str | None = None) -> str:
    """Resolve documented Pub/Sub and auxiliary WebSocket channels."""
    if channel not in WS_CHAINS | {"sol-stream", "sol-watch", "base-feed", "robinhood-feed"}:
        raise ValueError(f"No documented WebSocket endpoint for {channel}")
    if channel in {"sol-stream", "sol-watch"}:
        return f"/ws/{channel}"
    if api_key:
        encoded = quote(api_key, safe="")
        if channel in {"base", "base-feed"}:
            return f"/ws/{channel}/{encoded}"
        return f"/ws/r/{encoded}/{channel}"
    mount = "poly" if channel == "polygon" else channel
    return f"/ws/{mount}"


@dataclass(frozen=True, slots=True)
class Endpoints:
    """Endpoint configuration for HTTP, WebSocket and Solana Yellowstone clients."""

    api_key: str | None = field(default=None, repr=False)
    https_base: str = "https://triport.io"
    wss_base: str = "wss://triport.io"

    def https(self, chain: Chain) -> str:
        return self.https_base.rstrip("/") + rpc_path(chain, self.api_key)

    def wss(self, chain: Chain) -> str:
        return self.wss_base.rstrip("/") + ws_path(chain, self.api_key)

    @property
    def grpc_target(self) -> str:
        return GRPC_TARGET

    @property
    def grpc_metadata(self) -> tuple[tuple[str, str], ...]:
        if not self.api_key:
            raise ValueError("Solana gRPC requires an API key")
        return (("x-token", self.api_key),)
