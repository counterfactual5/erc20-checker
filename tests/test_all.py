"""Tests for erc20_checker package."""

from unittest.mock import MagicMock, patch

import erc20_checker
from erc20_checker.chains import CHAINS, CHAIN_BY_ID, normalize_chain
from erc20_checker.common import (
    build_approve_calldata,
    decode_allowance_from_data,
    encode_topic_address,
    format_units,
    topic_address,
    validate_address,
)
from erc20_checker.risk import RiskLevel, classify_risk, risk_report, summary
from erc20_checker.revoke import build_revoke_tx, build_revoke_batch
from erc20_checker.allowance import query_allowance
from erc20_checker.scanner import scan_approvals


# ── chains ──────────────────────────────────────────────────────────────────


class TestChains:
    def test_supported_chains(self):
        assert "ethereum" in CHAINS
        assert "base" in CHAINS
        assert "arbitrum" in CHAINS
        assert "optimism" in CHAINS
        assert "polygon" in CHAINS

    def test_chain_by_id(self):
        assert CHAIN_BY_ID[1].key == "ethereum"
        assert CHAIN_BY_ID[8453].key == "base"
        assert CHAIN_BY_ID[42161].key == "arbitrum"

    def test_normalize_chain(self):
        chain = normalize_chain("Ethereum")
        assert chain.key == "ethereum"
        chain = normalize_chain("  base  ")
        assert chain.key == "base"

    def test_normalize_chain_unknown(self):
        try:
            normalize_chain("solana")
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass


# ── common ──────────────────────────────────────────────────────────────────


class TestCommon:
    def test_validate_address(self):
        assert validate_address("0x" + "ab" * 20) == "0x" + "ab" * 20

    def test_validate_address_invalid(self):
        try:
            validate_address("0x123")
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass

    def test_topic_address(self):
        addr = topic_address("0x" + "00" * 12 + "ab" * 20)
        assert addr == "0x" + "ab" * 20

    def test_encode_topic_address(self):
        result = encode_topic_address("0x" + "ab" * 20)
        assert result.startswith("0x")
        assert result.endswith("ab" * 20)
        assert len(result) == 66

    def test_decode_allowance_zero(self):
        assert decode_allowance_from_data("0x0") == 0
        assert decode_allowance_from_data("0x") == 0

    def test_decode_allowance_value(self):
        assert decode_allowance_from_data("0xff") == 255

    def test_format_units(self):
        assert format_units(1_000_000, 6) == "1"
        assert format_units(1_500_000, 6) == "1.5"
        assert format_units(0, 18) == "0"

    def test_build_approve_calldata(self):
        spender = "0x" + "ab" * 20
        data = build_approve_calldata(spender, 0)
        assert data.startswith("0x095ea7b3")
        assert len(data) == 138  # 4 + 64 + 64 hex chars + 0x


# ── risk ────────────────────────────────────────────────────────────────────


class TestRisk:
    def test_classify_infinite(self):
        assert classify_risk(2**256 - 1) == RiskLevel.HIGH
        assert classify_risk(2**128) == RiskLevel.HIGH

    def test_classify_unknown_spender(self):
        """spender not in KNOWN_SPENDERS → MEDIUM"""
        assert classify_risk(1000, is_known_spender=False) == RiskLevel.MEDIUM

    def test_classify_known_spender(self):
        """known spender with finite allowance → LOW"""
        assert classify_risk(1000, is_known_spender=True) == RiskLevel.LOW
        assert classify_risk(1, is_known_spender=True) == RiskLevel.LOW

    def test_risk_report_with_known_and_unknown(self):
        approvals = [
            {"rawAllowance": str(2**256 - 1), "spender": "0x" + "aa" * 20},
            {"rawAllowance": "1000", "spender": "0x" + "bb" * 20},
            # Uniswap V2 Router (known) → should be LOW
            {"rawAllowance": "5000000", "spender": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"},
        ]
        report = risk_report(approvals)
        assert len(report) == 3
        assert report[0]["riskLevel"] == RiskLevel.HIGH.value   # infinite
        assert report[1]["riskLevel"] == RiskLevel.MEDIUM.value   # unknown
        assert report[2]["riskLevel"] == RiskLevel.LOW.value     # known (Uniswap V2)
        assert report[0]["isInfinite"] is True
        assert report[1]["isInfinite"] is False

    def test_summary(self):
        report = [
            {"riskLevel": 3},
            {"riskLevel": 3},
            {"riskLevel": 2},
            {"riskLevel": 1},
        ]
        s = summary(report)
        assert s["total"] == 4
        assert s["highRisk"] == 2
        assert s["mediumRisk"] == 1
        assert s["lowRisk"] == 1


# ── revoke ──────────────────────────────────────────────────────────────────


class TestRevoke:
    def test_build_revoke_tx(self):
        token = "0x" + "aa" * 20
        spender = "0x" + "bb" * 20
        tx = build_revoke_tx(token, spender)
        assert tx["to"] == token
        assert tx["data"].startswith("0x095ea7b3")
        assert tx["value"] == "0"

    def test_build_revoke_batch(self):
        approvals = [
            {"tokenAddress": "0x" + "aa" * 20, "spender": "0x" + "bb" * 20},
            {"tokenAddress": "0x" + "cc" * 20, "spender": "0x" + "dd" * 20},
        ]
        batch = build_revoke_batch(approvals)
        assert len(batch) == 2
        assert all("revokeTx" in b for b in batch)


# ── allowance (mocked RPC) ──────────────────────────────────────────────────


class TestAllowance:
    @patch("erc20_checker.allowance.query_token_symbol")
    @patch("erc20_checker.allowance.query_token_decimals")
    @patch("erc20_checker.allowance.query_erc20_allowance")
    @patch("erc20_checker.allowance.resolve_rpc_url")
    def test_query_allowance(self, mock_rpc, mock_allow, mock_dec, mock_sym):
        mock_rpc.return_value = ("http://localhost:8545", [])
        mock_allow.return_value = 1000000
        mock_dec.return_value = 6
        mock_sym.return_value = "USDC"

        result = query_allowance("ethereum", "0x" + "aa" * 20, "0x" + "bb" * 20, "0x" + "cc" * 20)
        assert result["rawAllowance"] == "1000000"
        assert result["humanAllowance"] == "1"
        assert result["token"]["symbol"] == "USDC"


# ── scanner (mocked) ───────────────────────────────────────────────────────


class TestScanner:
    @patch("erc20_checker.scanner.query_token_symbol")
    @patch("erc20_checker.scanner.query_token_decimals")
    @patch("erc20_checker.scanner.query_erc20_allowance")
    @patch("erc20_checker.scanner.get_block_number")
    @patch("erc20_checker.scanner.etherscan_request")
    @patch("erc20_checker.scanner.require_etherscan_api_key")
    @patch("erc20_checker.scanner.resolve_rpc_url")
    def test_scan_approvals_empty(self, mock_rpc, mock_key, mock_eth, mock_block, mock_allow, mock_dec, mock_sym):
        mock_rpc.return_value = ("http://localhost:8545", [])
        mock_key.return_value = "fake-key"
        mock_block.return_value = 100
        mock_eth.return_value = {"result": []}

        result = scan_approvals("ethereum", "0x" + "aa" * 20)
        assert result["approvalCount"] == 0
        assert result["approvals"] == []


# ── package import ──────────────────────────────────────────────────────────


class TestPackage:
    def test_version(self):
        assert erc20_checker.__version__ == "0.1.0"
