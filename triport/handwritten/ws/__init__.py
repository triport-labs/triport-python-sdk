"""Barrel for handwritten WS clients (api.5.4)."""

from .base import WSClient, WSClientOptions
from .base_chain import (
    BASE_AUCTION_STATUS,
    BaseFeedClient,
    BaseFeedControlEvent,
    BaseFeedEvent,
    BaseFlashblockDiff,
    BaseFlashblockEvent,
    BasePubSubClient,
    BaseSubscriptionKind,
    BaseWSChannel,
    base_chain_ws_url,
    parse_base_feed_frame,
)
from .errors import (
    WS_CLOSE_CODES,
    MethodUnknownError,
    RateLimitedError,
    SubscriptionExpiredError,
    TierInsufficientError,
    TrialExpiredError,
    TriportError,
    UnauthorizedError,
    frame_to_error,
)
from .eth_ws import (
    EthLogsFilter,
    EthNewPendingTxOpts,
    EthSubscriptionKind,
    EthWSClient,
    PolyWSClient,
)
from .sol_pubsub import SolPubsubClient, SolSubscribeMethod
from .sol_stream import (
    SolStreamAccountFilter,
    SolStreamBlocksFilter,
    SolStreamClient,
    SolStreamCommitment,
    SolStreamSlotsFilter,
    SolStreamSubscribeRequest,
    SolStreamTransactionsFilter,
)
from .watchlist import (
    WatchChangeKind,
    WatchEntryRevokedFrame,
    WatchEventFrame,
    WatchHeartbeatFrame,
    WatchlistClient,
    WatchSubscribeFrame,
)

# Sorted (RUF022). Groups: base / errors / Solana / EVM networks /
# watchlist — see the import block above for the domain grouping.
__all__ = [
    "BASE_AUCTION_STATUS",
    "WS_CLOSE_CODES",
    "BaseFeedClient",
    "BaseFeedControlEvent",
    "BaseFeedEvent",
    "BaseFlashblockDiff",
    "BaseFlashblockEvent",
    "BasePubSubClient",
    "BaseSubscriptionKind",
    "BaseWSChannel",
    "EthLogsFilter",
    "EthNewPendingTxOpts",
    "EthSubscriptionKind",
    "EthWSClient",
    "MethodUnknownError",
    "PolyWSClient",
    "RateLimitedError",
    "SolPubsubClient",
    "SolStreamAccountFilter",
    "SolStreamBlocksFilter",
    "SolStreamClient",
    "SolStreamCommitment",
    "SolStreamSlotsFilter",
    "SolStreamSubscribeRequest",
    "SolStreamTransactionsFilter",
    "SolSubscribeMethod",
    "SubscriptionExpiredError",
    "TierInsufficientError",
    "TrialExpiredError",
    "TriportError",
    "UnauthorizedError",
    "WSClient",
    "WSClientOptions",
    "WatchChangeKind",
    "WatchEntryRevokedFrame",
    "WatchEventFrame",
    "WatchHeartbeatFrame",
    "WatchSubscribeFrame",
    "WatchlistClient",
    "base_chain_ws_url",
    "frame_to_error",
    "parse_base_feed_frame",
]
