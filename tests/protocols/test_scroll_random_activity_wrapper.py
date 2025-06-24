"""
Unit tests for the random_activity wrapper function in the Scroll protocol.

This module tests the simplified random_activity function that wraps
the comprehensive perform_random_activity functionality.
"""

import pytest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from src.airdrops.protocols.scroll.scroll import random_activity
from src.airdrops.protocols.scroll.exceptions import ScrollRandomActivityError


class TestRandomActivity:
    """Test suite for the random_activity function."""

    @pytest.fixture
    def valid_config(self) -> Dict[str, Any]:
        """Fixture providing a valid configuration for random activity."""
        return {
            "random_activity": {
                "scroll": {
                    "action_weights": [
                        {"name": "swap", "weight": 50},
                        {"name": "lend", "weight": 30},
                        {"name": "bridge", "weight": 20}
                    ],
                    "max_retries": 3,
                    "amount_ranges": {
                        "swap": {"min": "0.01", "max": "0.1", "decimals": 4},
                        "lend": {"min": "0.005", "max": "0.05", "decimals": 4},
                        "bridge": {"min": "0.02", "max": "0.2", "decimals": 4}
                    },
                    "token_config": {
                        "ETH": {"address": "0x123"},
                        "USDC": {"address": "0x456"}
                    }
                }
            }
        }

    @pytest.fixture
    def mock_web3_instances(self) -> tuple[MagicMock, MagicMock]:
        """Fixture providing mock Web3 instances."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        return mock_web3_l1, mock_web3_l2

    def test_successful_execution_returns_tx_hash(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test successful execution returns transaction hash."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform:
            # Setup mock to return successful result
            mock_perform.return_value = [
                {
                    "attempt": 1,
                    "activity": "swap",
                    "status": "success",
                    "tx_hash": "0x123abc",
                    "timestamp": 1234567890.123
                }
            ]
            
            # Execute function
            result = random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify result
            assert result == "0x123abc"
            
            # Verify perform_random_activity was called with correct parameters
            mock_perform.assert_called_once_with(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )

    def test_multiple_attempts_returns_first_success(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that function returns first successful transaction hash."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform:
            # Setup mock to return failed then successful results
            mock_perform.return_value = [
                {
                    "attempt": 1,
                    "activity": "swap",
                    "status": "failed",
                    "error": "Swap failed",
                    "timestamp": 1234567890.123
                },
                {
                    "attempt": 2,
                    "activity": "lend",
                    "status": "success",
                    "tx_hash": "0x456def",
                    "timestamp": 1234567891.123
                }
            ]
            
            # Execute function
            result = random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify result is the first successful transaction
            assert result == "0x456def"

    def test_no_successful_results_raises_error(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that function raises error when no successful results."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform:
            # Setup mock to return only failed results
            mock_perform.return_value = [
                {
                    "attempt": 1,
                    "activity": "swap",
                    "status": "failed",
                    "error": "Swap failed",
                    "timestamp": 1234567890.123
                },
                {
                    "attempt": 2,
                    "activity": "lend",
                    "status": "failed",
                    "error": "Lend failed",
                    "timestamp": 1234567891.123
                }
            ]
            
            # Execute function and expect exception
            with pytest.raises(ScrollRandomActivityError, match="Random activity execution failed"):
                random_activity(
                    user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                    private_key="0x" + "a" * 64,
                    config=valid_config,
                    web3_l1=mock_web3_l1,
                    web3_l2=mock_web3_l2
                )

    def test_empty_results_raises_error(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that function raises error when results list is empty."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform:
            # Setup mock to return empty results
            mock_perform.return_value = []
            
            # Execute function and expect exception
            with pytest.raises(ScrollRandomActivityError, match="Random activity execution failed"):
                random_activity(
                    user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                    private_key="0x" + "a" * 64,
                    config=valid_config,
                    web3_l1=mock_web3_l1,
                    web3_l2=mock_web3_l2
                )

    def test_successful_result_without_tx_hash_raises_error(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that function raises error when successful result lacks tx_hash."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform:
            # Setup mock to return successful result without tx_hash
            mock_perform.return_value = [
                {
                    "attempt": 1,
                    "activity": "swap",
                    "status": "success",
                    # Missing tx_hash
                    "timestamp": 1234567890.123
                }
            ]
            
            # Execute function and expect exception
            with pytest.raises(ScrollRandomActivityError, match="Random activity execution failed"):
                random_activity(
                    user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                    private_key="0x" + "a" * 64,
                    config=valid_config,
                    web3_l1=mock_web3_l1,
                    web3_l2=mock_web3_l2
                )

    def test_perform_random_activity_exception_propagates(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that exceptions from perform_random_activity are propagated."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform:
            # Setup mock to raise exception
            mock_perform.side_effect = ScrollRandomActivityError("Configuration error")
            
            # Execute function and expect exception to propagate
            with pytest.raises(ScrollRandomActivityError, match="Configuration error"):
                random_activity(
                    user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                    private_key="0x" + "a" * 64,
                    config=valid_config,
                    web3_l1=mock_web3_l1,
                    web3_l2=mock_web3_l2
                )

    def test_function_with_minimal_parameters(
        self, 
        valid_config: Dict[str, Any]
    ) -> None:
        """Test function works with minimal parameters (no web3 instances)."""
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform:
            # Setup mock to return successful result
            mock_perform.return_value = [
                {
                    "attempt": 1,
                    "activity": "swap",
                    "status": "success",
                    "tx_hash": "0x789ghi",
                    "timestamp": 1234567890.123
                }
            ]
            
            # Execute function without web3 instances
            result = random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config
            )
            
            # Verify result
            assert result == "0x789ghi"
            
            # Verify perform_random_activity was called with None for web3 instances
            mock_perform.assert_called_once_with(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=None,
                web3_l2=None
            )

    def test_function_with_only_web3_l2(
        self, 
        valid_config: Dict[str, Any]
    ) -> None:
        """Test function works with only web3_l2 parameter."""
        mock_web3_l2 = MagicMock()
        
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform:
            # Setup mock to return successful result
            mock_perform.return_value = [
                {
                    "attempt": 1,
                    "activity": "swap",
                    "status": "success",
                    "tx_hash": "0xabcdef",
                    "timestamp": 1234567890.123
                }
            ]
            
            # Execute function with only web3_l2
            result = random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l2=mock_web3_l2
            )
            
            # Verify result
            assert result == "0xabcdef"
            
            # Verify perform_random_activity was called correctly
            mock_perform.assert_called_once_with(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=None,
                web3_l2=mock_web3_l2
            )

    def test_logging_behavior(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that function logs appropriately."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform, \
             patch('src.airdrops.protocols.scroll.scroll.logger') as mock_logger:
            
            # Setup mock to return successful result
            mock_perform.return_value = [
                {
                    "attempt": 1,
                    "activity": "swap",
                    "status": "success",
                    "tx_hash": "0x123abc",
                    "timestamp": 1234567890.123
                }
            ]
            
            # Execute function
            result = random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify logging calls
            mock_logger.info.assert_any_call(
                "Executing random activity for user 0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47"
            )
            mock_logger.info.assert_any_call(
                "Random activity completed successfully: 0x123abc"
            )
            
            # Verify result
            assert result == "0x123abc"

    def test_logging_behavior_on_failure(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that function logs errors appropriately."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('src.airdrops.protocols.scroll.scroll.perform_random_activity') as mock_perform, \
             patch('src.airdrops.protocols.scroll.scroll.logger') as mock_logger:
            
            # Setup mock to return failed results
            mock_perform.return_value = [
                {
                    "attempt": 1,
                    "activity": "swap",
                    "status": "failed",
                    "error": "Swap failed",
                    "timestamp": 1234567890.123
                }
            ]
            
            # Execute function and expect exception
            with pytest.raises(ScrollRandomActivityError):
                random_activity(
                    user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                    private_key="0x" + "a" * 64,
                    config=valid_config,
                    web3_l1=mock_web3_l1,
                    web3_l2=mock_web3_l2
                )
            
            # Verify error logging
            mock_logger.error.assert_called_with(
                "Random activity failed - no successful transactions"
            )