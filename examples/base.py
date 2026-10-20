"""Base read + parser-only write shape. No signed write is dispatched."""

from __future__ import annotations

import os

from triport import BaseFeedClient, BaseRpcClient

token = os.environ["TRIPORT_API_KEY"]
with BaseRpcClient(api_key=token) as client:
    print({"chain_id": client.call("eth_chainId", [])})

# Schema illustration: schema illustration, deliberately not passed to client.call().
sync_write_shape = ("0x<signed-transaction-bytes>", 10)

# Construction is offline. connect() is explicit and is not invoked here.
feed = BaseFeedClient(api_key=token)
print({"feed_ready": feed is not None, "write_shape_fields": len(sync_write_shape)})
