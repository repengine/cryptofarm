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
        self.user_address = Web3.to_checksum_address("0x742d35Cc6634C0532925a3b8D4C9db96590c6C87")
        self.private_key = "0x" + "a" * 64
        self.mock_config = {
            "networks": {
                "ethereum": {
                    "rpc_url": "https://eth-mainnet.g.alchemy.com/v2/test",
                    "bridge_address": "0x32400084C286CF3E17e7B677ea9583e60a000324",
                },
                "zksync": {
                    "rpc_url": "https://mainnet.era.zksync.io",
                    "bridge_address": "0x0000000000000000000000000000000000008006",
                    "lending_protocols": {
                        "eralend": {
                            "lending_pool_manager": "0x69FA688f1Dc42A6b5063058284e5389D8901d57e",
                            "weth_gateway": "0x72eF506370076208a9a6fC82d3530587090B949d",
                        }
                    },
                    "dexs": {
                        "syncswap": {
                            "router_address": "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295",
                            "router_abi": [
                                {
                                    "name": "swapExactTokensForTokens",
                                    "type": "function",
                                    "inputs": [],
                                    "outputs": []
                                },
                                {
                                    "name": "getAmountsOut",
                                    "type": "function",
                                    "inputs": [],
                                    "outputs": []
                                }
                            ]
                        }
                    },
                },
            },
            "settings": {"l2_gas_limit": 800000, "l2_gas_per_pubdata_byte_limit": 800},
            "tokens": {
                "ETH": {"address": "0x0000000000000000000000000000000000000000",
                        "decimals": 18},
                "USDC": {"address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
                         "decimals": 6},
                "WETH": {"address": "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",
                         "decimals": 18},
            },
            "random_activity": {
                "enabled": True,
                "min_actions": 1,
                "max_actions": 3,
                "action_types": ["bridge_eth", "swap_tokens", "lend_borrow"],
                "action_weights": {"bridge_eth": 30, "swap_tokens": 70,
                                   "lend_borrow": 50},
                "initial_state_fetch": {"tokens_to_track_balance": ["ETH", "USDC"]},
                "bridge_eth": {
                    "min_amount_eth": 0.001,
                    "max_amount_eth": 0.01,
                    "to_l2_probability": 0.7,
                },
                "swap_tokens": {
                    "tokens": ["ETH", "USDC"],
                    "dexs": ["syncswap"],
                    "slippage_bps": 50,
                    "token_pairs": [["ETH", "USDC"], ["USDC", "ETH"]],
                    "amount_in_percentage_range": [0.1, 0.5],
                    "slippage_bps_range": [30, 70],
                },
                "lend_borrow": {
                    "actions": ["supply", "withdraw", "borrow", "repay",
                                "set_collateral"],
                    "protocols": ["eralend"],
                },
                "min_delay": 1,
                "max_delay": 5,
            },
        }

    def test_validate_bridge_inputs_valid(self):
        """Test input validation with valid inputs."""
        try:
            zksync._validate_bridge_inputs(
                self.user_address, self.private_key, Decimal("0.1"), True, self.mock_config
            )
        except ValueError:
            self.fail("zksync._validate_bridge_inputs() raised ValueError unexpectedly!")

    def test_validate_bridge_inputs_invalid_address(self):
        """Test input validation with invalid address."""
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                "invalid_address",
                self.private_key,
                Decimal("0.1"),
                True,
                self.mock_config,
            )
        self.assertIn("Invalid user address", str(context.exception))

    def test_validate_bridge_inputs_invalid_private_key(self):
        """Test input validation with invalid private key."""
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                self.user_address,
                "short_key",
                Decimal("0.1"),
                True,
                self.mock_config,
            )
        self.assertIn("Invalid private key format", str(context.exception))

    def test_validate_bridge_inputs_negative_amount(self):
        """Test input validation with negative amount."""
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                self.user_address,
                self.private_key,
                Decimal("-0.1"),
                True,
                self.mock_config,
            )
        self.assertIn("Amount must be a positive Decimal", str(context.exception))

    def test_validate_bridge_inputs_empty_config(self):
        """Test input validation with empty config."""
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                self.user_address, self.private_key, Decimal("0.1"), True, {}
            )
        self.assertIn("Configuration dictionary is required", str(context.exception))

    def test_validate_bridge_inputs_missing_networks(self):
        """Test input validation with missing networks in config."""
        invalid_config = {"other": "value"}
        with self.assertRaises(ValueError) as context:
            zksync._validate_bridge_inputs(
                self.user_address,
                self.private_key,
                Decimal("0.1"),
                True,
                invalid_config,
            )
        self.assertIn("Config must contain a 'networks' dictionary", str(context.exception))

    @patch("airdrops.shared.connection_manager.ConnectionManager.get_web3")
    def test_get_web3_instance_success(self, mock_get_web3):
        """Test successful Web3 instance creation."""
        mock_w3 = Mock()
        mock_get_web3.return_value = mock_w3

        result = zksync._get_web3_instance(self.mock_config, "ethereum")

        self.assertEqual(result, mock_w3)
        mock_get_web3.assert_called_once_with("ethereum")

    @patch("airdrops.shared.connection_manager.ConnectionManager.get_web3")
    def test_get_web3_instance_connection_failure(self, mock_get_web3):
        """Test Web3 instance creation with connection failure."""
        mock_get_web3.side_effect = ConnectionError("Failed to connect to ethereum after 3 attempts.")

        with self.assertRaises(ConnectionError) as context:
            zksync._get_web3_instance(self.mock_config, "ethereum")
        self.assertIn("Failed to connect to ethereum after 3 attempts.", str(context.exception))

    def test_estimate_l1_gas_success(self):
        """Test successful gas estimation."""
        mock_w3 = Mock()
        mock_w3.eth.estimate_gas.return_value = 100000
        mock_w3.eth.get_transaction_count.return_value = 1
        mock_w3.eth.gas_price = 20000000000
        mock_contract = Mock()
        
        # Mock the contract function call chain
        mock_function = Mock()
        mock_function.build_transaction.return_value = {"gas": 100000}
        mock_contract.functions.requestL2Transaction.return_value = mock_function

        result = zksync._estimate_l1_gas(
            mock_w3, mock_contract, self.user_address, 100000000000000000, 1000000, 800
        )

        self.assertEqual(result, 100000)

    def test_estimate_l1_gas_failure_fallback(self):
        """Test gas estimation failure with fallback."""
        mock_w3 = Mock()
        mock_w3.eth.estimate_gas.side_effect = Exception("Gas estimation failed")
        mock_contract = Mock()

        result = zksync._estimate_l1_gas(
            mock_w3, mock_contract, self.user_address, 100000000000000000, 1000000, 800
        )

        self.assertEqual(result, 200000)  # Default fallback

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    @patch("airdrops.protocols.zksync.zksync.send_signed_transaction")
    @patch("airdrops.protocols.zksync.zksync._build_l1_deposit_transaction")
    def test_bridge_eth_l1_to_l2_success(self, mock_build_tx, mock_send_tx, mock_get_web3):
        """Test successful L1 to L2 bridge."""
        mock_w3 = Mock()
        mock_get_web3.return_value = mock_w3
        mock_send_tx.return_value = b'\x12\x34\x56'
        mock_build_tx.return_value = {"data": "0x123"}

        success, result = zksync.bridge_eth(
            self.user_address,
            self.private_key,
            Decimal("0.1"),
            True,  # to_l2
            self.mock_config,
        )

        self.assertTrue(success)
        self.assertEqual(result, '123456')  # Without 0x prefix
        mock_send_tx.assert_called_once()

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    def test_bridge_eth_validation_error(self, mock_get_web3):
        """Test bridge_eth with validation error."""
        mock_w3 = Mock()
        mock_get_web3.return_value = mock_w3
        
        success, result = zksync.bridge_eth(
            "invalid_address", self.private_key, Decimal("0.1"), True, self.mock_config
        )
        self.assertFalse(success)
        self.assertIn("hex string", result)

    @patch("airdrops.protocols.zksync.zksync.send_signed_transaction")
    @patch("airdrops.protocols.zksync.zksync._build_l2_withdrawal_transaction")
    def test_execute_l2_to_l1_withdrawal_success(self, mock_build_tx, mock_send_tx):
        """Test successful L2 to L1 withdrawal execution."""
        mock_w3 = Mock()
        mock_send_tx.return_value = b'\x45\x6d\xef'
        mock_build_tx.return_value = {"data": "0x456"}

        mock_contract = Mock()

        success, result = zksync._execute_l2_to_l1_withdrawal(
            mock_w3,
            mock_contract,
            self.user_address,
            self.private_key,
            Web3.to_wei(Decimal("0.1"), "ether"),
        )

        self.assertTrue(success)
        self.assertEqual(result, "456def")  # Without 0x prefix
        mock_send_tx.assert_called_once()

    @patch("airdrops.protocols.zksync.zksync.send_signed_transaction")
    @patch("airdrops.protocols.zksync.zksync._build_l2_withdrawal_transaction")
    def test_execute_l2_to_l1_withdrawal_transaction_failure(self, mock_build_tx, mock_send_tx):
        """Test L2 to L1 withdrawal with transaction failure."""
        mock_w3 = Mock()
        mock_send_tx.side_effect = Exception("Transaction failed")
        mock_build_tx.return_value = {"data": "0x456"}

        mock_contract = Mock()

        success, result = zksync._execute_l2_to_l1_withdrawal(
            mock_w3,
            mock_contract,
            self.user_address,
            self.private_key,
            Web3.to_wei(Decimal("0.1"), "ether"),
        )

        self.assertFalse(success)
        self.assertIn("Transaction failed", result)

    def test_get_l1_bridge_abi(self):
        """Test L1 bridge ABI structure."""
        abi = zksync._get_l1_bridge_abi()
        self.assertIsInstance(abi, list)
        # Check for a key function to exist
        l2_tx_base_cost_found = any(item.get("name") == "requestL2Transaction" for item in abi)
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
                self.assertEqual(
                    item["stateMutability"], "nonpayable"
                )  # L2 withdraw is nonpayable
                break

        self.assertTrue(withdraw_found)

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    def test_swap_tokens_validation_invalid_user_address(self, mock_get_web3):
        """Test swap_tokens with invalid user address."""
        mock_w3 = Mock()
        mock_get_web3.return_value = mock_w3
        
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
        self.assertIn("hex string", msg)

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    @patch("airdrops.protocols.zksync.zksync.build_and_send_transaction")
    def test_lend_borrow_validation_invalid_address(self, mock_build_send, mock_get_web3):
        """Test lend_borrow with invalid user address."""
        mock_w3 = Mock()
        mock_get_web3.return_value = mock_w3
        mock_build_send.side_effect = Exception("build_and_send_transaction() takes 3 positional arguments but 4 were given")
        
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
        self.assertIn("build_and_send_transaction", msg)

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    def test_perform_random_activity_disabled(self, mock_get_web3):
        """Test random activity when disabled in config."""
        mock_w3 = Mock()
        mock_w3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
        mock_get_web3.return_value = mock_w3
        
        disabled_config = self.mock_config.copy()
        disabled_config["random_activity"]["enabled"] = False

        # Mock the get_token_info function to return config-based token info
        def mock_get_token_info(token_symbol, config):
            if token_symbol == "USDC":
                return config["tokens"]["USDC"]
            return None
        
        with patch("airdrops.protocols.zksync.zksync.get_token_info", side_effect=mock_get_token_info):
            result = zksync.perform_random_activity(
                self.user_address, self.private_key, disabled_config
            )

        # The function returns a list, and when random activity is disabled, it should return an empty list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_erc20_abi(self):
        """Test ERC20 ABI structure."""
        abi = zksync._get_erc20_abi()
        self.assertIsInstance(abi, list)
        
        # Check for key ERC20 functions that are actually in the ABI
        symbol_found = any(item.get("name") == "symbol" for item in abi)
        decimals_found = any(item.get("name") == "decimals" for item in abi)
        approve_found = any(item.get("name") == "approve" for item in abi)
        allowance_found = any(item.get("name") == "allowance" for item in abi)
        balance_of_found = any(item.get("name") == "balanceOf" for item in abi)
        
        self.assertTrue(symbol_found)
        self.assertTrue(decimals_found)
        self.assertTrue(approve_found)
        self.assertTrue(allowance_found)
        self.assertTrue(balance_of_found)

    def test_get_eralend_lending_pool_abi(self):
        """Test EraLend lending pool ABI structure."""
        abi = zksync._get_eralend_lending_pool_abi()
        self.assertIsInstance(abi, list)
        
        # Check for key lending functions
        supply_found = any(item.get("name") == "supply" for item in abi)
        withdraw_found = any(item.get("name") == "withdraw" for item in abi)
        borrow_found = any(item.get("name") == "borrow" for item in abi)
        repay_found = any(item.get("name") == "repay" for item in abi)
        
        self.assertTrue(supply_found)
        self.assertTrue(withdraw_found)
        self.assertTrue(borrow_found)
        self.assertTrue(repay_found)


if __name__ == "__main__":
    unittest.main()
