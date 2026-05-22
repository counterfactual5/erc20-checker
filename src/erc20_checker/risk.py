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

    Expects each entry to have ``rawAllowance`` (string of int).
    Returns new list with ``riskLevel`` and ``riskLabel`` added.
    """
    results: list[dict[str, Any]] = []
    for entry in approvals:
        raw = int(entry.get("rawAllowance", "0"))
        level = classify_risk(raw)
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
