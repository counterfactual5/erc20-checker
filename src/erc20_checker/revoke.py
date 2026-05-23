"""Build revoke transactions for ERC20 approvals.

Returns unsigned transaction data (to, data, value) and optional gas estimates
— no signing or broadcasting.
"""

from __future__ import annotations

from typing import Any

from erc20_checker.common import build_approve_calldata, estimate_transaction_gas, validate_address


def build_revoke_tx(
    token_address: str,
    spender: str,
) -> dict[str, Any]:
    """Build a transaction to revoke an ERC20 approval (set allowance to 0).

    Parameters
    ----------
    token_address : str
        ERC20 token contract address.
    spender : str
        Address whose allowance should be revoked.

    Returns
    -------
    dict
        Unsigned transaction with keys: ``to``, ``data``, ``value``.
    """
    token = validate_address(token_address, "token")
    spender_addr = validate_address(spender, "spender")
    data = build_approve_calldata(spender_addr, 0)

    return {
        "to": token,
        "data": data,
        "value": "0",
    }


def build_revoke_batch(
    approvals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build revoke transactions for a list of approval entries.

    Each entry must have ``tokenAddress`` and ``spender`` keys.

    Returns a list of dicts with ``tokenAddress``, ``spender``, and ``revokeTx``.
    """
    results: list[dict[str, Any]] = []
    for entry in approvals:
        token = entry.get("tokenAddress", "")
        spender = entry.get("spender", "")
        if not token or not spender:
            continue
        tx = build_revoke_tx(token, spender)
        results.append({
            "tokenAddress": token,
            "spender": spender,
            "revokeTx": tx,
        })
    return results


def estimate_revoke_gas(
    token_address: str,
    spender: str,
    rpc_url: str,
    *,
    from_address: str | None = None,
) -> int:
    """Estimate the gas cost of a revoke transaction.

    Calls ``eth_estimateGas`` on the RPC endpoint.  The result may vary
    depending on whether the spender is a simple EOA or a contract that
    needs extra computation on 0-value approve calls.

    Parameters
    ----------
    token_address : str
        ERC20 token contract address.
    spender : str
        Address whose allowance should be revoked.
    rpc_url : str
        RPC endpoint URL.
    from_address : str | None
        Optional sender address for more accurate estimation.

    Returns
    -------
    int
        Estimated gas units.
    """
    tx = build_revoke_tx(token_address, spender)
    if from_address:
        tx["from"] = validate_address(from_address, "from")
    return estimate_transaction_gas(tx, rpc_url)
