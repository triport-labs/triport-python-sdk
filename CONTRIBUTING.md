# Contributing

Use Python 3.10 or later. Create a development environment outside the checkout:

```bash
python -m venv ../triport-dev
source ../triport-dev/bin/activate  # Windows: ..\triport-dev\Scripts\Activate.ps1
pip install -e '.[dev]'
ruff check . --no-cache
ruff format --check .
mypy triport --cache-dir ../triport-mypy-cache
pytest -p no:cacheprovider
python -m build --outdir ../triport-artifacts
```

The default tests use synthetic fixtures and mock transports; no API key is needed.
CI checks Python 3.10–3.13 and tests an installed wheel in a separate environment.
Keep credentials out of source, fixtures, logs and issues.

Generated bindings are committed. To regenerate from a local copy of the public
OpenRPC and OpenAPI contracts, supply their directories explicitly:

```bash
python scripts/gen_rpc.py --spec-dir /path/to/json-rpc --check
python scripts/gen_rest.py --spec-dir /path/to/product-rest --check
```

`TRIPORT_SPEC_DIR` can replace `--spec-dir`. Optional category overrides use
`--categories-file` or `TRIPORT_CATEGORIES_FILE`. The reviewed public RPC method
manifest is `tests/fixtures/methods.json`; update it when adding supported methods.
Only supply public contracts: generated metadata must be suitable for publication.

Open an issue or pull request with a focused change and relevant offline checks.
See [SECURITY.md](SECURITY.md) for private vulnerability reports.
