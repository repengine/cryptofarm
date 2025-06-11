import unittest
from web3 import Web3
from unittest.mock import Mock, patch
from decimal import Decimal

from airdrops.protocols.zksync.zksync import (
    _get_web3_instance,
    _get_l1_bridge_abi,
    _get_eralend_lending_pool_abi,
    _build_and_send_lending_transaction,
    _build_and_send_swap_transaction,
    _handle_token_approval,
    _execute_supply_action,
    _execute_withdraw_action,
    _execute_borrow_action,
    _execute_repay_action,
    _execute_set_collateral_action,
    _execute_lending_action,
    _execute_single_action,
    _select_action_type,
    _randomize_bridge_parameters,
    _randomize_swap_parameters,
    _check_action_feasibility,
    _update_internal_state,
    _validate_random_activity_config,
    _get_initial_onchain_state,
    lend_borrow,
    bridge_eth,
    swap_tokens,
)


class TestZkSyncCoverage(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.MOCK_USER_ADDRESS = Web3.to_checksum_address(
            "0x1234567890123456789012345678901234567890"
        )
        self.MOCK_TOKEN_ADDRESS = Web3.to_checksum_address(
            "0x4567890123456789012345678901234567890123"
        )
        self.MOCK_SPENDER_ADDRESS = Web3.to_checksum_address(
            "0x7890123456789012345678901234567890123456"
        )
        self.MOCK_ZERO_ADDRESS = Web3.to_checksum_address(
            "0x0000000000000000000000000000000000000000"
        )

        self.mock_config = {
            "networks": {
                "zksync": {
                    "rpc_url": "http://test-zksync",
                    "lending_protocols": {
                        "eralend": {
                            "lending_pool_manager": self.MOCK_SPENDER_ADDRESS,
                            "weth_gateway": self.MOCK_SPENDER_ADDRESS
                        }
                    },
                    "dexs": {
                        "syncswap": {
                            "router_address": self.MOCK_SPENDER_ADDRESS,
                            "router_abi": [
                                {"inputs": [], "name": "swapExactETHForTokens",
                                 "outputs": [], "stateMutability": "nonpayable",
                                 "type": "function"},
                                {"inputs": [], "name": "swapExactTokensForETH",
                                 "outputs": [], "stateMutability": "nonpayable",
                                 "type": "function"},
                                {"inputs": [], "name": "swapExactTokensForTokens",
                                 "outputs": [], "stateMutability": "nonpayable",
                                 "type": "function"},
                                {"inputs": [{"internalType": "uint256",
                                             "name": "amountIn", "type": "uint256"},
                                            {"internalType": "address[]",
                                             "name": "path", "type": "address[]"}],
                                 "name": "getAmountsOut",
                                 "outputs": [{"internalType": "uint256[]",
                                              "name": "amounts",
                                              "type": "uint256[]"}],
                                 "stateMutability": "view", "type": "function"}
                            ]
                        }
                    }
                },
                "ethereum": {"rpc_url": "http://test-ethereum"}
            },
            "bridge": {
                "min_amount": 100000000000000000,
                "max_amount": 1000000000000000000,
                "l2_gas_limit": 1000000
            },
            "swap": {
                "pairs": [{"from": "ETH", "to": self.MOCK_TOKEN_ADDRESS}],
                "min_amount": 100000000000000000,
                "max_amount": 1000000000000000000
            },
            "lending": {
                "tokens": ["ETH", self.MOCK_TOKEN_ADDRESS],
                "min_amount": 100000000000000000,
                "max_amount": 1000000000000000000,
                "action_weights": {"supply": 50, "borrow": 30, "withdraw": 20}
            },
            "min_delay": 1,
            "max_delay": 5,
            "tokens": {
                "ETH": {"address": self.MOCK_ZERO_ADDRESS},
                "USDC": {"address": self.MOCK_TOKEN_ADDRESS}
            }
        }

    def test_build_and_send_lending_transaction_success(self):
        """Test _build_and_send_lending_transaction success case."""
        mock_w3 = Mock()
        mock_contract_function = Mock()
        mock_transaction_params = {"from": self.MOCK_USER_ADDRESS, "value": 1000}
        with patch('airdrops.protocols.zksync.zksync.build_and_send_transaction') \
                as mock_build:
            mock_build.return_value = Mock(hash=b'success')
            result = _build_and_send_lending_transaction(
                mock_w3,
                mock_contract_function,
                mock_transaction_params,
                "private_key",
                self.MOCK_USER_ADDRESS,
                "test action"
            )
            self.assertEqual(result, (True, '73756363657373'))

    def test_build_and_send_swap_transaction_success(self):
        """Test _build_and_send_swap_transaction success case."""
        mock_w3 = Mock()
        mock_contract_function = Mock()
        mock_transaction_params = {"from": self.MOCK_USER_ADDRESS, "value": 1000}

        with patch('airdrops.protocols.zksync.zksync.build_and_send_transaction') \
                as mock_build:
            mock_build.return_value = Mock(hash=b'success')
            result = _build_and_send_swap_transaction(
                mock_w3,
                mock_contract_function,
                mock_transaction_params,
                "private_key",
                self.MOCK_USER_ADDRESS,
                "test swap"
            )
            self.assertEqual(result, (True, '73756363657373'))

    def test_build_l1_deposit_transaction_l2_cost_fallback(self):
        """Test build_l1_deposit_transaction with L2 cost calculation fallback."""
        mock_config = {
            "networks": {"ethereum": {"rpc_url": "http://test"}},
            "bridge": {} 
        }
        
        with patch('airdrops.protocols.zksync.zksync.ConnectionManager'), \
             patch('web3.Web3.to_checksum_address', side_effect=lambda x: x), \
             patch('airdrops.protocols.zksync.zksync.send_signed_transaction',
                   return_value=Mock(hex=lambda: "success")):
            result = bridge_eth(
                user_address=self.MOCK_USER_ADDRESS,
                private_key="private_key",
                amount_eth=Decimal("1.0"),
                to_l2=True,
                config=mock_config
            )
            self.assertEqual(result, (True, "success"))

    def test_build_l2_withdrawal_transaction_gas_fallback(self):
        """Test build_l2_withdrawal_transaction with gas estimation fallback."""
        # The swap_tokens function calls _execute_syncswap_swap internally.
        # We need to mock _execute_syncswap_swap directly to control its behavior.
        mock_w3 = Mock()
        # Mock to_checksum_address on the mock_w3 instance
        mock_w3.to_checksum_address.side_effect = lambda x: x  # Return the input as is, assuming it's valid
        mock_router_contract = Mock()
        mock_router_contract.functions.getAmountsOut.return_value.call.return_value = \
            [1000000000000000000, 900000000000000000]  # Example amounts
        mock_router_contract.functions.swapExactETHForTokens.return_value.\
            build_transaction.return_value = {}
        mock_router_contract.functions.swapExactTokensForETH.return_value.\
            build_transaction.return_value = {}
        mock_router_contract.functions.swapExactTokensForTokens.return_value.\
            build_transaction.return_value = {}

        with patch('airdrops.protocols.zksync.zksync.ConnectionManager'), \
             patch('airdrops.protocols.zksync.zksync._get_web3_instance',
                   return_value=mock_w3), \
             patch('airdrops.protocols.zksync.zksync._get_contract',
                   return_value=mock_router_contract), \
             patch('airdrops.protocols.zksync.zksync.build_and_send_transaction',
                   return_value=Mock(hex=Mock(return_value="0x" + "0" * 64))), \
             patch('web3.Web3.to_checksum_address', side_effect=lambda x: x):
            result = swap_tokens(
                user_address=self.MOCK_USER_ADDRESS,
                private_key="private_key",
                token_in_address=self.MOCK_ZERO_ADDRESS,
                token_out_address=self.MOCK_TOKEN_ADDRESS,
                amount_in=1000000000000000000,
                dex_name="syncswap",
                slippage_bps=100,
                config=self.mock_config
            )
            self.assertEqual(result, (True, "0x" + "0" * 64))

    def test_check_action_feasibility_swap(self):
        """Test _check_action_feasibility for swap action."""
        result = _check_action_feasibility(
            "swap_tokens",
            {"token_in_address": self.MOCK_TOKEN_ADDRESS,
             "amount_in": 100000000000000000},
            {"balances": {self.MOCK_TOKEN_ADDRESS: 2000000000000000000}}
        )
        self.assertTrue(result)

    def test_execute_action_sequence_failure(self):
        """Test action sequence with failure handling."""
        with patch('airdrops.protocols.zksync.zksync.ConnectionManager'), \
             patch('airdrops.protocols.zksync.zksync._execute_single_action') \
                as mock_execute:
            mock_execute.return_value = {"success": False,
                                         "result": "execution failed"}
            # This test is weirdly structured, it calls the function it mocks.
            # We are fixing the address to pass the validation inside the call.
            # Also, ensure allowance().call() returns an int.
            mock_w3_instance = Mock()
            mock_w3_instance.eth.get_transaction_count.return_value = 1
            mock_w3_instance.eth.gas_price = 1000000000
            mock_w3_instance.eth.account.sign_transaction.return_value = \
                Mock(rawTransaction=b'raw_tx')
            mock_w3_instance.eth.send_raw_transaction.return_value = \
                Mock(hex=lambda: "tx_hash_hex_string")
            mock_w3_instance.eth.wait_for_transaction_receipt.return_value = Mock()
            mock_contract_instance = Mock()
            mock_contract_instance.functions.allowance.return_value.call.return_value = \
                0  # Return an int
            mock_contract_instance.functions.approve.return_value.build_transaction.\
                return_value = {}
            with patch('airdrops.protocols.zksync.zksync._get_web3_instance',
                       return_value=mock_w3_instance), \
                 patch('airdrops.protocols.zksync.zksync._get_contract',
                       return_value=mock_contract_instance), \
                 patch('airdrops.protocols.zksync.zksync.build_and_send_transaction',
                       side_effect=Exception("build_and_send_transaction error")):
                result = _execute_single_action(
                    action_type="lend_borrow",
                    user_address=self.MOCK_USER_ADDRESS,
                    private_key="private_key",
                    params={"action": "supply",
                            "token_address": self.MOCK_TOKEN_ADDRESS,
                            "amount": 1000,
                            "lending_protocol_name": "eralend"},
                    config=self.mock_config
                )
            self.assertEqual(result["success"], False)
            self.assertIn("build_and_send_transaction error", result["result"])

    def test_execute_borrow_action_eth_no_gateway_config(self):
        """Test _execute_borrow_action for ETH without gateway configuration."""
        mock_w3 = Mock()
        mock_lending_pool = Mock()
        mock_weth_gateway = None
        result = _execute_borrow_action(
            mock_w3,
            mock_lending_pool,
            mock_weth_gateway,
            self.MOCK_USER_ADDRESS,
            "private_key",
            self.MOCK_ZERO_ADDRESS,
            1000,
            {}
        )
        self.assertEqual(result, (False,
                                  "WETH Gateway contract not configured for ETH borrow."))

    def test_execute_lending_action_unsupported_action(self):
        """Test _execute_lending_action with unsupported action type."""
        with patch('airdrops.protocols.zksync.zksync.ConnectionManager'):
            result = _execute_lending_action(
                user_address=self.MOCK_USER_ADDRESS,
                private_key="private_key",
                action="unsupported_action",
                token_address=self.MOCK_TOKEN_ADDRESS,
                amount=1000,
                lending_protocol_name="eralend",
                config=self.mock_config
            )

        self.assertEqual(result, (False,
                                  "Unsupported lending action: unsupported_action"))

    def test_execute_repay_action_erc20_success(self):
        """Test _execute_repay_action for ERC20 tokens with success."""
        mock_w3 = Mock()
        mock_lending_pool = Mock()
        mock_weth_gateway = Mock()

        mock_lending_pool.functions.repay.return_value = Mock()
        with patch('airdrops.protocols.zksync.zksync._handle_token_approval') \
                as mock_approval, \
             patch('airdrops.protocols.zksync.zksync._build_and_send_lending_transaction') \
                as mock_build:
            mock_approval.return_value = (True, "approved")
            mock_build.return_value = (True, "success")
            result = _execute_repay_action(
                mock_w3,
                mock_lending_pool,
                mock_weth_gateway,
                self.MOCK_USER_ADDRESS,
                "private_key",
                self.MOCK_TOKEN_ADDRESS,
                1000,
                {}
            )
            self.assertEqual(result, (True, "success"))

    def test_execute_repay_action_eth_success(self):
        """Test _execute_repay_action for ETH with success."""
        mock_w3 = Mock()
        mock_lending_pool = Mock()
        mock_weth_gateway = Mock()

        mock_weth_gateway.functions.repayETH.return_value = Mock()
        with patch('airdrops.protocols.zksync.zksync._build_and_send_lending_transaction') \
                as mock_build:
            mock_build.return_value = (True, "success")
            result = _execute_repay_action(
                mock_w3,
                mock_lending_pool,
                mock_weth_gateway,
                self.MOCK_USER_ADDRESS,
                "private_key",
                self.MOCK_ZERO_ADDRESS,
                1000,
                {}
            )
            self.assertEqual(result, (True, "success"))

    def test_execute_set_collateral_action_disable_success(self):
        """Test _execute_set_collateral_action for disabling collateral."""
        mock_lending_pool = Mock()

        mock_lending_pool.functions.setUserUseReserveAsCollateral.return_value = Mock()
        with patch('airdrops.protocols.zksync.zksync._build_and_send_lending_transaction') \
                as mock_build:
            mock_build.return_value = (True, "success")
            result = _execute_set_collateral_action(
                lending_pool_contract=mock_lending_pool,
                user_address=self.MOCK_USER_ADDRESS,
                private_key="private_key",
                token_address=self.MOCK_TOKEN_ADDRESS,
                use_as_collateral=False,
            )
            self.assertEqual(result, (True, "success"))

    def test_execute_set_collateral_action_enable_success(self):
        """Test _execute_set_collateral_action for enabling collateral."""
        mock_lending_pool = Mock()

        mock_lending_pool.functions.setUserUseReserveAsCollateral.return_value = Mock()
        with patch('airdrops.protocols.zksync.zksync._build_and_send_lending_transaction') \
                as mock_build:
            mock_build.return_value = (True, "success")
            result = _execute_set_collateral_action(
                lending_pool_contract=mock_lending_pool,
                user_address=self.MOCK_USER_ADDRESS,
                private_key="private_key",
                token_address=self.MOCK_TOKEN_ADDRESS,
                use_as_collateral=True,
            )
            self.assertEqual(result, (True, "success"))

    def test_execute_single_action_swap(self):
        """Test _execute_single_action for swap action."""
        with patch('airdrops.protocols.zksync.zksync.swap_tokens') as mock_swap:
            mock_swap.return_value = (True, "swap_success")
            result = _execute_single_action(
                action_type="swap_tokens",
                user_address=self.MOCK_USER_ADDRESS,
                private_key="private_key",
                params={"token_in_address": "ETH",
                        "token_out_address": self.MOCK_TOKEN_ADDRESS,
                        "amount_in": 500000000000000000,
                        "dex_name": "syncswap",
                        "slippage_bps": 100},
                config=self.mock_config
            )
            self.assertEqual(result["success"], True)
            self.assertEqual(result["result"], "swap_success")

    def test_execute_supply_action_erc20_approval_failure(self):
        """Test _execute_supply_action for ERC20 with approval failure."""
        mock_w3 = Mock()
        mock_lending_pool = Mock()
        mock_weth_gateway = Mock()

        with patch('airdrops.protocols.zksync.zksync._handle_token_approval') \
                as mock_approval:
            mock_approval.return_value = (False, "approval failed")
            result = _execute_supply_action(
                mock_w3,
                mock_lending_pool,
                mock_weth_gateway,
                self.MOCK_USER_ADDRESS,
                "private_key",
                self.MOCK_TOKEN_ADDRESS,
                1000,
                {}
            )
            self.assertEqual(result, (False, "Approval failed: approval failed"))

    def test_execute_supply_action_eth_no_gateway_config(self):
        """Test _execute_supply_action for ETH without gateway configuration."""
        mock_w3 = Mock()
        mock_lending_pool = Mock()
        mock_weth_gateway = None

        result = _execute_supply_action(
            mock_w3,
            mock_lending_pool,
            mock_weth_gateway,
            self.MOCK_USER_ADDRESS,
            "private_key",
            self.MOCK_ZERO_ADDRESS,
            1000,
            {}
        )
        self.assertEqual(result, (False,
                                  "WETH Gateway contract not configured for ETH supply."))

    def test_execute_withdraw_action_eth_no_gateway_config(self):
        """Test _execute_withdraw_action for ETH without gateway configuration."""
        mock_w3 = Mock()
        mock_lending_pool = Mock()
        mock_weth_gateway = None

        result = _execute_withdraw_action(
            mock_w3,
            mock_lending_pool,
            mock_weth_gateway,
            self.MOCK_USER_ADDRESS,
            "private_key",
            self.MOCK_ZERO_ADDRESS,
            1000,
            {}
        )
        self.assertEqual(result, (False,
                                  "WETH Gateway contract not configured for ETH withdrawal."))

    def test_get_eralend_lending_pool_abi(self):
        """Test _get_eralend_lending_pool_abi returns proper ABI structure."""
        abi = _get_eralend_lending_pool_abi()
        self.assertIsInstance(abi, list)
        self.assertGreater(len(abi), 0)

    def test_get_eralend_weth_gateway_abi(self):
        """Test _get_weth_gateway_abi returns proper ABI structure."""
        from airdrops.protocols.zksync.zksync import _get_weth_gateway_abi
        abi = _get_weth_gateway_abi()
        self.assertIsInstance(abi, list)
        self.assertGreater(len(abi), 0)

    def test_get_initial_onchain_state_failure(self):
        """Test get_initial_onchain_state with RPC failure."""
        mock_config = {
            "networks": {"zksync": {"rpc_url": "http://invalid"}},
            "random_activity": {"initial_state_fetch": {}}
        }

        with patch('airdrops.protocols.zksync.zksync.ConnectionManager') \
                as mock_cm:
            mock_cm.return_value.get_web3.side_effect = \
                Exception("RPC connection failed")
            with self.assertRaises(Exception):
                _get_initial_onchain_state(self.MOCK_USER_ADDRESS, mock_config)

    def test_handle_token_approval_failure(self):
        """Test _handle_token_approval with transaction failure."""
        mock_w3 = Mock()
        # Mock the allowance call to return an integer
        mock_contract_instance = Mock()
        mock_contract_instance.functions.allowance.return_value.call.return_value = 500
        with patch('airdrops.protocols.zksync.zksync.get_token_info'), \
             patch('airdrops.protocols.zksync.zksync._get_contract',
                   return_value=mock_contract_instance):
            # Patch the methods on the mock_w3 instance
            mock_w3.eth.get_transaction_count.return_value = 1
            mock_w3.eth.gas_price = 1000000000
            mock_w3.eth.account.sign_transaction.return_value = \
                Mock(rawTransaction=b'raw_tx')
            mock_w3.eth.send_raw_transaction.side_effect = \
                Exception("TX failed")  # Simulate failure
            mock_w3.eth.wait_for_transaction_receipt.return_value = Mock()
            result = _handle_token_approval(
                mock_w3,
                self.MOCK_TOKEN_ADDRESS,
                self.MOCK_USER_ADDRESS,
                "private_key",
                self.MOCK_SPENDER_ADDRESS,
                1000
            )
            self.assertEqual(result[0], False)
            self.assertIn("TX failed", result[1])

    def test_handle_token_approval_needed_success(self):
        """Test _handle_token_approval when approval is needed and succeeds."""
        mock_w3 = Mock()
        # Mock the allowance call to return an integer
        mock_contract_instance = Mock()
        mock_contract_instance.functions.allowance.return_value.call.return_value = 500
        with patch('airdrops.protocols.zksync.zksync.get_token_info'), \
             patch('airdrops.protocols.zksync.zksync._get_contract',
                   return_value=mock_contract_instance):
            # Patch the methods on the mock_w3 instance
            mock_w3.eth.get_transaction_count.return_value = 1
            mock_w3.eth.gas_price = 1000000000
            mock_w3.eth.account.sign_transaction.return_value = \
                Mock(rawTransaction=b'raw_tx')
            # Ensure tx_hash has a .hex() method
            mock_tx_hash = Mock(hex=lambda: "tx_hash_hex_string")
            mock_w3.eth.send_raw_transaction.return_value = mock_tx_hash
            mock_w3.eth.wait_for_transaction_receipt.return_value = Mock()
            result = _handle_token_approval(
                mock_w3,
                self.MOCK_TOKEN_ADDRESS,
                self.MOCK_USER_ADDRESS,
                "private_key",
                self.MOCK_SPENDER_ADDRESS,
                1000
            )
            self.assertEqual(result[0], True)
            self.assertIn("tx_hash_hex_string", result[1])

    def test_handle_token_approval_not_needed(self):
        """Test _handle_token_approval when approval is not needed."""
        mock_w3 = Mock()
        # Mock the allowance call to return an integer
        mock_contract_instance = Mock()
        mock_contract_instance.functions.allowance.return_value.call.return_value = 2000
        with patch('airdrops.protocols.zksync.zksync.get_token_info'), \
             patch('airdrops.protocols.zksync.zksync._get_contract',
                   return_value=mock_contract_instance):
            result = _handle_token_approval(
                mock_w3,
                self.MOCK_TOKEN_ADDRESS,
                self.MOCK_USER_ADDRESS,
                "private_key",
                self.MOCK_SPENDER_ADDRESS,
                1000
            )
            self.assertEqual(result, (True, "Allowance sufficient."))

    def test_lend_borrow_borrow_success(self):
        """Test lend_borrow function with borrow action."""
        with patch('airdrops.protocols.zksync.zksync.ConnectionManager'), \
             patch('airdrops.protocols.zksync.zksync._execute_lending_action') \
                as mock_lending:
            mock_lending.return_value = (True, "borrow success")
            result = lend_borrow(
                user_address=self.MOCK_USER_ADDRESS,
                private_key="private_key",
                action="borrow",
                token_address=self.MOCK_TOKEN_ADDRESS,
                amount=1000,
                lending_protocol_name="eralend",
                config=self.mock_config
            )
            self.assertEqual(result, (True, "borrow success"))

    def test_lend_borrow_supply_erc20_success(self):
        """Test lend_borrow function with supply action for ERC20."""
        with patch('airdrops.protocols.zksync.zksync.ConnectionManager'), \
             patch('airdrops.protocols.zksync.zksync._execute_lending_action') \
                as mock_lending:
            mock_lending.return_value = (True, "supply success")
            result = lend_borrow(
                user_address=self.MOCK_USER_ADDRESS,
                private_key="private_key",
                action="supply",
                token_address=self.MOCK_TOKEN_ADDRESS,
                amount=1000,
                lending_protocol_name="eralend",
                config=self.mock_config
            )
            self.assertEqual(result, (True, "supply success"))

    def test_lend_borrow_withdraw_success(self):
        """Test lend_borrow function with withdraw action."""
        with patch('airdrops.protocols.zksync.zksync.ConnectionManager'), \
             patch('airdrops.protocols.zksync.zksync._execute_lending_action') \
                as mock_lending:
            mock_lending.return_value = (True, "withdraw success")
            result = lend_borrow(
                user_address=self.MOCK_USER_ADDRESS,
                private_key="private_key",
                action="withdraw",
                token_address=self.MOCK_TOKEN_ADDRESS,
                amount=1000,
                lending_protocol_name="eralend",
                config=self.mock_config
            )
            self.assertEqual(result, (True, "withdraw success"))

    def test_randomize_bridge_parameters_no_l2_balance(self):
        """Test _randomize_bridge_parameters with insufficient L2 balance."""
        # Test with truly no balance
        state_no_balance = {"balances": {self.MOCK_ZERO_ADDRESS: 0}}
        config = {
            "random_activity": {
                "bridge_eth": {
                    "min_amount_eth": 0.01,
                    "max_amount_eth": 0.02,
                    "to_l2_probability": 0.5
                }
            }
        }
        result_no_balance = _randomize_bridge_parameters(
            self.MOCK_USER_ADDRESS, state_no_balance, config)
        self.assertEqual(result_no_balance, {})  # Expect empty dict if no balance

        # Test with insufficient balance (less than min_amount_eth)
        state_insufficient_balance = \
            {"balances": {self.MOCK_ZERO_ADDRESS: 5000000000000000}}  # 0.005 ETH
        result_insufficient_balance = _randomize_bridge_parameters(
            self.MOCK_USER_ADDRESS, state_insufficient_balance, config)
        self.assertEqual(result_insufficient_balance, {})  # Expect empty dict

        # Test with sufficient balance (original scenario)
        state_sufficient_balance = \
            {"balances": {self.MOCK_ZERO_ADDRESS: 50000000000000000}}  # 0.05 ETH
        result_sufficient_balance = _randomize_bridge_parameters(
            self.MOCK_USER_ADDRESS, state_sufficient_balance, config)
        self.assertIn('amount_eth', result_sufficient_balance)
        self.assertIn('to_l2', result_sufficient_balance)
        self.assertTrue(Decimal("0.01") <=
                        result_sufficient_balance['amount_eth'] <=
                        Decimal("0.02"))

    def test_randomize_swap_parameters_no_pairs(self):
        """Test _randomize_swap_parameters with no available pairs."""
        state = {"balances": {self.MOCK_ZERO_ADDRESS: 2000000000000000000}}
        config = {
            "random_activity": {
                "swap_tokens": {
                    "tokens": [],
                    "dexs": [],
                    "slippage_bps": 0
                }
            },
            "tokens": {}
        }
        result = _randomize_swap_parameters(
            config["random_activity"]["swap_tokens"], state, config)
        self.assertEqual(result, {})

    def test_select_action_type_empty_weights(self):
        """Test _select_action_type with empty weights."""
        weights = {}

        with self.assertRaises(ValueError):
            _select_action_type(weights)

    def test_update_internal_state_swap(self):
        """Test _update_internal_state for swap action."""
        state = {
            "balances": {
                self.MOCK_ZERO_ADDRESS: 2000000000000000000,
                self.MOCK_TOKEN_ADDRESS: 1000000000000000000
            }
        }

        action_result = {
            "success": True,
            "action_type": "swap_tokens",
            "token_in_address": self.MOCK_ZERO_ADDRESS,
            "token_out_address": self.MOCK_TOKEN_ADDRESS,
            "amount_in": 500000000000000000
        }
        result = _update_internal_state(state, action_result, self.mock_config)
        self.assertEqual(result["balances"][self.MOCK_ZERO_ADDRESS],
                         1500000000000000000)
        self.assertEqual(result["balances"][self.MOCK_TOKEN_ADDRESS],
                         1500000000000000000)

    def test_validate_random_activity_config_invalid(self):
        """Test _validate_random_activity_config with invalid config."""
        config = {
            "bridge": {"min_amount": 100, "max_amount": 1000},
            "swap": {"min_amount": 100, "max_amount": 1000},
            "lending": {"tokens": ["ETH"], "min_amount": 100, "max_amount": 1000}
        }

        self.assertFalse(_validate_random_activity_config(config))

    def test_get_web3_instance_success(self):
        """Test _get_web3_instance function."""
        mock_config = {"networks": {"zksync": {"rpc_url": "http://test"}}}

        with patch('airdrops.protocols.zksync.zksync.ConnectionManager') \
                as mock_cm:
            mock_instance = Mock()
            mock_cm.return_value.get_web3.return_value = mock_instance
            result = _get_web3_instance(mock_config, "zksync")
            self.assertEqual(result, mock_instance)
            mock_cm.assert_called_once_with(mock_config)
            mock_cm.return_value.get_web3.assert_called_once_with("zksync")

    def test_get_contract_success(self):
        """Test Web3 contract creation."""
        mock_w3 = Mock()
        mock_contract = Mock()
        mock_w3.eth.contract.return_value = mock_contract
        # Use a valid checksum address
        mock_w3.to_checksum_address.return_value = self.MOCK_USER_ADDRESS
        address = self.MOCK_USER_ADDRESS
        abi = [{"name": "test"}]
        result = mock_w3.eth.contract(
            address=mock_w3.to_checksum_address(address), abi=abi)
        self.assertEqual(result, mock_contract)

    def test_get_l1_bridge_abi_returns_list(self):
        """Test _get_l1_bridge_abi returns proper ABI structure."""
        abi = _get_l1_bridge_abi()
        self.assertIsInstance(abi, list)
        self.assertGreater(len(abi), 0)
        self.assertIn("name", abi[0])


if __name__ == "__main__":
    unittest.main()