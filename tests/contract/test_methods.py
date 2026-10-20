"""Public read contracts, split offline vs opt-in live.

Two distinct sets live in this file:

  * `test_fixture_pairs_with_spec` — HERMETIC. Runs in the default
    `pytest` invocation. Asserts, per discovered fixture, that the file
    parses, pairs with an OpenRPC method entry, and carries a usable
    params array. No network.

  * `test_method_matches_shape` — LIVE (`@pytest.mark.live`). Calls the
    staging API. Deselected by default; `pytest -m live` runs it and
    tests/conftest.py errors out when the staging env vars are missing,
    so this set can never report green-by-skip.
"""

from __future__ import annotations

from typing import Any

import pytest

from .runner import (
    fixture_expected,
    fixture_params,
    load_tests,
    shallow_matches,
    staging_client,
)

_TESTS: list[dict[str, Any]] = list(load_tests())


@pytest.mark.live
@pytest.mark.parametrize("case", _TESTS, ids=lambda t: f"{t['chain']}.{t['name']}")
def test_method_matches_shape(case: dict[str, Any]) -> None:
    client = staging_client()
    assert client is not None, (
        "staging_client() returned None despite the live set being selected; "
        "tests/conftest.py should have failed collection first"
    )
    params = fixture_params(case["fixture"])
    chain_ns = getattr(client, case["chain"])
    real = (
        chain_ns.call(case["name"], **params)
        if case["chain"] == "ton"
        else chain_ns.call(case["name"], params)
    )
    expected = fixture_expected(case["fixture"])
    if expected is None:
        return
    assert shallow_matches(real, expected), f"shape mismatch for {case['chain']}.{case['name']}"


@pytest.mark.live
def test_stellar_horizon_root_matches_hal() -> None:
    client = staging_client()
    assert client is not None
    result = client.stellar.horizon.call("stellarHorizonRoot")
    assert "_links" in result


def test_loader_finds_at_least_one_fixture() -> None:
    """Loader sanity — checks that the spec <-> fixture wiring (Pack B.3) is
    load-bearing even when staging is unreachable."""
    sol_fixtures = [t for t in _TESTS if t["chain"] == "sol"]
    assert len(sol_fixtures) > 0, "no sol fixtures discovered under _examples/sol/"


def test_loader_covers_every_chain() -> None:
    """Every chain must contribute at least one spec-paired fixture; a chain
    dropping to zero silently shrinks the live matrix."""
    for chain in ("sol", "eth", "polygon", "tron", "bsc", "robinhood", "stellar", "ton", "base"):
        got = [t for t in _TESTS if t["chain"] == chain]
        assert got, f"no spec-paired fixtures discovered for chain {chain}"


@pytest.mark.parametrize("case", _TESTS, ids=lambda t: f"{t['chain']}.{t['name']}")
def test_fixture_pairs_with_spec(case: dict[str, Any]) -> None:
    """HERMETIC per-fixture check: the fixture parsed, paired with an
    OpenRPC method entry of the same name, and yields a params list.

    This gives the fixture matrix a real, visible per-case status in the
    default run instead of a row of `s` characters.
    """
    assert case["spec"].get("name") == case["name"], (
        f"fixture {case['chain']}/{case['name']}.json paired with spec entry "
        f"{case['spec'].get('name')!r}"
    )
    params = fixture_params(case["fixture"])
    if case["spec"].get("paramStructure") == "by-name":
        assert isinstance(params, dict)
    else:
        assert isinstance(params, list)
