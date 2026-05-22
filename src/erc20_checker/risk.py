"""Risk scoring for ERC20 approvals.

Assigns risk levels based on allowance magnitude and spender characteristics.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any

# uint256 max = 2^256 - 1
UINT256_MAX = (1 << 256) - 1

# "Infinite" is commonly considered anything >= 2^128 (~3.4e38)
_INFINITE_THRESHOLD = 1 << 128

# Well-known protocol contract addresses (lowercase).
# These are predominantly Ethereum mainnet addresses.
# Many are deterministic CREATE2 deployments valid across multiple EVM chains.
# PRs welcome for chain-specific additions.
KNOWN_SPENDERS: set[str] = {
    # ── Uniswap ──
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap V2 Router
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",  # Uniswap V3 SwapRouter02
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",  # Uniswap Universal Router
    "0x000000000004444c5dc75cb358380d2e3de08a90",  # Uniswap V4 PoolManager
    # ── 1inch ──
    "0x111111125421ca6dc452d289314280a0f8842a65",  # 1inch V6 AggregationRouter
    "0x1111111254eeb25477b68fb85ed929f73a960582",  # 1inch V5 AggregationRouter
    # ── OpenSea ──
    "0x0000000000000068f116a894984e2db1123eb395",  # Seaport 1.6
    "0x00000000000000adc04c56bf30ac9d3c0aaf14dc",  # Seaport 1.5
    "0x00000000000001ad428e4906ae43d8f9852d0dd6",  # Seaport 1.4
    # ── Permit2 ──
    "0x000000000022d473030f116ddee9f6b43ac78ba3",  # Permit2 (cross-chain)
    # ── Aave ──
    "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2",  # Aave V3 Pool
    # ── CoWSwap ──
    "0x9008d19f58aabd9ed0d60971565aa8510560ab41",  # CoWSwap Settlement
    # ── WETH ──
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH (Ethereum)
}


class RiskLevel(IntEnum):
    """Risk severity levels."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


RISK_LABELS: dict[RiskLevel, str] = {
    RiskLevel.LOW: "🟢 LOW",
    RiskLevel.MEDIUM: "🟡 MEDIUM",
    RiskLevel.HIGH: "🔴 HIGH",
}


def classify_risk(raw_allowance: int, *, is_known_spender: bool = True) -> RiskLevel:
    """Classify the risk level of an approval.

    Parameters
    ----------
    raw_allowance : int
        The raw uint256 allowance value.
    is_known_spender : bool
        Whether the spender is a recognized protocol contract.

    Returns
    -------
    RiskLevel
    """
    if raw_allowance >= _INFINITE_THRESHOLD:
        return RiskLevel.HIGH
    if not is_known_spender:
        return RiskLevel.MEDIUM
    if raw_allowance > 0:
        return RiskLevel.LOW
    return RiskLevel.LOW


def risk_report(approvals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add risk assessment to a list of approval entries.

    Expects each entry to have ``rawAllowance`` (string of int) and ``spender`` (hex address).
    Returns new list with ``riskLevel`` and ``riskLabel`` added.
    """
    results: list[dict[str, Any]] = []
    for entry in approvals:
        raw = int(entry.get("rawAllowance", "0"))
        spender = str(entry.get("spender", "")).strip().lower()
        is_known = spender in KNOWN_SPENDERS if spender else False
        level = classify_risk(raw, is_known_spender=is_known)
        results.append({
            **entry,
            "riskLevel": level.value,
            "riskLabel": RISK_LABELS[level],
            "isInfinite": raw >= _INFINITE_THRESHOLD,
        })
    return results


def summary(report: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a summary of risk levels from a risk report."""
    counts = {level.value: 0 for level in RiskLevel}
    for entry in report:
        lvl = entry.get("riskLevel", RiskLevel.LOW.value)
        counts[lvl] = counts.get(lvl, 0) + 1

    return {
        "total": len(report),
        "highRisk": counts.get(RiskLevel.HIGH.value, 0),
        "mediumRisk": counts.get(RiskLevel.MEDIUM.value, 0),
        "lowRisk": counts.get(RiskLevel.LOW.value, 0),
    }
