# Triport Python examples

Install the package with `pip install triport` (or `pip install .` from a source
checkout). Set `TRIPORT_API_KEY` in your environment before running network examples.
Keep development virtual environments outside the checkout; see [Contributing](../CONTRIBUTING.md).

| Example | Purpose |
|---|---|
| `basic.py` | One light JSON-RPC read per network and local method metadata. |
| `sol_history.py` | Solana history pagination and structured errors. |
| `ws_subscribe.py` | Solana WebSocket subscription with explicit cleanup. |
| `base.py` | Base read, offline transaction request shape and feed parser. |
| `eth_bundle.py` | Submit an Ethereum bundle using a signed transaction supplied by the caller. |

```bash
python examples/basic.py
python examples/sol_history.py <public-key>
python examples/ws_subscribe.py
python examples/base.py
```

`eth_bundle.py` submits a transaction bundle. Run it only when you intend to submit
the signed transaction you supply. It is not part of the offline or live smoke checks.
Streaming access depends on the scopes and plan of your API key.
