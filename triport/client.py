"""Synchronous and asynchronous Triport JSON-RPC, REST and WebSocket entry points."""

from __future__ import annotations

import warnings
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from itertools import count
from types import TracebackType
from typing import Any, cast

import httpx

from .endpoints import Chain, Endpoints, rpc_path, ws_path
from .generated.rest import (
    STELLAR_OPERATIONS,
    TRON_OPERATIONS,
    StellarHALResponse,
    StellarHorizonPathParams,
    StellarHorizonQuery,
    StellarOperationName,
    TronOperationName,
)
from .generated.rpc import (
    BASE_METHOD_TIERS,
    BSC_METHOD_TIERS,
    ETH_METHOD_TIERS,
    POLYGON_METHOD_TIERS,
    ROBINHOOD_METHOD_TIERS,
    SOL_METHOD_TIERS,
    STELLAR_METHOD_TIERS,
    TON_METHOD_TIERS,
    TRON_METHOD_TIERS,
    BaseRpcClient,
    MethodTier,
)
from .handwritten.http import http_response_to_error, jsonrpc_envelope_to_error
from .handwritten.ws import (
    EthWSClient,
    PolyWSClient,
    SolPubsubClient,
    SolStreamClient,
    WatchlistClient,
    WSClientOptions,
)

DEFAULT_BASE_URL = "https://triport.io"
DEFAULT_WS_BASE_URL = "wss://triport.io"


# JSON-RPC result payloads are spec-shaped-but-untyped until the openrpc
# bodies deepen (see the public OpenRPC schemas); `JsonValue` names that
# intent so `Any` never leaks silently into a public signature.
JsonValue = Any

# Transport callables injected into the chain namespaces by Client /
# AsyncClient. Declaring them as Callable aliases (instead of `Any`)
# keeps _ChainNamespace type-checked against the real _callrpc bodies.
JsonRpcParams = list[JsonValue] | dict[str, JsonValue]
SyncCallRPC = Callable[[Chain, str, JsonRpcParams], JsonValue]
AsyncCallRPC = Callable[[Chain, str, JsonRpcParams], Awaitable[JsonValue]]
SyncHorizonCall = Callable[
    [StellarOperationName, StellarHorizonPathParams | None, StellarHorizonQuery | None],
    StellarHALResponse,
]
AsyncHorizonCall = Callable[
    [StellarOperationName, StellarHorizonPathParams | None, StellarHorizonQuery | None],
    Awaitable[StellarHALResponse],
]

# The generated registries are keyed by a per-chain Literal method-name
# union; Mapping keys are invariant, so a `Mapping[str, MethodTier]`
# parameter would reject all three of them. `Mapping[Any, MethodTier]`
# accepts every chain's registry while keeping the value type checked.
TierRegistry = Mapping[Any, MethodTier]


@dataclass(frozen=True, slots=True)
class ClientOptions:
    api_key: str | None = field(default=None, repr=False)
    bearer_token: str | None = field(default=None, repr=False)
    base_url: str = DEFAULT_BASE_URL
    ws_base_url: str = DEFAULT_WS_BASE_URL
    timeout_sec: float = 30.0
    max_retries: int = 3


class _ChainNamespaceBase:
    """Shared tier-lookup + deprecation plumbing for the chain namespaces.

    Sync and async namespaces do NOT share a `call()` signature (one
    returns a value, the other a coroutine), so they are siblings rather
    than parent/child — that removes the Liskov-violating override that
    previously needed `# type: ignore[override]`.
    """

    __slots__ = ("_chain", "_tiers")

    def __init__(self, chain: Chain, tiers: TierRegistry) -> None:
        self._chain = chain
        self._tiers = tiers

    def tier(self, method: str) -> MethodTier | None:
        return self._tiers.get(method)

    def _warn_if_deprecated(self, method: str) -> None:
        # Emit DeprecationWarning when the openrpc spec marks this method
        # deprecated:true (propagated through gen-rpc into MethodTier).
        # stacklevel=3 points the warning at the SDK consumer's call site
        # rather than this internal helper.
        t = self._tiers.get(method)
        if t is not None and t.deprecated:
            warnings.warn(
                f"Method {self._chain}/{method} is deprecated; "
                "see spec summary for the replacement.",
                DeprecationWarning,
                stacklevel=3,
            )


class _ChainNamespace(_ChainNamespaceBase):
    """Per-chain typed-call + tier-lookup facade. Internal — instantiated by Client."""

    __slots__ = ("_callrpc",)

    def __init__(self, chain: Chain, tiers: TierRegistry, callrpc: SyncCallRPC) -> None:
        super().__init__(chain, tiers)
        self._callrpc = callrpc

    def call(self, method: str, params: JsonRpcParams) -> JsonValue:
        self._warn_if_deprecated(method)
        return self._callrpc(self._chain, method, params)


class _AsyncChainNamespace(_ChainNamespaceBase):
    """Async variant — call() is a coroutine function."""

    __slots__ = ("_callrpc",)

    def __init__(self, chain: Chain, tiers: TierRegistry, callrpc: AsyncCallRPC) -> None:
        super().__init__(chain, tiers)
        self._callrpc = callrpc

    async def call(self, method: str, params: JsonRpcParams) -> JsonValue:
        self._warn_if_deprecated(method)
        return await self._callrpc(self._chain, method, params)


class _TonNamespace(_ChainNamespaceBase):
    """TON uses OpenRPC ``paramStructure: by-name`` for every method."""

    __slots__ = ("_callrpc",)

    def __init__(self, callrpc: SyncCallRPC) -> None:
        super().__init__("ton", TON_METHOD_TIERS)
        self._callrpc = callrpc

    def call(self, method: str, **params: JsonValue) -> JsonValue:
        self._warn_if_deprecated(method)
        return self._callrpc("ton", method, params)


class _AsyncTonNamespace(_ChainNamespaceBase):
    __slots__ = ("_callrpc",)

    def __init__(self, callrpc: AsyncCallRPC) -> None:
        super().__init__("ton", TON_METHOD_TIERS)
        self._callrpc = callrpc

    async def call(self, method: str, **params: JsonValue) -> JsonValue:
        self._warn_if_deprecated(method)
        return await self._callrpc("ton", method, params)


class _HorizonNamespace:
    __slots__ = ("_call",)

    def __init__(self, call: SyncHorizonCall) -> None:
        self._call = call

    def call(
        self,
        operation: StellarOperationName,
        *,
        path: StellarHorizonPathParams | None = None,
        query: StellarHorizonQuery | None = None,
    ) -> StellarHALResponse:
        return self._call(operation, path, query)


class _AsyncHorizonNamespace:
    __slots__ = ("_call",)

    def __init__(self, call: AsyncHorizonCall) -> None:
        self._call = call

    async def call(
        self,
        operation: StellarOperationName,
        *,
        path: StellarHorizonPathParams | None = None,
        query: StellarHorizonQuery | None = None,
    ) -> StellarHALResponse:
        return await self._call(operation, path, query)


class _StellarNamespace(_ChainNamespace):
    __slots__ = ("horizon",)

    def __init__(self, callrpc: SyncCallRPC, callhorizon: SyncHorizonCall) -> None:
        super().__init__("stellar", STELLAR_METHOD_TIERS, callrpc)
        self.horizon = _HorizonNamespace(callhorizon)


class _AsyncStellarNamespace(_AsyncChainNamespace):
    __slots__ = ("horizon",)

    def __init__(self, callrpc: AsyncCallRPC, callhorizon: AsyncHorizonCall) -> None:
        super().__init__("stellar", STELLAR_METHOD_TIERS, callrpc)
        self.horizon = _AsyncHorizonNamespace(callhorizon)


def _horizon_path(
    operation: StellarOperationName,
    path: StellarHorizonPathParams | None,
    query: StellarHorizonQuery | None,
) -> tuple[str, dict[str, str | int]]:
    operation_path = STELLAR_OPERATIONS[operation].path
    for name, value in (path or {}).items():
        operation_path = operation_path.replace("{" + name + "}", str(value))
    if "{" in operation_path:
        raise ValueError(f"Stellar Horizon operation {operation} has unresolved path parameters")
    params = {key: value for key, value in (query or {}).items() if isinstance(value, (str, int))}
    limit = params.get("limit")
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200
    ):
        raise ValueError("Stellar Horizon limit must be an integer from 1 to 200")
    suffix = "" if operation_path == "/" else operation_path
    return f"/rpc/stellar/horizon{suffix}", params


class _SubscribeNamespace:
    """Factory for the 5 WS channel clients.

    Each call returns a fresh client; the caller invokes connect().
    """

    __slots__ = ("_api_key", "_bearer", "_ws_base")

    def __init__(self, ws_base: str, api_key: str | None, bearer: str | None) -> None:
        self._ws_base = ws_base
        self._api_key = api_key
        self._bearer = bearer

    def _opts(self, channel: str) -> WSClientOptions:
        return WSClientOptions(
            url=self._ws_base.rstrip("/")
            + ws_path(channel, None if self._bearer else self._api_key),
            api_key=self._api_key if channel in {"sol-stream", "sol-watch"} else None,
            bearer_token=self._bearer,
        )

    def sol(self) -> SolPubsubClient:
        return SolPubsubClient(self._opts("sol"))

    def sol_stream(self) -> SolStreamClient:
        return SolStreamClient(self._opts("sol-stream"))

    def eth(self) -> EthWSClient:
        return EthWSClient(self._opts("eth"))

    def polygon(self) -> PolyWSClient:
        return PolyWSClient(self._opts("polygon"))

    def robinhood(self) -> EthWSClient:
        return EthWSClient(self._opts("robinhood"))

    def base(self) -> EthWSClient:
        return EthWSClient(self._opts("base"))

    def watchlist(self) -> WatchlistClient:
        return WatchlistClient(self._opts("sol-watch"))


def _auth_headers(api_key: str | None, bearer: str | None) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    elif api_key:
        headers["x-token"] = api_key
    return headers


class Client:
    """Sync client. Built on httpx.Client; recommended for scripts + CLI tooling."""

    def __init__(
        self,
        opts: ClientOptions | None = None,
        *,
        api_key: str | None = None,
        bearer_token: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        ws_base_url: str = DEFAULT_WS_BASE_URL,
        timeout_sec: float = 30.0,
        max_retries: int = 3,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if opts is None:
            opts = ClientOptions(
                api_key=api_key,
                bearer_token=bearer_token,
                base_url=base_url,
                ws_base_url=ws_base_url,
                timeout_sec=timeout_sec,
                max_retries=max_retries,
            )
        self.opts = opts
        self.endpoints = Endpoints(opts.api_key, opts.base_url, opts.ws_base_url)
        self._rpc_id = count(1)
        self._http = httpx.Client(
            base_url=opts.base_url,
            transport=transport,
            timeout=opts.timeout_sec,
            headers=_auth_headers(opts.api_key, opts.bearer_token),
        )
        callrpc = self._callrpc
        self.sol = _ChainNamespace("sol", SOL_METHOD_TIERS, callrpc)
        self.eth = _ChainNamespace("eth", ETH_METHOD_TIERS, callrpc)
        self.polygon = _ChainNamespace("polygon", POLYGON_METHOD_TIERS, callrpc)
        self.tron = _ChainNamespace("tron", TRON_METHOD_TIERS, callrpc)
        self.bsc = _ChainNamespace("bsc", BSC_METHOD_TIERS, callrpc)
        self.robinhood = _ChainNamespace("robinhood", ROBINHOOD_METHOD_TIERS, callrpc)
        self.stellar = _StellarNamespace(callrpc, self._call_stellar_horizon)
        self.ton = _TonNamespace(callrpc)
        self.base = BaseRpcClient(
            base_url=opts.base_url,
            api_key=None if opts.bearer_token else opts.api_key,
            bearer_token=opts.bearer_token,
            timeout_sec=opts.timeout_sec,
            transport=transport,
        )
        self.subscribe = _SubscribeNamespace(opts.ws_base_url, opts.api_key, opts.bearer_token)

    def _callrpc(self, chain: Chain, method: str, params: JsonRpcParams) -> JsonValue:
        body = {"jsonrpc": "2.0", "id": next(self._rpc_id), "method": method, "params": params}
        resp = self._http.post(
            rpc_path(chain, None if self.opts.bearer_token else self.opts.api_key), json=body
        )
        # 4xx mapping: typed error with body fields populated.
        # Cross-SDK parity with TS retryInterceptor.
        if 400 <= resp.status_code < 500:
            err = http_response_to_error(resp)
            if err is not None:
                raise err
            resp.raise_for_status()
        resp.raise_for_status()
        envelope: dict[str, Any] = resp.json()
        if "error" in envelope:
            rpc_err = jsonrpc_envelope_to_error(envelope)
            if rpc_err is not None:
                raise rpc_err
            raise RuntimeError(envelope["error"].get("message", "rpc error"))
        return envelope.get("result")

    def call_tron_wallet(self, operation: TronOperationName, body: JsonValue) -> JsonValue:
        """Call a generated Tron wallet operation at /rpc/tron/wallet/<name>."""
        meta = TRON_OPERATIONS[operation]
        if not meta.path.startswith("/wallet/"):
            raise ValueError(f"Tron operation {operation} is not a wallet operation")
        resp = self._http.post(
            rpc_path("tron", None if self.opts.bearer_token else self.opts.api_key) + meta.path,
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    def _call_stellar_horizon(
        self,
        operation: StellarOperationName,
        path: StellarHorizonPathParams | None,
        query: StellarHorizonQuery | None,
    ) -> StellarHALResponse:
        url, params = _horizon_path(operation, path, query)
        url = rpc_path(
            "stellar", None if self.opts.bearer_token else self.opts.api_key
        ) + url.removeprefix("/rpc/stellar")
        resp = self._http.get(url, params=params, headers={"Accept": "application/hal+json"})
        resp.raise_for_status()
        return cast(StellarHALResponse, resp.json())

    def close(self) -> None:
        self._http.close()
        self.base.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class AsyncClient:
    """Async client. Built on httpx.AsyncClient; recommended for long-running
    services + WS combos."""

    def __init__(
        self,
        opts: ClientOptions | None = None,
        *,
        api_key: str | None = None,
        bearer_token: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        ws_base_url: str = DEFAULT_WS_BASE_URL,
        timeout_sec: float = 30.0,
        max_retries: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if opts is None:
            opts = ClientOptions(
                api_key=api_key,
                bearer_token=bearer_token,
                base_url=base_url,
                ws_base_url=ws_base_url,
                timeout_sec=timeout_sec,
                max_retries=max_retries,
            )
        self.opts = opts
        self.endpoints = Endpoints(opts.api_key, opts.base_url, opts.ws_base_url)
        self._rpc_id = count(1)
        self._http = httpx.AsyncClient(
            base_url=opts.base_url,
            transport=transport,
            timeout=opts.timeout_sec,
            headers=_auth_headers(opts.api_key, opts.bearer_token),
        )
        callrpc = self._callrpc
        self.sol = _AsyncChainNamespace("sol", SOL_METHOD_TIERS, callrpc)
        self.eth = _AsyncChainNamespace("eth", ETH_METHOD_TIERS, callrpc)
        self.polygon = _AsyncChainNamespace("polygon", POLYGON_METHOD_TIERS, callrpc)
        self.tron = _AsyncChainNamespace("tron", TRON_METHOD_TIERS, callrpc)
        self.bsc = _AsyncChainNamespace("bsc", BSC_METHOD_TIERS, callrpc)
        self.robinhood = _AsyncChainNamespace("robinhood", ROBINHOOD_METHOD_TIERS, callrpc)
        self.stellar = _AsyncStellarNamespace(callrpc, self._call_stellar_horizon)
        self.ton = _AsyncTonNamespace(callrpc)
        self.base = _AsyncChainNamespace("base", BASE_METHOD_TIERS, callrpc)
        self.subscribe = _SubscribeNamespace(opts.ws_base_url, opts.api_key, opts.bearer_token)

    async def _callrpc(self, chain: Chain, method: str, params: JsonRpcParams) -> JsonValue:
        body = {"jsonrpc": "2.0", "id": next(self._rpc_id), "method": method, "params": params}
        resp = await self._http.post(
            rpc_path(chain, None if self.opts.bearer_token else self.opts.api_key), json=body
        )
        if 400 <= resp.status_code < 500:
            err = http_response_to_error(resp)
            if err is not None:
                raise err
            resp.raise_for_status()
        resp.raise_for_status()
        envelope: dict[str, Any] = resp.json()
        if "error" in envelope:
            rpc_err = jsonrpc_envelope_to_error(envelope)
            if rpc_err is not None:
                raise rpc_err
            raise RuntimeError(envelope["error"].get("message", "rpc error"))
        return envelope.get("result")

    async def call_tron_wallet(self, operation: TronOperationName, body: JsonValue) -> JsonValue:
        """Async variant of Client.call_tron_wallet."""
        meta = TRON_OPERATIONS[operation]
        if not meta.path.startswith("/wallet/"):
            raise ValueError(f"Tron operation {operation} is not a wallet operation")
        resp = await self._http.post(
            rpc_path("tron", None if self.opts.bearer_token else self.opts.api_key) + meta.path,
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    async def _call_stellar_horizon(
        self,
        operation: StellarOperationName,
        path: StellarHorizonPathParams | None,
        query: StellarHorizonQuery | None,
    ) -> StellarHALResponse:
        url, params = _horizon_path(operation, path, query)
        url = rpc_path(
            "stellar", None if self.opts.bearer_token else self.opts.api_key
        ) + url.removeprefix("/rpc/stellar")
        resp = await self._http.get(url, params=params, headers={"Accept": "application/hal+json"})
        resp.raise_for_status()
        return cast(StellarHALResponse, resp.json())

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()


__all__ = ["AsyncClient", "Client", "ClientOptions"]
