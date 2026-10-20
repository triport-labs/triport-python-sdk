"""Transport-level regression checks for every public network and URL template."""

from __future__ import annotations

import json

import httpx
import pytest

from triport import CHAINS, AsyncClient, Client, ClientOptions, Endpoints
from triport.handwritten.ws.base import WSClientOptions

# Independent expected values; never compute expected paths with the production builder.
RPC_CASES = (
    ("sol", "getSlot", [], "/r/test-key/sol"),
    ("eth", "eth_chainId", [], "/r/test-key/eth"),
    ("polygon", "eth_chainId", [], "/r/test-key/polygon"),
    ("bsc", "eth_chainId", [], "/r/test-key/bsc"),
    ("base", "eth_chainId", [], "/r/test-key/rpc/base"),
    ("tron", "eth_chainId", [], "/r/test-key/tron"),
    ("robinhood", "eth_chainId", [], "/r/test-key/robinhood"),
    ("stellar", "getHealth", {}, "/r/test-key/stellar"),
    ("ton", "getMasterchainInfo", {}, "/r/test-key/ton"),
)


def handler_for(recorded: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        body = json.loads(request.content) if request.content else {}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body.get("id"), "result": 42})

    return handler


@pytest.mark.parametrize(("chain", "method", "params", "path"), RPC_CASES)
def test_sync_rpc_routes_all_nine_networks(chain, method, params, path):
    recorded = []
    with Client(api_key="test-key", transport=httpx.MockTransport(handler_for(recorded))) as c:
        ns = getattr(c, chain)
        result = ns.call(method, **params) if chain == "ton" else ns.call(method, params)
        assert result == 42
        assert ns.tier(method) is not None
    assert len(recorded) == 1
    assert str(recorded[0].url) == "https://triport.io" + path
    assert json.loads(recorded[0].content) == {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }


@pytest.mark.parametrize(("chain", "method", "params", "path"), RPC_CASES)
async def test_async_rpc_routes_all_nine_networks(chain, method, params, path):
    recorded = []
    async with AsyncClient(
        api_key="test-key", transport=httpx.MockTransport(handler_for(recorded))
    ) as c:
        ns = getattr(c, chain)
        result = (
            await ns.call(method, **params) if chain == "ton" else await ns.call(method, params)
        )
        assert result == 42
        assert ns.tier(method) is not None
    assert len(recorded) == 1
    assert str(recorded[0].url) == "https://triport.io" + path
    assert json.loads(recorded[0].content)["params"] == params


@pytest.mark.parametrize(
    ("chain", "path"),
    [
        ("sol", "/sol"),
        ("eth", "/eth"),
        ("polygon", "/polygon"),
        ("bsc", "/rpc/bsc"),
        ("base", "/rpc/base"),
        ("tron", "/rpc/tron"),
        ("robinhood", "/rpc/robinhood"),
        ("stellar", "/rpc/stellar"),
        ("ton", "/rpc/ton"),
    ],
)
def test_bearer_auth_wins_over_api_key(chain, path):
    recorded = []
    with Client(
        api_key="unused",
        bearer_token="test-bearer",
        transport=httpx.MockTransport(handler_for(recorded)),
    ) as c:
        ns = getattr(c, chain)
        if chain == "ton":
            ns.call("getMasterchainInfo")
        else:
            ns.call("getHealth" if chain == "stellar" else "eth_chainId", [])
    assert str(recorded[0].url) == "https://triport.io" + path
    assert recorded[0].headers["Authorization"] == "Bearer test-bearer"
    assert "X-API-Key" not in recorded[0].headers


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        ("sol", "sol"),
        ("eth", "eth"),
        ("polygon", "polygon"),
        ("base", "base"),
        ("robinhood", "robinhood"),
        ("sol_stream", "sol-stream"),
        ("watchlist", "sol-watch"),
    ],
)
def test_ws_factories_use_keyed_public_routes(factory, expected):
    with Client(api_key="test-key") as c:
        ws = getattr(c.subscribe, factory)()
        if factory == "base":
            assert ws._build_url() == "wss://triport.io/ws/base/test-key"
        elif factory in {"sol_stream", "watchlist"}:
            assert ws._build_url() == f"wss://triport.io/ws/{expected}"
            assert ws.opts.api_key == "test-key"
        else:
            assert ws._build_url() == f"wss://triport.io/ws/r/test-key/{expected}"
        assert "api-key=" not in ws._build_url()


@pytest.mark.parametrize("chain", ["bsc", "tron", "stellar", "ton"])
def test_unsupported_websockets_are_explicit(chain):
    with pytest.raises(ValueError, match="No documented WebSocket"):
        Endpoints("test-key").wss(chain)


def test_endpoint_configuration_and_credential_encoding():
    endpoints = Endpoints("key/with +?#", "https://triport.io/", "wss://triport.io/")
    assert endpoints.https("polygon") == "https://triport.io/r/key%2Fwith%20%2B%3F%23/polygon"
    assert endpoints.wss("polygon") == "wss://triport.io/ws/r/key%2Fwith%20%2B%3F%23/polygon"
    assert endpoints.grpc_target == "grpc.triport.io:443"
    assert endpoints.grpc_metadata == (("x-token", "key/with +?#"),)
    assert "key/with" not in repr(endpoints)
    assert "test-secret" not in repr(ClientOptions(api_key="test-secret"))
    assert "test-secret" not in repr(WSClientOptions(url="wss://triport.io/test-secret"))
    with pytest.raises(ValueError, match="requires an API key"):
        _ = Endpoints().grpc_metadata
    assert set(CHAINS) == {case[0] for case in RPC_CASES}


def test_tron_wallet_and_stellar_horizon_routes():
    recorded = []
    with Client(api_key="test-key", transport=httpx.MockTransport(handler_for(recorded))) as c:
        c.call_tron_wallet("tronWalletGetAccount", {"address": "41" + "0" * 40})
        c.stellar.horizon.call(
            "stellarHorizonListAccountPayments",
            path={"account": "GABC"},
            query={"cursor": "now", "limit": 200, "order": "desc"},
        )
        with pytest.raises(ValueError, match="1 to 200"):
            c.stellar.horizon.call("stellarHorizonListLedgers", query={"limit": 500})
    assert recorded[0].url.path == "/r/test-key/tron/wallet/getaccount"
    assert str(recorded[1].url) == (
        "https://triport.io/r/test-key/stellar/horizon/accounts/GABC/payments"
        "?cursor=now&limit=200&order=desc"
    )


async def test_async_tron_wallet_and_stellar_horizon_routes():
    recorded = []
    async with AsyncClient(
        api_key="test-key", transport=httpx.MockTransport(handler_for(recorded))
    ) as c:
        await c.call_tron_wallet("tronWalletGetAccount", {"address": "41" + "0" * 40})
        await c.stellar.horizon.call("stellarHorizonRoot")
    assert recorded[0].url.path == "/r/test-key/tron/wallet/getaccount"
    assert recorded[1].url.path == "/r/test-key/stellar/horizon"
