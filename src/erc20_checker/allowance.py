"""Query current ERC20 allowance for a wallet/spender pair."""

from __future__ import annotations

from typing import Any

from erc20_checker.common import (
    format_units,
    query_erc20_allowance,
    query_token_decimals,
    query_token_symbol,
    resolve_rpc_url,
    validate_address,
)
from erc20_checker.chains import normalize_chain


def query_allowance(
    chain: str,
    wallet: str,
    token: str,
    spender: str,
    *,
    rpc_url: str | None = None,
) -> dict[str, Any]:
    """Query the current ERC20 allowance for a wallet/spender pair.

    Parameters
    ----------
    chain : str
        Chain key (e.g. "ethereum", "base", "arbitrum").
    wallet : str
        Owner address.
    token : str
        ERC20 token address.
    spender : str
        Spender contract address.
    rpc_url : str | None
        Explicit RPC URL (optional).

    Returns
    -------
    dict
        Structured allowance report.
    """
    chain_obj = normalize_chain(chain)
    wallet_addr = validate_address(wallet, "wallet")
    spender_addr = validate_address(spender, "spender")
    token_addr = validate_address(token, "token")
    rpc, rpc_candidates = resolve_rpc_url(rpc_url, chain_obj.chain_id)

    decimals = query_token_decimals(token_addr, rpc)
    symbol = query_token_symbol(token_addr, rpc) or token_addr
    raw_allowance = query_erc20_allowance(token_addr, wallet_addr, spender_addr, rpc)

    return {
        "chain": {"key": chain_obj.key, "chainId": chain_obj.chain_id},
        "wallet": wallet_addr,
        "spender": spender_addr,
        "token": {
            "address": token_addr,
            "symbol": symbol,
            "decimals": decimals,
        },
        "rawAllowance": str(raw_allowance),
        "humanAllowance": format_units(raw_allowance, decimals),
    }
