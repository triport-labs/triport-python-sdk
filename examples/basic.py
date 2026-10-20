"""examples/basic.py — minimal end-to-end usage.

Run after `pip install -e .[dev]`:
    python examples/basic.py  # reads TRIPORT_API_KEY from the environment
"""

from __future__ import annotations

import os
import sys

from triport import SDK_VERSION, Client


def main() -> int:
    print(f"Triport SDK v{SDK_VERSION}")
    api_key = os.environ.get("TRIPORT_API_KEY")
    if not api_key:
        print("Set TRIPORT_API_KEY first", file=sys.stderr)
        return 1

    with Client(api_key=api_key) as c:
        print("sol getSlot:", c.sol.call("getSlot", []))
        print("eth eth_chainId:", c.eth.call("eth_chainId", []))
        print("polygon eth_chainId:", c.polygon.call("eth_chainId", []))
        print("base eth_chainId:", c.base.call("eth_chainId", []))
        print("bsc eth_chainId:", c.bsc.call("eth_chainId", []))
        print("robinhood eth_chainId:", c.robinhood.call("eth_chainId", []))
        print("tron eth_chainId:", c.tron.call("eth_chainId", []))
        print("stellar getHealth:", c.stellar.call("getHealth", []))
        print(
            "ton getAddressInformation:",
            c.ton.call(
                "getAddressInformation",
                address="0:0000000000000000000000000000000000000000000000000000000000000000",
            ),
        )

        meta = c.sol.tier("getAssetsByOwner")
        if meta:
            print(f"getAssetsByOwner requires tier={meta.required} category={meta.category}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
