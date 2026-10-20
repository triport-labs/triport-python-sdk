"""tests/smoke_test.py вЂ” pip-install smoke + barrel-shape sanity.

Run: cd sdk/python && pytest tests/

Two scenarios:
    1. Public API surface (barrel) imports cleanly; expected names exist + are of the expected kind.
    2. (Skipped here; CI runs a separate `pip install -e .` + import-from-fresh-venv probe.)
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path


def test_sdk_version_is_pep440() -> None:
    from triport import SDK_VERSION

    assert re.match(r"^\d+\.\d+\.\d+", SDK_VERSION)


def test_client_constructible_without_network() -> None:
    from triport import Client

    c = Client(api_key="test")
    assert c.sol is not None
    assert c.eth is not None
    assert c.polygon is not None
    assert c.tron is not None
    assert c.bsc is not None
    assert c.stellar is not None
    assert c.ton is not None
    assert c.subscribe is not None
    assert not hasattr(c.subscribe, "bsc")
    assert not hasattr(c.subscribe, "stellar")
    assert not hasattr(c.subscribe, "ton")
    c.close()


def test_base_clients_export_without_network() -> None:
    from triport import BaseFeedClient, BasePubSubClient, BaseRpcClient

    rpc = BaseRpcClient()
    assert rpc.url == "https://triport.io/rpc/base"
    rpc.close()
    assert BasePubSubClient() is not None
    assert BaseFeedClient() is not None


def test_async_client_constructible() -> None:
    from triport import AsyncClient

    c = AsyncClient(api_key="test")
    assert c.sol is not None
    assert c.eth is not None
    assert c.polygon is not None
    assert c.tron is not None
    assert c.bsc is not None
    assert c.ton is not None
    # aclose deferred to async test below.


def test_async_client_aclose() -> None:
    from triport import AsyncClient

    async def run() -> None:
        async with AsyncClient(api_key="test") as c:
            assert c.sol is not None

    asyncio.run(run())


def test_ws_close_codes_canonical() -> None:
    from triport import WS_CLOSE_CODES

    assert WS_CLOSE_CODES.unauthorized == 4001
    assert WS_CLOSE_CODES.forbidden == 4003
    assert WS_CLOSE_CODES.rate_limited == 4029
    assert WS_CLOSE_CODES.trial_expired == 4030


def test_error_subclasses_set_close_code() -> None:
    from triport import RateLimitedError, TierInsufficientError

    err = TierInsufficientError("msg", required_tier="pro")
    assert err.close_code == 4003
    assert err.required_tier == "pro"

    rl = RateLimitedError("msg", retry_after_sec=1)
    assert rl.close_code == 4029
    assert rl.retry_after_sec == 1


def test_method_tiers_cover_spec_counts() -> None:
    from triport.generated.rpc import (
        BASE_METHOD_TIERS,
        BSC_METHOD_TIERS,
        ETH_METHOD_TIERS,
        POLYGON_METHOD_TIERS,
        ROBINHOOD_METHOD_TIERS,
        SOL_METHOD_TIERS,
        STELLAR_METHOD_TIERS,
        TON_METHOD_TIERS,
        TRON_METHOD_TIERS,
    )

    assert len(SOL_METHOD_TIERS) >= 50
    assert len(ETH_METHOD_TIERS) >= 48
    assert len(POLYGON_METHOD_TIERS) >= 41
    assert len(TRON_METHOD_TIERS) == 12
    assert len(BSC_METHOD_TIERS) == 29
    assert len(BASE_METHOD_TIERS) == 61
    robinhood_spec = json.loads(
        (Path(__file__).parent / "fixtures/methods.json").read_text(encoding="utf-8")
    )
    assert set(ROBINHOOD_METHOD_TIERS) == {method["name"] for method in robinhood_spec["robinhood"]}
    assert len(STELLAR_METHOD_TIERS) == 10
    assert len(TON_METHOD_TIERS) == 13


def test_operations_cover_openapi_counts() -> None:
    from triport.generated.rest import (
        ETH_OPERATIONS,
        POLYGON_OPERATIONS,
        SOL_OPERATIONS,
        STELLAR_OPERATIONS,
        TRON_OPERATIONS,
    )

    assert len(SOL_OPERATIONS) >= 20
    assert len(ETH_OPERATIONS) >= 15
    assert len(POLYGON_OPERATIONS) >= 14
    assert len(TRON_OPERATIONS) == 12
    assert len(STELLAR_OPERATIONS) == 11


def test_ws_clients_constructible() -> None:
    from triport import Client

    c = Client(api_key="test")
    assert c.subscribe.sol() is not None
    assert c.subscribe.sol_stream() is not None
    assert c.subscribe.eth() is not None
    assert c.subscribe.polygon() is not None
    assert c.subscribe.watchlist() is not None
    c.close()
