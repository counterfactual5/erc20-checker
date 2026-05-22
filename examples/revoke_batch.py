#!/usr/bin/env python3
"""Build revoke transactions for all high-risk approvals on a wallet.

Usage:
    python examples/revoke_batch.py <chain> <wallet_address>

Example:
    python examples/revoke_batch.py ethereum 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

Output:
    A list of unsigned transaction payloads ready for signing.
    This script NEVER signs or broadcasts — you must sign manually.

Environment:
    ETHERSCAN_API_KEY  — Etherscan API key (required)
    ETHEREUM_RPC_URL   — RPC URL for the chain (or RPC_URL as fallback)
"""

import os
import sys

from erc20_checker.scanner import scan_approvals
from erc20_checker.risk import risk_report, summary
from erc20_checker.revoke import build_revoke_batch


def main() -> None:
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <chain> <wallet_address>")
        print("Example: python examples/revoke_batch.py ethereum 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        sys.exit(1)

    chain = sys.argv[1]
    wallet = sys.argv[2]

    if not os.environ.get("ETHERSCAN_API_KEY"):
        print("❌ ETHERSCAN_API_KEY is not set")
        sys.exit(1)

    print(f"🔍 Scanning approvals for {wallet} on {chain}...")
    result = scan_approvals(chain, wallet)
    print(f"   Found {result['approvalCount']} approval(s)")

    if result["approvalCount"] == 0:
        print("   Nothing to revoke. ✅")
        return

    # Risk assessment
    report = risk_report(result["approvals"])
    stats = summary(report)

    # Filter to high-risk only
    high_risk = [e for e in report if e["riskLevel"] == 3]
    print(f"   🔴 HIGH risk: {stats['highRisk']}")
    print(f"   🟡 MEDIUM risk: {stats['mediumRisk']}")
    print(f"   🟢 LOW risk: {stats['lowRisk']}")
    print()

    if not high_risk:
        print("   No HIGH-risk approvals found. Nothing urgent to revoke. ✅")
        print()
        print("   MEDIUM-risk approvals (unknown spenders) may still warrant review.")
        return

    # Build revoke transactions
    print(f"⚠️  Building revoke transactions for {len(high_risk)} HIGH-risk approval(s):")
    print()
    batch = build_revoke_batch(high_risk)
    for i, item in enumerate(batch):
        tx = item["revokeTx"]
        print(f"  [{i + 1}] Token: {item['tokenAddress']}")
        print(f"      Spender: {item['spender']}")
        print(f"      Revoke TX: to={tx['to']}")
        print(f"                 data={tx['data'][:66]}...")

    print()
    print("── ⚠️  SECURITY WARNING ──────────────────────────────────────")
    print("These are UNSIGNED transaction payloads.")
    print("You must sign and broadcast them yourself.")
    print("VERIFY the `to` address and `data` before signing.")
    print("The calldata should be approve(spender, 0).")
    print("──────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
