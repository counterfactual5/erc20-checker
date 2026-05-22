"""CLI entry point — zero dependencies (argparse, stdlib only).

Usage:
    erc20-check scan ethereum 0x...
    erc20-check allowance ethereum 0x... 0xTOKEN 0xSPENDER
    erc20-check revoke ethereum 0x...
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from erc20_checker import __version__
from erc20_checker.allowance import query_allowance
from erc20_checker.chains import CHAINS
from erc20_checker.revoke import build_revoke_batch
from erc20_checker.risk import risk_report, summary
from erc20_checker.scanner import scan_approvals

# ── helpers ─────────────────────────────────────────────────────────────────

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


def _label(spender: str) -> str:
    return KNOWN_LABELS.get(spender.lower(), spender)


def _check_env(var: str) -> None:
    if not os.environ.get(var):
        sys.exit(f"❌ {var} is not set.  export {var}='...'")


# ── subcommands ─────────────────────────────────────────────────────────────

def cmd_scan(args: argparse.Namespace) -> None:
    """Scan all ERC20 approvals for a wallet."""
    _check_env("ETHERSCAN_API_KEY")

    chain: str = args.chain
    wallet: str = args.wallet
    rpc_url: str | None = args.rpc_url

    print(f"🔍 Scanning {wallet} on {chain}...")
    result = scan_approvals(
        chain,
        wallet,
        start_block=args.start_block,
        end_block=args.end_block,
        rpc_url=rpc_url,
        max_logs=args.max_logs,
        include_zero=args.include_zero,
    )

    n = result["approvalCount"]
    print(f"   {n} approval(s) found  (blocks {result['range']['startBlock']} → {result['range']['endBlock']})")
    if n == 0:
        return

    report = risk_report(result["approvals"])
    stats = summary(report)

    print(f"   🔴 {stats['highRisk']} HIGH  🟡 {stats['mediumRisk']} MEDIUM  🟢 {stats['lowRisk']} LOW")
    print()

    if args.quiet:
        return

    header = f"  {'Token':<14} {'Spender':<32} {'Allowance':<18} {'Risk'}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for entry in report:
        token = (entry.get("tokenSymbol") or entry["tokenAddress"][:10])[:13]
        spender_label = _label(entry["spender"])[:31]
        allowance = entry.get("humanAllowance", "?")[:17]
        risk = entry["riskLabel"]
        print(f"  {token:<14} {spender_label:<32} {allowance:<18} {risk}")


def cmd_allowance(args: argparse.Namespace) -> None:
    """Query allowance for a specific token-spender pair."""
    chain: str = args.chain
    wallet: str = args.wallet
    token: str = args.token
    spender: str = args.spender
    rpc_url: str | None = args.rpc_url

    result = query_allowance(chain, wallet, token, spender, rpc_url=rpc_url)

    print(f"Chain:      {result['chain']['key']} (ID {result['chain']['chainId']})")
    print(f"Token:      {result['token']['symbol']} ({result['token']['address']})")
    print(f"  Decimals: {result['token']['decimals']}")
    print(f"Spender:    {result['spender']}")
    print(f"Allowance:  {result['humanAllowance']}  (raw: {result['rawAllowance']})")


def cmd_revoke(args: argparse.Namespace) -> None:
    """Build revoke transactions for HIGH-risk approvals."""
    _check_env("ETHERSCAN_API_KEY")

    chain: str = args.chain
    wallet: str = args.wallet
    rpc_url: str | None = args.rpc_url

    print(f"🔍 Scanning {wallet} on {chain}...")
    result = scan_approvals(chain, wallet, rpc_url=rpc_url)

    approvals = result["approvals"]
    if not approvals:
        print("   No approvals found. Nothing to revoke.")
        return

    report = risk_report(approvals)
    stats = summary(report)

    print(f"   🔴 {stats['highRisk']} HIGH  🟡 {stats['mediumRisk']} MEDIUM  🟢 {stats['lowRisk']} LOW")

    high_risk = [e for e in report if e["riskLevel"] == 3]
    if not high_risk:
        print("   No HIGH-risk approvals. Nothing urgent. ✅")
        return

    batch = build_revoke_batch(high_risk)
    for i, item in enumerate(batch):
        tx: dict[str, Any] = item["revokeTx"]
        print(f"  [{i + 1}] Token: {item['tokenAddress']}")
        print(f"      Spender: {item['spender']}")
        print(f"      TX: to={tx['to']}")
        print(f"          data={tx['data'][:66]}...")
        print()

    print("⚠️  These are UNSIGNED payloads. Verify before signing.")
    print("   The calldata should be approve(spender, 0).")

# ── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="erc20-check",
        description="Scan ERC20 approvals, assess risk, and build revoke transactions.",
    )
    parser.add_argument("--version", action="version", version=f"erc20-check {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # ── scan ──
    p_scan = sub.add_parser("scan", help="Scan all approvals for a wallet")
    p_scan.add_argument("chain", choices=sorted(CHAINS.keys()), help="Chain name")
    p_scan.add_argument("wallet", help="Wallet address (0x...)")
    p_scan.add_argument("--start-block", type=int, default=0, help="Start block (default: 0)")
    p_scan.add_argument("--end-block", type=int, help="End block (default: latest)")
    p_scan.add_argument("--rpc-url", help="Override RPC URL")
    p_scan.add_argument("--max-logs", type=int, default=5000, help="Max logs to fetch (default: 5000)")
    p_scan.add_argument("--include-zero", action="store_true", help="Include zero-allowance entries")
    p_scan.add_argument("-q", "--quiet", action="store_true", help="Only show summary, not details")
    p_scan.set_defaults(func=cmd_scan)

    # ── allowance ──
    p_alw = sub.add_parser("allowance", help="Check allowance for a token-spender pair")
    p_alw.add_argument("chain", choices=sorted(CHAINS.keys()), help="Chain name")
    p_alw.add_argument("wallet", help="Owner address (0x...)")
    p_alw.add_argument("token", help="ERC20 token address (0x...)")
    p_alw.add_argument("spender", help="Spender address (0x...)")
    p_alw.add_argument("--rpc-url", help="Override RPC URL")
    p_alw.set_defaults(func=cmd_allowance)

    # ── revoke ──
    p_rev = sub.add_parser("revoke", help="Build revoke TXs for HIGH-risk approvals")
    p_rev.add_argument("chain", choices=sorted(CHAINS.keys()), help="Chain name")
    p_rev.add_argument("wallet", help="Wallet address (0x...)")
    p_rev.add_argument("--rpc-url", help="Override RPC URL")
    p_rev.set_defaults(func=cmd_revoke)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
