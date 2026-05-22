"""Common utilities — RPC, Etherscan, address validation, formatting.

Pure Python standard library.  No external CLI tools (cast/foundry) required.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from decimal import Decimal
from typing import Any

from erc20_checker.chains import CHAIN_BY_ID, Chain, normalize_chain

# ── Address validation ────────────────────────────────────────────────────

_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def validate_address(address: str, label: str = "address") -> str:
    """Validate and return a checksummed-lowered address."""
    addr = str(address).strip()
    if not _ADDRESS_RE.match(addr):
        raise ValueError(f"Invalid {label}: {address!r}")
    return addr.lower()


# ── RPC helpers ────────────────────────────────────────────────────────────

_GLOBAL_RPC_ENV = ("ETH_RPC_URL", "RPC_URL")


def rpc_env_candidates(chain_id: int) -> list[str]:
    """Return environment variable names to probe for an RPC URL."""
    chain = CHAIN_BY_ID.get(chain_id)
    candidates: list[str] = []
    if chain:
        key = chain.key.upper()
        candidates.extend([f"{key}_RPC_URL", f"RPC_URL_{key}", f"{key}_MAINNET_RPC_URL"])
    candidates.extend(_GLOBAL_RPC_ENV)
    # deduplicate preserving order
    seen: set[str] = set()
    return [c for c in candidates if not (c in seen or seen.add(c))]  # type: ignore[func-returns-value]


def resolve_rpc_url(explicit: str | None, chain_id: int) -> tuple[str, list[str]]:
    """Resolve an RPC URL from an explicit value or environment variables."""
    if explicit:
        return explicit, []
    candidates = rpc_env_candidates(chain_id)
    for env_name in candidates:
        value = os.environ.get(env_name)
        if value:
            return value, candidates
    raise RuntimeError(
        f"RPC URL not configured. Set one of {', '.join(candidates)} or pass --rpc-url."
    )


def _json_rpc(method: str, params: list[Any], rpc_url: str, timeout: int = 30) -> Any:
    """Send a JSON-RPC request and return the ``result`` field."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }).encode("utf-8")
    req = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read())
    if body.get("error"):
        raise RuntimeError(f"RPC error: {body['error']}")
    return body.get("result")


def _decode_int(hex_or_int: Any) -> int:
    """Decode a hex string or int from an RPC response."""
    if isinstance(hex_or_int, int):
        return hex_or_int
    if isinstance(hex_or_int, str):
        return int(hex_or_int, 0)
    raise ValueError(f"Cannot decode integer from {type(hex_or_int)}: {hex_or_int}")


# ── ERC-20 ABI selectors ──────────────────────────────────────────────────

_SEL_ALLOWANCE = "0xdd62ed3e"   # allowance(address,address)
_SEL_DECIMALS = "0x313ce567"    # decimals()
_SEL_SYMBOL = "0x95d89b41"      # symbol()
_SEL_APPROVE = "0x095ea7b3"     # approve(address,uint256)


def _encode_address(addr: str) -> str:
    return addr.lower().replace("0x", "").rjust(64, "0")


def _encode_uint256(val: int) -> str:
    return hex(val)[2:].rjust(64, "0")


# ── Public RPC queries ────────────────────────────────────────────────────

def eth_call(to: str, data: str, rpc_url: str, block: str = "latest") -> str:
    """Make an eth_call and return the raw hex result."""
    result = _json_rpc("eth_call", [{"to": to, "data": data}, block], rpc_url)
    if result is None:
        raise RuntimeError(f"eth_call to {to} returned null (contract may have reverted)")
    return result


def get_block_number(rpc_url: str) -> int:
    """Get the latest block number."""
    result = _json_rpc("eth_blockNumber", [], rpc_url)
    return _decode_int(result)


def query_erc20_allowance(token: str, owner: str, spender: str, rpc_url: str) -> int:
    """Query ERC-20 allowance via eth_call."""
    data = _SEL_ALLOWANCE + _encode_address(owner) + _encode_address(spender)
    result = eth_call(token, "0x" + data, rpc_url)
    return _decode_int(result)


def query_token_decimals(token: str, rpc_url: str) -> int:
    """Query ERC-20 decimals() via eth_call."""
    result = eth_call(token, _SEL_DECIMALS, rpc_url)
    return _decode_int(result)


def query_token_symbol(token: str, rpc_url: str) -> str | None:
    """Query ERC-20 symbol() via eth_call. Returns None on failure."""
    try:
        raw = eth_call(token, _SEL_SYMBOL, rpc_url)
    except RuntimeError:
        return None
    return _decode_string(raw)


def _decode_string(hex_val: str) -> str:
    """Decode a dynamic ABI string from hex."""
    clean = hex_val.replace("0x", "")
    if len(clean) < 128:
        return ""
    length = int(clean[64:128], 16)
    hex_str = clean[128 : 128 + length * 2]
    return bytes.fromhex(hex_str).decode("utf-8", errors="replace")


# ── Etherscan API ─────────────────────────────────────────────────────────

_EMPTY_RESULT_MESSAGES = {
    "No transactions found",
    "No internal transactions found",
    "No token transfers found",
    "No records found",
}


def require_etherscan_api_key() -> str:
    """Return ETHERSCAN_API_KEY from environment or raise."""
    api_key = os.environ.get("ETHERSCAN_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ETHERSCAN_API_KEY is not configured")
    return api_key


def etherscan_request(
    *,
    chain_id: int,
    module: str,
    action: str,
    api_key: str,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make an Etherscan API request and return the parsed JSON payload."""
    from erc20_checker.chains import CHAIN_BY_ID

    chain = CHAIN_BY_ID.get(chain_id)
    if chain is None:
        raise ValueError(f"Unknown chain_id: {chain_id}")

    params: dict[str, str] = {
        "chainid": str(chain_id),
        "module": module,
        "action": action,
        "apikey": api_key,
    }
    if extra_params:
        for k, v in extra_params.items():
            if v is not None:
                params[k] = str(v)

    url = chain.etherscan_url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Etherscan request failed for {module}.{action}: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"Etherscan {module}.{action} returned non-object JSON")

    status = str(payload.get("status", ""))
    message = str(payload.get("message", ""))
    result = payload.get("result")

    if status == "1":
        return payload

    if isinstance(result, str) and result in _EMPTY_RESULT_MESSAGES:
        payload["result"] = []
        return payload

    if module == "logs" and action == "getLogs" and isinstance(result, list) and len(result) == 0:
        payload["result"] = []
        return payload

    details = [x for x in [message, str(result) if result else ""] if x]
    raise RuntimeError(f"Etherscan {module}.{action} error: {' | '.join(details)}")


# ── Formatting ─────────────────────────────────────────────────────────────

def format_units(raw_value: int, decimals: int) -> str:
    """Format a raw uint256 token amount as a human-readable decimal string."""
    scaled = Decimal(raw_value) / (Decimal(10) ** decimals)
    text = format(scaled, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


# ── Approval topic helpers ─────────────────────────────────────────────────

APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"


def topic_address(topic_hex: str) -> str:
    """Extract a 0x-prefixed address from a 32-byte topic."""
    value = str(topic_hex)
    if value.startswith("0x"):
        value = value[2:]
    if len(value) != 64:
        raise RuntimeError(f"invalid topic length for address: {topic_hex}")
    return "0x" + value[-40:]


def encode_topic_address(address: str) -> str:
    """Encode an address as a 32-byte EVM topic."""
    cleaned = validate_address(address).replace("0x", "")
    return "0x" + ("0" * 24) + cleaned


def decode_allowance_from_data(data_hex: str) -> int:
    """Decode the uint256 value from Approval event data."""
    value = str(data_hex or "0x0")
    if value.startswith("0x"):
        value = value[2:]
    if value == "":
        return 0
    return int(value, 16)


# ── Revoke calldata ───────────────────────────────────────────────────────

def build_approve_calldata(spender: str, amount: int) -> str:
    """Build approve(address,uint256) calldata."""
    return "0x" + _SEL_APPROVE.replace("0x", "") + _encode_address(spender) + _encode_uint256(amount)
