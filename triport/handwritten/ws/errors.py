"""WS error classes — Python mirror of sdk/typescript/src/handwritten/ws/errors.ts.

One subclass per canonical close code from the public WebSocket error reference
(4001 Unauthorized / 4003 TierInsufficient / 4029 RateLimited /
4030 TrialExpired). Mirrors the runtime envelope at
Public WebSocket error envelope field-
for-field; ``frame_to_error`` dispatches on the runtime
``WSCloseCode.String()`` value-set (unauthorized / forbidden /
rate_limited / trial_expired / unknown default).

``MethodUnknownError`` is shipped for the HTTP/REST surface (JSON-RPC
``-32601`` envelope) — the WS close-frame path never emits ``method_unknown``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

# Canonical WS close codes (the public WebSocket error reference). Declared as module constants so
# the per-subclass default `close_code=` values stay single-sourced with
# WS_CLOSE_CODES below.
WS_UNAUTHORIZED: Final = 4001
WS_FORBIDDEN: Final = 4003
WS_RATE_LIMITED: Final = 4029
WS_TRIAL_EXPIRED: Final = 4030


class TriportError(Exception):
    """Base error for all SDK-surfaced failures."""

    def __init__(
        self,
        message: str,
        *,
        close_code: int | None = None,
        current_tier: str | None = None,
        required_tier: str | None = None,
        category: str | None = None,
    ) -> None:
        super().__init__(message)
        self.close_code = close_code
        self.current_tier = current_tier
        self.required_tier = required_tier
        self.category = category


class UnauthorizedError(TriportError):
    """WS close 4001 — credentials missing/invalid."""

    def __init__(
        self,
        message: str = "unauthorized",
        *,
        close_code: int | None = WS_UNAUTHORIZED,
        current_tier: str | None = None,
        required_tier: str | None = None,
        category: str | None = None,
    ) -> None:
        super().__init__(
            message,
            close_code=close_code,
            current_tier=current_tier,
            required_tier=required_tier,
            category=category,
        )


class TierInsufficientError(TriportError):
    """WS close 4003 — caller's tier is below required. Wire-format error
    code is ``"forbidden"`` (WSCloseCode.String() in
    the public error reference). The frame carries ``method`` (the
    gated RPC) and ``upgrade_url`` (matrix-derived pre-built link to the
    required tier's checkout page).
    """

    def __init__(
        self,
        message: str = "forbidden",
        *,
        method: str | None = None,
        upgrade_url: str | None = None,
        close_code: int | None = WS_FORBIDDEN,
        current_tier: str | None = None,
        required_tier: str | None = None,
        category: str | None = None,
    ) -> None:
        super().__init__(
            message,
            close_code=close_code,
            current_tier=current_tier,
            required_tier=required_tier,
            category=category,
        )
        self.method = method
        self.upgrade_url = upgrade_url


class MethodUnknownError(TriportError):
    """WS close 4003 — method not part of the current product (chain-scoped)."""

    def __init__(
        self,
        message: str = "method_unknown",
        *,
        chain: str | None = None,
        method: str | None = None,
        close_code: int | None = WS_FORBIDDEN,
        current_tier: str | None = None,
        required_tier: str | None = None,
        category: str | None = None,
    ) -> None:
        super().__init__(
            message,
            close_code=close_code,
            current_tier=current_tier,
            required_tier=required_tier,
            category=category,
        )
        self.chain = chain
        self.method = method


class RateLimitedError(TriportError):
    """WS close 4029 — sustained RPS exceeded; retry_after_sec gives cool-down."""

    def __init__(
        self,
        message: str = "rate_limited",
        *,
        retry_after_sec: int | None = None,
        limit_rps: int | None = None,
        burst_capacity: int | None = None,
        close_code: int | None = WS_RATE_LIMITED,
        current_tier: str | None = None,
        required_tier: str | None = None,
        category: str | None = None,
    ) -> None:
        super().__init__(
            message,
            close_code=close_code,
            current_tier=current_tier,
            required_tier=required_tier,
            category=category,
        )
        self.retry_after_sec = retry_after_sec
        self.limit_rps = limit_rps
        self.burst_capacity = burst_capacity


class TrialExpiredError(TriportError):
    """WS close 4030 — free trial period ended. Runtime emits only
    message + upgrade_url on this path
    (public trial-expired envelope); the SDK field
    set mirrors that 1:1."""

    def __init__(
        self,
        message: str = "trial_expired",
        *,
        upgrade_url: str | None = None,
        close_code: int | None = WS_TRIAL_EXPIRED,
        current_tier: str | None = None,
        required_tier: str | None = None,
        category: str | None = None,
    ) -> None:
        super().__init__(
            message,
            close_code=close_code,
            current_tier=current_tier,
            required_tier=required_tier,
            category=category,
        )
        self.upgrade_url = upgrade_url


class SubscriptionExpiredError(TriportError):
    """HTTP 401 / JSON-RPC -32004 — paid subscription expired (post-trial).

    Distinct from TrialExpiredError (free-trial period) and UnauthorizedError
    (no/invalid credentials). Carries upgrade_url for the renewal flow. No
    canonical WS close code — runtime emits this on the REST + JSON-RPC
    surface only (public subscription-expired envelope).
    """

    def __init__(
        self,
        message: str = "subscription_expired",
        *,
        upgrade_url: str | None = None,
        # No canonical WS close code for this class — defaults to None.
        close_code: int | None = None,
        current_tier: str | None = None,
        required_tier: str | None = None,
        category: str | None = None,
    ) -> None:
        super().__init__(
            message,
            close_code=close_code,
            current_tier=current_tier,
            required_tier=required_tier,
            category=category,
        )
        self.upgrade_url = upgrade_url


@dataclass(frozen=True, slots=True)
class WSCloseCodes:
    """Public WebSocket close codes — re-exported for runtime introspection."""

    unauthorized: int = WS_UNAUTHORIZED
    forbidden: int = WS_FORBIDDEN
    rate_limited: int = WS_RATE_LIMITED
    trial_expired: int = WS_TRIAL_EXPIRED


WS_CLOSE_CODES: Final = WSCloseCodes()


def frame_to_error(frame: dict[str, Any], close_code: int | None = None) -> TriportError:
    """Translate a WSErrorFrame (+ optional close code) into a typed error.

    Mirrors ``frameToError`` in sdk/typescript/src/handwritten/ws/errors.ts.
    Dispatch keys are the runtime ``WSCloseCode.String()`` value-set:
    ``unauthorized`` / ``forbidden`` / ``rate_limited`` / ``trial_expired``
    plus an ``unknown`` default — see the public error reference
    lines 174-186. Anything else falls through to a generic TriportError.
    """
    err = frame.get("error")
    msg = frame.get("message") or (err if isinstance(err, str) else "")
    if err == "unauthorized":
        return UnauthorizedError(
            msg,
            current_tier=frame.get("current_tier"),
            category=frame.get("category"),
        )
    if err == "forbidden":
        return TierInsufficientError(
            msg,
            current_tier=frame.get("current_tier"),
            required_tier=frame.get("required_tier"),
            method=frame.get("method"),
            category=frame.get("category"),
            upgrade_url=frame.get("upgrade_url"),
        )
    if err == "rate_limited":
        return RateLimitedError(
            msg,
            current_tier=frame.get("current_tier"),
            category=frame.get("category"),
            retry_after_sec=frame.get("retry_after_sec"),
            limit_rps=frame.get("limit_rps"),
            burst_capacity=frame.get("burst_capacity"),
        )
    if err == "trial_expired":
        return TrialExpiredError(
            msg,
            current_tier=frame.get("current_tier"),
            upgrade_url=frame.get("upgrade_url"),
        )
    if err == "subscription_expired":
        # Defensive: runtime has no WS close code for subscription_expired
        # (HTTP/JSON-RPC only) — dispatch here so a future cross-surface
        # frame doesn't fall through to a generic TriportError.
        return SubscriptionExpiredError(
            msg,
            current_tier=frame.get("current_tier"),
            upgrade_url=frame.get("upgrade_url"),
        )
    return TriportError(
        msg,
        close_code=close_code,
        current_tier=frame.get("current_tier"),
        category=frame.get("category"),
    )
