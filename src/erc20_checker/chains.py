"""Chain configuration for supported EVM networks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chain:
    """Metadata for a supported EVM chain."""

    key: str
    chain_id: int
    native_symbol: str
    etherscan_url: str


# All chains use the unified Etherscan v2 API endpoint.
# The ``chainid`` parameter in requests routes to the correct network.
# Note: free-tier API keys only support Ethereum (chainid=1).
# For other chains, a paid Etherscan plan is required.
CHAINS: dict[str, Chain] = {
    "ethereum": Chain(
        key="ethereum",
        chain_id=1,
        native_symbol="ETH",
        etherscan_url="https://api.etherscan.io/v2/api",
    ),
    "base": Chain(
        key="base",
        chain_id=8453,
        native_symbol="ETH",
        etherscan_url="https://api.etherscan.io/v2/api",
    ),
    "arbitrum": Chain(
        key="arbitrum",
        chain_id=42161,
        native_symbol="ETH",
        etherscan_url="https://api.etherscan.io/v2/api",
    ),
    "optimism": Chain(
        key="optimism",
        chain_id=10,
        native_symbol="ETH",
        etherscan_url="https://api.etherscan.io/v2/api",
    ),
    "polygon": Chain(
        key="polygon",
        chain_id=137,
        native_symbol="MATIC",
        etherscan_url="https://api.etherscan.io/v2/api",
    ),
}

CHAIN_BY_ID: dict[int, Chain] = {c.chain_id: c for c in CHAINS.values()}


def normalize_chain(chain_key: str) -> Chain:
    """Look up a chain by key (case-insensitive)."""
    key = chain_key.strip().lower()
    chain = CHAINS.get(key)
    if chain is None:
        raise ValueError(
            f"Unknown chain '{chain_key}'. Supported: {', '.join(sorted(CHAINS.keys()))}"
        )
    return chain
