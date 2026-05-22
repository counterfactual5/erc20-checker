"""Build revoke transactions for ERC20 approvals.

Returns unsigned transaction data (to, data, value) — no signing or broadcasting.
"""

from __future__ import annotations

from typing import Any

from erc20_checker.common import build_approve_calldata, validate_address


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
