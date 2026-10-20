"""examples/ws_subscribe.py — typed Solana logsSubscribe over /ws/sol."""

from __future__ import annotations

import asyncio
import os
import sys

from triport import AsyncClient, RateLimitedError, TriportError


async def main() -> int:
    api_key = os.environ.get("TRIPORT_API_KEY")
    if not api_key:
        print("Set TRIPORT_API_KEY first", file=sys.stderr)
        return 1

    async with AsyncClient(api_key=api_key) as c:
        ws = c.subscribe.sol()
        await ws.connect()
        try:
            sub_id = await ws.subscribe(
                "logsSubscribe",
                [{"mentions": ["11111111111111111111111111111111"]}, {"commitment": "confirmed"}],
            )
            print(f"subscribed: id={sub_id}")
            # Drain ~10 frames or until cancelled.
            count = 0
            async for frame in ws:
                print(f"frame: {str(frame)[:200]}")
                count += 1
                if count >= 10:
                    break
            await ws.unsubscribe(sub_id)
        except RateLimitedError as err:
            print(f"rate-limited; retry_after_sec={err.retry_after_sec}", file=sys.stderr)
            return 1
        except TriportError as err:
            print(f"WS error: {err}", file=sys.stderr)
            return 1
        finally:
            await ws.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
