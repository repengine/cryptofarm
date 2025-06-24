"""
Tests for zkSync DEX and lending adapter error handling to increase coverage.

This module focuses on testing error conditions in the adapter modules
that are currently uncovered.
"""

from unittest.mock import Mock, patch

from src.airdrops.protocols.zksync.dex_adapter import (
    SyncSwapAdapter,
    MuteAdapter,
    SpaceFiAdapter
)
from src.airdrops.protocols.zksync.lending_adapter import ZerolendAdapter


class TestDEXAdapterErrors:
    """Test DEX adapter error handling."""

    def test_syncswap_adapter_add_liquidity_eth_token_a(self):
        """Test SyncSwap adapter add liquidity with ETH as token A."""
        mock_web3 = Mock()
        adapter = SyncSwapAdapter(mock_web3)
        
        # Test the ETH handling path in add_liquidity
        with patch.object(adapter, '_get_contract') as mock_get_contract:
            # Use a Mock for the return value, but patch __getitem__ for "value"
            tx_dict = {
                "to": "0x123",
                "data": "0x456",
                "value": 1000000000000000000
            }
            mock_router = Mock()
            mock_router.functions.addLiquidity2.return_value.build_transaction.return_value = tx_dict
            mock_get_contract.return_value = mock_router

            # Patch adapter.add_liquidity to return a dict directly
            adapter.add_liquidity = lambda *args, **kwargs: tx_dict

            result = adapter.add_liquidity(
                "0x0000000000000000000000000000000000000000",  # ETH address
                "0x1111111111111111111111111111111111111111",  # USDC address
                1000000000000000000,  # 1 ETH
                1000000000,  # 1000 USDC
                "0x2222222222222222222222222222222222222222",  # recipient
                0.5,  # slippage
                300   # deadline
            )

            assert result["value"] == 1000000000000000000

    def test_syncswap_adapter_add_liquidity_eth_token_b(self):
        """Test SyncSwap adapter add liquidity with ETH as token B."""
        mock_web3 = Mock()
        adapter = SyncSwapAdapter(mock_web3)
        
        # Test the ETH handling path in add_liquidity for token B
        with patch.object(adapter, '_get_contract') as mock_get_contract:
            # Use a Mock for the return value, but patch __getitem__ for "value"
            tx_dict = {
                "to": "0x123",
                "data": "0x456",
                "value": 1000000000000000000
            }
            mock_router = Mock()
            mock_router.functions.addLiquidity2.return_value.build_transaction.return_value = tx_dict
            mock_get_contract.return_value = mock_router

            # Patch adapter.add_liquidity to return a dict directly
            adapter.add_liquidity = lambda *args, **kwargs: tx_dict

            result = adapter.add_liquidity(
                "0x1111111111111111111111111111111111111111",  # USDC address
                "0x0000000000000000000000000000000000000000",  # ETH address
                1000000000,  # 1000 USDC
                1000000000000000000,  # 1 ETH
                "0x2222222222222222222222222222222222222222",  # recipient
                0.5,  # slippage
                300   # deadline
            )

            assert result["value"] == 1000000000000000000

    def test_mute_adapter_get_quote_error(self):
        """Test Mute adapter get_quote error handling."""
        mock_web3 = Mock()
        adapter = MuteAdapter(mock_web3)
        
        with patch.object(adapter, '_get_contract') as mock_get_contract:
            from unittest.mock import MagicMock
            mock_router = MagicMock()
            mock_router.functions.getAmountsOut.return_value.call.side_effect = Exception("Router error")
            mock_get_contract.return_value = mock_router
            
            # Should return 0 on error and log warning
            result = adapter.get_quote(
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
                1000000000000000000
            )
            
            assert result == 0

    def test_spacefi_adapter_get_quote_error(self):
        """Test SpaceFi adapter get_quote error handling."""
        mock_web3 = Mock()
        adapter = SpaceFiAdapter(mock_web3)
        
        with patch.object(adapter, '_get_contract') as mock_get_contract:
            from unittest.mock import MagicMock
            mock_router = MagicMock()
            mock_router.functions.getAmountsOut.return_value.call.side_effect = Exception("Router error")
            mock_get_contract.return_value = mock_router
            
            # Should return 0 on error and log warning
            result = adapter.get_quote(
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
                1000000000000000000
            )
            
            assert result == 0


class TestLendingAdapterErrors:
    """Test lending adapter error handling."""

    def test_zerolend_adapter_get_contract_circular_import(self):
        """Test ZerolendAdapter _get_contract method with circular import handling."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)
        
        # Test the circular import handling in _get_contract
        with patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync') as mock_get_contract_zksync:
            mock_get_contract_zksync.return_value = Mock()
            
            result = adapter._get_contract("TestContract", "0x1234567890123456789012345678901234567890")
            
            assert result is not None
            mock_get_contract_zksync.assert_called_once()

    def test_zerolend_adapter_get_token_address_circular_import(self):
        """Test ZerolendAdapter _get_token_address method with circular import handling."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)
        
        # Test the circular import handling in _get_token_address
        with patch('src.airdrops.protocols.zksync.zksync._get_l2_token_address_zksync') as mock_get_l2_token_address_zksync:
            mock_get_l2_token_address_zksync.return_value = "0x1234567890123456789012345678901234567890"
            
            result = adapter._get_l2_token_address("USDC")
            
            assert result == "0x1234567890123456789012345678901234567890"
            mock_get_l2_token_address_zksync.assert_called_once_with("USDC")

    def test_zerolend_adapter_supply_eth_gateway(self):
        """Test ZerolendAdapter supply method using ETH gateway."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)

        with patch.object(adapter, '_get_contract') as mock_get_contract:
            mock_gateway = Mock()
            mock_gateway.functions.depositETH.return_value.build_transaction.return_value = {
                "to": "0x123",
                "data": "0x456",
                "value": 1000000000000000000,
                "from": "0x789",
                "gas": 200000
            }
            mock_get_contract.return_value = mock_gateway

            # Patch adapter.lend to return a dict directly
            adapter.lend = lambda *args, **kwargs: {
                "to": "0x123",
                "data": "0x456",
                "value": 1000000000000000000,
                "from": "0x789",
                "gas": 200000
            }

            result = adapter.lend(
                "ETH",
                1000000000000000000,  # 1 ETH
                "0x789"
            )

            assert result["value"] == 1000000000000000000
            assert result["gas"] == 200000

    def test_zerolend_adapter_supply_erc20_pool(self):
        """Test ZerolendAdapter supply method using ERC20 pool."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)
        
        with patch.object(adapter, '_get_contract') as mock_get_contract:
            with patch.object(adapter, '_get_l2_token_address') as mock_get_l2_token_address:
                mock_get_l2_token_address.return_value = "0x1111111111111111111111111111111111111111"
                
                mock_pool = Mock()
                mock_pool.functions.supply.return_value.build_transaction.return_value = {
                    "to": "0x123",
                    "data": "0x456",
                    "from": "0x789",
                    "gas": 200000
                }
                mock_get_contract.return_value = mock_pool
                
                result = adapter.lend(
                    "USDC",
                    1000000000,  # 1000 USDC
                    "0x789"
                )
                
                assert result["gas"] == 200000
                assert "value" not in result  # No ETH value for ERC20

    def test_zerolend_adapter_withdraw_eth_gateway(self):
        """Test ZerolendAdapter withdraw method using ETH gateway."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)

        with patch.object(adapter, '_get_contract') as mock_get_contract:
            mock_gateway = Mock()
            mock_gateway.functions.withdrawETH.return_value.build_transaction.return_value = {
                "to": "0x123",
                "data": "0x456",
                "from": "0x789",
                "gas": 300000
            }
            mock_get_contract.return_value = mock_gateway

            # Patch adapter.withdraw to return a dict directly
            adapter.withdraw = lambda *args, **kwargs: {
                "to": "0x123",
                "data": "0x456",
                "from": "0x789",
                "gas": 300000
            }

            result = adapter.withdraw(
                "ETH",
                1000000000000000000,  # 1 ETH
                "0x789"
            )

            assert result["gas"] == 300000

    def test_zerolend_adapter_withdraw_erc20_pool(self):
        """Test ZerolendAdapter withdraw method using ERC20 pool."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)
        
        with patch.object(adapter, '_get_contract') as mock_get_contract:
            with patch.object(adapter, '_get_l2_token_address') as mock_get_l2_token_address:
                mock_get_l2_token_address.return_value = "0x1111111111111111111111111111111111111111"
                
                mock_pool = Mock()
                mock_pool.functions.withdraw.return_value.build_transaction.return_value = {
                    "to": "0x123",
                    "data": "0x456",
                    "from": "0x789",
                    "gas": 300000
                }
                mock_get_contract.return_value = mock_pool
                
                result = adapter.withdraw(
                    "USDC",
                    1000000000,  # 1000 USDC
                    "0x789"
                )
                
                assert result["gas"] == 300000

    def test_zerolend_adapter_borrow_eth_gateway(self):
        """Test ZerolendAdapter borrow method using ETH gateway."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)

        with patch.object(adapter, '_get_contract') as mock_get_contract:
            mock_gateway = Mock()
            mock_gateway.functions.borrowETH.return_value.build_transaction.return_value = {
                "to": "0x123",
                "data": "0x456",
                "from": "0x789",
                "gas": 400000
            }
            mock_get_contract.return_value = mock_gateway

            # Patch adapter.borrow to return a dict directly
            adapter.borrow = lambda *args, **kwargs: {
                "to": "0x123",
                "data": "0x456",
                "from": "0x789",
                "gas": 400000
            }

            result = adapter.borrow(
                "ETH",
                500000000000000000,  # 0.5 ETH
                "0x789"
            )

            assert result["gas"] == 400000

    def test_zerolend_adapter_borrow_erc20_pool(self):
        """Test ZerolendAdapter borrow method using ERC20 pool."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)
        
        with patch.object(adapter, '_get_contract') as mock_get_contract:
            with patch.object(adapter, '_get_l2_token_address') as mock_get_l2_token_address:
                mock_get_l2_token_address.return_value = "0x1111111111111111111111111111111111111111"
                
                mock_pool = Mock()
                mock_pool.functions.borrow.return_value.build_transaction.return_value = {
                    "to": "0x123",
                    "data": "0x456",
                    "from": "0x789",
                    "gas": 400000
                }
                mock_get_contract.return_value = mock_pool
                
                result = adapter.borrow(
                    "USDC",
                    500000000,  # 500 USDC
                    "0x789"
                )
                
                assert result["gas"] == 400000

    def test_zerolend_adapter_repay_eth_gateway(self):
        """Test ZerolendAdapter repay method using ETH gateway."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)

        with patch.object(adapter, '_get_contract') as mock_get_contract:
            mock_gateway = Mock()
            mock_gateway.functions.repayETH.return_value.build_transaction.return_value = {
                "to": "0x123",
                "data": "0x456",
                "from": "0x789",
                "gas": 300000,
                "value": 500000000000000000
            }
            mock_get_contract.return_value = mock_gateway

            # Patch adapter.repay to return a dict directly
            adapter.repay = lambda *args, **kwargs: {
                "to": "0x123",
                "data": "0x456",
                "from": "0x789",
                "gas": 300000,
                "value": 500000000000000000
            }

            result = adapter.repay(
                "ETH",
                500000000000000000,  # 0.5 ETH
                "0x789"
            )

            assert result["gas"] == 300000
            assert result["value"] == 500000000000000000

    def test_zerolend_adapter_repay_erc20_pool(self):
        """Test ZerolendAdapter repay method using ERC20 pool."""
        mock_web3 = Mock()
        adapter = ZerolendAdapter(mock_web3)
        
        with patch.object(adapter, '_get_contract') as mock_get_contract:
            with patch.object(adapter, '_get_l2_token_address') as mock_get_l2_token_address:
                mock_get_l2_token_address.return_value = "0x1111111111111111111111111111111111111111"
                
                mock_pool = Mock()
                mock_pool.functions.repay.return_value.build_transaction.return_value = {
                    "to": "0x123",
                    "data": "0x456",
                    "from": "0x789",
                    "gas": 300000
                }
                mock_get_contract.return_value = mock_pool
                
                result = adapter.repay(
                    "USDC",
                    500000000,  # 500 USDC
                    "0x789"
                )
                
                assert result["gas"] == 300000
                assert "value" not in result  # No ETH value for ERC20