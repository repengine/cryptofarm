"""
Comprehensive tests for zkSync core functions to increase test coverage.

This module tests the internal helper functions and core functionality
of the zkSync protocol that are currently uncovered by existing tests.
"""

import json
import pytest
from unittest.mock import Mock, patch
from web3.exceptions import ContractLogicError
from eth_account.signers.local import LocalAccount

from src.airdrops.protocols.zksync.zksync import (
    _load_abi_zksync,
    _get_account_zksync,
    _get_l1_token_address_zksync,
    _get_l2_token_address_zksync,
    _get_contract_zksync,
    _build_and_send_tx_zksync,
    _approve_erc20_zksync,
    _get_syncswap_classic_pool_factory_contract_zksync,
    _get_syncswap_pool_address_zksync,
    _get_expected_amount_out_syncswap_zksync,
    _calculate_amount_out_min_syncswap_zksync,
    _encode_swap_step_data_zksync,
    bridge_assets,
    provide_liquidity,
    remove_liquidity
)
from src.airdrops.protocols.zksync.exceptions import (
    TransactionRevertedError,
    GasEstimationError,
    InsufficientLiquidityError,
    TokenNotSupportedError
)


class TestABILoading:
    """Test ABI loading functionality."""

    def test_load_abi_success(self, tmp_path):
        """Test successful ABI loading."""
        # Create a temporary ABI file
        abi_dir = tmp_path / "abi"
        abi_dir.mkdir()
        abi_file = abi_dir / "TestContract.json"
        test_abi = [{"type": "function", "name": "test"}]
        abi_file.write_text(json.dumps(test_abi))
        
        with patch('src.airdrops.protocols.zksync.zksync.Path') as mock_path:
            mock_path.return_value.parent = tmp_path
            result = _load_abi_zksync("TestContract")
            assert result == test_abi

    def test_load_abi_file_not_found(self):
        """Test ABI loading with missing file."""
        with pytest.raises(FileNotFoundError, match="ABI file not found"):
            _load_abi_zksync("NonExistentContract")

    def test_load_abi_invalid_json(self, tmp_path):
        """Test ABI loading with invalid JSON."""
        abi_dir = tmp_path / "abi"
        abi_dir.mkdir()
        abi_file = abi_dir / "InvalidContract.json"
        abi_file.write_text("invalid json content")
        
        with patch('src.airdrops.protocols.zksync.zksync.Path') as mock_path:
            mock_path.return_value.parent = tmp_path
            with pytest.raises(json.JSONDecodeError):
                _load_abi_zksync("InvalidContract")


class TestAccountManagement:
    """Test account management functions."""

    def test_get_account_valid_key(self):
        """Test account creation with valid private key."""
        private_key = "0x" + "1" * 64
        mock_web3 = Mock()
        
        with patch('src.airdrops.protocols.zksync.zksync.Account') as mock_account:
            mock_local_account = Mock(spec=LocalAccount)
            mock_account.from_key.return_value = mock_local_account
            
            result = _get_account_zksync(private_key, mock_web3)
            
            assert result == mock_local_account
            mock_account.from_key.assert_called_once_with(private_key)

    def test_get_account_key_without_prefix(self):
        """Test account creation with private key without 0x prefix."""
        private_key = "1" * 64
        mock_web3 = Mock()
        
        with patch('src.airdrops.protocols.zksync.zksync.Account') as mock_account:
            mock_local_account = Mock(spec=LocalAccount)
            mock_account.from_key.return_value = mock_local_account
            
            result = _get_account_zksync(private_key, mock_web3)
            
            assert result == mock_local_account
            mock_account.from_key.assert_called_once_with("0x" + private_key)

    def test_get_account_invalid_key(self):
        """Test account creation with invalid private key."""
        private_key = "invalid_key"
        mock_web3 = Mock()
        
        with patch('src.airdrops.protocols.zksync.zksync.Account') as mock_account:
            mock_account.from_key.side_effect = ValueError("Invalid key")
            
            with pytest.raises(ValueError, match="Invalid private key"):
                _get_account_zksync(private_key, mock_web3)


class TestTokenAddressResolution:
    """Test token address resolution functions."""

    @patch('src.airdrops.protocols.zksync.zksync.ZKSYNC_TOKEN_ADDRESSES')
    def test_get_l1_token_address_success(self, mock_addresses):
        """Test successful L1 token address retrieval."""
        mock_addresses.__getitem__.return_value = {"L1": "0x1234567890123456789012345678901234567890"}
        mock_addresses.__contains__.return_value = True
        
        result = _get_l1_token_address_zksync("USDC")
        assert result == "0x1234567890123456789012345678901234567890"

    @patch('src.airdrops.protocols.zksync.zksync.ZKSYNC_TOKEN_ADDRESSES')
    def test_get_l1_token_address_not_found(self, mock_addresses):
        """Test L1 token address retrieval for unsupported token."""
        mock_addresses.__contains__.return_value = False
        
        with pytest.raises(TokenNotSupportedError, match="not supported"):
            _get_l1_token_address_zksync("UNKNOWN")

    @patch('src.airdrops.protocols.zksync.zksync.constants.ZKSYNC_TOKEN_ADDRESSES')
    def test_get_l2_token_address_success(self, mock_addresses):
        """Test successful L2 token address retrieval."""
        mock_addresses.__getitem__.return_value = {"L2": "0x9876543210987654321098765432109876543210"}
        mock_addresses.__contains__.return_value = True
        
        result = _get_l2_token_address_zksync("USDC")
        assert result == "0x9876543210987654321098765432109876543210"

    @patch('src.airdrops.protocols.zksync.zksync.constants.ZKSYNC_TOKEN_ADDRESSES')
    def test_get_l2_token_address_eth_special_case(self, mock_addresses):
        """Test L2 token address retrieval for ETH (uses WETH)."""
        mock_addresses.__contains__.side_effect = lambda x: x in ["ETH", "WETH"]
        mock_addresses.__getitem__.side_effect = lambda x: {
            "ETH": {"L1": "0x0000000000000000000000000000000000000000", "L2": None},
            "WETH": {"L1": "0x1111111111111111111111111111111111111111", "L2": "0x2222222222222222222222222222222222222222"}
        }[x]
        mock_addresses.get.return_value = {"L1": "0x1111111111111111111111111111111111111111", "L2": "0x2222222222222222222222222222222222222222"}
        
        result = _get_l2_token_address_zksync("ETH")
        assert result == "0x2222222222222222222222222222222222222222"


class TestContractInteraction:
    """Test contract interaction functions."""

    @patch('src.airdrops.protocols.zksync.zksync._load_abi_zksync')
    def test_get_contract_success(self, mock_load_abi):
        """Test successful contract instantiation."""
        mock_abi = [{"type": "function", "name": "test"}]
        mock_load_abi.return_value = mock_abi
        
        mock_web3 = Mock()
        mock_contract = Mock()
        mock_web3.eth.contract.return_value = mock_contract
        
        with patch('src.airdrops.protocols.zksync.zksync.Web3') as mock_web3_class:
            mock_web3_class.to_checksum_address.return_value = "0x1234567890123456789012345678901234567890"
            
            result = _get_contract_zksync(mock_web3, "TestContract", "0x1234567890123456789012345678901234567890")
            
            assert result == mock_contract
            mock_load_abi.assert_called_once_with("TestContract")
            mock_web3.eth.contract.assert_called_once()


class TestTransactionBuilding:
    """Test transaction building and sending functions."""

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_build_and_send_tx_success(self, mock_get_account):
        """Test successful transaction building and sending."""
        # Setup mocks
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.return_value = 1
        mock_web3.eth.gas_price = 20000000000
        mock_web3.eth.estimate_gas.return_value = 21000
        mock_web3.eth.account.sign_transaction.return_value = Mock(raw_transaction=b"signed_tx")
        mock_web3.eth.send_raw_transaction.return_value = b"tx_hash"
        mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 1}
        
        tx_params = {
            "to": "0x9876543210987654321098765432109876543210",
            "value": 1000000000000000000,
            "data": "0x"
        }
        
        result = _build_and_send_tx_zksync(mock_web3, "0x" + "1" * 64, tx_params)
        
        assert result == "74785f68617368"  # hex encoding of b"tx_hash"
        mock_web3.eth.send_raw_transaction.assert_called_once()

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_build_and_send_tx_gas_estimation_failure(self, mock_get_account):
        """Test transaction building with gas estimation failure."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.return_value = 1
        mock_web3.eth.gas_price = 20000000000
        mock_web3.eth.estimate_gas.side_effect = ContractLogicError("Revert", data="0x123")
        
        tx_params = {"to": "0x9876543210987654321098765432109876543210", "value": 1000000000000000000}
        
        with pytest.raises(GasEstimationError, match="Gas estimation failed"):
            _build_and_send_tx_zksync(mock_web3, "0x" + "1" * 64, tx_params)

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_build_and_send_tx_transaction_reverted(self, mock_get_account):
        """Test transaction building with reverted transaction."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.return_value = 1
        mock_web3.eth.gas_price = 20000000000
        mock_web3.eth.estimate_gas.return_value = 21000
        mock_web3.eth.account.sign_transaction.return_value = Mock(raw_transaction=b"signed_tx")
        mock_web3.eth.send_raw_transaction.return_value = b"tx_hash"
        mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 0}  # Failed
        
        tx_params = {"to": "0x9876543210987654321098765432109876543210", "value": 1000000000000000000}
        
        with pytest.raises(TransactionRevertedError, match="reverted"):
            _build_and_send_tx_zksync(mock_web3, "0x" + "1" * 64, tx_params)


class TestERC20Approval:
    """Test ERC20 approval functionality."""

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._build_and_send_tx_zksync')
    def test_approve_erc20_success(self, mock_build_send, mock_get_contract, mock_get_account):
        """Test successful ERC20 approval."""
        # Setup mocks
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_contract = Mock()
        mock_contract.functions.allowance.return_value.call.return_value = 0  # No existing allowance
        mock_contract.functions.approve.return_value.build_transaction.return_value = {
            "to": "0x9876543210987654321098765432109876543210",
            "data": "0x095ea7b3"
        }
        mock_get_contract.return_value = mock_contract
        
        mock_build_send.return_value = "0x789"
        
        mock_web3 = Mock()
        mock_web3.eth.gas_price = 20000000000
        
        result = _approve_erc20_zksync(
            mock_web3, "0x" + "1" * 64, "0x9876543210987654321098765432109876543210", 
            "0x1111111111111111111111111111111111111111", 1000000000000000000
        )
        
        assert result == "0x789"
        mock_build_send.assert_called_once()

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    def test_approve_erc20_sufficient_allowance(self, mock_get_contract, mock_get_account):
        """Test ERC20 approval when sufficient allowance already exists."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_contract = Mock()
        mock_contract.functions.allowance.return_value.call.return_value = 2000000000000000000  # 2 ETH
        mock_get_contract.return_value = mock_contract
        
        mock_web3 = Mock()
        
        result = _approve_erc20_zksync(
            mock_web3, "0x" + "1" * 64, "0x9876543210987654321098765432109876543210", 
            "0x1111111111111111111111111111111111111111", 1000000000000000000  # 1 ETH
        )
        
        assert "existing_approval_sufficient" in result


class TestSyncSwapHelpers:
    """Test SyncSwap helper functions."""

    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    def test_get_syncswap_factory_contract(self, mock_get_contract):
        """Test getting SyncSwap factory contract."""
        mock_contract = Mock()
        mock_get_contract.return_value = mock_contract
        mock_web3 = Mock()
        
        result = _get_syncswap_classic_pool_factory_contract_zksync(mock_web3)
        
        assert result == mock_contract
        mock_get_contract.assert_called_once()

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_classic_pool_factory_contract_zksync')
    def test_get_syncswap_pool_address_success(self, mock_get_factory):
        """Test successful pool address retrieval."""
        mock_factory = Mock()
        mock_factory.functions.getPool.return_value.call.return_value = "0x1234567890123456789012345678901234567890"
        mock_get_factory.return_value = mock_factory
        
        mock_web3 = Mock()
        
        with patch('src.airdrops.protocols.zksync.zksync.Web3') as mock_web3_class:
            mock_web3_class.to_checksum_address.side_effect = lambda x: x
            
            result = _get_syncswap_pool_address_zksync(
                mock_web3, "0x9876543210987654321098765432109876543210", 
                "0x1111111111111111111111111111111111111111"
            )
            
            assert result == "0x1234567890123456789012345678901234567890"

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_classic_pool_factory_contract_zksync')
    def test_get_syncswap_pool_address_not_found(self, mock_get_factory):
        """Test pool address retrieval when pool doesn't exist."""
        mock_factory = Mock()
        mock_factory.functions.getPool.return_value.call.return_value = "0x0000000000000000000000000000000000000000"
        mock_get_factory.return_value = mock_factory
        
        mock_web3 = Mock()
        
        with patch('src.airdrops.protocols.zksync.zksync.Web3') as mock_web3_class:
            mock_web3_class.to_checksum_address.side_effect = lambda x: x
            
            result = _get_syncswap_pool_address_zksync(
                mock_web3, "0x9876543210987654321098765432109876543210", 
                "0x1111111111111111111111111111111111111111"
            )
            
            assert result is None


class TestSwapCalculations:
    """Test swap calculation functions."""

    def test_calculate_amount_out_min_valid_slippage(self):
        """Test amount out min calculation with valid slippage."""
        expected_amount = 1000000000000000000  # 1 ETH
        slippage = 0.5  # 0.5%
        
        result = _calculate_amount_out_min_syncswap_zksync(expected_amount, slippage)
        
        expected_min = int(expected_amount * 0.995)  # 99.5% of expected
        assert result == expected_min

    def test_calculate_amount_out_min_invalid_slippage(self):
        """Test amount out min calculation with invalid slippage."""
        expected_amount = 1000000000000000000
        
        with pytest.raises(ValueError, match="Slippage percent must be between 0 and 100"):
            _calculate_amount_out_min_syncswap_zksync(expected_amount, -1)
        
        with pytest.raises(ValueError, match="Slippage percent must be between 0 and 100"):
            _calculate_amount_out_min_syncswap_zksync(expected_amount, 101)

    def test_encode_swap_step_data(self):
        """Test swap step data encoding."""
        with patch('src.airdrops.protocols.zksync.zksync.abi_encode') as mock_encode:
            with patch('src.airdrops.protocols.zksync.zksync.Web3') as mock_web3:
                mock_web3.to_checksum_address.side_effect = lambda x: x
                mock_encode.return_value = b"encoded_data"
                
                result = _encode_swap_step_data_zksync(
                    "0x1234567890123456789012345678901234567890", 
                    "0x9876543210987654321098765432109876543210", 1
                )
                
                mock_encode.assert_called_once()
                assert result.hex() == "encoded_data".encode().hex()


class TestBridgeFunctions:
    """Test bridge functionality."""

    @patch('src.airdrops.protocols.zksync.zksync._bridge_eth_zksync')
    def test_bridge_assets_eth_deposit(self, mock_bridge_eth):
        """Test bridging ETH for deposit."""
        mock_bridge_eth.return_value = "0x1234567890123456789012345678901234567890123456789012345678901234"
        mock_web3_l1 = Mock()
        mock_web3_l2 = Mock()
        
        result = bridge_assets(
            mock_web3_l1, mock_web3_l2, "0x" + "1" * 64, "ETH", 1000000000000000000, "deposit"
        )
        
        assert result == "0x1234567890123456789012345678901234567890123456789012345678901234"
        mock_bridge_eth.assert_called_once()

    def test_bridge_assets_invalid_direction(self):
        """Test bridge assets with invalid direction."""
        mock_web3_l1 = Mock()
        mock_web3_l2 = Mock()
        
        with pytest.raises(ValueError, match="Direction must be"):
            bridge_assets(
                mock_web3_l1, mock_web3_l2, "0x" + "1" * 64, "ETH", 1000000000000000000, "invalid"
            )

    def test_bridge_assets_negative_amount(self):
        """Test bridge assets with negative amount."""
        mock_web3_l1 = Mock()
        mock_web3_l2 = Mock()
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            bridge_assets(
                mock_web3_l1, mock_web3_l2, "0x" + "1" * 64, "ETH", -1, "deposit"
            )


class TestExpectedAmountOut:
    """Test expected amount out calculation for SyncSwap."""

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_pool_address_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_classic_pool_contract_zksync')
    def test_get_expected_amount_out_direct_pool(self, mock_get_pool_contract, mock_get_pool_address):
        """Test expected amount out with direct pool."""
        mock_get_pool_address.return_value = "0x1234567890123456789012345678901234567890"
        
        mock_pool = Mock()
        mock_pool.functions.getAmountOut.return_value.call.return_value = 1000000000
        mock_get_pool_contract.return_value = mock_pool
        
        mock_web3 = Mock()
        
        with patch('src.airdrops.protocols.zksync.zksync.Web3') as mock_web3_class:
            mock_web3_class.to_checksum_address.side_effect = lambda x: x
            
            result = _get_expected_amount_out_syncswap_zksync(
                mock_web3, "0x9876543210987654321098765432109876543210", 
                "0x1111111111111111111111111111111111111111", 500000000, 
                "0x2222222222222222222222222222222222222222", 
                "0x3333333333333333333333333333333333333333"
            )
            
            assert result == 1000000000

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_pool_address_zksync')
    def test_get_expected_amount_out_no_pool(self, mock_get_pool_address):
        """Test expected amount out with no available pool."""
        mock_get_pool_address.return_value = None
        
        mock_web3 = Mock()
        
        with pytest.raises(InsufficientLiquidityError, match="No liquidity or path found"):
            _get_expected_amount_out_syncswap_zksync(
                mock_web3, "0x9876543210987654321098765432109876543210", 
                "0x1111111111111111111111111111111111111111", 500000000, 
                "0x2222222222222222222222222222222222222222", 
                "0x3333333333333333333333333333333333333333"
            )


class TestLiquidityFunctions:
    """Test liquidity provision and removal functions."""

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_l2_token_address_zksync')
    def test_provide_liquidity_invalid_dex(self, mock_get_token_address, mock_get_account):
        """Test liquidity provision with invalid DEX."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        
        with pytest.raises(ValueError, match="Unsupported DEX"):
            provide_liquidity(
                mock_web3, "0x" + "1" * 64, "ETH", "USDC",
                1000000000000000000, 1000000000, "invalid_dex"
            )

    @patch('src.airdrops.protocols.zksync.zksync._get_account_zksync')
    @patch('src.airdrops.protocols.zksync.zksync._get_l2_token_address_zksync')
    def test_remove_liquidity_invalid_percent(self, mock_get_token_address, mock_get_account):
        """Test liquidity removal with invalid percentage."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3 = Mock()
        
        with pytest.raises(ValueError, match="Liquidity percent must be between 0 and 100"):
            remove_liquidity(
                mock_web3, "0x" + "1" * 64, "ETH", "USDC", -10.0, "syncswap"
            )
        
        with pytest.raises(ValueError, match="Liquidity percent must be between 0 and 100"):
            remove_liquidity(
                mock_web3, "0x" + "1" * 64, "ETH", "USDC", 150.0, "syncswap"
            )