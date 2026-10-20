"""Default tests are offline. Opt-in live reads require explicit endpoint and key env vars.

TRIPORT_STAGING_URL sets the public API origin; TRIPORT_CONTRACT_KEY supplies a key.
Only environment variable names are included in collection errors.
"""

from __future__ import annotations

import os

import pytest

LIVE_ENV_VARS = (
    "TRIPORT_STAGING_URL",
    "TRIPORT_CONTRACT_KEY",
)


def missing_live_env() -> list[str]:
    """Names (never values) of the live-staging env vars that are unset."""
    return [name for name in LIVE_ENV_VARS if not os.environ.get(name)]


def _live_selected(config: pytest.Config) -> bool:
    """True when the caller explicitly asked for the live set.

    `-m live` / `-m "live and x"` selects it. The default marker
    expression from pyproject is `not live`, which does not.
    """
    markexpr = str(config.getoption("-m") or "")
    if not markexpr:
        return False
    # Cheap textual check: "live" present and not negated as "not live".
    normalised = " ".join(markexpr.split())
    if normalised == "not live" or normalised.startswith("not live "):
        return False
    return "live" in normalised


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Fail loudly when the live set is requested without its secrets."""
    if not _live_selected(config):
        return
    live_items = [it for it in items if it.get_closest_marker("live") is not None]
    if not live_items:
        return
    missing = missing_live_env()
    if missing:
        raise pytest.UsageError(
            "live test set selected (-m live) but required env vars are unset: "
            + ", ".join(missing)
            + " — set them (CI: repository secrets) or drop -m live to run the "
            "hermetic set."
        )
