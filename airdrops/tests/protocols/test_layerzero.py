# airdrops/tests/protocols/test_layerzero.py
"""
Unit tests for the LayerZero/Stargate protocol module.
"""
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
import copy  # For deepcopy
from typing import Dict, Any  # For type hints

from web3 import Web3  # Direct import for utility functions

# Import the module to be tested
from airdrops.protocols.layerzero import layerzero


class TestLayerZeroModule(unittest.TestCase):
    """
    Tests for the LayerZero/Stargate module functions.
    """

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.user_address = "0x1234567890123456789012345678901234567890"
        self.private_key = "0x" + "a" * 64  # Mock private key
        self.mock_config = {
            "layerzero": {
                "chains": {
                    1: {
                        "name": "ethereum",
                        "rpc_url": "https://eth.llamarpc.com",
                        "layerzero_chain_id": 101,
                        "stargate_router_address": (
                            "0x8731d54E9D02c286767d56ac03e8037C07e01e98"
                        ),
                        "explorer_url": "https://etherscan.io/tx/",
                    },
                    42161: {
                        "name": "arbitrum",
                        "rpc_url": "https://arb1.arbitrum.io/rpc",
                        "layerzero_chain_id": 110,
                        "stargate_router_address": (
                            "0x53Bf833A5d6c4ddA888F69c22C88C9f356a41614"
                        ),
                        "explorer_url": "https://arbiscan.io/tx/",
                    },
                },
                "tokens": {
                    "USDC": {
                        1: {
                            "address": ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"),
                            "decimals": 6,
                            "stargate_pool_id": 1,
                        },
                        42161: {
                            "address": ("0xaf88d065e77c8cC2239327C5EDb3A432268e5831"),
                            "decimals": 6,
                            "stargate_pool_id": 1,
                        },
                    },
                    "ETH": {
                        1: {
                            "address": "NATIVE",
                            "decimals": 18,
                            "stargate_pool_id": 13,
                        },
                        42161: {
                            "address": "NATIVE",
                            "decimals": 18,
                            "stargate_pool_id": 13,
                        },
                    },
                },
                "gas_settings": {
                    "gas_limit": 500000,
                    "gas_price_gwei": 20,
                    "transaction_timeout_seconds": 300,
                },
                "perform_random_bridge_settings": {
                    "enabled_chains": ["ethereum", "arbitrum"],
                    "enabled_tokens": ["USDC", "ETH"],
                    "chain_weights": {"ethereum": 50, "arbitrum": 50},
                    "token_weights": {"USDC": 70, "ETH": 30},
                    "amount_usd_min": 10.0,
                    "amount_usd_max": 100.0,
                    "slippage_bps_min": 10,  # 0.1%
                    "slippage_bps_max": 50,  # 0.5%
                    "min_source_balance_usd_threshold": 5.0,
                },
            }
        }
        # Deepcopy for tests that modify settings
        self.random_bridge_config: Dict[str, Any] = copy.deepcopy(
            {
                "layerzero": {
                    "chains": {
                        1: {
                            "name": "ethereum",
                            "rpc_url": "https://eth.llamarpc.com",
                            "layerzero_chain_id": 101,
                            "stargate_router_address": (
                                "0x8731d54E9D02c286767d56ac03e8037C07e01e98"
                            ),
                            "explorer_url": "https://etherscan.io/tx/",
                        },
                        42161: {
                            "name": "arbitrum",
                            "rpc_url": "https://arb1.arbitrum.io/rpc",
                            "layerzero_chain_id": 110,
                            "stargate_router_address": (
                                "0x53Bf833A5d6c4ddA888F69c22C88C9f356a41614"
                            ),
                            "explorer_url": "https://arbiscan.io/tx/",
                        },
                        10: {  # Add Optimism for more diverse testing
                            "name": "optimism",
                            "rpc_url": "https://mainnet.optimism.io",
                            "layerzero_chain_id": 111,
                            "stargate_router_address": (
                                "0xB0D502E938ed5f4df2E681fE6E419ff29631d62b"
                            ),
                            "explorer_url": "https://optimistic.etherscan.io/tx/",
                        },
                    },
                    "tokens": {
                        "USDC": {
                            1: {
                                "address": (
                                    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
                                ),
                                "decimals": 6,
                                "stargate_pool_id": 1,
                            },
                            42161: {
                                "address": (
                                    "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
                                ),
                                "decimals": 6,
                                "stargate_pool_id": 1,
                            },
                            10: {
                                "address": (
                                    "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85"
                                ),
                                "decimals": 6,
                                "stargate_pool_id": 1,
                            },
                        },
                        "ETH": {
                            1: {
                                "address": "NATIVE",
                                "decimals": 18,
                                "stargate_pool_id": 13,
                            },
                            42161: {
                                "address": "NATIVE",
                                "decimals": 18,
                                "stargate_pool_id": 13,
                            },
                            10: {
                                "address": "NATIVE",
                                "decimals": 18,
                                "stargate_pool_id": 13,
                            },
                        },
                    },
                    "gas_settings": {
                        "gas_limit": 500000,
                        "gas_price_gwei": 20,
                        "transaction_timeout_seconds": 300,
                    },
                    "perform_random_bridge_settings": {
                        "enabled_chains": ["ethereum", "arbitrum", "optimism"],
                        "enabled_tokens": ["USDC", "ETH"],
                        "chain_weights": {
                            "ethereum": 30,
                            "arbitrum": 40,
                            "optimism": 30,
                        },
                        "token_weights": {"USDC": 60, "ETH": 40},
                        "amount_usd_min": 10.0,
                        "amount_usd_max": 100.0,
                        "slippage_bps_min": 10,
                        "slippage_bps_max": 50,
                        "min_source_balance_usd_threshold": 5.0,
                    },
                }
            }
        )

    @patch("airdrops.protocols.layerzero.layerzero._get_web3_provider")
    @patch("airdrops.protocols.layerzero.layerzero._get_contract")
    @patch("airdrops.protocols.layerzero.layerzero._check_or_approve_token")
    @patch("airdrops.protocols.layerzero.layerzero._estimate_lz_fee")
    def test_bridge_successful_usdc(
        self,
        mock_estimate_fee: MagicMock,
        mock_approve: MagicMock,
        mock_get_contract: MagicMock,
        mock_get_web3: MagicMock,
    ) -> None:
        """Test successful USDC bridge from Ethereum to Arbitrum."""
        # Setup mocks
        mock_w3 = MagicMock()
        mock_get_web3.return_value = mock_w3
        mock_w3.eth.get_transaction_count.return_value = 42
        mock_w3.to_wei.return_value = 20000000000
        mock_w3.eth.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b"signed_tx"
        )
        mock_w3.eth.send_raw_transaction.return_value = MagicMock(
            hex=lambda: "0x" + "a" * 40
        )  # Valid hex

        mock_w3.eth.wait_for_transaction_receipt.return_value = {
            "status": 1,
            "transactionHash": Web3.to_bytes(hexstr="0x" + "a" * 40),
        }

        mock_router = MagicMock()
        mock_get_contract.return_value = mock_router
        build_transaction_return = (
            mock_router.functions.swap.return_value.build_transaction
        )
        build_transaction_return.return_value = {
            "from": self.user_address,
            "value": 1000000000000000,
            "nonce": 42,
            "gas": 500000,
            "gasPrice": 20000000000,
        }

        mock_approve.return_value = True
        mock_estimate_fee.return_value = 1000000000000000  # 0.001 ETH

        # Execute bridge
        success, result = layerzero.bridge(
            source_chain_id=1,
            destination_chain_id=42161,
            source_token_symbol="USDC",
            amount_in_source_token_units=Decimal("100"),
            user_address=self.user_address,
            slippage_bps=50,
            config=self.mock_config,
            private_key=self.private_key,
        )

        # Assertions
        self.assertTrue(success)
        self.assertEqual(result, "0x" + "a" * 40)
        mock_approve.assert_called_once()
        mock_estimate_fee.assert_called_once()
        mock_w3.eth.send_raw_transaction.assert_called_once()

    @patch("airdrops.protocols.layerzero.layerzero._get_web3_provider")
    @patch("airdrops.protocols.layerzero.layerzero._get_contract")
    @patch("airdrops.protocols.layerzero.layerzero._estimate_lz_fee")
    def test_bridge_successful_native_eth(
        self,
        mock_estimate_fee: MagicMock,
        mock_get_contract: MagicMock,
        mock_get_web3: MagicMock,
    ) -> None:
        """Test successful native ETH bridge (no approval needed)."""
        # Setup mocks
        mock_w3 = MagicMock()
        mock_get_web3.return_value = mock_w3
        mock_w3.eth.get_transaction_count.return_value = 42
        mock_w3.to_wei.return_value = 20000000000
        mock_w3.eth.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b"signed_tx"
        )
        mock_w3.eth.send_raw_transaction.return_value = MagicMock(
            hex=lambda: "0x" + "b" * 40
        )  # Valid hex

        mock_w3.eth.wait_for_transaction_receipt.return_value = {
            "status": 1,
            "transactionHash": layerzero.Web3.to_bytes(hexstr="0x" + "b" * 40),
        }
        mock_router = MagicMock()
        mock_get_contract.return_value = mock_router
        build_transaction_return = (
            mock_router.functions.swap.return_value.build_transaction
        )

        build_transaction_return.return_value = {
            "from": self.user_address,
            "value": 1000000000000000,
            "nonce": 42,
            "gas": 500000,
            "gasPrice": 20000000000,
        }

        mock_estimate_fee.return_value = 1000000000000000  # 0.001 ETH

        # Execute bridge
        success, result = layerzero.bridge(
            source_chain_id=1,
            destination_chain_id=42161,
            source_token_symbol="ETH",
            amount_in_source_token_units=Decimal("0.1"),
            user_address=self.user_address,
            slippage_bps=50,
            config=self.mock_config,
            private_key=self.private_key,
        )

        # Assertions
        self.assertTrue(success)
        self.assertEqual(result, "0x" + "b" * 40)
        mock_estimate_fee.assert_called_once()
        mock_w3.eth.send_raw_transaction.assert_called_once()

    def test_bridge_invalid_source_chain(self) -> None:
        """Test bridge with invalid source chain ID."""
        success, result = layerzero.bridge(
            source_chain_id=999,  # Invalid chain
            destination_chain_id=42161,
            source_token_symbol="USDC",
            amount_in_source_token_units=Decimal("100"),
            user_address=self.user_address,
            slippage_bps=50,
            config=self.mock_config,
            private_key=self.private_key,
        )

        self.assertFalse(success)
        self.assertIn("Source chain 999 not configured", result)

    def test_bridge_invalid_destination_chain(self) -> None:
        """Test bridge with invalid destination chain ID."""
        success, result = layerzero.bridge(
            source_chain_id=1,
            destination_chain_id=999,  # Invalid chain
            source_token_symbol="USDC",
            amount_in_source_token_units=Decimal("100"),
            user_address=self.user_address,
            slippage_bps=50,
            config=self.mock_config,
            private_key=self.private_key,
        )

        self.assertFalse(success)
        self.assertIn("Destination chain 999 not configured", result)

    def test_bridge_invalid_token(self) -> None:
        """Test bridge with invalid token symbol."""
        success, result = layerzero.bridge(
            source_chain_id=1,
            destination_chain_id=42161,
            source_token_symbol="INVALID_TOKEN",
            amount_in_source_token_units=Decimal("100"),
            user_address=self.user_address,
            slippage_bps=50,
            config=self.mock_config,
            private_key=self.private_key,
        )

        self.assertFalse(success)
        self.assertIn("Token INVALID_TOKEN not configured", result)

    @patch("airdrops.protocols.layerzero.layerzero._get_web3_provider")
    @patch("airdrops.protocols.layerzero.layerzero._check_or_approve_token")
    def test_bridge_approval_failure(
        self, mock_approve: MagicMock, mock_get_web3: MagicMock
    ) -> None:
        """Test bridge failure due to token approval failure."""
        mock_w3 = MagicMock()
        mock_get_web3.return_value = mock_w3
        mock_approve.return_value = False  # Approval fails

        success, result = layerzero.bridge(
            source_chain_id=1,
            destination_chain_id=42161,
            source_token_symbol="USDC",
            amount_in_source_token_units=Decimal("100"),
            user_address=self.user_address,
            slippage_bps=50,
            config=self.mock_config,
            private_key=self.private_key,
        )

        self.assertFalse(success)
        self.assertEqual(result, "Token approval failed")

    @patch("airdrops.protocols.layerzero.layerzero._get_web3_provider")
    @patch("airdrops.protocols.layerzero.layerzero._get_contract")
    @patch("airdrops.protocols.layerzero.layerzero._check_or_approve_token")
    @patch("airdrops.protocols.layerzero.layerzero._estimate_lz_fee")
    def test_bridge_transaction_failure(
        self,
        mock_estimate_fee: MagicMock,
        mock_approve: MagicMock,
        mock_get_contract: MagicMock,
        mock_get_web3: MagicMock,
    ) -> None:
        """Test bridge failure due to transaction failure."""
        # Setup mocks
        mock_w3 = MagicMock()
        mock_get_web3.return_value = mock_w3
        mock_w3.eth.get_transaction_count.return_value = 42
        mock_w3.to_wei.return_value = 20000000000
        mock_w3.eth.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b"signed_tx"
        )
        mock_w3.eth.send_raw_transaction.return_value = MagicMock(
            hex=lambda: "0x" + "c" * 40
        )  # Valid hex

        # Transaction fails
        mock_w3.eth.wait_for_transaction_receipt.return_value = {
            "status": 0,
            "transactionHash": Web3.to_bytes(hexstr="0x" + "c" * 40),
        }
        mock_router = MagicMock()
        mock_get_contract.return_value = mock_router
        build_transaction_return = (
            mock_router.functions.swap.return_value.build_transaction
        )

        build_transaction_return.return_value = {
            "from": self.user_address,
            "value": 1000000000000000,
            "nonce": 42,
            "gas": 500000,
            "gasPrice": 20000000000,
        }

        mock_approve.return_value = True
        mock_estimate_fee.return_value = 1000000000000000

        # Execute bridge
        success, result = layerzero.bridge(
            source_chain_id=1,
            destination_chain_id=42161,
            source_token_symbol="USDC",
            amount_in_source_token_units=Decimal("100"),
            user_address=self.user_address,
            slippage_bps=50,
            config=self.mock_config,
            private_key=self.private_key,
        )

        # Assertions
        self.assertFalse(success)
        self.assertEqual(result, "Transaction failed on source chain")

    @patch("airdrops.protocols.layerzero.layerzero._get_web3_provider")
    def test_bridge_web3_connection_failure(self, mock_get_web3: MagicMock) -> None:
        """Test bridge failure due to Web3 connection failure."""
        mock_get_web3.side_effect = ValueError("Failed to connect to RPC")

        success, result = layerzero.bridge(
            source_chain_id=1,
            destination_chain_id=42161,
            source_token_symbol="USDC",
            amount_in_source_token_units=Decimal("100"),
            user_address=self.user_address,
            slippage_bps=50,
            config=self.mock_config,
            private_key=self.private_key,
        )

        self.assertFalse(success)
        self.assertIn("Failed to connect to RPC", result)

    # --- Tests for perform_random_bridge ---

    @patch("airdrops.protocols.layerzero.layerzero.bridge")
    @patch("random.choices")
    @patch("random.uniform")
    @patch("random.randint")
    def test_perform_random_bridge_successful_selection_and_call(
        self,
        mock_randint: MagicMock,
        mock_uniform: MagicMock,
        mock_choices: MagicMock,
        mock_bridge_func: MagicMock,
    ) -> None:
        """Test successful random parameter selection and call to bridge."""
        # Mock random selections
        # random.choices for chains: first call for source, second for dest
        mock_choices.side_effect = [
            ["ethereum"],  # Source chain name
            ["arbitrum"],  # Destination chain name
            ["USDC"],  # Token symbol
        ]
        mock_uniform.return_value = 50.0  # USD amount
        mock_randint.return_value = 25  # Slippage bps

        # Mock the underlying bridge function
        mock_bridge_func.return_value = (True, "0x" + "d" * 40)  # Valid hex

        success, message = layerzero.perform_random_bridge(
            user_address=self.user_address,
            config=self.random_bridge_config,
            private_key=self.private_key,
        )

        self.assertTrue(success)
        self.assertIn("Successfully initiated random bridge", message)
        self.assertIn("0x" + "d" * 40, message)
        # Based on 6 decimals for USDC
        self.assertIn("50.000000 USDC from ethereum to arbitrum", message)

        mock_bridge_func.assert_called_once()
        called_args, called_kwargs = mock_bridge_func.call_args

        self.assertEqual(called_kwargs["source_chain_id"], 1)  # ethereum
        self.assertEqual(called_kwargs["destination_chain_id"], 42161)  # arb
        self.assertEqual(called_kwargs["source_token_symbol"], "USDC")
        # Amount is Decimal('50.0'), token decimals for USDC is 6
        expected_amount = Decimal("50.000000")
        self.assertEqual(called_kwargs["amount_in_source_token_units"], expected_amount)
        self.assertEqual(called_kwargs["slippage_bps"], 25)
        self.assertEqual(called_kwargs["user_address"], self.user_address)

    @patch("airdrops.protocols.layerzero.layerzero.bridge")
    @patch("random.choices")
    @patch("random.uniform")
    @patch("random.randint")
    def test_perform_random_bridge_token_not_on_dest_chain_retry_selection(
        self,
        mock_randint: MagicMock,
        mock_uniform: MagicMock,
        mock_choices: MagicMock,
        mock_bridge_func: MagicMock,
    ) -> None:
        """Test token selection retry if first choice is not on dest."""
        # Mock random.choices:
        # 1st call (source chain): ethereum
        # 2nd call (dest chain): arbitrum
        # 3rd call (token): ETH (assume ETH is NOT on Arbitrum in temp config)
        # 4th call (token retry): USDC (assume USDC IS on Arbitrum)
        mock_choices.side_effect = [
            ["ethereum"],
            ["arbitrum"],
            ["ETH"],  # First token choice
            ["USDC"],  # Second token choice (after retry)
        ]
        mock_uniform.return_value = 20.0
        mock_randint.return_value = 15

        mock_bridge_func.return_value = (True, "0x" + "e" * 40)  # Valid hex

        # Modify config temporarily so ETH is not on Arbitrum
        temp_config = copy.deepcopy(self.random_bridge_config)
        # Ensure ETH is not configured for Arbitrum (chain_id 42161)
        if (
            "ETH" in temp_config["layerzero"]["tokens"]
            and 42161 in temp_config["layerzero"]["tokens"]["ETH"]
        ):
            temp_config["layerzero"]["tokens"]["ETH"].pop(42161, None)

        success, message = layerzero.perform_random_bridge(
            user_address=self.user_address,
            config=temp_config,
            private_key=self.private_key,
        )

        self.assertTrue(success)
        self.assertIn("Successfully initiated random bridge", message)
        self.assertIn("USDC", message)  # Should have selected USDC
        # Ensure ETH wasn't the final token
        self.assertNotIn("ETH", message.split("Token:")[0])

        mock_bridge_func.assert_called_once()
        _, called_kwargs = mock_bridge_func.call_args
        self.assertEqual(called_kwargs["source_token_symbol"], "USDC")

    def test_perform_random_bridge_missing_settings(self) -> None:
        """Test handling of missing perform_random_bridge_settings."""
        config_no_settings: Dict[str, Any] = {"layerzero": {}}
        success, message = layerzero.perform_random_bridge(
            self.user_address, config_no_settings, self.private_key
        )
        self.assertFalse(success)
        self.assertEqual(message, "perform_random_bridge_settings not found in config")

    def test_perform_random_bridge_missing_specific_setting(self) -> None:
        """Test handling of a missing specific required setting."""
        config_missing_key = copy.deepcopy(self.random_bridge_config)
        config_missing_key["layerzero"]["perform_random_bridge_settings"].pop(
            "amount_usd_min", None
        )
        success, message = layerzero.perform_random_bridge(
            self.user_address, config_missing_key, self.private_key
        )
        self.assertFalse(success)
        self.assertEqual(
            message, "Missing 'amount_usd_min' in perform_random_bridge_settings"
        )

    def test_perform_random_bridge_not_enough_chains(self) -> None:
        """Test handling when less than 2 enabled_chains are configured."""
        config_one_chain = copy.deepcopy(self.random_bridge_config)
        config_one_chain["layerzero"]["perform_random_bridge_settings"][
            "enabled_chains"
        ] = ["ethereum"]
        success, message = layerzero.perform_random_bridge(
            self.user_address, config_one_chain, self.private_key
        )
        self.assertFalse(success)
        self.assertEqual(
            message, "At least two enabled_chains are required for bridging."
        )

    @patch("random.choices")
    def test_perform_random_bridge_cannot_select_different_destination(
        self, mock_choices: MagicMock
    ) -> None:
        """Test when no different destination chain can be selected."""
        # Mock random.choices to select "ethereum" as the source chain
        mock_choices.side_effect = [["ethereum"]]

        config_only_one_unique_chain = copy.deepcopy(self.random_bridge_config)
        # Set enabled_chains to only contain "ethereum" (repeated)
        config_only_one_unique_chain["layerzero"]["perform_random_bridge_settings"][
            "enabled_chains"
        ] = ["ethereum", "ethereum"]
        # Ensure "ethereum" is chosen by setting its weight high
        config_only_one_unique_chain["layerzero"]["perform_random_bridge_settings"][
            "chain_weights"
        ] = {"ethereum": 100}

        success, message = layerzero.perform_random_bridge(
            user_address=self.user_address,
            config=config_only_one_unique_chain,
            private_key=self.private_key,
        )

        self.assertFalse(success)
        # This specific message is returned when possible_dest_chains is empty
        self.assertEqual(
            message, "Could not select a destination chain different from the source."
        )

    @patch("random.choices")
    def test_perform_random_bridge_no_compatible_token(
        self, mock_choices: MagicMock
    ) -> None:
        """Test when no token is compatible with the selected chain pair."""
        # Source: ethereum, Dest: arbitrum
        # Tokens to try: USDC, then ETH (both made incompatible)
        mock_choices.side_effect = [
            ["ethereum"],  # Source chain selection
            ["arbitrum"],  # Destination chain selection
            ["USDC"],  # First token choice
            ["ETH"],  # Second token choice (after retry)
            ["USDC"],  # Third token choice (if loop continues)
            ["ETH"],  # Fourth token choice (if loop continues)
        ]
        config_no_compat_token = copy.deepcopy(self.random_bridge_config)
        # Remove all tokens from arbitrum config to ensure no compatibility
        config_no_compat_token["layerzero"]["tokens"]["USDC"].pop(42161, None)
        config_no_compat_token["layerzero"]["tokens"]["ETH"].pop(42161, None)

        success, message = layerzero.perform_random_bridge(
            self.user_address, config_no_compat_token, self.private_key
        )
        self.assertFalse(success)
        self.assertEqual(
            message,
            "Could not find a token compatible with selected source and "
            "destination chains.",
        )

    def test_perform_random_bridge_invalid_amount_range(self) -> None:
        """Test invalid amount_usd_min/max settings."""
        config_invalid_amount = copy.deepcopy(self.random_bridge_config)
        config_invalid_amount["layerzero"]["perform_random_bridge_settings"][
            "amount_usd_min"
        ] = 100.0
        config_invalid_amount["layerzero"]["perform_random_bridge_settings"][
            "amount_usd_max"
        ] = 10.0
        success, message = layerzero.perform_random_bridge(
            self.user_address, config_invalid_amount, self.private_key
        )
        self.assertFalse(success)
        self.assertEqual(message, "Invalid amount_usd_min/max settings.")

    def test_perform_random_bridge_invalid_slippage_range(self) -> None:
        """Test invalid slippage_bps_min/max settings."""
        config_invalid_slippage = copy.deepcopy(self.random_bridge_config)
        config_invalid_slippage["layerzero"]["perform_random_bridge_settings"][
            "slippage_bps_min"
        ] = 100
        config_invalid_slippage["layerzero"]["perform_random_bridge_settings"][
            "slippage_bps_max"
        ] = 10
        success, message = layerzero.perform_random_bridge(
            self.user_address, config_invalid_slippage, self.private_key
        )
        self.assertFalse(success)
        self.assertEqual(message, "Invalid slippage_bps_min/max settings.")

    @patch("airdrops.protocols.layerzero.layerzero.bridge")
    @patch("random.choices")
    @patch("random.uniform")
    @patch("random.randint")
    def test_perform_random_bridge_underlying_bridge_fails(
        self,
        mock_randint: MagicMock,
        mock_uniform: MagicMock,
        mock_choices: MagicMock,
        mock_bridge_func: MagicMock,
    ) -> None:
        """Test when the underlying bridge() call fails."""
        mock_choices.side_effect = [["ethereum"], ["arbitrum"], ["USDC"]]
        mock_uniform.return_value = 30.0
        mock_randint.return_value = 20
        mock_bridge_func.return_value = (False, "RPC Error during bridge")

        success, message = layerzero.perform_random_bridge(
            self.user_address, self.random_bridge_config, self.private_key
        )
        self.assertFalse(success)
        self.assertIn("Random bridge failed: RPC Error during bridge", message)

    def test_perform_random_bridge_empty_enabled_chains(self) -> None:
        """Test perform_random_bridge with empty enabled_chains."""
        config_empty_chains = copy.deepcopy(self.random_bridge_config)
        config_empty_chains["layerzero"]["perform_random_bridge_settings"][
            "enabled_chains"
        ] = []
        success, message = layerzero.perform_random_bridge(
            self.user_address, config_empty_chains, self.private_key
        )
        self.assertFalse(success)
        self.assertEqual(message, "enabled_chains or enabled_tokens cannot be empty.")

    def test_perform_random_bridge_empty_enabled_tokens(self) -> None:
        """Test perform_random_bridge with empty enabled_tokens."""
        config_empty_tokens = copy.deepcopy(self.random_bridge_config)
        config_empty_tokens["layerzero"]["perform_random_bridge_settings"][
            "enabled_tokens"
        ] = []
        success, message = layerzero.perform_random_bridge(
            self.user_address, config_empty_tokens, self.private_key
        )
        self.assertFalse(success)
        self.assertEqual(message, "enabled_chains or enabled_tokens cannot be empty.")

    @patch("airdrops.protocols.layerzero.layerzero.Web3")
    def test_get_web3_provider_success(self, mock_web3_class: MagicMock) -> None:
        """Test successful Web3 provider creation."""
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_web3_class.return_value = mock_w3
        mock_web3_class.HTTPProvider = MagicMock()

        result = layerzero._get_web3_provider("https://test.rpc")

        self.assertEqual(result, mock_w3)
        mock_web3_class.HTTPProvider.assert_called_once_with("https://test.rpc")

    @patch("airdrops.protocols.layerzero.layerzero.Web3")
    def test_get_web3_provider_connection_failure(
        self, mock_web3_class: MagicMock
    ) -> None:
        """Test Web3 provider creation failure."""
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = False
        mock_web3_class.return_value = mock_w3
        mock_web3_class.HTTPProvider = MagicMock()

        with self.assertRaises(ValueError) as context:
            layerzero._get_web3_provider("https://test.rpc")

        self.assertIn("Failed to connect to RPC", str(context.exception))

    @patch("airdrops.protocols.layerzero.layerzero._get_contract")
    def test_check_or_approve_token_sufficient_allowance(
        self, mock_get_contract: MagicMock
    ) -> None:
        """Test token approval when allowance is sufficient."""
        mock_w3 = MagicMock()
        mock_token = MagicMock()
        allowance_return = mock_token.functions.allowance.return_value.call

        allowance_return.return_value = 1000000  # Sufficient
        mock_get_contract.return_value = mock_token

        token_addr_cs = Web3.to_checksum_address(
            self.mock_config["layerzero"]["tokens"]["USDC"][1]["address"]
        )
        spender_addr_cs = Web3.to_checksum_address(
            self.mock_config["layerzero"]["chains"][1]["stargate_router_address"]
        )

        result = layerzero._check_or_approve_token(
            mock_w3,
            token_addr_cs,
            Web3.to_checksum_address(self.user_address),
            spender_addr_cs,
            500000,
            self.private_key,
            {
                "gas_limit": 100000,
                "gas_price_gwei": 20,
                "transaction_timeout_seconds": 300,
            },
        )

        self.assertTrue(result)
        mock_token.functions.approve.assert_not_called()

    @patch("airdrops.protocols.layerzero.layerzero._get_contract")
    def test_check_or_approve_token_approval_needed(
        self, mock_get_contract: MagicMock
    ) -> None:
        """Test token approval when approval is needed and successful."""
        mock_w3 = MagicMock()
        mock_w3.eth.get_transaction_count.return_value = 42
        mock_w3.to_wei.return_value = 20000000000
        mock_w3.eth.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b"signed_tx"
        )
        mock_w3.eth.send_raw_transaction.return_value = MagicMock(
            hex=lambda: "0x" + "f" * 40
        )  # Valid hex for approval tx

        mock_w3.eth.wait_for_transaction_receipt.return_value = {
            "status": 1,
            "transactionHash": Web3.to_bytes(hexstr="0x" + "f" * 40),
        }
        mock_token = MagicMock()
        allowance_return = mock_token.functions.allowance.return_value.call

        allowance_return.return_value = 0  # No allowance
        approve_build_transaction = (
            mock_token.functions.approve.return_value.build_transaction
        )

        approve_build_transaction.return_value = {
            "from": self.user_address,
            "nonce": 42,
            "gas": 100000,
            "gasPrice": 20000000000,
        }
        mock_get_contract.return_value = mock_token

        token_addr_cs = Web3.to_checksum_address(
            self.mock_config["layerzero"]["tokens"]["USDC"][1]["address"]
        )
        spender_addr_cs = Web3.to_checksum_address(
            self.mock_config["layerzero"]["chains"][1]["stargate_router_address"]
        )

        result = layerzero._check_or_approve_token(
            mock_w3,
            token_addr_cs,
            Web3.to_checksum_address(self.user_address),
            spender_addr_cs,
            1000000,
            self.private_key,
            {
                "gas_limit": 100000,
                "gas_price_gwei": 20,
                "transaction_timeout_seconds": 300,
            },
        )

        self.assertTrue(result)
        mock_token.functions.approve.assert_called_once()
        mock_w3.eth.send_raw_transaction.assert_called_once()

    def test_estimate_lz_fee_success(self) -> None:
        """Test successful LayerZero fee estimation."""
        mock_router = MagicMock()
        quote_layer_zero_fee = mock_router.functions.quoteLayerZeroFee
        quote_fee_return = quote_layer_zero_fee.return_value.call

        quote_fee_return.return_value = (1000000000000000, 0)

        result = layerzero._estimate_lz_fee(mock_router, 110, self.user_address)

        self.assertEqual(result, 1000000000000000)
        mock_router.functions.quoteLayerZeroFee.assert_called_once()

    def test_estimate_lz_fee_failure(self) -> None:
        """Test LayerZero fee estimation failure."""
        mock_router = MagicMock()
        quote_layer_zero_fee = mock_router.functions.quoteLayerZeroFee
        quote_fee_call = quote_layer_zero_fee.return_value.call

        quote_fee_call.side_effect = Exception("RPC error")

        with self.assertRaises(ValueError) as context:
            layerzero._estimate_lz_fee(mock_router, 110, self.user_address)

        exception_message = str(context.exception)
        self.assertIn("Failed to estimate LayerZero fee", exception_message)


if __name__ == "__main__":
    unittest.main()
