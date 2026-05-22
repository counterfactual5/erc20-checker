# Changelog

All notable changes to erc20-checker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-05-23

### Added
- Core scanner: `scan_approvals()` — scan all ERC20 Approval events for a wallet via Etherscan v2 API
- Single allowance query: `query_allowance()` — check allowance for a specific (owner, token, spender) triple
- Risk scoring: `classify_risk()` / `risk_report()` / `summary()` — three-tier risk assessment (HIGH/MEDIUM/LOW) with `KNOWN_SPENDERS` whitelist
- Revoke transaction builder: `build_revoke_tx()` / `build_revoke_batch()` — unsigned transaction payloads for `approve(spender, 0)`
- Multi-chain support: Ethereum, Base, Arbitrum, Optimism, Polygon (unified Etherscan v2 API)
- Pure Python JSON-RPC implementation — zero external dependencies
- Manual ABI encoding (allowance, decimals, symbol, approve selectors)
- 22 tests covering all 6 modules
- GitHub Actions CI (Python 3.10, 3.11, 3.12)
- MIT License

[0.1.0]: https://github.com/counterfactual5/erc20-checker/releases/tag/v0.1.0
