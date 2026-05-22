#!/usr/bin/env python3
"""Check the current ERC20 allowance for a specific (token, spender) pair.

Usage:
    python examples/check_allowance.py <chain> <wallet> <token> <spender>

Example:
    # Check USDC allowance for Uniswap Universal Router
    python examples/check_allowance.py ethereum \\
        0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \\
        0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 \\
        0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD

Environment:
    ETHERSCAN_API_KEY  — not needed for single allowance checks
    ETHEREUM_RPC_URL   — RPC URL for the chain (or RPC_URL as fallback)
"""

import sys

from erc20_checker.allowance import query_allowance


def main() -> None:
    if len(sys.argv) < 5:
        print(f"Usage: python {sys.argv[0]} <chain> <wallet> <token> <spender>")
        print()
        print("Common token addresses:")
        print("  USDC (Ethereum):  0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
        print("  USDT (Ethereum):  0xdAC17F958D2ee523a2206206994597C13D831ec7")
        print("  DAI  (Ethereum):  0x6B175474E89094C44Da98b954EedeAC495271d0F")
        print("  WETH (Ethereum):  0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
        print()
        print("Common spender addresses:")
        print("  Uniswap V3 SwapRouter:  0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45")
        print("  Uniswap UniversalRouter: 0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7Fad")
        print("  1inch V6 Router:         0x111111125421cA6dc452d289314280a0f8842A65")
        print("  OpenSea Seaport 1.6:     0x0000000000000068F116a894984e2DB1123eB395")
        sys.exit(1)

    chain = sys.argv[1]
    wallet = sys.argv[2]
    token = sys.argv[3]
    spender = sys.argv[4]

    result = query_allowance(chain, wallet, token, spender)

    print(f"Chain:      {result['chain']['key']} (chain ID {result['chain']['chainId']})")
    print(f"Wallet:     {result['wallet']}")
    print(f"Token:      {result['token']['symbol']} ({result['token']['address']})")
    print(f"  Decimals: {result['token']['decimals']}")
    print(f"Spender:    {result['spender']}")
    print(f"Allowance:  {result['humanAllowance']} (raw: {result['rawAllowance']})")


if __name__ == "__main__":
    main()
