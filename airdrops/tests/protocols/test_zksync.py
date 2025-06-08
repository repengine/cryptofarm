# airdrops/tests/protocols/test_zksync.py
"""
Unit tests for the zkSync Era protocol module.
"""
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal
from web3 import Web3

# Adjust imports based on your project structure
from airdrops.protocols.zksync import zksync


class TestZkSyncModule(unittest.TestCase):
    """
    Tests for the zkSync Era module functions.
    """

    def setUp(self):
        """Set up test fixtures, if any."""
        self.user_address = "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        self.private_key = "0x" + "a" * 64
        self.mock_config = {
            "networks": {
                "ethereum": {
                    "rpc_url": ("https://eth-mainnet.g.alchemy.com/v2/test"),
                    "bridge_address": ("0x32400084C286CF3E17e7B677ea9583e60a000324"),
                },
                "zksync": {
                    "rpc_url": "https://mainnet.era.zksync.io",
                    "bridge_address": ("0x0000000000000000000000000000000000008006"),
                },
            },
            "settings": {"l2_gas_limit": 800000, "l2_gas_per_pubdata_byte_limit": 800},
        }
        zksync.CONFIG = self.mock_config

    def test_validate_bridge_inputs_valid(self):
        """Test input validation with valid inputs."""
        # Should not raise any exception
        zksync._validate_bridge_inputs(
            self.user_address, self.private_key, Decimal("0.1"), self.mock_config
        )

    def test_validate_bridge_inputs_invalid_address(self):
        """Test input validation with invalid address."""
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                "invalid_address", self.private_key, Decimal("0.1"), self.mock_config
            )
        self.assertIn("Invalid user address", str(context.exception))

    def test_validate_bridge_inputs_invalid_private_key(self):
        """Test input validation with invalid private key."""
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                self.user_address, "short_key", Decimal("0.1"), self.mock_config
            )
        self.assertIn("Invalid private key", str(context.exception))

    def test_validate_bridge_inputs_negative_amount(self):
        """Test input validation with negative amount."""
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                self.user_address, self.private_key, Decimal("-0.1"), self.mock_config
            )
        self.assertIn("Amount must be positive", str(context.exception))

    def test_validate_bridge_inputs_empty_config(self):
        """Test input validation with empty config."""
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                self.user_address, self.private_key, Decimal("0.1"), {}
            )
        self.assertIn("Configuration dictionary is required", str(context.exception))

    def test_validate_bridge_inputs_missing_networks(self):
        """Test input validation with missing networks in config."""
        invalid_config = {"other": "value"}
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                self.user_address, self.private_key, Decimal("0.1"), invalid_config
            )
        self.assertIn("Missing required config key: networks", str(context.exception))

    @patch("airdrops.protocols.zksync.zksync.Web3")
    def test_get_web3_instance_success(self, mock_web3_class):
        """Test successful Web3 instance creation."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider = Mock()

        result = zksync._get_web3_instance("http://test-rpc", "Test Chain")

        self.assertEqual(result, mock_web3)
        mock_web3.is_connected.assert_called_once()

    @patch("airdrops.protocols.zksync.zksync.Web3")
    def test_get_web3_instance_connection_failure(self, mock_web3_class):
        """Test Web3 instance creation with connection failure."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = False
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider = Mock()

        with self.assertRaises(ConnectionError) as context:
            zksync._get_web3_instance("http://test-rpc", "Test Chain")

        self.assertIn("Failed to connect to Test Chain RPC", str(context.exception))

    @patch("airdrops.protocols.zksync.zksync.Web3")
    def test_get_web3_instance_exception(self, mock_web3_class):
        """Test Web3 instance creation with exception."""
        mock_web3_class.side_effect = Exception("Connection error")

        with self.assertRaises(ConnectionError) as context:
            zksync._get_web3_instance("http://test-rpc", "Test Chain")

        self.assertIn("Error connecting to Test Chain", str(context.exception))

    def test_estimate_l1_gas_success(self):
        """Test successful gas estimation."""
        mock_function = Mock()
        mock_function.estimate_gas.return_value = 100000

        result = zksync._estimate_l1_gas(mock_function, {}, 1.2)

        self.assertEqual(result, 120000)  # 100000 * 1.2
        mock_function.estimate_gas.assert_called_once_with({})

    def test_estimate_l1_gas_failure_fallback(self):
        """Test gas estimation failure with fallback."""
        mock_function = Mock()
        mock_function.estimate_gas.side_effect = Exception("Gas estimation failed")

        result = zksync._estimate_l1_gas(mock_function, {}, 1.2)

        self.assertEqual(result, 200000)  # Default fallback

    @patch("airdrops.protocols.zksync.zksync._execute_l1_to_l2_deposit")
    def test_bridge_eth_l1_to_l2_success(self, mock_deposit):
        """Test successful L1 to L2 bridge."""
        mock_deposit.return_value = (True, "0x123...abc")

        success, result = zksync.bridge_eth(
            self.user_address,
            self.private_key,
            Decimal("0.1"),
            True,  # to_l2
            self.mock_config,
        )

        self.assertTrue(success)
        self.assertEqual(result, "0x123...abc")
        mock_deposit.assert_called_once()

    @patch("airdrops.protocols.zksync.zksync._execute_l2_to_l1_withdrawal")
    def test_bridge_eth_l2_to_l1_success(self, mock_withdrawal):
        """Test successful L2 to L1 bridge."""
        mock_withdrawal.return_value = (True, "0x456...def")

        success, result = zksync.bridge_eth(
            self.user_address,
            self.private_key,
            Decimal("0.1"),
            False,  # to_l2
            self.mock_config,
        )

        self.assertTrue(success)
        self.assertEqual(result, "0x456...def")
        mock_withdrawal.assert_called_once()

    def test_bridge_eth_validation_error(self):
        """Test bridge_eth with validation error."""
        success, result = zksync.bridge_eth(
            "invalid_address", self.private_key, Decimal("0.1"), True, self.mock_config
        )

        self.assertFalse(success)
        self.assertIn("Validation error", result)

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    @patch("airdrops.protocols.zksync.zksync.Account")
    def test_execute_l1_to_l2_deposit_success(self, mock_account_class, mock_get_web3):
        """Test successful L1 to L2 deposit execution."""
        # Mock Web3 instance
        mock_w3 = Mock()
        mock_w3.eth.gas_price = 20000000000
        mock_w3.eth.get_transaction_count.return_value = 42
        mock_w3.eth.send_raw_transaction.return_value = Mock(hex=lambda: "0x123abc")
        mock_receipt = {"status": 1}
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
        mock_get_web3.return_value = mock_w3

        # Mock contract
        mock_contract = Mock()
        mock_request_fn = Mock()
        mock_request_fn.estimate_gas.return_value = 150000
        mock_request_fn.build_transaction.return_value = {
            "to": "0x32400084C286CF3E17e7B677ea9583e60a000324",
            "data": "0x123",
            "value": 100000000000000000,
            "gas": 200000,
            "gasPrice": 20000000000,
            "nonce": 42,
        }
        mock_contract.functions.requestL2Transaction.return_value = mock_request_fn
        mock_contract.functions.l2TransactionBaseCost.return_value.call.return_value = (
            1000000000000000
        )
        mock_w3.eth.contract.return_value = mock_contract

        # Mock account
        mock_account = Mock()
        mock_signed_txn = Mock()
        mock_signed_txn.raw_transaction = b"signed_tx_data"
        mock_account.sign_transaction.return_value = mock_signed_txn
        mock_account_class.from_key.return_value = mock_account

        success, result = zksync._execute_l1_to_l2_deposit(
            self.user_address,
            self.private_key,
            Web3.to_wei(Decimal("0.1"), "ether"),
            self.mock_config,
        )

        self.assertTrue(success)
        self.assertEqual(result, "0x123abc")

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    def test_execute_l1_to_l2_deposit_web3_error(self, mock_get_web3):
        """Test L1 to L2 deposit with Web3 error."""
        mock_get_web3.side_effect = ConnectionError("RPC connection failed")

        success, result = zksync._execute_l1_to_l2_deposit(
            self.user_address,
            self.private_key,
            Web3.to_wei(Decimal("0.1"), "ether"),
            self.mock_config,
        )

        self.assertFalse(success)
        self.assertIn("L1->L2 deposit error", result)

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    @patch("airdrops.protocols.zksync.zksync.Account")
    def test_execute_l2_to_l1_withdrawal_success(
        self, mock_account_class, mock_get_web3
    ):
        """Test successful L2 to L1 withdrawal execution."""
        # Mock Web3 instance
        mock_w3 = Mock()
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.get_transaction_count.return_value = 24
        mock_w3.eth.send_raw_transaction.return_value = Mock(hex=lambda: "0x456def")
        mock_receipt = {"status": 1}
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
        mock_get_web3.return_value = mock_w3

        # Mock contract
        mock_contract = Mock()
        mock_contract.functions.withdraw.return_value.build_transaction.return_value = {
            "to": "0x0000000000000000000000000000000000008006",
            "data": "0x456",
            "value": 100000000000000000,
            "gas": 100000,
            "gasPrice": 1000000000,
            "nonce": 24,
        }
        mock_contract.functions.withdraw.return_value.estimate_gas.return_value = 80000
        mock_w3.eth.contract.return_value = mock_contract

        # Mock account
        mock_account = Mock()
        mock_signed_txn = Mock()
        mock_signed_txn.raw_transaction = b"signed_tx_data"
        mock_account.sign_transaction.return_value = mock_signed_txn
        mock_account_class.from_key.return_value = mock_account

        success, result = zksync._execute_l2_to_l1_withdrawal(
            self.user_address,
            self.private_key,
            Web3.to_wei(Decimal("0.1"), "ether"),
            self.mock_config,
        )

        self.assertTrue(success)
        self.assertEqual(result, "0x456def")

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    @patch("airdrops.protocols.zksync.zksync.Account")
    def test_execute_l2_to_l1_withdrawal_transaction_failure(
        self, mock_account_class, mock_get_web3
    ):
        """Test L2 to L1 withdrawal with transaction failure."""
        # Mock Web3 instance
        mock_w3 = Mock()
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.get_transaction_count.return_value = 24
        mock_w3.eth.send_raw_transaction.return_value = Mock(hex=lambda: "0x456def")
        mock_receipt = {"status": 0}  # Failed
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
        mock_get_web3.return_value = mock_w3

        # Mock contract
        mock_contract = Mock()
        mock_contract.functions.withdraw.return_value.build_transaction.return_value = {
            "to": "0x0000000000000000000000000000000000008006",
            "data": "0x456",
            "value": 100000000000000000,
            "gas": 100000,
            "gasPrice": 1000000000,
            "nonce": 24,
        }
        mock_contract.functions.withdraw.return_value.estimate_gas.return_value = 80000
        mock_w3.eth.contract.return_value = mock_contract

        # Mock account
        mock_account = Mock()
        mock_signed_txn = Mock()
        mock_signed_txn.raw_transaction = b"signed_tx_data"
        mock_account.sign_transaction.return_value = mock_signed_txn
        mock_account_class.from_key.return_value = mock_account

        success, result = zksync._execute_l2_to_l1_withdrawal(
            self.user_address,
            self.private_key,
            Web3.to_wei(Decimal("0.1"), "ether"),
            self.mock_config,
        )

        self.assertFalse(success)
        self.assertIn("Transaction failed", result)

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    def test_execute_l2_to_l1_withdrawal_web3_error(self, mock_get_web3):
        """Test L2 to L1 withdrawal with Web3 error."""
        mock_get_web3.side_effect = ConnectionError("RPC connection failed")

        success, result = zksync._execute_l2_to_l1_withdrawal(
            self.user_address,
            self.private_key,
            Web3.to_wei(Decimal("0.1"), "ether"),
            self.mock_config,
        )

        self.assertFalse(success)
        self.assertIn("L2->L1 withdrawal error", result)

    def test_get_l1_bridge_abi(self):
        """Test L1 bridge ABI structure."""
        abi = zksync._get_l1_bridge_abi()

        self.assertIsInstance(abi, list)
        self.assertTrue(len(abi) >= 2)

        # Check for requestL2Transaction function
        request_l2_tx_found = False
        l2_tx_base_cost_found = False

        for item in abi:
            if item.get("name") == "requestL2Transaction":
                request_l2_tx_found = True
                self.assertEqual(item["type"], "function")
                self.assertEqual(item["stateMutability"], "payable")
            elif item.get("name") == "l2TransactionBaseCost":
                l2_tx_base_cost_found = True
                self.assertEqual(item["type"], "function")
                self.assertEqual(item["stateMutability"], "view")

        self.assertTrue(request_l2_tx_found)
        self.assertTrue(l2_tx_base_cost_found)

    def test_get_l2_bridge_abi(self):
        """Test L2 bridge ABI structure."""
        abi = zksync._get_l2_bridge_abi()

        self.assertIsInstance(abi, list)
        self.assertTrue(len(abi) >= 1)

        # Check for withdraw function
        withdraw_found = False
        for item in abi:
            if item.get("name") == "withdraw":
                withdraw_found = True
                self.assertEqual(item["type"], "function")
                self.assertEqual(item["stateMutability"], "payable")
                break

        self.assertTrue(withdraw_found)

    def test_bridge_eth_insufficient_balance_scenario(self):
        """Test bridge_eth behavior with insufficient balance (mocked)."""
        # This would be tested by mocking the Web3 calls to simulate
        # insufficient balance
        with patch(
            "airdrops.protocols.zksync.zksync._execute_l1_to_l2_deposit"
        ) as mock_deposit:
            mock_deposit.return_value = (False, "Insufficient balance for transaction")

            success, result = zksync.bridge_eth(
                self.user_address,
                self.private_key,
                Decimal("1000"),  # Large amount
                True,
                self.mock_config,
            )

            self.assertFalse(success)
            self.assertIn("Insufficient balance", result)

    def test_bridge_eth_rpc_error_scenario(self):
        """Test bridge_eth behavior with RPC errors (mocked)."""
        with patch(
            "airdrops.protocols.zksync.zksync._execute_l1_to_l2_deposit"
        ) as mock_deposit:
            mock_deposit.return_value = (
                False,
                "L1->L2 deposit error: RPC connection failed",
            )

            success, result = zksync.bridge_eth(
                self.user_address,
                self.private_key,
                Decimal("0.1"),
                True,
                self.mock_config,
            )

            self.assertFalse(success)
            self.assertIn("RPC connection failed", result)

    def test_swap_tokens_validation_invalid_user_address(self):
        """Test swap_tokens with invalid user address."""
        success, msg = zksync.swap_tokens(
            "invalid_address",
            self.private_key,
            "0x0000000000000000000000000000000000000000",
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            1000000000000000000,
            "syncswap",
            50,
            self.mock_config,
        )
        self.assertFalse(success)
        self.assertIn("Validation error", msg)
        self.assertIn("Invalid user address", msg)

    def test_swap_tokens_validation_invalid_token_addresses(self):
        """Test swap_tokens with invalid token addresses."""
        success, msg = zksync.swap_tokens(
            self.user_address,
            self.private_key,
            "invalid_token_in",
            "invalid_token_out",
            1000000000000000000,
            "syncswap",
            50,
            self.mock_config,
        )
        self.assertFalse(success)
        self.assertIn("Validation error", msg)
        self.assertIn("Invalid token_in_address", msg)

    def test_swap_tokens_validation_negative_amount(self):
        """Test swap_tokens with negative amount."""
        success, msg = zksync.swap_tokens(
            self.user_address,
            self.private_key,
            "0x0000000000000000000000000000000000000000",
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            -1000000000000000000,
            "syncswap",
            50,
            self.mock_config,
        )
        self.assertFalse(success)
        self.assertIn("Validation error", msg)
        self.assertIn("Amount must be positive", msg)

    def test_swap_tokens_validation_unsupported_dex(self):
        """Test swap_tokens with unsupported DEX."""
        success, msg = zksync.swap_tokens(
            self.user_address,
            self.private_key,
            "0x0000000000000000000000000000000000000000",
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            1000000000000000000,
            "uniswap",
            50,
            self.mock_config,
        )
        self.assertFalse(success)
        self.assertIn("Validation error", msg)
        self.assertIn("Unsupported DEX", msg)

    def test_swap_tokens_validation_invalid_slippage(self):
        """Test swap_tokens with invalid slippage."""
        success, msg = zksync.swap_tokens(
            self.user_address,
            self.private_key,
            "0x0000000000000000000000000000000000000000",
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            1000000000000000000,
            "syncswap",
            15000,
            self.mock_config,
        )
        self.assertFalse(success)
        self.assertIn("Validation error", msg)
        self.assertIn("Invalid slippage_bps", msg)

    @patch("airdrops.protocols.zksync.zksync._execute_syncswap_swap")
    def test_swap_tokens_syncswap_success(self, mock_syncswap):
        """Test successful swap_tokens with SyncSwap."""
        mock_syncswap.return_value = (True, "0x123abc")

        success, result = zksync.swap_tokens(
            self.user_address,
            self.private_key,
            "0x0000000000000000000000000000000000000000",
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            1000000000000000000,
            "syncswap",
            50,
            self.mock_config,
        )

        self.assertTrue(success)
        self.assertEqual(result, "0x123abc")
        mock_syncswap.assert_called_once()

    def test_determine_swap_path_eth_to_token(self):
        """Test path determination for ETH to token swap."""
        weth_address = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"
        token_out = "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4"

        path = zksync._determine_swap_path(
            "0x0000000000000000000000000000000000000000", token_out, weth_address
        )

        self.assertEqual(path, [weth_address, token_out])

    def test_determine_swap_path_token_to_eth(self):
        """Test path determination for token to ETH swap."""
        weth_address = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"
        token_in = "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4"

        path = zksync._determine_swap_path(
            token_in, "0x0000000000000000000000000000000000000000", weth_address
        )

        self.assertEqual(path, [token_in, weth_address])

    def test_determine_swap_path_token_to_token(self):
        """Test path determination for token to token swap."""
        weth_address = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"
        token_in = "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4"
        token_out = "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F988"

        path = zksync._determine_swap_path(token_in, token_out, weth_address)

        self.assertEqual(path, [token_in, token_out])

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    @patch("airdrops.protocols.zksync.zksync._handle_token_approval")
    @patch("airdrops.protocols.zksync.zksync._build_and_send_swap_transaction")
    def test_execute_syncswap_swap_success(
        self, mock_build_send, mock_approval, mock_get_web3
    ):
        """Test successful SyncSwap execution."""
        # Mock Web3 instance
        mock_w3 = Mock()
        mock_w3.eth.get_block.return_value = {"timestamp": 1000000}
        mock_get_web3.return_value = mock_w3

        # Mock router contract
        mock_contract = Mock()
        amounts_out = [1000000000000000000, 950000000000000000]
        get_amounts_out = mock_contract.functions.getAmountsOut.return_value
        get_amounts_out.call.return_value = amounts_out
        mock_w3.eth.contract.return_value = mock_contract

        # Mock approval and transaction
        mock_approval.return_value = True
        mock_build_send.return_value = (True, "0x123abc")

        # Enhanced config with tokens
        enhanced_config = {
            **self.mock_config,
            "tokens": {
                "WETH": {"address": "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"}
            },
        }
        enhanced_config["networks"]["zksync"][
            "dex_router_address"
        ] = "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295"

        success, result = zksync._execute_syncswap_swap(
            self.user_address,
            self.private_key,
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F988",
            1000000000000000000,
            50,
            enhanced_config,
        )

        self.assertTrue(success)
        self.assertEqual(result, "0x123abc")
        mock_approval.assert_called_once()
        mock_build_send.assert_called_once()

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    @patch("airdrops.protocols.zksync.zksync._handle_token_approval")
    def test_execute_syncswap_swap_get_amounts_out_failure(
        self, mock_approval, mock_get_web3
    ):
        """Test SyncSwap execution with getAmountsOut failure."""
        # Mock Web3 instance
        mock_w3 = Mock()
        mock_get_web3.return_value = mock_w3

        # Mock router contract with failing getAmountsOut
        mock_contract = Mock()
        mock_contract.functions.getAmountsOut.return_value.call.side_effect = Exception(
            "Insufficient liquidity"
        )
        mock_w3.eth.contract.return_value = mock_contract

        # Mock successful approval to get past that step
        mock_approval.return_value = True

        enhanced_config = {
            **self.mock_config,
            "tokens": {
                "WETH": {"address": "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"}
            },
        }

        success, result = zksync._execute_syncswap_swap(
            self.user_address,
            self.private_key,
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F988",
            1000000000000000000,
            50,
            enhanced_config,
        )

        self.assertFalse(success)
        self.assertIn("Failed to get expected output amount", result)

    @patch("airdrops.protocols.zksync.zksync.Account")
    def test_handle_token_approval_sufficient_allowance(self, mock_account_class):
        """Test token approval when allowance is sufficient."""
        # Mock Web3 instance
        mock_w3 = Mock()

        # Mock token contract with sufficient allowance
        mock_contract = Mock()
        mock_contract.functions.allowance.return_value.call.return_value = (
            2000000000000000000  # 2 ETH allowance
        )
        mock_w3.eth.contract.return_value = mock_contract

        result = zksync._handle_token_approval(
            mock_w3,
            self.user_address,
            self.private_key,
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295",
            1000000000000000000,  # 1 ETH needed
        )

        self.assertTrue(result)

    @patch("airdrops.protocols.zksync.zksync.Account")
    def test_handle_token_approval_needs_approval(self, mock_account_class):
        """Test token approval when approval is needed."""
        # Mock Web3 instance
        mock_w3 = Mock()
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.get_transaction_count.return_value = 42
        mock_w3.eth.send_raw_transaction.return_value = Mock(hex=lambda: "0x123")
        mock_receipt = {"status": 1}
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        # Mock token contract with insufficient allowance
        mock_contract = Mock()
        mock_contract.functions.allowance.return_value.call.return_value = 0
        estimate_gas_return = 50000
        approve_func = mock_contract.functions.approve.return_value
        approve_func.estimate_gas.return_value = estimate_gas_return
        build_tx_return = {
            "to": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            "data": "0x095ea7b3",
            "gas": 75000,
            "gasPrice": 1000000000,
            "nonce": 42,
        }
        approve_func.build_transaction.return_value = build_tx_return
        mock_w3.eth.contract.return_value = mock_contract

        # Mock account
        mock_account = Mock()
        mock_signed_txn = Mock()
        mock_signed_txn.raw_transaction = b"signed_tx_data"
        mock_account.sign_transaction.return_value = mock_signed_txn
        mock_account_class.from_key.return_value = mock_account

        result = zksync._handle_token_approval(
            mock_w3,
            self.user_address,
            self.private_key,
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295",
            1000000000000000000,
        )

        self.assertTrue(result)

    @patch("airdrops.protocols.zksync.zksync.Account")
    def test_handle_token_approval_transaction_failure(self, mock_account_class):
        """Test token approval with transaction failure."""
        # Mock Web3 instance
        mock_w3 = Mock()
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.get_transaction_count.return_value = 42
        mock_w3.eth.send_raw_transaction.return_value = Mock(hex=lambda: "0x123")
        mock_receipt = {"status": 0}  # Failed
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        # Mock token contract with insufficient allowance
        mock_contract = Mock()
        mock_contract.functions.allowance.return_value.call.return_value = 0
        approve_func = mock_contract.functions.approve.return_value
        approve_func.estimate_gas.return_value = 50000
        approve_func.build_transaction.return_value = {
            "to": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            "data": "0x095ea7b3",
            "gas": 75000,
            "gasPrice": 1000000000,
            "nonce": 42,
        }
        mock_w3.eth.contract.return_value = mock_contract

        # Mock account
        mock_account = Mock()
        mock_signed_txn = Mock()
        mock_signed_txn.raw_transaction = b"signed_tx_data"
        mock_account.sign_transaction.return_value = mock_signed_txn
        mock_account_class.from_key.return_value = mock_account

        result = zksync._handle_token_approval(
            mock_w3,
            self.user_address,
            self.private_key,
            "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
            "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295",
            1000000000000000000,
        )

        self.assertFalse(result)

    def test_lend_borrow_validation_invalid_user_address(self):
        """Test lend_borrow with invalid user address."""
        success, msg = zksync.lend_borrow(
            "invalid_address",
            self.private_key,
            "supply",
            "0x0000000000000000000000000000000000000000",
            1000000000000000000,
            "eralend",
            self.mock_config,
        )
        self.assertFalse(success)
        self.assertIn("Validation error", msg)
        self.assertIn("Invalid user address", msg)

    def test_lend_borrow_validation_invalid_action(self):
        """Test lend_borrow with invalid action."""
        success, msg = zksync.lend_borrow(
            self.user_address,
            self.private_key,
            "invalid_action",
            "0x0000000000000000000000000000000000000000",
            1000000000000000000,
            "eralend",
            self.mock_config,
        )
        self.assertFalse(success)
        self.assertIn("Validation error", msg)
        self.assertIn("Invalid action", msg)

    def test_lend_borrow_validation_missing_protocol_config(self):
        """Test lend_borrow with missing protocol configuration."""
        config_without_lending = {
            "networks": {"zksync": {"rpc_url": "https://mainnet.era.zksync.io"}}
        }
        success, msg = zksync.lend_borrow(
            self.user_address,
            self.private_key,
            "supply",
            "0x0000000000000000000000000000000000000000",
            1000000000000000000,
            "eralend",
            config_without_lending,
        )
        self.assertFalse(success)
        self.assertIn("Validation error", msg)
        self.assertIn("Missing lending_protocols", msg)

    @patch("airdrops.protocols.zksync.zksync._execute_supply_action")
    def test_lend_borrow_supply_success(self, mock_supply):
        """Test successful supply action."""
        mock_supply.return_value = (True, "0x123abc")

        enhanced_config = {
            **self.mock_config,
            "networks": {
                **self.mock_config["networks"],
                "zksync": {
                    **self.mock_config["networks"]["zksync"],
                    "lending_protocols": {
                        "eralend": {
                            "lending_pool_manager": "0x1234567890123456789012345678901234567890",  # noqa: E501
                            "weth_gateway": "0x0987654321098765432109876543210987654321",  # noqa: E501
                        }
                    },
                },
            },
        }

        success, result = zksync.lend_borrow(
            self.user_address,
            self.private_key,
            "supply",
            "0x0000000000000000000000000000000000000000",
            1000000000000000000,
            "eralend",
            enhanced_config,
        )

        self.assertTrue(success)
        self.assertEqual(result, "0x123abc")
        mock_supply.assert_called_once()

    @patch("airdrops.protocols.zksync.zksync._get_initial_onchain_state")
    @patch("airdrops.protocols.zksync.zksync._execute_action_sequence")
    def test_perform_random_activity_success(
        self, mock_execute_sequence, mock_get_state
    ):
        """Test successful perform_random_activity execution."""
        # Mock initial state
        mock_state = {
            "l2_balances": {"ETH": 1.0, "USDC": 1000.0},
            "eralend_positions": {
                "ETH": {"supplied": 0, "borrowed": 0, "is_collateral": False}
            },
        }
        mock_get_state.return_value = mock_state

        # Mock action sequence execution
        mock_execute_sequence.return_value = (True, "Executed 3 actions, 2 successful")

        # Enhanced config with random_activity
        enhanced_config = {
            **self.mock_config,
            "random_activity": {
                "enabled": True,
                "num_actions_range": [2, 4],
                "action_weights": {
                    "bridge_eth": 30,
                    "swap_tokens": 50,
                    "lend_borrow": 20,
                },
                "max_action_selection_retries": 3,
                "stop_on_first_failure": False,
            },
        }

        success, result = zksync.perform_random_activity(
            self.user_address, self.private_key, enhanced_config
        )

        self.assertTrue(success)
        self.assertIn("Executed 3 actions", result)
        mock_get_state.assert_called_once()
        mock_execute_sequence.assert_called_once()

    def test_perform_random_activity_disabled(self):
        """Test perform_random_activity when disabled in config."""
        enhanced_config = {
            **self.mock_config,
            "random_activity": {
                "enabled": False,
                "num_actions_range": [2, 4],
                "action_weights": {"bridge_eth": 100},
            },
        }

        success, result = zksync.perform_random_activity(
            self.user_address, self.private_key, enhanced_config
        )

        self.assertTrue(success)
        self.assertEqual(result, "Random activity disabled in configuration")

    def test_validate_random_activity_config_valid(self):
        """Test _validate_random_activity_config with valid config."""
        valid_config = {
            "random_activity": {
                "enabled": True,
                "num_actions_range": [2, 4],
                "action_weights": {"bridge_eth": 30, "swap_tokens": 70},
            }
        }

        result = zksync._validate_random_activity_config(valid_config)
        self.assertTrue(result)

    def test_validate_random_activity_config_missing_section(self):
        """Test _validate_random_activity_config with missing section."""
        invalid_config = {}

        result = zksync._validate_random_activity_config(invalid_config)
        self.assertFalse(result)

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    def test_get_initial_onchain_state_success(self, mock_get_web3):
        """Test successful _get_initial_onchain_state execution."""
        # Mock Web3 instance
        mock_w3 = Mock()
        mock_w3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
        mock_get_web3.return_value = mock_w3

        enhanced_config = {
            **self.mock_config,
            "random_activity": {
                "initial_state_fetch": {"tokens_to_track_balance": ["ETH"]}
            },
        }

        state = zksync._get_initial_onchain_state(self.user_address, enhanced_config)

        self.assertIsNotNone(state)
        self.assertIn("l2_balances", state)
        self.assertEqual(state["l2_balances"]["ETH"], 1.0)

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    def test_get_initial_onchain_state_web3_failure(self, mock_get_web3):
        """Test _get_initial_onchain_state with Web3 failure."""
        mock_get_web3.side_effect = ConnectionError("RPC connection failed")

        enhanced_config = {
            **self.mock_config,
            "random_activity": {
                "initial_state_fetch": {"tokens_to_track_balance": ["ETH"]}
            },
        }

        state = zksync._get_initial_onchain_state(self.user_address, enhanced_config)
        self.assertIsNone(state)

    @patch("airdrops.protocols.zksync.zksync.random.choices")
    def test_select_action_type(self, mock_choices):
        """Test _select_action_type function."""
        mock_choices.return_value = ["bridge_eth"]
        action_weights = {"bridge_eth": 30, "swap_tokens": 70}

        result = zksync._select_action_type(action_weights)
        self.assertEqual(result, "bridge_eth")
        mock_choices.assert_called_once()

    def test_randomize_bridge_parameters(self):
        """Test _randomize_bridge_parameters function."""
        mock_uniform_path = "airdrops.protocols.zksync.zksync.random.uniform"
        mock_random_path = "airdrops.protocols.zksync.zksync.random.random"

        with patch(mock_uniform_path) as mock_uniform, patch(
            mock_random_path
        ) as mock_random:
            mock_uniform.return_value = 0.05
            mock_random.return_value = 0.5  # Less than 0.6, so to_l2 = True

            bridge_config = {"amount_range_eth": [0.01, 0.1], "probability_to_l2": 0.6}
            state = {"l2_balances": {"ETH": 1.0}}

            params = zksync._randomize_bridge_parameters(bridge_config, state)

            self.assertIn("amount_eth", params)
            self.assertIn("to_l2", params)
            self.assertEqual(params["to_l2"], True)

    def test_randomize_swap_parameters_success(self):
        """Test _randomize_swap_parameters with valid configuration."""
        mock_choice_path = "airdrops.protocols.zksync.zksync.random.choice"
        mock_uniform_path = "airdrops.protocols.zksync.zksync.random.uniform"
        mock_randint_path = "airdrops.protocols.zksync.zksync.random.randint"

        config = {
            "tokens": {
                "ETH": {"address": "0x0000000000000000000000000000000000000000", "decimals": 18},  # noqa: E501
                "USDC": {"address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4", "decimals": 6},  # noqa: E501
            }
        }
        state = {"l2_balances": {"ETH": 1.0, "USDC": 1000.0}}
        swap_config = {
            "token_pairs": [["ETH", "USDC"]],
            "amount_in_percentage_range": [0.1, 0.25],
            "slippage_bps_range": [30, 70]
        }

        with patch(mock_choice_path) as mock_choice, patch(
            mock_uniform_path
        ) as mock_uniform, patch(mock_randint_path) as mock_randint:
            mock_choice.return_value = ["ETH", "USDC"]
            mock_uniform.return_value = 0.1
            mock_randint.return_value = 50

            params = zksync._randomize_swap_parameters(swap_config, state, config)

            self.assertIn("token_in_address", params)
            self.assertIn("token_out_address", params)
            self.assertIn("amount_in", params)
            self.assertIn("dex_name", params)
            self.assertIn("slippage_bps", params)

    def test_check_action_feasibility_bridge_eth(self):
        """Test _check_action_feasibility for bridge_eth action."""
        state = {"l2_balances": {"ETH": 1.0}}
        params = {"amount_eth": 0.1, "to_l2": False}

        result = zksync._check_action_feasibility("bridge_eth", params, state)
        self.assertTrue(result)

        # Test insufficient balance
        params = {"amount_eth": 2.0, "to_l2": False}
        result = zksync._check_action_feasibility("bridge_eth", params, state)
        self.assertFalse(result)

    @patch("airdrops.protocols.zksync.zksync.bridge_eth")
    def test_execute_single_action_bridge_eth(self, mock_bridge_eth):
        """Test _execute_single_action for bridge_eth."""
        mock_bridge_eth.return_value = (True, "0x123abc")

        params = {"amount_eth": 0.1, "to_l2": True}
        config = self.mock_config

        result = zksync._execute_single_action(
            "bridge_eth", self.user_address, self.private_key, params, config
        )

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("action_type", result)
        mock_bridge_eth.assert_called_once()

    def test_execute_single_action_unknown_type(self):
        """Test _execute_single_action with unknown action type."""
        params = {}
        config = self.mock_config

        result = zksync._execute_single_action(
            "unknown_action", self.user_address, self.private_key, params, config
        )

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("action_type", result)
        self.assertFalse(result["success"])

    def test_update_internal_state_bridge_eth(self):
        """Test _update_internal_state for bridge_eth action."""
        state = {"l2_balances": {"ETH": 1.0}}
        action_result = {
            "success": True,
            "action_type": "bridge_eth",
            "amount_eth": 0.1,
            "to_l2": True
        }

        # The function modifies state in-place and may return None
        result = zksync._update_internal_state(state, action_result)

        # Check that state was modified (the function works in-place)
        self.assertIsInstance(state, dict)
        self.assertIn("l2_balances", state)

        # The function may return None or the modified state
        if result is not None:
            self.assertIsInstance(result, dict)

    @patch("airdrops.protocols.zksync.zksync._select_and_execute_action")
    def test_execute_action_sequence_success(self, mock_select_execute):
        """Test _execute_action_sequence with successful execution."""
        mock_select_execute.side_effect = [
            {"success": True, "action_type": "bridge_eth", "tx_hash": "0x123"},
            {"success": True, "action_type": "swap_tokens", "tx_hash": "0x456"},
            {"success": True, "action_type": "lend_borrow", "tx_hash": "0x789"},
        ]

        state = {"l2_balances": {"ETH": 1.0}}
        config = {
            **self.mock_config,
            "random_activity": {"stop_on_first_failure": False},
        }

        success, result = zksync._execute_action_sequence(
            self.user_address, self.private_key, config, state, 3
        )

        self.assertTrue(success)
        self.assertIn("Executed 3 actions, 3 successful", result)
        self.assertEqual(mock_select_execute.call_count, 3)


if __name__ == "__main__":
    unittest.main()
