#!/usr/bin/env python3
"""Offline smoke test for an installed wheel in a clean virtual environment.

Install the wheel, change to a directory outside the checkout, then run this script
with the clean environment's interpreter. No development dependencies are needed.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import NoReturn


def fail(msg: str) -> NoReturn:
    """Abort the smoke run. `NoReturn` lets mypy narrow after every call site."""
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    import triport

    # 1. Imported from an installed distribution, not the working tree.
    origin = Path(triport.__file__).resolve()
    if "site-packages" not in origin.parts:
        fail(
            f"triport imported from {origin}, not from site-packages — "
            "run this from a clean venv, outside the repo checkout"
        )
    print(f"ok: imported {triport.__name__} from {origin}")

    # 2. Barrel completeness.
    missing = [n for n in triport.__all__ if not hasattr(triport, n)]
    if missing:
        fail(f"__all__ names missing from the module: {missing}")
    print(f"ok: barrel exports {len(triport.__all__)} names")

    version = triport.SDK_VERSION
    if not version:
        fail("SDK_VERSION empty")
    print(f"ok: SDK_VERSION={version}")

    # 3. Offline construction — sync.
    client = triport.Client(api_key="smoke-not-a-real-key")
    chains = ("sol", "eth", "polygon", "tron", "bsc", "stellar", "ton", "base", "robinhood")
    for chain in chains:
        if getattr(client, chain, None) is None:
            fail(f"Client.{chain} namespace missing")
    channels = ("sol", "sol_stream", "eth", "polygon", "watchlist", "base", "robinhood")
    for name in channels:
        if getattr(client.subscribe, name)() is None:
            fail(f"Client.subscribe.{name}() returned None")
    if hasattr(client.subscribe, "bsc"):
        fail("Client.subscribe.bsc must remain absent until the BSC WS mount exists")
    if hasattr(client.subscribe, "stellar"):
        fail("Client.subscribe.stellar must remain absent; Horizon SSE has no SDK wrapper")
    if hasattr(client.subscribe, "ton"):
        fail("Client.subscribe.ton must remain absent; TON has no streaming surface")
    print(f"ok: Client constructed; {len(chains)} chains + {len(channels)} WS factories")

    # 4. Tier lookup through the generated registry.
    tier = client.sol.tier("getBalance")
    if tier is None:
        fail("sol.tier('getBalance') returned None — generated registry not shipped?")
    print(f"ok: sol.tier('getBalance') -> required={tier.required!r}")

    client.close()

    # 3b. Offline construction — async.
    async def _async_probe() -> None:
        async with triport.AsyncClient(api_key="smoke-not-a-real-key") as ac:
            for chain in chains:
                if getattr(ac, chain, None) is None:
                    fail(f"AsyncClient.{chain} namespace missing")

    asyncio.run(_async_probe())
    print("ok: AsyncClient constructed + closed")

    print("wheel smoke PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
