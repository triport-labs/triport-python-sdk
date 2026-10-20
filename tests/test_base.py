from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import httpx
import pytest

from scripts.gen_rpc import _python_literal, _wire_type
from triport import (
    BASE_AUCTION_STATUS,
    BASE_METHOD_TIERS,
    BaseFeedClient,
    BasePubSubClient,
    BaseRpcClient,
    base_chain_ws_url,
    parse_base_feed_frame,
)
from triport.generated.rpc.base import BaseRpcProtocolError
from triport.generated.rpc.base_wire import BaseParams, BaseResults


def flashblock(index: int) -> dict[str, object]:
    return {
        "payload_id": "0x0123456789abcdef",
        "index": index,
        "diff": {
            "state_root": "0x1",
            "receipts_root": "0x2",
            "gas_used": "0x3",
            "block_hash": "0x4",
            "transactions": ["0x7e00"],
        },
        "provenance": "raw_flashblocks_primary",
        "finality": "preconfirmed",
    }


def test_python_generator_translates_nested_json_literals() -> None:
    value = {
        "default": False,
        "enum": [True, None],
        "examples": [{"enabled": False, "fallback": None}],
    }
    rendered = _python_literal(value)
    assert ast.literal_eval(rendered) == value
    assert re.search(r"\b(?:false|true|null)\b", rendered) is None
    assert _wire_type({"enum": [False, True, None]}) == "Literal[False, True, None]"


def test_base_method_and_wire_sets_match_openrpc() -> None:
    spec = json.loads((Path(__file__).parent / "fixtures/methods.json").read_text(encoding="utf-8"))
    methods = {method["name"] for method in spec["base"]}
    assert len(methods) == 61
    assert set(BASE_METHOD_TIERS) == methods
    assert set(BaseParams.__annotations__) == methods
    assert set(BaseResults.__annotations__) == methods


def test_sync_result_is_receipt_not_hash() -> None:
    assert (
        BaseResults.__annotations__["eth_sendRawTransactionSync"]
        != BaseResults.__annotations__["eth_sendRawTransaction"]
    )


def test_base_rpc_path_and_no_write_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.path == "/r/token-variable-value/rpc/base"
        return httpx.Response(503, request=request)

    with (
        BaseRpcClient(
            api_key="token-variable-value", transport=httpx.MockTransport(handler)
        ) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        client.call("eth_sendRawTransaction", ["0x00"])
    assert calls == 1


def _base_client_for_response(
    envelope: object,
    *,
    api_key: str | None = None,
    bearer_token: str | None = None,
) -> BaseRpcClient:
    raw_response = envelope if isinstance(envelope, str) else json.dumps(envelope)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=raw_response, request=request)

    return BaseRpcClient(
        api_key=api_key,
        bearer_token=bearer_token,
        transport=httpx.MockTransport(handler),
    )


def test_base_rpc_accepts_valid_result_envelope() -> None:
    with _base_client_for_response({"jsonrpc": "2.0", "id": 1, "result": "0x2105"}) as client:
        assert client.call("eth_chainId", []) == "0x2105"


@pytest.mark.parametrize(
    ("reason", "envelope"),
    [
        ("invalid_envelope", []),
        ("jsonrpc_version", {"jsonrpc": "1.0", "id": 1, "result": "0x2105"}),
        ("id_mismatch", {"jsonrpc": "2.0", "id": "1", "result": "0x2105"}),
        ("missing_result", {"jsonrpc": "2.0", "id": 1}),
        (
            "result_and_error",
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": "0x2105",
                "error": {"code": -1, "message": "bad"},
            },
        ),
        ("malformed_error", {"jsonrpc": "2.0", "id": 1, "error": {"message": "missing code"}}),
    ],
)
def test_base_rpc_rejects_malformed_envelope(reason: str, envelope: object) -> None:
    with (
        _base_client_for_response(envelope) as client,
        pytest.raises(BaseRpcProtocolError) as exc_info,
    ):
        client.call("eth_chainId", [])
    assert exc_info.value.reason == reason


def test_base_rpc_rejects_empty_object_before_missing_result() -> None:
    with (
        _base_client_for_response({}) as client,
        pytest.raises(BaseRpcProtocolError) as exc_info,
    ):
        client.call("eth_chainId", [])
    assert exc_info.value.reason == "jsonrpc_version"


def test_base_rpc_protocol_fragment_is_bounded_and_redacts_tokens() -> None:
    token = "token-must-not-leak"
    with (
        _base_client_for_response(
            json.dumps(f"{token}:{'é' * 600}"),
            api_key=token,
            bearer_token=token,
        ) as client,
        pytest.raises(BaseRpcProtocolError) as exc_info,
    ):
        client.call("eth_chainId", [])
    assert exc_info.value.reason == "invalid_envelope"
    assert token not in exc_info.value.raw_response
    assert len(exc_info.value.raw_response.encode("utf-8")) <= 512


def test_base_rpc_preserves_valid_error_code_and_data() -> None:
    with (
        _base_client_for_response(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32000,
                    "message": "provider rejected request",
                    "data": {"retryable": False},
                },
            }
        ) as client,
        pytest.raises(RuntimeError, match="provider rejected request") as exc_info,
    ):
        client.call("eth_chainId", [])
    assert not isinstance(exc_info.value, BaseRpcProtocolError)
    assert exc_info.value.code == -32000
    assert exc_info.value.data == {"retryable": False}


def test_base_ws_paths_provenance_gap_and_auction_status() -> None:
    assert base_chain_ws_url("pubsub", api_key="token") == "wss://triport.io/ws/base/token"
    assert base_chain_ws_url("feed", api_key="token") == "wss://triport.io/ws/base-feed/token"
    assert isinstance(BasePubSubClient(api_key="token"), BasePubSubClient)
    assert parse_base_feed_frame(flashblock(0))["finality"] == "preconfirmed"
    with pytest.raises(TypeError, match="provenance"):
        parse_base_feed_frame({**flashblock(0), "provenance": "provider-direct"})
    first_gap = BaseFeedClient().ingest(flashblock(2))
    assert first_gap[0]["control"] == "gap"
    assert first_gap[0]["expected_index"] == 0
    feed = BaseFeedClient()
    assert len(feed.ingest(flashblock(0))) == 1
    events = feed.ingest(flashblock(2))
    assert events[0] == {
        "type": "control",
        "control": "gap",
        "provenance": "raw_flashblocks_primary",
        "payload_id": "0x0123456789abcdef",
        "expected_index": 1,
        "received_index": 2,
    }
    assert BASE_AUCTION_STATUS["availability"] == "key_required"
    assert BASE_AUCTION_STATUS["wire_enabled"] is False
