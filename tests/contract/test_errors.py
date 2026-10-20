"""Offline public HTTP and JSON-RPC error envelope contracts."""

from __future__ import annotations

import httpx

from triport import RateLimitedError, TierInsufficientError
from triport.handwritten.http import (
    http_response_to_error,
    jsonrpc_envelope_to_error,
)


def test_jsonrpc_rate_limited_envelope_maps_offline() -> None:
    err = jsonrpc_envelope_to_error(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32003,
                "message": "rate_limited",
                "data": {
                    "current_tier": "free",
                    "category": "standard",
                    "retry_after_sec": 3,
                    "limit_rps": 10,
                    "burst_capacity": 20,
                },
            },
        }
    )
    assert isinstance(err, RateLimitedError)
    assert err.retry_after_sec == 3
    assert err.limit_rps == 10
    assert err.burst_capacity == 20
    assert err.current_tier == "free"


def test_jsonrpc_tier_insufficient_envelope_maps_offline() -> None:
    err = jsonrpc_envelope_to_error(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32002,
                "message": "tier_insufficient",
                "data": {
                    "current_tier": "free",
                    "required_tier": "pro",
                    "method": "eth_sendBundle",
                    "upgrade_url": "https://triport.io/app/pricing",
                },
            },
        }
    )
    assert isinstance(err, TierInsufficientError)
    assert err.current_tier == "free"
    assert err.required_tier == "pro"
    assert err.method == "eth_sendBundle"


def test_http_429_maps_to_rate_limited_with_retry_after_header() -> None:
    resp = httpx.Response(
        429,
        headers={"Retry-After": "7"},
        json={"message": "rate_limited", "current_tier": "free", "limit_rps": 10},
        request=httpx.Request("POST", "https://example.test/rpc/sol"),
    )
    err = http_response_to_error(resp)
    assert isinstance(err, RateLimitedError)
    # Body carries no retry_after_sec, so the header value must win.
    assert err.retry_after_sec == 7
    assert err.limit_rps == 10


def test_http_403_maps_to_tier_insufficient() -> None:
    resp = httpx.Response(
        403,
        json={
            "message": "tier_insufficient",
            "current_tier": "free",
            "required_tier": "business",
            "method": "getProgramAccounts",
        },
        request=httpx.Request("POST", "https://example.test/rpc/sol"),
    )
    err = http_response_to_error(resp)
    assert isinstance(err, TierInsufficientError)
    assert err.required_tier == "business"
    assert err.close_code == 4003
