"""Local synthetic read fixtures and opt-in public API contract helpers."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from triport import Client

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CHAINS = ("sol", "eth", "polygon", "bsc", "base", "tron", "robinhood", "stellar", "ton")


def load_tests() -> Iterator[dict[str, Any]]:
    """Load reviewed synthetic read fixtures, failing on missing or invalid data."""
    manifests = json.loads((FIXTURES / "methods.json").read_text(encoding="utf-8"))
    cases = json.loads((FIXTURES / "reads.json").read_text(encoding="utf-8"))
    assert {case["chain"] for case in cases} == set(CHAINS)
    for case in cases:
        methods = {method["name"]: method for method in manifests[case["chain"]]}
        yield {**case, "spec": methods[case["name"]]}


def fixture_params(fixture: dict[str, Any]) -> list[Any] | dict[str, Any]:
    """Extract params — accepts both canonical {request.params}
    and flat {params} shapes from the live _examples files."""
    req = fixture.get("request")
    if isinstance(req, dict) and isinstance(req.get("params"), (list, dict)):
        return req["params"].copy()
    if isinstance(fixture.get("params"), (list, dict)):
        return fixture["params"].copy()
    return []


def fixture_expected(fixture: dict[str, Any]) -> Any:
    """Return the expected JSON-RPC result. None when fixture lacks one."""
    resp = fixture.get("response")
    if isinstance(resp, dict) and "result" in resp:
        return resp["result"]
    if "result" in fixture:
        return fixture["result"]
    return None


def shallow_matches(got: Any, expected: Any) -> bool:
    """Top-level key + array/object shape sanity. Mirrors TS
    runner.shallowMatches so the two contract suites assert the same
    invariants."""
    if expected is None:
        return True
    if type(got) is not type(expected):
        return False
    if isinstance(expected, dict):
        for k, ev in expected.items():
            if k not in got:
                return False
            if isinstance(ev, dict) and not isinstance(got[k], dict):
                return False
        return True
    if isinstance(expected, list):
        return isinstance(got, list)
    return True


def staging_client(key_var: str = "TRIPORT_CONTRACT_KEY") -> Client | None:
    """Build the SDK Client pointed at staging. Returns None when env
    vars are missing — callers skip the test suite."""
    base_url = os.environ.get("TRIPORT_STAGING_URL")
    api_key = os.environ.get(key_var)
    if not base_url or not api_key:
        return None
    return Client(base_url=base_url, api_key=api_key)
