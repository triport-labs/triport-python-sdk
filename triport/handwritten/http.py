"""HTTP / JSON-RPC error mappers — HTTP-side analog of ws.errors.frame_to_error.

Source of truth:
    Public JSON-RPC error codes  (JSON-RPC code constants)
    Public JSON-RPC error envelope (JSON-RPC rate-limited envelope shape)
    Public error tags   (ErrCode* string constants)
    Public REST error envelope   (REST rate-limited body shape)

Mapping (JSON-RPC code -> typed error class):
    -32001 trial_expired        -> TrialExpiredError
    -32002 tier_insufficient    -> TierInsufficientError
    -32003 rate_limited         -> RateLimitedError
    -32004 subscription_expired -> SubscriptionExpiredError
    -32005 unauthorized         -> UnauthorizedError
    -32601 method_unknown       -> MethodUnknownError
    other                       -> None  (caller can fall back to RuntimeError or pass-through)

HTTP-status mapping (no JSON-RPC envelope available — pure REST path):
    401 -> UnauthorizedError
    403 -> TierInsufficientError  (most common 403 cause on tier surface)
    429 -> RateLimitedError       (body parsed for current_tier / limit_rps /
                                   burst_capacity / retry_after_sec)

Both mappers extract the same body fields the runtime emits (current_tier,
required_tier, method, category, upgrade_url, limit_rps, burst_capacity,
retry_after_sec). Missing fields stay None. Never throws on malformed input.
"""

from __future__ import annotations

from typing import Any

import httpx

from .ws.errors import (
    MethodUnknownError,
    RateLimitedError,
    SubscriptionExpiredError,
    TierInsufficientError,
    TrialExpiredError,
    TriportError,
    UnauthorizedError,
)


def _safe_int(v: object) -> int | None:
    """Narrow an arbitrary decoded-JSON value to int. `object` (not `Any`)
    so callers get a real type error when they pass something unnarrowed."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    return None


def _safe_str(v: object) -> str | None:
    """Narrow an arbitrary decoded-JSON value to a non-empty str."""
    return v if isinstance(v, str) and v else None


def jsonrpc_envelope_to_error(envelope: dict[str, Any]) -> TriportError | None:
    """Map a JSON-RPC error envelope to a typed TriportError subclass.

    Returns None when the envelope is not in error shape OR the code is
    unrecognised (caller can then surface a generic RuntimeError).
    """
    err = envelope.get("error")
    if not isinstance(err, dict):
        return None
    code = _safe_int(err.get("code"))
    msg = _safe_str(err.get("message")) or "rpc error"
    # Bind once then narrow — calling err.get("data") twice let mypy widen
    # the second result back to `... | None` (union-attr on data.get below).
    raw_data = err.get("data")
    data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
    if code == -32001:
        return TrialExpiredError(
            msg,
            current_tier=_safe_str(data.get("current_tier")),
            upgrade_url=_safe_str(data.get("upgrade_url")),
        )
    if code == -32002:
        return TierInsufficientError(
            msg,
            current_tier=_safe_str(data.get("current_tier")),
            required_tier=_safe_str(data.get("required_tier")),
            method=_safe_str(data.get("method")),
            category=_safe_str(data.get("category")),
            upgrade_url=_safe_str(data.get("upgrade_url")),
        )
    if code == -32003:
        return RateLimitedError(
            msg,
            current_tier=_safe_str(data.get("current_tier")),
            category=_safe_str(data.get("category")),
            retry_after_sec=_safe_int(data.get("retry_after_sec")),
            limit_rps=_safe_int(data.get("limit_rps")),
            burst_capacity=_safe_int(data.get("burst_capacity")),
        )
    if code == -32004:
        return SubscriptionExpiredError(
            msg,
            current_tier=_safe_str(data.get("current_tier")),
            upgrade_url=_safe_str(data.get("upgrade_url")),
        )
    if code == -32005:
        return UnauthorizedError(msg)
    if code == -32601:
        return MethodUnknownError(
            msg,
            chain=_safe_str(data.get("chain")),
            method=_safe_str(data.get("method")),
        )
    return None


def http_response_to_error(resp: httpx.Response) -> TriportError | None:
    """Map a 4xx httpx.Response to a typed TriportError subclass.

    Returns None for non-error responses (2xx/3xx) and 5xx (caller may
    want retry semantics handled separately). On 401/403/429 the body is
    parsed best-effort to populate matrix-derived fields; an unparseable
    body still yields a typed error with status-derived class.
    """
    status = resp.status_code
    if status < 400 or status >= 500:
        return None
    try:
        body: dict[str, Any] = resp.json() if resp.content else {}
    except Exception:
        body = {}
    # JSON-RPC envelope sometimes rides on a 4xx body — try that mapping
    # first since it preserves the most fidelity (code, data fields).
    body_err = body.get("error")
    if "jsonrpc" in body or (isinstance(body_err, dict) and "code" in body_err):
        rpc = jsonrpc_envelope_to_error(body)
        if rpc is not None:
            return rpc
    # Pure REST envelope (rateLimitedBody / unauthorizedBody / tierInsufficientBody shape):
    msg = _safe_str(body.get("message")) or _safe_str(body.get("error")) or f"HTTP {status}"
    if status == 401:
        return UnauthorizedError(
            msg,
            current_tier=_safe_str(body.get("current_tier")),
            category=_safe_str(body.get("category")),
        )
    if status == 403:
        return TierInsufficientError(
            msg,
            current_tier=_safe_str(body.get("current_tier")),
            required_tier=_safe_str(body.get("required_tier")),
            method=_safe_str(body.get("method")),
            category=_safe_str(body.get("category")),
            upgrade_url=_safe_str(body.get("upgrade_url")),
        )
    if status == 429:
        # Retry-After header takes precedence when body lacks retry_after_sec.
        retry_hdr = resp.headers.get("Retry-After", "")
        retry_from_hdr = int(retry_hdr) if retry_hdr.isdigit() else None
        return RateLimitedError(
            msg,
            current_tier=_safe_str(body.get("current_tier")),
            category=_safe_str(body.get("category")),
            retry_after_sec=_safe_int(body.get("retry_after_sec")) or retry_from_hdr,
            limit_rps=_safe_int(body.get("limit_rps")),
            burst_capacity=_safe_int(body.get("burst_capacity")),
        )
    # Other 4xx — fall back to generic.
    return TriportError(msg)


__all__ = ["http_response_to_error", "jsonrpc_envelope_to_error"]
