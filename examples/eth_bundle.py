"""examples/eth_bundle.py — Ethereum bundle dispatch via Triport.

Triport relays eth_sendBundle to block builders. Pro+ tier per matrix.
"""

from __future__ import annotations

import os
import sys

from triport import Client, TierInsufficientError


def main() -> int:
    api_key = os.environ.get("TRIPORT_API_KEY")
    if not api_key:
        print("Set TRIPORT_API_KEY first", file=sys.stderr)
        return 1
    if len(sys.argv) < 2:
        print("usage: python examples/eth_bundle.py <0x-rlp-signed-tx>", file=sys.stderr)
        return 2
    raw_tx = sys.argv[1]

    with Client(api_key=api_key) as c:
        try:
            result = c.eth.call(
                "eth_sendBundle",
                [{"txs": [raw_tx], "blockNumber": "pending"}],
            )
            print(f"bundleHash: {result.get('bundleHash')}")
        except TierInsufficientError as err:
            print(
                f"eth_sendBundle requires {err.required_tier or 'pro'}; "
                f"upgrade: https://triport.io/upgrade/{err.required_tier or 'pro'}",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
