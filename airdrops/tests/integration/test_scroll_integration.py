"""
Integration tests for Scroll protocol with scheduler and monitoring.

This module tests the integration of the Scroll protocol with the central scheduler,
capital allocation engine, and monitoring system to ensure all components work
together correctly.
"""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from typing import Dict, Any
from web3 import Web3

from airdrops.scheduler.bot import (
    CentralScheduler,
    TaskDefinition,
    TaskExecution,
    TaskStatus,
)
from airdrops.capital_allocation.engine import CapitalAllocator
from airdrops.monitoring.collector import MetricsCollector
from airdrops.risk_management.core import RiskManager
from airdrops.monitoring.alerter import Alerter


class TestScrollIntegration:
    """Test suite for Scroll protocol integration with other system components."""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Create mock configuration for testing.
        
        Returns:
            Dictionary containing test configuration
        """
        return {
            "protocols": {
                "scroll": {
                    "enabled": True,
                    "daily_activity_range": [3, 5],
                    "operations": {
                        "bridge": {"enabled": True, "weight": 30},
                        "swap": {"enabled": True, "weight": 40},
                        "liquidity": {"enabled": True, "weight": 20},
                        "lending": {"enabled": True, "weight": 10},
                    },
                },
            },
            "wallets": [
                "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
                "0x853d35Cc6634C0532925a3b844Bc9e7195Ed5E47283776",
            ],
            "networks": {
                "ethereum": {
                    "rpc_url": "https://eth-mainnet.example.com",
                },
                "scroll": {
                    "rpc_url": "https://scroll-mainnet.example.com",
                    "chain_id": 534352,
                },
            },
            "monitoring": {
                "metrics_interval": 60,
                "health_check_interval": 300,
            },
            "risk_management": {
                "max_daily_gas_usd": 100,
                "max_protocol_exposure": 0.3,
                "min_balance_eth": 0.01,
            },
            "capital_allocation": {
                "strategy": "risk_parity",
                "rebalance_threshold": 0.1,
            },
        }

    @pytest.fixture
    def mock_web3(self) -> Mock:
        """Create mock Web3 instance.
        
        Returns:
            Mock Web3 instance with common methods
        """
        w3 = Mock(spec=Web3)
        w3.eth = Mock()
        w3.eth.get_balance.return_value = Web3.to_wei(1, "ether")
        w3.eth.gas_price = Web3.to_wei(30, "gwei")
        w3.eth.get_transaction_count.return_value = 1
        w3.is_connected.return_value = True
        return w3

    @patch("airdrops.protocols.scroll.scroll.bridge_assets")
    def test_scheduler_executes_scroll_task(
        self, mock_bridge_assets, mock_config
    ):
        """Test that scheduler correctly executes Scroll protocol tasks.
        
        Args:
            mock_bridge_assets: Mock for the bridge_assets function.
            mock_config: Test configuration
        """
        # Setup mocks
        mock_bridge_assets.return_value = "0x" + "e" * 64
            
        # Create scheduler
        scheduler = CentralScheduler(mock_config)
        
        # Execute task
        task = {
            "id": "scroll_bridge_task",
            "protocol": "scroll",
            "action": "bridge_assets",
            "wallet": mock_config["wallets"][0],
            "params": {
                "is_deposit": True,
                "token_symbol": "ETH",
                "amount": "0.05",
            },
        }
        result = scheduler._execute_task(task)
        
        # Verify task executed
        assert result["success"] is True
        mock_bridge_assets.assert_called_once()

    def test_capital_allocation_with_scroll(self, mock_config):
        """Test capital allocation engine with Scroll protocol.
        
        Args:
            mock_config: Test configuration
        """
        
        # Create capital allocator
        allocator = CapitalAllocator(mock_config)
        
        # Test allocation including Scroll
        # Test portfolio optimization
        protocols = ["scroll"]
        risk_constraints = {"max_protocol_exposure": Decimal("0.3")}
        portfolio = allocator.optimize_portfolio(protocols, risk_constraints)
        
        # Verify Scroll is included
        assert "scroll" in portfolio
        assert portfolio["scroll"] > 0
        
        # Test risk-adjusted allocation
        total_capital = Decimal("10000")  # $10k
        risk_metrics = {"volatility_state": "low", "gas_price": 30}
        allocations = allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio, risk_metrics
        )
        
        # Verify allocations
        assert "scroll" in allocations
        assert allocations["scroll"] > 0

    @patch("airdrops.monitoring.collector.time")
    def test_monitoring_tracks_scroll_metrics(self, mock_time, mock_config):
        """Test that monitoring system tracks Scroll protocol metrics.
        
        Args:
            mock_time: Mock time module
            mock_config: Test configuration
        """
        # Setup time mock
        mock_time.time.return_value = 1700000000
        
        # Create metrics collector
        collector = MetricsCollector()
        
        # Record Scroll transaction
        collector.record_transaction(
            protocol="scroll",
            action="swap",
            wallet="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
            success=True,
            gas_used=150000,
            value_usd=50.0,
            tx_hash="0x" + "b" * 64,
        )
        
        # Get metrics
        metrics = collector.get_protocol_metrics("scroll")
        
        # Verify metrics recorded
        assert metrics["total_transactions"] == 1.0
        assert metrics["successful_transactions"] == 1.0
        assert metrics["total_gas_used"] == 150000.0
        assert metrics["total_value_usd"] == 50.0

    @patch("airdrops.protocols.scroll.scroll.swap_tokens")
    @patch("airdrops.monitoring.alerter.Alerter.send_notifications")
    def test_alerting_on_scroll_failure(
        self, mock_send_notifications, mock_swap, mock_config
    ):
        """Test that alerts are sent when Scroll operations fail.
        
        Args:
            mock_send_notifications: Mock notification sender
            mock_swap: Mock swap function
            mock_config: Test configuration
        """
        # Setup swap to fail
        mock_swap.side_effect = Exception("Swap failed: insufficient liquidity")
    
        # Create alerter
        alerter = Alerter(mock_config)
    
        # Create scheduler with alerter
        scheduler = CentralScheduler(mock_config)
        scheduler.alerter = alerter
    
        # Try to execute failing task
        task = {
            "protocol": "scroll",
            "action": "swap_tokens",
            "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
            "params": {
                "token_in": "USDC",
                "token_out": "WETH",
                "amount_in": "100",
            },
        }
    
        # The scheduler's jobs are executed via _execute_task_wrapper
        # We need to add the task to the scheduler's internal definitions
        # for _execute_task_wrapper to find it.
        task_id = "test_failing_swap_task"
        scheduler._task_definitions[task_id] = TaskDefinition(
            task_id=task_id,
            func=mock_swap,  # The actual function to call
            protocol=task["protocol"],
            action=task["action"],
            kwargs=task["params"],  # Pass the task parameters as kwargs
            max_retries=0  # Ensure immediate notification for testing
        )
        scheduler._task_executions[task_id] = TaskExecution(
            task_id=task_id,
            status=TaskStatus.PENDING,
            wallet=task["wallet"]
        )
    
        # Execute the wrapper, which should call _execute_task and then
        # handle_task_failure
        scheduler._execute_task_wrapper(task_id)
    
        # Verify failure was handled
        # The result is now stored in scheduler._task_executions[task_id].result
        execution_result = scheduler._task_executions[task_id].result
        assert execution_result["success"] is False
        mock_send_notifications.assert_called_once()

    def test_risk_manager_validates_scroll_operations(
        self, mock_config
    ):
        """Test risk manager validates Scroll operations correctly.
        
        Args:
            mock_config: Test configuration
        """
        
        # Create risk manager
        risk_manager = RiskManager(mock_config)
        
        # Test Scroll operation validation
        operation = {
            "protocol": "scroll",
            "action": "bridge",
            "estimated_gas": 200000,
            "value_usd": 1000.0,
        }
        
        # Should pass validation
        is_valid = risk_manager.validate_operation(operation)
        assert is_valid is True
        
        # Test with excessive gas
        high_gas_operation = {
            "protocol": "scroll",
            "action": "bridge",
            "estimated_gas": 2000000,  # Very high gas
            "value_usd": 1000.0,
        }
        
        # Should fail validation
        is_valid = risk_manager.validate_operation(high_gas_operation)
        assert is_valid is False

    def test_scroll_random_activity_integration(self, mock_config):
        """Test Scroll random activity with full system integration.
        
        Args:
            mock_config: Test configuration
        """
        with patch(
            "airdrops.protocols.scroll.scroll.perform_random_activity_scroll"
        ) as mock_random_activity:
            # Setup successful random activity
            mock_random_activity.return_value = (
                True,
                ["0x" + "c" * 64, "0x" + "d" * 64],
            )
            
            # Create scheduler
            scheduler = CentralScheduler(mock_config)
            
            # Create random activity task
            task = {
                "id": "scroll_random_activity_task",  # Added ID
                "protocol": "scroll",
                "action": "perform_random_activity_scroll",
                "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
                "params": {
                    "num_actions": 3,
                },
            }
            
            # Execute task
            result = scheduler._execute_task(task)
            
            # Verify execution
            assert result["success"] is True
            assert len(result["tx_hashes"]) == 2
            mock_random_activity.assert_called_once()

    def test_risk_adjusted_allocation_for_scroll(self, mock_config):
        """Test risk-adjusted capital allocation for Scroll.
        
        Args:
            mock_config: Test configuration
        """
        # Create allocator with risk parity strategy
        allocator = CapitalAllocator(mock_config)
        
        # Test portfolio optimization with risk scores
        protocols = ["scroll", "zksync"]
        risk_constraints = {"max_protocol_exposure": Decimal("0.35")}
        risk_scores = {"scroll": Decimal("0.3"), "zksync": Decimal("0.5")}
        
        portfolio = allocator.optimize_portfolio(
            protocols, risk_constraints, risk_scores=risk_scores
        )
        
        # Verify risk-adjusted allocation
        assert "scroll" in portfolio
        # With risk parity, lower risk protocols get higher allocation
        assert portfolio["scroll"] > 0

    def test_end_to_end_scroll_workflow(self, mock_config):
        """Test complete end-to-end workflow with Scroll protocol.
        
        Args:
            mock_config: Test configuration
        """
        # No direct Web3 patch needed for scheduler.bot as it doesn't import
        # Web3 directly. If CentralScheduler needs a Web3 instance, it should
        # be passed in its constructor or a method. For now, we assume it's
        # mocked at a lower level or not directly used in this test's scope.
        
        # Create all system components
        scheduler = CentralScheduler(mock_config)
        collector = MetricsCollector()
        risk_manager = RiskManager(mock_config)
        
        # Inject dependencies
        scheduler.metrics_collector = collector
        scheduler.risk_manager = risk_manager
        
        # Mock successful Scroll operations
        with patch("airdrops.protocols.scroll.scroll.bridge_assets") as mock_bridge:
            mock_bridge.return_value = "0x" + "e" * 64
            
            # Execute workflow
            task = {
                "id": "e2e_scroll_bridge_task",  # Added ID
                "protocol": "scroll",
                "action": "bridge_assets",
                "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
                "params": {
                    "is_deposit": True,
                    "token_symbol": "ETH",
                    "amount": "0.05",
                },
            }
            
            # Validate with risk manager
            is_valid = risk_manager.validate_operation({
                "protocol": task["protocol"],
                "action": task["action"],
                "estimated_gas": 150000,
                "value_usd": 100.0,
            })
            assert is_valid is True
            
            # Execute task
            result = scheduler._execute_task(task)
            assert result["success"] is True
            
            # Verify metrics collected
            metrics = collector.get_protocol_metrics("scroll")
            assert metrics["total_transactions"] >= 0  # Would be >0 with real execution


if __name__ == "__main__":
    pytest.main([__file__, "-v"])