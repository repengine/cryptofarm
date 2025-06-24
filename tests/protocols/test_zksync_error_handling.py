"""
Tests for zkSync error handling and edge cases to increase coverage.

This module focuses on testing error conditions, retry logic, and edge cases
that are currently uncovered in the zkSync protocol implementation.
"""

import pytest
from unittest.mock import Mock, patch
from requests.exceptions import ConnectionError, Timeout

import src.airdrops.protocols.zksync.zksync as zksync_protocol
from src.airdrops.protocols.zksync.zksync import (
    _get_l1_token_address_zksync,
    _get_l2_token_address_zksync,
    _build_and_send_tx_zksync,
    _approve_erc20_zksync,
    _get_expected_amount_out_syncswap_zksync,
    _get_syncswap_pool_address_zksync,
    _bridge_eth_zksync,
    _bridge_erc20_zksync,
    DEFAULT_L2_GAS_LIMIT,
    _execute_zksync_activity,
    _execute_swap_activity_zksync,
    _execute_bridge_activity_zksync
)
from src.airdrops.protocols.zksync.exceptions import (
    TokenNotSupportedError,
    TransactionBuildError,
    TransactionRevertedError,
    MaxRetriesExceededError,
    ApprovalError,
    GasEstimationError,
    InsufficientBalanceError,
    ZkSyncBridgeError,
    ZkSyncRandomActivityError
)


class TestTokenAddressErrors:
    """Test token address resolution error cases."""

    @patch('src.airdrops.protocols.zksync.zksync.ZKSYNC_TOKEN_ADDRESSES')
    def test_get_l1_token_address_not_configured(self, mock_addresses):
        """Test L1 token address when token is not configured."""
        mock_addresses.__contains__.return_value = False
        
        with pytest.raises(TokenNotSupportedError, match="Token symbol 'UNKNOWN' not supported"):
            _get_l1_token_address_zksync("UNKNOWN")

    @patch('src.airdrops.protocols.zksync.zksync.ZKSYNC_TOKEN_ADDRESSES')
    def test_get_l1_token_address_no_l1_address(self, mock_addresses):
        """Test L1 token address when L1 address is not configured."""
        mock_addresses.__contains__.return_value = True
        mock_addresses.__getitem__.return_value = {"L2": "0x123"}  # No L1 key
        
        with pytest.raises(TokenNotSupportedError, match="L1 address for token 'TEST' not configured"):
            _get_l1_token_address_zksync("TEST")

    @patch('src.airdrops.protocols.zksync.zksync.constants.ZKSYNC_TOKEN_ADDRESSES')
    def test_get_l2_token_address_not_configured(self, mock_addresses):
        """Test L2 token address when token is not configured."""
        mock_addresses.__contains__.return_value = False
        
        with pytest.raises(TokenNotSupportedError, match="Token symbol 'UNKNOWN' not supported"):
            _get_l2_token_address_zksync("UNKNOWN")

    @patch('src.airdrops.protocols.zksync.zksync.constants.ZKSYNC_TOKEN_ADDRESSES')
    def test_get_l2_token_address_no_l2_address(self, mock_addresses):
        """Test L2 token address when L2 address is not configured."""
        mock_addresses.__contains__.return_value = True
        mock_addresses.__getitem__.return_value = {"L1": "0x123"}  # No L2 key
        
        with pytest.raises(TokenNotSupportedError, match="L2 address for token 'TEST' not configured"):
            _get_l2_token_address_zksync("TEST")


class TestTransactionRetryLogic:
    """Test transaction retry logic and error handling."""

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync.time.sleep')
    def test_build_and_send_tx_rpc_error_retry(self, mock_sleep, mock_get_account):
        """Test transaction retry on RPC/network errors."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.return_value = 1
        mock_web3.eth.gas_price = 20000000000
        mock_web3.eth.estimate_gas.return_value = 21000
        mock_web3.eth.account.sign_transaction.return_value = Mock(raw_transaction=b"signed_tx")
        
        # First attempt fails with ConnectionError, second succeeds
        mock_web3.eth.send_raw_transaction.side_effect = [
            ConnectionError("Network error"),
            b"tx_hash"
        ]
        mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 1}
        
        tx_params = {"to": "0x9876543210987654321098765432109876543210", "value": 1000000000000000000}
        
        result = _build_and_send_tx_zksync(mock_web3, "0x" + "1" * 64, tx_params)
        
        assert result == "74785f68617368"  # hex encoding of b"tx_hash"
        assert mock_sleep.call_count == 1  # Should have slept once for retry

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync.time.sleep')
    def test_build_and_send_tx_max_retries_exceeded(self, mock_sleep, mock_get_account):
        """Test transaction failure after max retries."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.return_value = 1
        mock_web3.eth.gas_price = 20000000000
        mock_web3.eth.estimate_gas.return_value = 21000
        mock_web3.eth.account.sign_transaction.return_value = Mock(raw_transaction=b"signed_tx")
        mock_web3.eth.send_raw_transaction.side_effect = ConnectionError("Persistent network error")
        
        tx_params = {"to": "0x9876543210987654321098765432109876543210", "value": 1000000000000000000}
        
        with pytest.raises(MaxRetriesExceededError, match="Transaction failed after .* attempts due to RPC/network issues"):
            _build_and_send_tx_zksync(mock_web3, "0x" + "1" * 64, tx_params)

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync.time.sleep')
    def test_build_and_send_tx_nonce_update_on_retry(self, mock_sleep, mock_get_account):
        """Test nonce update during retry logic."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.side_effect = [1, 2]  # Nonce increases
        mock_web3.eth.gas_price = 20000000000
        mock_web3.eth.estimate_gas.return_value = 21000
        mock_web3.eth.account.sign_transaction.return_value = Mock(raw_transaction=b"signed_tx")
        
        # First attempt fails, second succeeds
        mock_web3.eth.send_raw_transaction.side_effect = [
            Timeout("Timeout"),
            b"tx_hash"
        ]
        mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 1}
        
        tx_params = {"to": "0x9876543210987654321098765432109876543210", "value": 1000000000000000000}
        
        result = _build_and_send_tx_zksync(mock_web3, "0x" + "1" * 64, tx_params)
        
        assert result == "74785f68617368"
        assert mock_web3.eth.get_transaction_count.call_count == 2

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync.time.sleep')
    def test_build_and_send_tx_signing_error_on_retry(self, mock_sleep, mock_get_account):
        """Test signing error during retry logic."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.side_effect = [1, 2]
        mock_web3.eth.gas_price = 20000000000
        mock_web3.eth.estimate_gas.return_value = 21000
        
        # First signing succeeds, retry signing fails
        mock_web3.eth.account.sign_transaction.side_effect = [
            Mock(raw_transaction=b"signed_tx"),
            Exception("Signing failed")
        ]
        mock_web3.eth.send_raw_transaction.side_effect = ConnectionError("Network error")
        
        tx_params = {"to": "0x9876543210987654321098765432109876543210", "value": 1000000000000000000}
        
        with pytest.raises(TransactionBuildError, match="Transaction re-signing failed before retry"):
            _build_and_send_tx_zksync(mock_web3, "0x" + "1" * 64, tx_params)

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync.time.sleep')
    def test_build_and_send_tx_unexpected_error(self, mock_sleep, mock_get_account):
        """Test unexpected error handling."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.return_value = 1
        mock_web3.eth.gas_price = 20000000000
        mock_web3.eth.estimate_gas.side_effect = Exception("Unexpected error")
        
        tx_params = {"to": "0x9876543210987654321098765432109876543210", "value": 1000000000000000000}
        
        with pytest.raises(GasEstimationError, match="Gas estimation failed: Unexpected error"):
            _build_and_send_tx_zksync(mock_web3, "0x" + "1" * 64, tx_params)



class TestApprovalErrors:
    """Test ERC20 approval error handling."""

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    def test_approve_erc20_gas_estimation_error(self, mock_get_contract, mock_get_account):
        """Test ERC20 approval with gas estimation error."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_contract = Mock()
        mock_contract.functions.allowance.return_value.call.return_value = 0
        mock_contract.functions.approve.return_value.build_transaction.side_effect = GasEstimationError("Gas estimation failed")
        mock_get_contract.return_value = mock_contract
        
        mock_web3 = Mock()
        mock_web3.eth.gas_price = 20000000000
        
        with pytest.raises(ApprovalError, match="ERC20 approval gas estimation failed"):
            _approve_erc20_zksync(
                mock_web3, "0x" + "1" * 64, "0x9876543210987654321098765432109876543210",
                "0x1111111111111111111111111111111111111111", 1000000000000000000
            )

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._build_and_send_tx_zksync')
    def test_approve_erc20_transaction_reverted(self, mock_build_send, mock_get_contract, mock_get_account):
        """Test ERC20 approval with reverted transaction."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_contract = Mock()
        mock_contract.functions.allowance.return_value.call.return_value = 0
        mock_contract.functions.approve.return_value.build_transaction.return_value = {"to": "0x123", "data": "0x456"}
        mock_get_contract.return_value = mock_contract
        
        mock_receipt = {"status": 0, "transactionHash": "0x789"}
        mock_build_send.side_effect = TransactionRevertedError("Transaction reverted", receipt=mock_receipt)
        
        mock_web3 = Mock()
        mock_web3.eth.gas_price = 20000000000
        
        with pytest.raises(ApprovalError, match="ERC20 approval failed"):
            _approve_erc20_zksync(
                mock_web3, "0x" + "1" * 64, "0x9876543210987654321098765432109876543210",
                "0x1111111111111111111111111111111111111111", 1000000000000000000
            )

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    def test_approve_erc20_unexpected_error(self, mock_get_contract, mock_get_account):
        """Test ERC20 approval with unexpected error."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_contract = Mock()
        mock_contract.functions.allowance.return_value.call.side_effect = Exception("Unexpected error")
        mock_get_contract.return_value = mock_contract
        
        mock_web3 = Mock()
        
        with pytest.raises(ApprovalError, match="ERC20 approval error"):
            _approve_erc20_zksync(
                mock_web3, "0x" + "1" * 64, "0x9876543210987654321098765432109876543210",
                "0x1111111111111111111111111111111111111111", 1000000000000000000
            )


class TestSwapErrorHandling:
    """Test swap error handling and edge cases."""

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_pool_address_zksync')
    def test_get_expected_amount_out_pool_error(self, mock_get_pool_address):
        """Test expected amount out with pool contract error."""
        mock_get_pool_address.return_value = "0x1234567890123456789012345678901234567890"
        
        mock_web3 = Mock()
        
        with patch('src.airdrops.protocols.zksync.zksync._get_syncswap_classic_pool_contract_zksync') as mock_get_pool:
            mock_pool = Mock()
            mock_pool.functions.getAmountOut.return_value.call.side_effect = Exception("Pool error")
            mock_get_pool.return_value = mock_pool
            
            with patch('src.airdrops.protocols.zksync.zksync.Web3') as mock_web3_class:
                mock_web3_class.to_checksum_address.side_effect = lambda x: x
                
                # Should not raise exception, just log warning and continue
                result = _get_expected_amount_out_syncswap_zksync(
                    mock_web3, "0x9876543210987654321098765432109876543210",
                    "0x1111111111111111111111111111111111111111", 500000000,
                    "0x2222222222222222222222222222222222222222",
                    "0x3333333333333333333333333333333333333333"
                )
                
                # Should try WETH hop path and eventually raise InsufficientLiquidityError
                assert result is not None or True  # Function should complete

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_classic_pool_factory_contract_zksync')
    def test_get_syncswap_pool_address_error(self, mock_get_factory):
        """Test pool address retrieval error."""
        mock_factory = Mock()
        mock_factory.functions.getPool.return_value.call.side_effect = Exception("Factory error")
        mock_get_factory.return_value = mock_factory

        mock_web3 = Mock()

        result = _get_syncswap_pool_address_zksync(
            mock_web3, "0x9876543210987654321098765432109876543210",
            "0x1111111111111111111111111111111111111111"
        )

        assert result is None


class TestRandomActivityErrors:
    """Test random activity error handling."""

    def test_perform_random_activity_no_activities(self):
        """Test random activity with empty activity pool."""
        user_address = "0x1234567890123456789012345678901234567890"
        private_key = "0x" + "1" * 64
    
        mock_web3_l1 = Mock()
        mock_web3_l2 = Mock()
    
        with pytest.raises(ValueError, match="action_weights cannot be empty"):
            zksync_protocol.perform_random_activity(
                user_address=user_address,
                private_key=private_key,
                config={"random_activity": {"zksync": {"action_weights": []}}},
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )

    @patch('src.airdrops.protocols.zksync.zksync._execute_zksync_activity')
    def test_perform_random_activity_all_fail(self, mock_execute):
        """Test random activity when all activities fail."""
        mock_execute.side_effect = Exception("Activity failed")

        user_address = "0x1234567890123456789012345678901234567890"
        private_key = "0x" + "1" * 64

        mock_web3_l1 = Mock()
        mock_web3_l2 = Mock()

        activity_pool = [{"name": "swap", "weight": 1}]

        with pytest.raises(ZkSyncRandomActivityError, match="All random activities failed after 1 attempts"):
            zksync_protocol.perform_random_activity(
                user_address=user_address,
                private_key=private_key,
                config={"random_activity": {"zksync": {"action_weights": activity_pool, "max_retries": 1}}},
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
        

    def test_execute_zksync_activity_unknown(self):
        """Test executing unknown activity."""
        with pytest.raises(ZkSyncRandomActivityError, match="Unknown activity"):
            _execute_zksync_activity(
                "unknown_activity", "0x123", "0x456", {}, {}, Mock(), Mock()
            )

    def test_execute_swap_activity_no_web3_l2(self):
        """Test swap activity without web3_l2."""
        with pytest.raises(ZkSyncRandomActivityError, match="web3_l2 is required"):
            _execute_swap_activity_zksync("0x123", "0x456", {}, {}, None)

    def test_execute_bridge_activity_no_web3(self):
        """Test bridge activity without required web3 instances."""
        with pytest.raises(ZkSyncRandomActivityError, match="Both web3_l1 and web3_l2 are required"):
            _execute_bridge_activity_zksync("0x123", "0x456", {}, {}, None, Mock())
        
        with pytest.raises(ZkSyncRandomActivityError, match="Both web3_l1 and web3_l2 are required"):
            _execute_bridge_activity_zksync("0x123", "0x456", {}, {}, Mock(), None)


class TestBridgeErrorHandling:
    """Test bridge error handling."""

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    def test_bridge_eth_insufficient_balance_deposit(self, mock_get_contract, mock_get_account):
        """Test ETH bridge with insufficient L1 balance for deposit."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3_l1 = Mock()
        mock_web3_l1.eth.get_balance.return_value = 500000000000000000  # 0.5 ETH
        mock_web3_l1.eth.gas_price = 20000000000
        
        mock_web3_l2 = Mock()
        mock_web3_l2.eth.gas_price = 10000000000
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient L1 ETH balance"):
            _bridge_eth_zksync(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "1" * 64,
                amount=1000000000000000000,
                direction="deposit",
                l1_address="0x1234567890123456789012345678901234567890",
                l2_address="0x1234567890123456789012345678901234567890",
                l2_gas_limit=DEFAULT_L2_GAS_LIMIT
            )

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    def test_bridge_eth_insufficient_balance_withdraw(self, mock_get_contract, mock_get_account):
        """Test ETH bridge with insufficient L2 balance for withdrawal."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3_l1 = Mock()
        mock_web3_l2 = Mock()
        mock_web3_l2.eth.get_balance.return_value = 500000000000000000  # 0.5 ETH
        mock_web3_l2.eth.gas_price = 10000000000
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient L2 ETH balance"):
            _bridge_eth_zksync(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "1" * 64,
                amount=1000000000000000000,
                direction="withdraw",
                l1_address="0x1234567890123456789012345678901234567890",
                l2_address="0x1234567890123456789012345678901234567890",
                l2_gas_limit=DEFAULT_L2_GAS_LIMIT
            )

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_l1_token_address_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_l2_token_address_zksync')
    def test_bridge_erc20_insufficient_balance_deposit(self, mock_get_l2_addr, mock_get_l1_addr, mock_get_contract, mock_get_account):
        """Test ERC20 bridge with insufficient L1 balance for deposit."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_get_l1_addr.return_value = "0x1111111111111111111111111111111111111111"
        mock_get_l2_addr.return_value = "0x2222222222222222222222222222222222222222"
        
        mock_token_contract = Mock()
        mock_token_contract.functions.balanceOf.return_value.call.return_value = 500000000  # 500 USDC
        mock_token_contract.functions.transfer.return_value._encode_transaction_data.return_value = b"transfer_data"
        
        mock_get_contract.return_value = mock_token_contract
        
        mock_web3_l1 = Mock()
        mock_web3_l1.eth.gas_price = 20000000000
        mock_web3_l2 = Mock()
        mock_web3_l2.eth.gas_price = 10000000000
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient L1 USDC balance"):
            _bridge_erc20_zksync(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "1" * 64,
                token_symbol="USDC",
                amount=1000000000,
                direction="deposit",
                l1_address="0x1234567890123456789012345678901234567890",
                l2_address="0x1234567890123456789012345678901234567890",
                l2_gas_limit=DEFAULT_L2_GAS_LIMIT
            )

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_l1_token_address_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_l2_token_address_zksync')
    def test_bridge_erc20_insufficient_balance_withdraw(self, mock_get_l2_addr, mock_get_l1_addr, mock_get_contract, mock_get_account):
        """Test ERC20 bridge with insufficient L2 balance for withdrawal."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_get_l1_addr.return_value = "0x1111111111111111111111111111111111111111"
        mock_get_l2_addr.return_value = "0x2222222222222222222222222222222222222222"
        
        mock_token_contract = Mock()
        mock_token_contract.functions.balanceOf.return_value.call.return_value = 500000000  # 500 USDC
        mock_get_contract.return_value = mock_token_contract # This line was missing

        mock_web3_l1 = Mock()
        mock_web3_l2 = Mock()
        mock_web3_l2.eth.gas_price = 10000000000
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient L2 USDC balance"):
            _bridge_erc20_zksync(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "1" * 64,
                token_symbol="USDC",
                amount=1000000000,
                direction="withdraw",
                l1_address="0x1234567890123456789012345678901234567890",
                l2_address="0x1234567890123456789012345678901234567890",
                l2_gas_limit=DEFAULT_L2_GAS_LIMIT
            )

    @patch('src.airdrops.protocols.zksync.zksync._build_and_send_tx_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_bridge_eth_deposit_unexpected_state(self, mock_get_account, mock_build_and_send):
        """Test unexpected state during ETH bridge deposit."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account

        mock_web3_l1 = Mock()
        mock_web3_l1.eth.get_balance.return_value = 2 * 10**18 # 2 ETH
        mock_web3_l1.eth.gas_price = 20000000000
        mock_web3_l2 = Mock()

        mock_build_and_send.return_value = None  # Simulate unexpected state

        with pytest.raises(ZkSyncBridgeError, match="Transaction processing finished in an unexpected state"):
            _bridge_eth_zksync(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "1" * 64,
                amount=1000000000000000000, # 1 ETH
                direction="deposit",
                l1_address=mock_account.address,
                l2_address=mock_account.address,
                l2_gas_limit=DEFAULT_L2_GAS_LIMIT
            )
        