"""
Unit tests for the perform_random_activity function in the zkSync protocol.

This module tests the orchestration logic of perform_random_activity, focusing on
the retry mechanism, fallback logic, and parameter generation without testing
the underlying on-chain functions.
"""

import pytest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from airdrops.protocols.zksync.zksync import perform_random_activity
from airdrops.protocols.zksync.exceptions import ZkSyncRandomActivityError


class TestPerformRandomActivity:
    """Test suite for the perform_random_activity function."""

    @pytest.fixture
    def valid_config(self) -> Dict[str, Any]:
        """Fixture providing a valid configuration for random activity."""
        return {
            "random_activity": {
                "zksync": {
                    "action_weights": [
                        {"name": "swap", "weight": 60},
                        {"name": "bridge", "weight": 40}
                    ],
                    "max_retries": 3,
                    "amount_ranges": {
                        "swap": {"min": "0.01", "max": "0.1", "decimals": 4},
                        "bridge": {"min": "0.02", "max": "0.2", "decimals": 4}
                    },
                    "token_config": {
                        "ETH": {"address": "0x000000000000000000000000000000000000800A"},
                        "USDC": {"address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4"}
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

    def test_successful_execution_first_attempt(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test successful execution on the first attempt."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks
            mock_select.return_value = "swap"
            mock_execute.return_value = "0x123abc"
            
            # Execute function
            results = perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify results
            assert len(results) == 1
            assert results[0]["attempt"] == 1
            assert results[0]["activity"] == "swap"
            assert results[0]["status"] == "success"
            assert results[0]["tx_hash"] == "0x123abc"
            assert "timestamp" in results[0]
            
            # Verify function calls
            mock_select.assert_called_once()
            mock_execute.assert_called_once_with(
                "swap",
                "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                "0x" + "a" * 64,
                valid_config["random_activity"]["zksync"]["amount_ranges"],
                valid_config["random_activity"]["zksync"]["token_config"],
                mock_web3_l1,
                mock_web3_l2
            )

    def test_fallback_logic_second_attempt_success(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test fallback logic where first activity fails, second succeeds."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks - first call fails, second succeeds
            mock_select.side_effect = ["swap", "bridge"]
            mock_execute.side_effect = [
                Exception("Swap failed"),
                "0x456def"
            ]
            
            # Execute function
            results = perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify results
            assert len(results) == 2
            
            # First attempt (failed)
            assert results[0]["attempt"] == 1
            assert results[0]["activity"] == "swap"
            assert results[0]["status"] == "failed"
            assert results[0]["error"] == "Swap failed"
            assert "timestamp" in results[0]
            
            # Second attempt (successful)
            assert results[1]["attempt"] == 2
            assert results[1]["activity"] == "bridge"
            assert results[1]["status"] == "success"
            assert results[1]["tx_hash"] == "0x456def"
            assert "timestamp" in results[1]
            
            # Verify function calls
            assert mock_select.call_count == 2
            assert mock_execute.call_count == 2

    def test_max_retries_failure(
        self,
        valid_config: Dict[str, Any],
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that function raises exception after all activities fail."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks - all activities fail
            mock_select.side_effect = ["swap", "bridge"]
            mock_execute.side_effect = [
                Exception("Swap failed"),
                Exception("Bridge failed")
            ]
            
            # Execute function and expect exception
            with pytest.raises(ZkSyncRandomActivityError, match="All random activities failed after 3 attempts"):
                perform_random_activity(
                    user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                    private_key="0x" + "a" * 64,
                    config=valid_config,
                    web3_l1=mock_web3_l1,
                    web3_l2=mock_web3_l2
                )
            
            # Verify both activities were attempted (pool becomes empty after 2 failures)
            assert mock_select.call_count == 2
            assert mock_execute.call_count == 2

    def test_parameter_generation_swap_activity(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that correct parameters are generated for swap activity."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks
            mock_select.return_value = "swap"
            mock_execute.return_value = "0x123abc"
            
            # Execute function
            perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify _execute_zksync_activity was called with correct parameters
            mock_execute.assert_called_once_with(
                "swap",
                "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                "0x" + "a" * 64,
                valid_config["random_activity"]["zksync"]["amount_ranges"],
                valid_config["random_activity"]["zksync"]["token_config"],
                mock_web3_l1,
                mock_web3_l2
            )

    def test_parameter_generation_bridge_activity(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that correct parameters are generated for bridge activity."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks
            mock_select.return_value = "bridge"
            mock_execute.return_value = "0x789ghi"
            
            # Execute function
            perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify _execute_zksync_activity was called with correct parameters
            mock_execute.assert_called_once_with(
                "bridge",
                "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                "0x" + "a" * 64,
                valid_config["random_activity"]["zksync"]["amount_ranges"],
                valid_config["random_activity"]["zksync"]["token_config"],
                mock_web3_l1,
                mock_web3_l2
            )

    def test_invalid_configuration_missing_random_activity(
        self, 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test handling of missing random_activity configuration."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        invalid_config: Dict[str, Any] = {"some_other_config": {}}
        
        with pytest.raises(ValueError, match="config must contain 'random_activity' section"):
            perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=invalid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )

    def test_invalid_configuration_missing_zksync_section(
        self, 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test handling of missing zksync section in configuration."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        invalid_config: Dict[str, Any] = {
            "random_activity": {
                "other_protocol": {}
            }
        }
        
        with pytest.raises(ValueError, match="config must contain 'random_activity.zksync' section"):
            perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=invalid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )

    def test_invalid_configuration_empty_action_weights(
        self, 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test handling of empty action_weights configuration."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        invalid_config = {
            "random_activity": {
                "zksync": {
                    "action_weights": [],
                    "max_retries": 3,
                    "amount_ranges": {},
                    "token_config": {}
                }
            }
        }
        
        with pytest.raises(ValueError, match="action_weights cannot be empty"):
            perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=invalid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )

    def test_invalid_user_address(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test handling of invalid user address."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with pytest.raises(ValueError, match="user_address and private_key are required"):
            perform_random_activity(
                user_address="",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )

    def test_invalid_private_key(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test handling of invalid private key."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with pytest.raises(ValueError, match="user_address and private_key are required"):
            perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="",
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )

    def test_activity_pool_removal_on_failure(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that failed activities are removed from the activity pool."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks - first activity fails, second succeeds
            mock_select.side_effect = ["swap", "bridge"]
            mock_execute.side_effect = [
                Exception("Swap failed"),
                "0x456def"
            ]
            
            # Execute function
            perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify that select_activity_by_weight was called with reduced pool on second call
            assert mock_select.call_count == 2
            
            # First call should have all activities
            first_call_args = mock_select.call_args_list[0][0][0]
            assert len(first_call_args) == 2
            assert any(activity["name"] == "swap" for activity in first_call_args)
            
            # Second call should not have "swap" activity
            second_call_args = mock_select.call_args_list[1][0][0]
            assert len(second_call_args) == 1
            assert not any(activity["name"] == "swap" for activity in second_call_args)
            assert any(activity["name"] == "bridge" for activity in second_call_args)

    def test_timestamp_generation(
        self, 
        valid_config: Dict[str, Any], 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that timestamps are correctly generated for results."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute, \
             patch('time.time') as mock_time:
            
            # Setup mocks
            mock_select.return_value = "swap"
            mock_execute.return_value = "0x123abc"
            mock_time.return_value = 1234567890.123
            
            # Execute function
            results = perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify timestamp
            assert results[0]["timestamp"] == 1234567890.123

    def test_config_defaults_handling(
        self, 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that configuration defaults are handled correctly."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        minimal_config = {
            "random_activity": {
                "zksync": {
                    "action_weights": [
                        {"name": "swap", "weight": 50}
                    ]
                    # Missing max_retries, amount_ranges, token_config
                }
            }
        }
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks
            mock_select.return_value = "swap"
            mock_execute.return_value = "0x123abc"
            
            # Execute function
            results = perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=minimal_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify function succeeds with defaults
            assert len(results) == 1
            assert results[0]["status"] == "success"
            
            # Verify _execute_zksync_activity was called with empty defaults
            mock_execute.assert_called_once_with(
                "swap",
                "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                "0x" + "a" * 64,
                {},  # empty amount_ranges
                {},  # empty token_config
                mock_web3_l1,
                mock_web3_l2
            )

    def test_specific_swap_activity_path(
        self, 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that swap activity is handled correctly when forced."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        swap_only_config = {
            "random_activity": {
                "zksync": {
                    "action_weights": [
                        {"name": "swap", "weight": 100}
                    ],
                    "max_retries": 3,
                    "amount_ranges": {
                        "swap": {"min": "0.01", "max": "0.1", "decimals": 4}
                    },
                    "token_config": {
                        "ETH": {"address": "0x000000000000000000000000000000000000800A"},
                        "USDC": {"address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4"}
                    }
                }
            }
        }
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks
            mock_select.return_value = "swap"
            mock_execute.return_value = "0xabcdef"
            
            # Execute function
            results = perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=swap_only_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify results
            assert len(results) == 1
            assert results[0]["activity"] == "swap"
            assert results[0]["status"] == "success"
            assert results[0]["tx_hash"] == "0xabcdef"
            
            # Verify _execute_zksync_activity was called with correct parameters
            mock_execute.assert_called_once_with(
                "swap",
                "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                "0x" + "a" * 64,
                swap_only_config["random_activity"]["zksync"]["amount_ranges"],
                swap_only_config["random_activity"]["zksync"]["token_config"],
                mock_web3_l1,
                mock_web3_l2
            )

    def test_specific_bridge_activity_path(
        self, 
        mock_web3_instances: tuple[MagicMock, MagicMock]
    ) -> None:
        """Test that bridge activity is handled correctly when forced."""
        mock_web3_l1, mock_web3_l2 = mock_web3_instances
        
        bridge_only_config = {
            "random_activity": {
                "zksync": {
                    "action_weights": [
                        {"name": "bridge", "weight": 100}
                    ],
                    "max_retries": 3,
                    "amount_ranges": {
                        "bridge": {"min": "0.02", "max": "0.2", "decimals": 4}
                    },
                    "token_config": {
                        "ETH": {"address": "0x000000000000000000000000000000000000800A"}
                    }
                }
            }
        }
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks
            mock_select.return_value = "bridge"
            mock_execute.return_value = "0xfedcba"
            
            # Execute function
            results = perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=bridge_only_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify results
            assert len(results) == 1
            assert results[0]["activity"] == "bridge"
            assert results[0]["status"] == "success"
            assert results[0]["tx_hash"] == "0xfedcba"
            
            # Verify _execute_zksync_activity was called with correct parameters
            mock_execute.assert_called_once_with(
                "bridge",
                "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                "0x" + "a" * 64,
                bridge_only_config["random_activity"]["zksync"]["amount_ranges"],
                bridge_only_config["random_activity"]["zksync"]["token_config"],
                mock_web3_l1,
                mock_web3_l2
            )

    def test_web3_instances_passed_correctly(
        self, 
        valid_config: Dict[str, Any]
    ) -> None:
        """Test that Web3 instances are passed correctly to sub-functions."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        
        # Set specific attributes to verify they're passed through
        mock_web3_l1.eth.chain_id = 1
        mock_web3_l2.eth.chain_id = 324
        
        with patch('airdrops.protocols.zksync.zksync.select_activity_by_weight') as mock_select, \
             patch('airdrops.protocols.zksync.zksync._execute_zksync_activity') as mock_execute:
            
            # Setup mocks
            mock_select.return_value = "bridge"
            mock_execute.return_value = "0x123abc"
            
            # Execute function
            perform_random_activity(
                user_address="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47",
                private_key="0x" + "a" * 64,
                config=valid_config,
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2
            )
            
            # Verify the exact Web3 instances were passed
            call_args = mock_execute.call_args[0]
            assert call_args[5] is mock_web3_l1  # web3_l1 parameter
            assert call_args[6] is mock_web3_l2  # web3_l2 parameter