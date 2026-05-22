<div align="center">

# 🔍 ERC20 Checker

**Scan ERC20 approvals · Assess risk · Build revoke transactions**

*Zero dependencies · Pure Python · Multi-chain*

[![PyPI](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://pypi.org/project/erc20-checker/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/counterfactual5/erc20-checker/actions/workflows/test.yml/badge.svg)](https://github.com/counterfactual5/erc20-checker/actions/workflows/test.yml)

</div>

---

## ⚡ Quick Start

```python
from erc20_checker.scanner import scan_approvals
from erc20_checker.risk import risk_report, summary

# Scan all approvals for a wallet on Ethereum
result = scan_approvals("ethereum", "0xYourWalletAddress")

# Add risk assessment
report = risk_report(result["approvals"])
print(summary(report))
# {'total': 3, 'highRisk': 1, 'mediumRisk': 0, 'lowRisk': 2}
```

That's it. Three lines of code to audit every ERC20 approval on your wallet.

## 🛡️ Risk Levels

| Level | Criteria | Meaning |
|:-----:|----------|---------|
| 🔴 **HIGH** | Unlimited approval (≥ 2¹²⁸) | Spender can drain **all** your tokens. Revoke immediately. |
| 🟡 **MEDIUM** | Unknown spender contract | Spender is not a recognized protocol. Exercise caution. |
| 🟢 **LOW** | Finite approval, known spender | Normal DeFi interaction. Low risk. |

## 📦 Install

```bash
pip install erc20-checker
```

Or from source:

```bash
git clone https://github.com/counterfactual5/erc20-checker.git
cd erc20-checker
pip install -e .
```

## 🔧 Usage

### Scan All Approvals

```python
from erc20_checker.scanner import scan_approvals

result = scan_approvals(
    chain="base",
    wallet="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    start_block=0,
    max_logs=5000,
)

for approval in result["approvals"]:
    print(f"{approval['tokenSymbol']}: {approval['humanAllowance']} → {approval['spender']}")
```

### Check Single Allowance

```python
from erc20_checker.allowance import query_allowance

result = query_allowance(
    chain="ethereum",
    wallet="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    spender="0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",  # Uniswap Router
)
print(result["humanAllowance"])  # e.g. "115792089237316195423570985008687907853269984665640564039457584007913129639935"
```

### Risk Assessment

```python
from erc20_checker.risk import risk_report, summary

report = risk_report(result["approvals"])
for entry in report:
    print(f"{entry['tokenSymbol']}: {entry['riskLabel']} (infinite: {entry['isInfinite']})")

# Aggregate
print(summary(report))
```

### Build Revoke Transactions

```python
from erc20_checker.revoke import build_revoke_tx, build_revoke_batch

# Single revoke
tx = build_revoke_tx(
    token_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    spender="0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
)
# tx = {"to": "0xa0b8...", "data": "0x095ea7b3...00000000", "value": "0"}

# Batch revoke for all high-risk approvals
high_risk = [e for e in report if e["riskLevel"] == 3]
batch = build_revoke_batch(high_risk)
```

## 📋 Example Output

```json
{
  "chain": {"key": "ethereum", "chainId": 1},
  "wallet": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
  "approvalCount": 3,
  "approvals": [
    {
      "tokenAddress": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
      "tokenSymbol": "USDC",
      "spender": "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",
      "rawAllowance": "115792089237316195423570985008687907853269984665640564039457584007913129639935",
      "humanAllowance": "115792089237316195423570985008687907853269984665640564039457584007913129639935",
      "decimals": 6,
      "lastApprovalBlock": 19283000
    }
  ]
}
```

## 🔗 Supported Chains

| Chain | Chain ID | Etherscan |
|-------|----------|-----------|
| Ethereum | 1 | etherscan.io |
| Base | 8453 | basescan.org |
| Arbitrum | 42161 | arbiscan.io |
| Optimism | 10 | optimistic.etherscan.io |
| Polygon | 137 | polygonscan.com |

## 📊 Comparison

| Feature | **erc20-checker** | revoke.cash | Manual (Etherscan) |
|---------|:-:|:-:|:-:|
| Programmatic API | ✅ | ❌ (web only) | ❌ |
| Multi-chain | ✅ 5 chains | ✅ | Per-chain manual |
| Risk scoring | ✅ Built-in | ⚠️ Basic | ❌ |
| Batch revoke data | ✅ | ✅ | ❌ |
| Zero dependencies | ✅ | N/A | N/A |
| Self-hosted / offline | ✅ | ❌ | ❌ |

## ⚙️ Configuration

Set environment variables:

```bash
# Required for scanning (Etherscan API)
export ETHERSCAN_API_KEY="your-api-key"

# RPC URL (auto-detected by chain name)
export ETHEREUM_RPC_URL="https://eth.llamarpc.com"
export BASE_RPC_URL="https://mainnet.base.org"
export ARBITRUM_RPC_URL="https://arb1.arbitrum.io/rpc"
# ... or use a generic fallback
export RPC_URL="https://eth.llamarpc.com"
```

## ⚠️ Security

- **Read-only**: This library only *reads* on-chain data and builds unsigned transaction payloads. It never signs or broadcasts transactions.
- **No private keys**: No wallet private keys or seed phrases are ever needed.
- **No external dependencies**: Only Python standard library — minimal attack surface.
- **Verify before revoking**: Always verify the `to` address and `data` in the revoke transaction before signing. The calldata should be `approve(spender, 0)`.

## 📄 License

[MIT](LICENSE) © 2026 counterfactual5
