#!/usr/bin/env python3
"""Scan all ERC20 approvals for a wallet and show risk summary.

Usage:
    python examples/scan_wallet.py <chain> <wallet_address>

Example:
    python examples/scan_wallet.py ethereum 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

Environment:
    ETHERSCAN_API_KEY  — Etherscan API key (required)
    ETHEREUM_RPC_URL   — RPC URL for Ethereum (or RPC_URL as fallback)
    BASE_RPC_URL       — RPC URL for Base
    ... (one per chain, or use generic RPC_URL)
"""

import os
import sys

from erc20_checker.scanner import scan_approvals
from erc20_checker.risk import risk_report, summary

# ── helpers ─────────────────────────────────────────────────────────────────

# Known protocol labels for common spenders (display only)
KNOWN_LABELS: dict[str, str] = {
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3 SwapRouter",
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "Uniswap Universal Router",
    "0x000000000004444c5dc75cb358380d2e3de08a90": "Uniswap V4 PoolManager",
    "0x111111125421ca6dc452d289314280a0f8842a65": "1inch V6 Router",
    "0x0000000000000068f116a894984e2db1123eb395": "OpenSea Seaport 1.6",
    "0x000000000022d473030f116ddee9f6b43ac78ba3": "Permit2",
    "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2": "Aave V3 Pool",
    "0x9008d19f58aabd9ed0d60971565aa8510560ab41": "CoWSwap Settlement",
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH",
}


def label(spender: str) -> str:
    """Return a human-readable label for a known spender, or the address."""
    return KNOWN_LABELS.get(spender, spender)


# ── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <chain> <wallet_address>")
        print("Example: python examples/scan_wallet.py ethereum 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        sys.exit(1)

    chain = sys.argv[1]
    wallet = sys.argv[2]

    # Check required env vars
    if not os.environ.get("ETHERSCAN_API_KEY"):
        print("❌ ETHERSCAN_API_KEY is not set")
        print("   export ETHERSCAN_API_KEY='your-key'")
        sys.exit(1)

    print(f"🔍 Scanning {wallet} on {chain}...")
    result = scan_approvals(chain, wallet)

    print(f"   Found {result['approvalCount']} approval(s)")
    print(f"   Block range: {result['range']['startBlock']} → {result['range']['endBlock']}")
    print(f"   Logs processed: {result['logCount']}")
    print()

    if result["approvalCount"] == 0:
        print("   No active approvals found. ✅")
        return

    # Risk assessment
    report = risk_report(result["approvals"])
    stats = summary(report)

    # Summary
    print(f"🛡️  Risk Summary: {stats['total']} total | "
          f"🔴 {stats['highRisk']} HIGH | "
          f"🟡 {stats['mediumRisk']} MEDIUM | "
          f"🟢 {stats['lowRisk']} LOW")
    print()

    # Detailed report
    print(f"{'Token':<12} {'Spender':<30} {'Allowance':<18} {'Risk':<14} {'Infinite?'}")
    print("-" * 90)
    for entry in report:
        token = entry.get("tokenSymbol", entry["tokenAddress"][:10])[:11]
        spender_label = label(entry["spender"])[:29]
        allowance = entry.get("humanAllowance", "?")[:17]
        risk = entry["riskLabel"]
        infinite = "⚠️ YES" if entry.get("isInfinite") else ""
        print(f"{token:<12} {spender_label:<30} {allowance:<18} {risk:<14} {infinite}")


if __name__ == "__main__":
    main()
