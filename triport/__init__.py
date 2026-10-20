"""Triport SDK — official Python SDK for Triport.

Exports:
    - SDK_VERSION : current package version (PEP 440)
    - Client / AsyncClient : sync + async HTTP + WS entry points
    - ClientOptions : dataclass for explicit Client construction
    - WS error classes + WS_CLOSE_CODES (re-exported from handwritten.ws)
"""

from .client import AsyncClient, Client, ClientOptions
from .endpoints import CHAINS, GRPC_TARGET, WS_CHAINS, Endpoints
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
    BaseMethodName,
    BaseRpcClient,
    BscMethodName,
    EthMethodName,
    PolygonMethodName,
    RobinhoodMethodName,
    SolMethodName,
    StellarMethodName,
    TonMethodName,
    TronMethodName,
)
from .generated.rpc.base_wire import BaseParams, BaseResults
from .generated.rpc.bsc_wire import BscParams, BscResults
from .generated.rpc.robinhood_wire import RobinhoodParams, RobinhoodResults
from .handwritten.ws import (
    BASE_AUCTION_STATUS,
    WS_CLOSE_CODES,
    BaseFeedClient,
    BasePubSubClient,
    MethodUnknownError,
    RateLimitedError,
    SubscriptionExpiredError,
    TierInsufficientError,
    TrialExpiredError,
    TriportError,
    UnauthorizedError,
    base_chain_ws_url,
    parse_base_feed_frame,
)

SDK_VERSION = "0.1.0a0"

__all__ = [
    "BASE_AUCTION_STATUS",
    "BASE_METHOD_TIERS",
    "BSC_METHOD_TIERS",
    "CHAINS",
    "ETH_METHOD_TIERS",
    "GRPC_TARGET",
    "POLYGON_METHOD_TIERS",
    "ROBINHOOD_METHOD_TIERS",
    "SDK_VERSION",
    "SOL_METHOD_TIERS",
    "STELLAR_METHOD_TIERS",
    "TON_METHOD_TIERS",
    "TRON_METHOD_TIERS",
    "WS_CHAINS",
    "WS_CLOSE_CODES",
    "AsyncClient",
    "BaseFeedClient",
    "BaseMethodName",
    "BaseParams",
    "BasePubSubClient",
    "BaseResults",
    "BaseRpcClient",
    "BscMethodName",
    "BscParams",
    "BscResults",
    "Client",
    "ClientOptions",
    "Endpoints",
    "EthMethodName",
    "MethodUnknownError",
    "PolygonMethodName",
    "RateLimitedError",
    "RobinhoodMethodName",
    "RobinhoodParams",
    "RobinhoodResults",
    "SolMethodName",
    "StellarMethodName",
    "SubscriptionExpiredError",
    "TierInsufficientError",
    "TonMethodName",
    "TrialExpiredError",
    "TriportError",
    "TronMethodName",
    "UnauthorizedError",
    "base_chain_ws_url",
    "parse_base_feed_frame",
]
