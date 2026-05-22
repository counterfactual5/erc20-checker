"""Scan ERC20 Approval events for a wallet address.

Retrieves all Approval logs from Etherscan, deduplicates by (token, spender)
keeping only the latest event, then queries on-chain allowance for each pair.
"""

from __future__ import annotations

from typing import Any

from erc20_checker.common import (
    APPROVAL_TOPIC,
    decode_allowance_from_data,
    encode_topic_address,
    etherscan_request,
    format_units,
    get_block_number,
    query_erc20_allowance,
    query_token_decimals,
    query_token_symbol,
    require_etherscan_api_key,
    resolve_rpc_url,
    topic_address,
    validate_address,
)
from erc20_checker.chains import normalize_chain


def fetch_approval_logs(
    *,
    chain_id: int,
    api_key: str,
    owner_topic: str,
    start_block: int,
    end_block: int,
    chunk_size: int = 20_000,
    max_logs: int = 5_000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch Approval event logs from Etherscan in chunks.

    Returns (logs, metadata).
    """
    logs: list[dict[str, Any]] = []
    chunk_count = 0
    cursor = start_block

    while cursor <= end_block:
        chunk_count += 1
        chunk_end = min(cursor + chunk_size - 1, end_block)
        payload = etherscan_request(
            chain_id=chain_id,
            module="logs",
            action="getLogs",
            api_key=api_key,
            extra_params={
                "fromBlock": str(cursor),
                "toBlock": str(chunk_end),
                "topic0": APPROVAL_TOPIC,
                "topic1": owner_topic,
            },
        )
        for item in payload.get("result") or []:
            if isinstance(item, dict):
                logs.append(item)
                if len(logs) >= max_logs:
                    return logs, {
                        "chunkCount": chunk_count,
                        "truncated": True,
                        "maxLogs": max_logs,
                        "startBlock": start_block,
                        "endBlock": end_block,
                    }
        cursor = chunk_end + 1

    return logs, {
        "chunkCount": chunk_count,
        "truncated": False,
        "maxLogs": max_logs,
        "startBlock": start_block,
        "endBlock": end_block,
    }


def _parse_block_and_index(log: dict[str, Any]) -> tuple[int, int]:
    block_raw = str(log.get("blockNumber") or "0").strip()
    index_raw = str(log.get("logIndex") or "0").strip()
    try:
        bn = int(block_raw, 0)
        li = int(index_raw, 0)
    except ValueError as exc:
        raise RuntimeError(f"invalid log blockNumber/logIndex: {block_raw!r} / {index_raw!r}") from exc
    return bn, li


def latest_approval_per_pair(logs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Deduplicate logs by (token, spender), keeping the latest event per pair."""
    parsed: list[dict[str, Any]] = []
    for log in logs:
        topics = log.get("topics")
        if not isinstance(topics, list) or len(topics) < 3:
            continue
        token_address = str(log.get("address") or "").lower()
        if not token_address:
            continue
        spender = topic_address(str(topics[2])).lower()
        bn, li = _parse_block_and_index(log)
        raw_allowance = decode_allowance_from_data(str(log.get("data") or "0x0"))
        parsed.append({
            "tokenAddress": token_address,
            "spender": spender,
            "rawLastApprovalEventAllowance": raw_allowance,
            "lastApprovalBlock": bn,
            "logIndex": li,
        })

    # Sort newest-first so the first seen pair wins
    parsed.sort(key=lambda x: (x["lastApprovalBlock"], x["logIndex"]), reverse=True)

    seen: set[tuple[str, str]] = set()
    latest: list[dict[str, Any]] = []
    for item in parsed:
        key = (item["tokenAddress"], item["spender"])
        if key in seen:
            continue
        seen.add(key)
        latest.append(item)

    duplicates = len(parsed) - len(latest)
    return latest, {
        "parsedLogRows": len(parsed),
        "uniquePairsFromLogs": len(latest),
        "duplicatePairsSkipped": duplicates,
    }


def scan_approvals(
    chain: str,
    wallet: str,
    *,
    start_block: int | None = None,
    end_block: int | None = None,
    chunk_size: int = 20_000,
    max_logs: int = 5_000,
    rpc_url: str | None = None,
    min_allowance_raw: int = 1,
    include_zero: bool = False,
) -> dict[str, Any]:
    """Scan all ERC20 approvals for a wallet on a given chain.

    Returns a structured report with approval details and revoke transactions.
    """
    chain_obj = normalize_chain(chain)
    wallet_addr = validate_address(wallet, "wallet")
    rpc, rpc_candidates = resolve_rpc_url(rpc_url, chain_obj.chain_id)
    api_key = require_etherscan_api_key()

    # Resolve block range
    if start_block is None:
        start_block = 0
    if end_block is None:
        end_block = get_block_number(rpc)

    owner_topic = encode_topic_address(wallet_addr)

    logs, scan_meta = fetch_approval_logs(
        chain_id=chain_obj.chain_id,
        api_key=api_key,
        owner_topic=owner_topic,
        start_block=start_block,
        end_block=end_block,
        chunk_size=chunk_size,
        max_logs=max_logs,
    )

    latest_events, dedup_meta = latest_approval_per_pair(logs)
    scan_meta = {**scan_meta, **dedup_meta}

    entries: list[dict[str, Any]] = []
    for event in latest_events:
        token_address = event["tokenAddress"]
        spender = event["spender"]
        decimals = query_token_decimals(token_address, rpc)
        symbol = query_token_symbol(token_address, rpc) or token_address
        allowance = query_erc20_allowance(token_address, wallet_addr, spender, rpc)

        if allowance < min_allowance_raw:
            continue
        if allowance == 0 and not include_zero:
            continue

        entries.append({
            "tokenAddress": token_address,
            "tokenSymbol": symbol,
            "spender": spender,
            "rawAllowance": str(allowance),
            "humanAllowance": format_units(allowance, decimals),
            "decimals": decimals,
            "lastApprovalBlock": event["lastApprovalBlock"],
        })

    entries.sort(key=lambda x: int(x["rawAllowance"]), reverse=True)

    return {
        "chain": {"key": chain_obj.key, "chainId": chain_obj.chain_id},
        "wallet": wallet_addr,
        "range": {"startBlock": str(start_block), "endBlock": str(end_block)},
        "scan": scan_meta,
        "logCount": len(logs),
        "approvalCount": len(entries),
        "approvals": entries,
    }
