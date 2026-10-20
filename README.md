<p align="center"><img src="https://raw.githubusercontent.com/triport-labs/.github/main/profile/assets/banner-9-networks.png" alt="Triport" width="100%"></p>

# Triport Python SDK

Synchronous and asynchronous Python clients for Triport JSON-RPC, REST helpers
and WebSocket subscriptions across nine networks. Includes typed method registries,
structured API errors and Solana Yellowstone gRPC endpoint configuration.

[Website](https://triport.io) · [Docs](https://triport.io/docs) · [X](https://x.com/triport_io) · [Telegram](https://t.me/triport_sales) · [Email](mailto:sales@triport.io)

## Install

Requires Python 3.10 or later.

```bash
pip install triport
```

For a source checkout before the first PyPI release, use `pip install .`.
Create an API key in the Triport dashboard and set `TRIPORT_API_KEY` in your environment.

## Quick start

```python
import os
import triport

with triport.Client(api_key=os.environ["TRIPORT_API_KEY"]) as client:
    print(client.sol.call("getSlot", []))
    print(client.eth.call("eth_chainId", []))
    print(client.base.call("eth_chainId", []))
```

Async clients expose the same network namespaces:

```python
import asyncio
import os
import triport


async def main():
    async with triport.AsyncClient(api_key=os.environ["TRIPORT_API_KEY"]) as client:
        print(await client.sol.call("getSlot", []))
        print(await client.stellar.call("getHealth", {}))
        print(await client.ton.call("getMasterchainInfo"))


asyncio.run(main())
```

Most calls accept a list of positional parameters; Stellar Soroban accepts named
parameters as a dictionary. TON uses keyword arguments, for example
`client.ton.call("getAddressInformation", address=address)`.

## WebSocket subscriptions

```python
import asyncio
import os
import triport


async def main():
    async with triport.AsyncClient(api_key=os.environ["TRIPORT_API_KEY"]) as client:
        ws = client.subscribe.sol()
        try:
            await ws.connect()
            subscription = await ws.subscribe("slotSubscribe", [])
            async for update in ws:
                print(update)
                break
            await ws.unsubscribe(subscription)
        finally:
            await ws.close()


asyncio.run(main())
```

Ethereum, Polygon, Base and Robinhood expose `subscribe.eth()`, `.polygon()`,
`.base()` and `.robinhood()` factories with `await ws.subscribe("newHeads")`.
Solana also provides `.sol_stream()` and `.watchlist()` helpers. Close WebSocket
clients explicitly; closing the HTTP client does not close separate subscriptions.
`BaseFeedClient` parses the Base feed and reports sequence gaps.

## Networks and endpoints

`{key}` denotes your locally held API key; resolved URLs contain credentials and
should not be logged or persisted. Access depends on the key's scopes and plan.

| Network | Namespace | HTTPS | WebSocket |
|---|---|---|---|
| Solana | `client.sol` | `https://triport.io/r/{key}/sol` | `wss://triport.io/ws/r/{key}/sol` |
| Ethereum | `client.eth` | `https://triport.io/r/{key}/eth` | `wss://triport.io/ws/r/{key}/eth` |
| Polygon | `client.polygon` | `https://triport.io/r/{key}/polygon` | `wss://triport.io/ws/r/{key}/polygon` |
| BNB Smart Chain | `client.bsc` | `https://triport.io/r/{key}/bsc` | — |
| Base | `client.base` | `https://triport.io/r/{key}/rpc/base` | `wss://triport.io/ws/base/{key}` |
| Tron | `client.tron` | `https://triport.io/r/{key}/tron` | — |
| Robinhood Chain | `client.robinhood` | `https://triport.io/r/{key}/robinhood` | `wss://triport.io/ws/r/{key}/robinhood` |
| Stellar | `client.stellar` | `https://triport.io/r/{key}/stellar` | Horizon REST/SSE |
| TON | `client.ton` | `https://triport.io/r/{key}/ton` | — |

Base uses the network-specific URL forms shown above.
The SDK does not create WebSocket endpoints for networks without a documented
streaming service. Stellar Horizon REST calls are available through
`client.stellar.horizon.call(...)`; an SSE consumer is not included.
Tron wallet operations use `client.call_tron_wallet(operation, body)`.

## Solana gRPC

Use the endpoint configuration with your generated Yellowstone protobuf client.
Install `grpcio` separately and provide the standard `geyser_pb2` / `geyser_pb2_grpc`
stubs from your Yellowstone proto distribution:

```python
import os
import grpc
import triport
from geyser_pb2 import GetVersionRequest
from geyser_pb2_grpc import GeyserStub

endpoints = triport.Endpoints(api_key=os.environ["TRIPORT_API_KEY"])
with grpc.secure_channel(endpoints.grpc_target, grpc.ssl_channel_credentials()) as channel:
    result = GeyserStub(channel).GetVersion(
        GetVersionRequest(),
        metadata=endpoints.grpc_metadata,
        timeout=10,
    )
    print(result.version)
```

The TLS target is `grpc.triport.io:443`; authentication uses `x-token` metadata.
Protobuf stubs and a gRPC streaming client are not bundled with this package.
`Endpoints.https(chain)` and `.wss(chain)` also resolve URLs for other libraries.

## Errors and request behavior

```python
from triport import RateLimitedError, TierInsufficientError

try:
    result = client.sol.call("getSlot", [])
except RateLimitedError as error:
    print("Retry after:", error.retry_after_sec)
except TierInsufficientError as error:
    print("Required tier:", error.required_tier)
```

`namespace.tier(method)` reads the bundled method metadata without a network call.
Both HTTP clients make one request per call; they do not automatically retry writes
or reads. The legacy `max_retries` option is reserved and has no effect.
`bearer_token` takes precedence over `api_key`. Configure `timeout_sec`, `base_url`
and `ws_base_url` when needed. Base protocol errors preserve a bounded, credential
redacted response fragment for inspection.

See [examples](examples/) and [CONTRIBUTING.md](CONTRIBUTING.md) for development
checks and contract generation. Licensed under [MIT](LICENSE), © 2026 Triport Labs.
