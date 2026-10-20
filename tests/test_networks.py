"""Reviewed registry coverage and WebSocket authentication contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from triport import CHAINS, WS_CHAINS, Client
from triport.generated import rpc


def test_public_method_manifest_matches_all_generated_registries():
    manifest = json.loads((Path(__file__).parent / "fixtures/methods.json").read_text())
    assert set(manifest) == set(CHAINS)
    for chain, methods in manifest.items():
        registry = getattr(rpc, f"{chain.upper()}_METHOD_TIERS")
        assert set(registry) == {method["name"] for method in methods}
        assert registry
    assert {"sol", "eth", "polygon", "base", "robinhood"} == WS_CHAINS


@pytest.mark.parametrize("channel", ["sol_stream", "watchlist"])
@pytest.mark.parametrize("bearer", [None, "test-bearer"])
async def test_auxiliary_ws_authentication_uses_upgrade_headers(monkeypatch, channel, bearer):
    recorded = []

    class Socket:
        async def close(self, **kwargs):
            pass

    async def connect(url, *, additional_headers):
        recorded.append((url, additional_headers))
        return Socket()

    monkeypatch.setattr("triport.handwritten.ws.base.connect", connect)
    with Client(api_key="test-key", bearer_token=bearer) as client:
        ws = getattr(client.subscribe, channel)()
        await ws.connect()
        await ws.close()
    expected_path = "sol-stream" if channel == "sol_stream" else "sol-watch"
    headers = {"Authorization": "Bearer test-bearer"} if bearer else {"x-token": "test-key"}
    assert recorded == [(f"wss://triport.io/ws/{expected_path}", headers)]
