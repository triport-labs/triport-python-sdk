"""examples/sol_history.py — wallet history with tier-aware error handling."""

from __future__ import annotations

import os
import sys

from triport import Client, RateLimitedError, TierInsufficientError


def main() -> int:
    api_key = os.environ.get("TRIPORT_API_KEY")
    if not api_key:
        print("Set TRIPORT_API_KEY first", file=sys.stderr)
        return 1

    address = sys.argv[1] if len(sys.argv) > 1 else "So11111111111111111111111111111111111111112"

    with Client(api_key=api_key) as c:
        try:
            sigs = c.sol.call(
                "getSignaturesForAddress",
                [address, {"limit": 5}],
            )
            for s in sigs:
                print(f"{s.get('slot')}\t{s.get('signature')}")
        except TierInsufficientError as err:
            print(
                f"Tier insufficient. Required={err.required_tier}; upgrade at "
                f"https://triport.io/upgrade/{err.required_tier or 'pro'}",
                file=sys.stderr,
            )
            return 1
        except RateLimitedError as err:
            print(
                f"Rate limited; retry after {err.retry_after_sec}s (limit={err.limit_rps} RPS)",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
