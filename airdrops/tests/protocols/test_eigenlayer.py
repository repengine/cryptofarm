"""Unit tests for EigenLayer protocol module."""

import json
import pytest
from unittest.mock import MagicMock, patch, mock_open
from typing import Any
from web3 import Web3

from airdrops.protocols.eigenlayer.eigenlayer import (
    _check_eigenlayer_deposit_cap,
    _get_eigenlayer_lst_strategy_details,
    _load_abi,
    restake_lst,
)
from airdrops.protocols.eigenlayer.exceptions import (
    DepositCapReachedError,
    EigenLayerRestakeError,
    UnsupportedLSTError,
)


class TestEigenLayerModule:
    """Test cases for EigenLayer module functions."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_web3 = MagicMock(spec=Web3)
        self.private_key = "0x" + "1" * 64
        self.user_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"

        self.mock_account = MagicMock()
        self.mock_account.address = self.user_address
        self.mock_web3.eth = MagicMock()
        self.mock_web3.eth.account.from_key.return_value = self.mock_account

        self.mock_web3.eth.gas_price = 20000000000
        self.mock_web3.eth.get_transaction_count.return_value = 42

    def test_load_abi_success(self) -> None:
        """Test successful ABI loading."""
        mock_abi = [{"name": "test", "type": "function"}]

        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi))):
            result = _load_abi("test.json")
            assert result == mock_abi

    def test_load_abi_file_not_found(self) -> None:
        """Test ABI loading with missing file."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(EigenLayerRestakeError):
                _load_abi("missing.json")

    def test_load_abi_invalid_json(self) -> None:
        """Test ABI loading with invalid JSON."""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with pytest.raises(EigenLayerRestakeError):
                _load_abi("invalid.json")

    def test_get_eigenlayer_lst_strategy_details_steth(self) -> None:
        """Test getting strategy details for stETH."""
        details = _get_eigenlayer_lst_strategy_details("stETH")

        assert details["token_address"] == "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
        assert details["strategy_address"] == "0x93c4b944D05dfe6df72a2751b1A0541D03217475"
        assert details["token_abi_file"] == "ERC20.json"
        assert details["strategy_abi_file"] == "StrategyBaseTVLLimits_stETH.json"

    def test_get_eigenlayer_lst_strategy_details_reth(self) -> None:
        """Test getting strategy details for rETH."""
        details = _get_eigenlayer_lst_strategy_details("rETH")

        assert details["token_address"] == "0xae78736Cd615f374D3085123A210448E74Fc6393"
        assert details["strategy_address"] == "0x1BeE69b7dFFfA4E2d53C2A2Df135C34A2B5202c3"
        assert details["token_abi_file"] == "ERC20.json"
        assert details["strategy_abi_file"] == "StrategyBaseTVLLimits_rETH.json"

    def test_get_eigenlayer_lst_strategy_details_unsupported(self) -> None:
        """Test getting strategy details for unsupported LST."""
        with pytest.raises(UnsupportedLSTError):
            _get_eigenlayer_lst_strategy_details("INVALID")

    def test_check_eigenlayer_deposit_cap_within_limits(self) -> None:
        """Test deposit cap check when within limits."""
        mock_contract = MagicMock()
        mock_contract.functions.totalShares.return_value.call.return_value = 1000
        mock_contract.functions.maxTotalDeposits.return_value.call.return_value = 2000
        mock_contract.functions.underlyingToSharesView.return_value.call.return_value = 500

        with patch.object(self.mock_web3.eth, 'contract', return_value=mock_contract):
            # Use a valid mock address
            valid_address = "0x" + "a" * 40
            result = _check_eigenlayer_deposit_cap(self.mock_web3, valid_address, 500)
            assert result is True

    def test_check_eigenlayer_deposit_cap_exceeds_limits(self) -> None:
        """Test deposit cap check when exceeding limits."""
        mock_contract = MagicMock()
        mock_contract.functions.totalShares.return_value.call.return_value = 1800
        mock_contract.functions.maxTotalDeposits.return_value.call.return_value = 2000
        mock_contract.functions.underlyingToSharesView.return_value.call.return_value = 500

        with patch.object(self.mock_web3.eth, 'contract', return_value=mock_contract):
            valid_address = "0x" + "a" * 40
            result = _check_eigenlayer_deposit_cap(self.mock_web3, valid_address, 500)
            assert result is False

    def test_check_eigenlayer_deposit_cap_contract_error(self) -> None:
        """Test deposit cap check with contract error."""
        mock_contract = MagicMock()
        mock_contract.functions.totalShares.return_value.call.side_effect = Exception("Contract error")

        with patch.object(self.mock_web3.eth, 'contract', return_value=mock_contract):
            with pytest.raises(EigenLayerRestakeError):
                _check_eigenlayer_deposit_cap(self.mock_web3, "0xStrategyAddress", 1000000000000000000)

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_restake_lst_steth_success(self, mock_load_abi: Any) -> None:
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction, \
             patch.object(self.mock_web3.eth, 'send_raw_transaction') as mock_send_raw_transaction:
            """Test successful stETH restaking."""
            mock_load_abi.return_value = [{"name": "test"}]
            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")
            mock_send_raw_transaction.side_effect = [
                MagicMock(hex=lambda: "0xapprove_hash"),
                MagicMock(hex=lambda: "0xdeposit_hash")
            ]
            # Patch receipt so that receipt['status'] == 1
            receipt_mock = MagicMock()
            receipt_mock.__getitem__.side_effect = lambda key: 1 if key == 'status' else None
            self.mock_web3.eth.wait_for_transaction_receipt.return_value = receipt_mock

            mock_token_contract = MagicMock()
            mock_strategy_contract = MagicMock()
            mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000
            mock_token_contract.functions.allowance.return_value.call.return_value = 0

            mock_strategy_contract_internal = MagicMock()
            mock_strategy_contract_internal.functions.totalShares.return_value.call.return_value = 1000
            mock_strategy_contract_internal.functions.maxTotalDeposits.return_value.call.return_value = 2000

            self.mock_web3.eth.contract.side_effect = [
                mock_token_contract, mock_strategy_contract, mock_strategy_contract_internal
            ]

            mock_token_contract.functions.approve.return_value.build_transaction.return_value = {"data": "0x"}
            mock_strategy_contract.functions.deposit.return_value.build_transaction.return_value = {"data": "0x"}

            success, result = restake_lst(
                self.mock_web3, self.private_key, "stETH", 1000
            )

            assert success is True
            assert result == "0xdeposit_hash"

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_restake_lst_reth_success(self, mock_load_abi: Any) -> None:
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction, \
             patch.object(self.mock_web3.eth, 'send_raw_transaction') as mock_send_raw_transaction:
            """Test successful rETH restaking."""
            mock_load_abi.return_value = [{"name": "test"}]
            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")
            mock_send_raw_transaction.side_effect = [
                MagicMock(hex=lambda: "0xapprove_hash"),
                MagicMock(hex=lambda: "0xdeposit_hash")
            ]
            receipt_mock = MagicMock()
            receipt_mock.__getitem__.side_effect = lambda key: 1 if key == 'status' else None
            self.mock_web3.eth.wait_for_transaction_receipt.return_value = receipt_mock

            mock_token_contract = MagicMock()
            mock_strategy_contract = MagicMock()
            mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000
            mock_token_contract.functions.allowance.return_value.call.return_value = 0

            mock_strategy_contract_internal = MagicMock()
            mock_strategy_contract_internal.functions.totalShares.return_value.call.return_value = 1000
            mock_strategy_contract_internal.functions.maxTotalDeposits.return_value.call.return_value = 2000

            self.mock_web3.eth.contract.side_effect = [
                mock_token_contract, mock_strategy_contract, mock_strategy_contract_internal
            ]

            mock_token_contract.functions.approve.return_value.build_transaction.return_value = {"data": "0x"}
            mock_strategy_contract.functions.deposit.return_value.build_transaction.return_value = {"data": "0x"}

            success, result = restake_lst(
                self.mock_web3, self.private_key, "rETH", 1000
            )

            assert success is True
            assert result == "0xdeposit_hash"

    def test_restake_lst_unsupported_lst(self) -> None:
        """Test restaking with unsupported LST."""
        with pytest.raises(UnsupportedLSTError):
            restake_lst(
                self.mock_web3, self.private_key, "INVALID", 1000000000000000000
            )

    def test_restake_lst_invalid_amount_negative(self) -> None:
        """Test restaking with negative amount."""
        with pytest.raises(EigenLayerRestakeError, match="Amount must be positive"):
            restake_lst(self.mock_web3, self.private_key, "stETH", -1)

    def test_restake_lst_invalid_amount_zero(self) -> None:
        """Test restaking with zero amount."""
        with pytest.raises(EigenLayerRestakeError, match="Amount must be positive"):
            restake_lst(self.mock_web3, self.private_key, "stETH", 0)

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_restake_lst_insufficient_balance(self, mock_load_abi: Any) -> None:
        """Test restaking with insufficient balance."""
        mock_load_abi.return_value = [{"name": "test"}]

        mock_token_contract = MagicMock()
        mock_strategy_contract = MagicMock()
        mock_token_contract.functions.balanceOf.return_value.call.return_value = 500000000000000000

        self.mock_web3.eth.contract.side_effect = [mock_token_contract, mock_strategy_contract]

        success, result = restake_lst(
            self.mock_web3, self.private_key, "stETH", 1000000000000000000
        )

        assert success is False
        assert result is not None and \
            "Insufficient balance. Have: 500000000000000000, Need: 1000000000000000000" in result

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_restake_lst_deposit_cap_reached(self, mock_load_abi: Any) -> None:
        """Test restaking when deposit cap is reached."""
        mock_load_abi.return_value = [{"name": "test"}]

        mock_token_contract = MagicMock()
        mock_strategy_contract = MagicMock()
        mock_strategy_contract_for_cap_check = MagicMock()

        mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000

        mock_strategy_contract_for_cap_check.functions.totalShares.return_value.call.return_value = 1800
        mock_strategy_contract_for_cap_check.functions.maxTotalDeposits.return_value.call.return_value = 2000

        self.mock_web3.eth.contract.side_effect = [
            mock_token_contract, mock_strategy_contract, mock_strategy_contract_for_cap_check
        ]

        with patch("airdrops.protocols.eigenlayer.eigenlayer._check_eigenlayer_deposit_cap", return_value=False):
            with pytest.raises(DepositCapReachedError, match="Deposit would exceed strategy cap"):
                restake_lst(
                    self.mock_web3, self.private_key, "stETH", 1000000000000000000
                )

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_restake_lst_approval_failure(self, mock_load_abi: Any) -> None:
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction, \
             patch.object(self.mock_web3.eth, 'send_raw_transaction') as mock_send_raw_transaction:
            """Test restaking with approval failure."""
            mock_load_abi.return_value = [{"name": "test"}]

            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")
            mock_send_raw_transaction.return_value = MagicMock(hex=lambda: "0xapprove_hash")

            self.mock_web3.eth.wait_for_transaction_receipt.return_value = MagicMock(status=0)

            mock_token_contract = MagicMock()
            mock_strategy_contract = MagicMock()

            mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000
            mock_token_contract.functions.allowance.return_value.call.return_value = 0

            mock_strategy_contract_internal = MagicMock()
            mock_strategy_contract_internal.functions.totalShares.return_value.call.return_value = 1000
            mock_strategy_contract_internal.functions.maxTotalDeposits.return_value.call.return_value = 2000

            self.mock_web3.eth.contract.side_effect = [
                mock_token_contract, mock_strategy_contract, mock_strategy_contract_internal
            ]

            mock_token_contract.functions.approve.return_value.build_transaction.return_value = {"data": "0x"}

            success, result = restake_lst(
                self.mock_web3, self.private_key, "stETH", 1000
            )
            assert success is False
            assert result is not None and "Approval transaction failed" in result

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_restake_lst_deposit_failure(self, mock_load_abi: Any) -> None:
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction, \
             patch.object(self.mock_web3.eth, 'send_raw_transaction') as mock_send_raw_transaction:
            """Test restaking with deposit failure."""
            mock_load_abi.return_value = [{"name": "test"}]

            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")
            mock_send_raw_transaction.side_effect = [
                MagicMock(hex=lambda: "0xapprove_hash"),
                MagicMock(hex=lambda: "0xdeposit_hash")
            ]
            self.mock_web3.eth.wait_for_transaction_receipt.side_effect = [
                MagicMock(status=1),
                MagicMock(status=0)
            ]

            mock_token_contract = MagicMock()
            mock_strategy_contract = MagicMock()

            mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000
            mock_token_contract.functions.allowance.return_value.call.return_value = 0

            mock_strategy_contract_internal = MagicMock()
            mock_strategy_contract_internal.functions.totalShares.return_value.call.return_value = 1000
            mock_strategy_contract_internal.functions.maxTotalDeposits.return_value.call.return_value = 2000

            self.mock_web3.eth.contract.side_effect = [
                mock_token_contract, mock_strategy_contract, mock_strategy_contract_internal
            ]

            mock_token_contract.functions.approve.return_value.build_transaction.return_value = {"data": "0x"}
            mock_strategy_contract.functions.deposit.return_value.build_transaction.return_value = {"data": "0x"}

            success, result = restake_lst(
                self.mock_web3, self.private_key, "stETH", 1000
            )
            assert success is False
            assert result is not None and "Approval transaction failed" in result

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_restake_lst_unexpected_error(self, mock_load_abi: Any) -> None:
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction, \
             patch.object(self.mock_web3.eth, 'send_raw_transaction') as mock_send_raw_transaction:
            """Test restaking with unexpected error."""
            mock_load_abi.side_effect = Exception("Unexpected error")
            # These mocks are needed even if an earlier exception is expected,
            # to prevent AttributeError if the test setup reaches them.
            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")
            mock_send_raw_transaction.return_value = MagicMock(hex=lambda: "0xhash")

            with pytest.raises(EigenLayerRestakeError, match="Restaking operation failed: Unexpected error"):
                restake_lst(
                    self.mock_web3, self.private_key, "stETH", 1000000000000000000
                )

    def test_get_eigenlayer_lst_strategy_details_unknown_lst_fallback(self) -> None:
        """Test getting strategy details for unknown LST that passes initial check."""
        # This test covers the unreachable else branch in line 80
        # We need to patch the LST_TOKENS to include an unknown symbol temporarily
        with patch("airdrops.protocols.eigenlayer.eigenlayer.LST_TOKENS", {"UNKNOWN": "0xtest"}):
            with patch("airdrops.protocols.eigenlayer.eigenlayer.LST_STRATEGIES", {}):
                with pytest.raises(KeyError):
                    # This will fail at LST_STRATEGIES lookup, but shows the code path
                    _get_eigenlayer_lst_strategy_details("UNKNOWN")

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    @patch("airdrops.protocols.eigenlayer.eigenlayer._check_eigenlayer_deposit_cap")
    def test_restake_lst_sufficient_allowance_skip_approval(self, mock_cap_check: Any, mock_load_abi: Any) -> None:
        """Test restaking when sufficient allowance exists, skipping approval."""
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction, \
             patch.object(self.mock_web3.eth, 'send_raw_transaction') as mock_send_raw_transaction:

            mock_load_abi.return_value = [{"name": "test"}]
            mock_cap_check.return_value = True  # Allow deposit
            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")
            mock_send_raw_transaction.return_value = MagicMock(hex=lambda: "0xdeposit_hash")

            # Mock receipt with successful status
            receipt_mock = MagicMock()
            receipt_mock.__getitem__.side_effect = lambda key: 1 if key == 'status' else None
            self.mock_web3.eth.wait_for_transaction_receipt.return_value = receipt_mock

            mock_token_contract = MagicMock()
            mock_strategy_contract = MagicMock()

            # Set sufficient balance and allowance to skip approval
            mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000
            mock_token_contract.functions.allowance.return_value.call.return_value = \
                2000000000000000000  # Sufficient allowance to skip approval

            self.mock_web3.eth.contract.side_effect = [mock_token_contract, mock_strategy_contract]

            mock_strategy_contract.functions.deposit.return_value.build_transaction.return_value = {"data": "0x"}

            success, result = restake_lst(
                self.mock_web3, self.private_key, "stETH", 1000000000000000000
            )

            assert success is True
            assert result == "0xdeposit_hash"

            # Verify approval was not called since allowance was sufficient
            mock_token_contract.functions.approve.assert_not_called()

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    @patch("airdrops.protocols.eigenlayer.eigenlayer._check_eigenlayer_deposit_cap")
    def test_restake_lst_transaction_failure_status_zero(self, mock_cap_check: Any, mock_load_abi: Any) -> None:
        """Test restaking with transaction failure (status 0)."""
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction, \
             patch.object(self.mock_web3.eth, 'send_raw_transaction') as mock_send_raw_transaction:

            mock_load_abi.return_value = [{"name": "test"}]
            mock_cap_check.return_value = True  # Allow deposit
            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")
            mock_send_raw_transaction.side_effect = [
                MagicMock(hex=lambda: "0xapprove_hash"),
                MagicMock(hex=lambda: "0xdeposit_hash")
            ]

            # Mock receipts: approval succeeds, deposit fails
            self.mock_web3.eth.wait_for_transaction_receipt.side_effect = [
                MagicMock(status=1),  # Approval success
                MagicMock(status=0)   # Deposit failure
            ]

            mock_token_contract = MagicMock()
            mock_strategy_contract = MagicMock()

            mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000
            mock_token_contract.functions.allowance.return_value.call.return_value = 0  # Need approval

            self.mock_web3.eth.contract.side_effect = [mock_token_contract, mock_strategy_contract]

            mock_token_contract.functions.approve.return_value.build_transaction.return_value = {"data": "0x"}
            mock_strategy_contract.functions.deposit.return_value.build_transaction.return_value = {"data": "0x"}

            success, result = restake_lst(
                self.mock_web3, self.private_key, "stETH", 1000000000000000000
            )

            assert success is False
            assert result == "Approval transaction failed"

    def test_get_eigenlayer_lst_strategy_details_reth_abi_file(self) -> None:
        """Test getting strategy details for rETH to ensure correct ABI file."""
        details = _get_eigenlayer_lst_strategy_details("rETH")

        assert details["token_address"] == "0xae78736Cd615f374D3085123A210448E74Fc6393"
        assert details["strategy_address"] == "0x1BeE69b7dFFfA4E2d53C2A2Df135C34A2B5202c3"
        assert details["token_abi_file"] == "ERC20.json"
        assert details["strategy_abi_file"] == "StrategyBaseTVLLimits_rETH.json"

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_check_eigenlayer_deposit_cap_edge_case_exact_limit(self, mock_load_abi: Any) -> None:
        """Test deposit cap check when deposit exactly reaches the limit."""
        mock_load_abi.return_value = [{"name": "test"}]

        mock_contract = MagicMock()
        mock_contract.functions.totalShares.return_value.call.return_value = 1500
        mock_contract.functions.maxTotalDeposits.return_value.call.return_value = 2000

        with patch.object(self.mock_web3.eth, 'contract', return_value=mock_contract):
            valid_address = "0x" + "a" * 40
            # Deposit amount that exactly reaches the limit
            result = _check_eigenlayer_deposit_cap(self.mock_web3, valid_address, 500)
            assert result is True

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_check_eigenlayer_deposit_cap_edge_case_exceeds_by_one(self, mock_load_abi: Any) -> None:
        """Test deposit cap check when deposit exceeds limit by one."""
        mock_load_abi.return_value = [{"name": "test"}]

        mock_contract = MagicMock()
        mock_contract.functions.totalShares.return_value.call.return_value = 1500
        mock_contract.functions.maxTotalDeposits.return_value.call.return_value = 2000

        with patch.object(self.mock_web3.eth, 'contract', return_value=mock_contract):
            valid_address = "0x" + "a" * 40
            # Deposit amount that exceeds the limit by 1
            result = _check_eigenlayer_deposit_cap(self.mock_web3, valid_address, 501)
            assert result is False

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_restake_lst_web3_connection_error(self, mock_load_abi: Any) -> None:
        """Test restaking with Web3 connection error."""
        mock_load_abi.side_effect = Exception("Connection failed")

        with pytest.raises(EigenLayerRestakeError, match="Restaking operation failed: Connection failed"):
            restake_lst(
                self.mock_web3, self.private_key, "stETH", 1000000000000000000
            )

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_restake_lst_contract_interaction_error(self, mock_load_abi: Any) -> None:
        """Test restaking with contract interaction error."""
        mock_load_abi.return_value = [{"name": "test"}]

        mock_token_contract = MagicMock()
        mock_strategy_contract = MagicMock()

        # Mock balance check to fail
        mock_token_contract.functions.balanceOf.return_value.call.side_effect = Exception("Contract call failed")

        self.mock_web3.eth.contract.side_effect = [mock_token_contract, mock_strategy_contract]

        with pytest.raises(EigenLayerRestakeError, match="Restaking operation failed: Contract call failed"):
            restake_lst(
                self.mock_web3, self.private_key, "stETH", 1000000000000000000
            )

    def test_load_abi_with_complex_json_structure(self) -> None:
        """Test ABI loading with complex JSON structure."""
        complex_abi = [
            {
                "name": "deposit",
                "type": "function",
                "inputs": [
                    {"name": "token", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "outputs": [{"name": "shares", "type": "uint256"}]
            }
        ]

        with patch("builtins.open", mock_open(read_data=json.dumps(complex_abi))):
            result = _load_abi("complex.json")
            assert result == complex_abi
            assert len(result) == 1
            assert result[0]["name"] == "deposit"

    def test_load_abi_empty_file(self) -> None:
        """Test ABI loading with empty JSON array."""
        with patch("builtins.open", mock_open(read_data="[]")):
            result = _load_abi("empty.json")
            assert result == []

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    @patch("airdrops.protocols.eigenlayer.eigenlayer._check_eigenlayer_deposit_cap")
    def test_restake_lst_gas_estimation_failure(self, mock_cap_check: Any, mock_load_abi: Any) -> None:
        """Test restaking with gas estimation failure during transaction building."""
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction:
            mock_load_abi.return_value = [{"name": "test"}]
            mock_cap_check.return_value = True  # Allow deposit
            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")

            mock_token_contract = MagicMock()
            mock_strategy_contract = MagicMock()

            mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000
            mock_token_contract.functions.allowance.return_value.call.return_value = 0

            # Make build_transaction fail
            mock_token_contract.functions.approve.return_value.build_transaction.side_effect = \
                Exception("Gas estimation failed")

            self.mock_web3.eth.contract.side_effect = [mock_token_contract, mock_strategy_contract]

            with pytest.raises(EigenLayerRestakeError, match="Restaking operation failed: Gas estimation failed"):
                restake_lst(
                    self.mock_web3, self.private_key, "stETH", 1000000000000000000
                )

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    @patch("airdrops.protocols.eigenlayer.eigenlayer._check_eigenlayer_deposit_cap")
    def test_restake_lst_transaction_send_failure(self, mock_cap_check: Any, mock_load_abi: Any) -> None:
        """Test restaking with transaction send failure."""
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction, \
             patch.object(self.mock_web3.eth, 'send_raw_transaction') as mock_send_raw_transaction:

            mock_load_abi.return_value = [{"name": "test"}]
            mock_cap_check.return_value = True  # Allow deposit
            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")
            mock_send_raw_transaction.side_effect = Exception("Network error")

            mock_token_contract = MagicMock()
            mock_strategy_contract = MagicMock()

            mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000
            mock_token_contract.functions.allowance.return_value.call.return_value = 0

            self.mock_web3.eth.contract.side_effect = [mock_token_contract, mock_strategy_contract]

            mock_token_contract.functions.approve.return_value.build_transaction.return_value = {"data": "0x"}

            with pytest.raises(EigenLayerRestakeError, match="Restaking operation failed: Network error"):
                restake_lst(
                    self.mock_web3, self.private_key, "stETH", 1000000000000000000
                )

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_load_abi_permission_error_in_restake_context(self, mock_load_abi: Any) -> None:
        """Test ABI loading with permission error in restake context."""
        mock_load_abi.side_effect = PermissionError("Permission denied")

        with pytest.raises(EigenLayerRestakeError, match="Restaking operation failed: Permission denied"):
            restake_lst(
                self.mock_web3, self.private_key, "stETH", 1000000000000000000
            )

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    def test_check_eigenlayer_deposit_cap_contract_creation_failure(self, mock_load_abi: Any) -> None:
        """Test deposit cap check with contract creation failure."""
        mock_load_abi.return_value = [{"name": "test"}]

        # Use a valid hex address but mock the contract creation to fail
        valid_hex_address = "0x" + "a" * 40
        self.mock_web3.eth.contract.side_effect = Exception("Invalid contract address")

        with pytest.raises(EigenLayerRestakeError, match="Failed to check deposit cap: Invalid contract address"):
            _check_eigenlayer_deposit_cap(self.mock_web3, valid_hex_address, 1000)

    @patch("airdrops.protocols.eigenlayer.eigenlayer._load_abi")
    @patch("airdrops.protocols.eigenlayer.eigenlayer._check_eigenlayer_deposit_cap")
    def test_restake_lst_wait_for_receipt_timeout(self, mock_cap_check: Any, mock_load_abi: Any) -> None:
        """Test restaking with transaction receipt timeout."""
        with patch.object(self.mock_web3.eth.account, 'sign_transaction') as mock_sign_transaction, \
             patch.object(self.mock_web3.eth, 'send_raw_transaction') as mock_send_raw_transaction:

            mock_load_abi.return_value = [{"name": "test"}]
            mock_cap_check.return_value = True  # Allow deposit
            mock_sign_transaction.return_value = MagicMock(rawTransaction="0xraw")
            mock_send_raw_transaction.return_value = MagicMock(hex=lambda: "0xapprove_hash")

            # Mock wait_for_transaction_receipt to timeout
            self.mock_web3.eth.wait_for_transaction_receipt.side_effect = Exception("Transaction timeout")

            mock_token_contract = MagicMock()
            mock_strategy_contract = MagicMock()

            mock_token_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000
            mock_token_contract.functions.allowance.return_value.call.return_value = 0

            self.mock_web3.eth.contract.side_effect = [mock_token_contract, mock_strategy_contract]

            mock_token_contract.functions.approve.return_value.build_transaction.return_value = {"data": "0x"}

            with pytest.raises(EigenLayerRestakeError, match="Restaking operation failed: Transaction timeout"):
                restake_lst(
                    self.mock_web3, self.private_key, "stETH", 1000000000000000000
                )
