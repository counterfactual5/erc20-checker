# Contributing to erc20-checker

Thanks for contributing! This document covers the basics.

## Setup

```bash
git clone https://github.com/counterfactual5/erc20-checker.git
cd erc20-checker

# Install with dev dependencies
uv pip install -e ".[dev]"
```

No external services or API keys are needed for development — tests mock all RPC and Etherscan calls.

## Running Tests

```bash
uv run pytest tests/ -v
```

22 tests covering all 6 modules. All tests should pass before submitting a PR.

## Code Style

- Python 3.10+ compatible (no `X | None` syntax in runtime paths used by older versions)
- 120-char line length (configured in `pyproject.toml`)
- Public functions have docstrings (Google-style or numpydoc)
- Addresses are stored and compared in lowercase

## Project Philosophy

### Zero Dependencies

`erc20-checker` uses **only the Python standard library**. This is a deliberate constraint:

- No `requests`, no `web3.py`, no `eth-account`
- RPC calls use `urllib`
- ABI encoding is done by hand
- JSON parsing uses `json`

Before proposing a new dependency, consider whether it can be implemented with stdlib.

### Read-Only

This library reads on-chain data and builds unsigned transaction payloads. It never:
- Signs transactions
- Broadcasts transactions
- Requires private keys

## Adding a New Chain

1. Add the chain to `CHAINS` dict in `src/erc20_checker/chains.py`
2. The Etherscan URL should point to `https://api.etherscan.io/v2/api` (unified v2 endpoint)
3. Ensure the chain's RPC env var candidates are covered in `common.py::rpc_env_candidates()`
4. Add a test case in `tests/test_all.py::TestChains`

## Adding to KNOWN_SPENDERS

`risk.py` maintains a `KNOWN_SPENDERS` set of well-known protocol addresses. When adding entries:

- Use lowercase hex addresses
- Include a comment with the protocol name
- Prefer deterministic CREATE2 addresses (valid across chains)
- Add a test in `TestRisk` if the address introduces new classification behavior

## Pull Requests

1. Fork the repo
2. Create a feature branch
3. Make changes + add tests
4. Run `uv run pytest tests/ -v` and ensure all pass
5. Submit a PR to `main`

Keep PRs focused — one concern per PR.
