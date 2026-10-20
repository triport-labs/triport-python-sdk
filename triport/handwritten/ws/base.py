"""Async WSClient base — shared by all 5 channels.

Python mirror of sdk/typescript/src/handwritten/ws/base.ts.

Uses `websockets` (PEP 525 native asyncio). Exposes connect / send /
close + an async-iterable for received frames; WSErrorFrames are
translated into typed TriportError subclasses transparently.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from websockets.asyncio.client import ClientConnection, connect

from .errors import TriportError, frame_to_error


@dataclass(frozen=True, slots=True)
class WSClientOptions:
    url: str = field(repr=False)
    api_key: str | None = field(default=None, repr=False)
    bearer_token: str | None = field(default=None, repr=False)
    reconnect: bool = True
    max_reconnect_delay_ms: int = 30_000
    initial_reconnect_delay_ms: int = 500


class WSClient:
    """Base async WebSocket client.

    Subclasses add channel-specific subscribe/unsubscribe helpers.
    """

    def __init__(self, options: WSClientOptions) -> None:
        self.opts = options
        self._socket: ClientConnection | None = None
        self._closed = False
        self._reconnect_attempt = 0

    async def connect(self) -> None:
        """Open the WS connection. Re-callable on disconnect."""
        self._closed = False
        url = self._build_url()
        headers: dict[str, str] = {}
        if self.opts.bearer_token:
            headers["Authorization"] = f"Bearer {self.opts.bearer_token}"
        elif self.opts.api_key:
            headers["x-token"] = self.opts.api_key
        self._socket = await connect(url, additional_headers=headers)

    def _build_url(self) -> str:
        return self.opts.url

    async def send(self, payload: object) -> None:
        """Send a frame. `payload` is either a pre-serialized str or any
        JSON-serializable value (typed `object`, not `Any`, so callers do
        not silently lose type-checking on the value they pass)."""
        if self._socket is None:
            raise TriportError("WS not open — call connect() first")
        data = payload if isinstance(payload, str) else json.dumps(payload, default=str)
        await self._socket.send(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self._closed = True
        if self._socket is not None:
            await self._socket.close(code=code, reason=reason)

    async def __aiter__(self) -> AsyncIterator[Any]:
        """Async iterator over received frames; WSErrorFrames raise typed errors.

        Yields decoded-JSON values, whose shape is channel-specific and
        server-defined; `Any` is the honest element type here.
        """
        if self._socket is None:
            raise TriportError("WS not open — call connect() first")
        async for raw in self._socket:
            text = raw if isinstance(raw, str) else raw.decode("utf-8")
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise TriportError(f"malformed WS frame: {exc}") from exc
            if isinstance(parsed, dict) and "error" in parsed and "message" in parsed:
                raise frame_to_error(parsed)
            yield parsed

    async def reconnect_loop(self) -> None:
        """Optional helper: repeatedly connect() with exponential backoff
        until close() is called."""
        if not self.opts.reconnect:
            return
        while not self._closed:
            try:
                await self.connect()
                # Caller consumes frames via `async for ... in client`. Loop
                # is here only to schedule reconnects after disconnects.
                return
            except OSError:
                delay = min(
                    self.opts.initial_reconnect_delay_ms * (2**self._reconnect_attempt),
                    self.opts.max_reconnect_delay_ms,
                )
                self._reconnect_attempt += 1
                await asyncio.sleep(delay / 1000)
