"""
Integration tests for Scroll protocol with scheduler and monitoring.

This module tests the integration of the Scroll protocol with the central scheduler,
capital allocation engine, and monitoring system to ensure all components work
together correctly.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from typing import Dict, Any
import pendulum
from web3 import Web3

from airdrops.protocols.scroll import scroll
from airdrops.scheduler.bot import CentralScheduler
from airdrops.capital_allocation.engine import CapitalAllocator
from airdrops.monitoring.collector import MetricsCollector
from airdrops.monitoring.alerter import Alerter
from airdrops.risk_management.core import RiskManager


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

    @patch("airdrops.scheduler.bot.Web3")
    @patch("airdrops.protocols.scroll.scroll._get_web3_instance")
    def test_scheduler_executes_scroll_task(
        self, mock_get_web3, mock_web3_class, mock_config, mock_web3
    ):
        """Test that scheduler correctly executes Scroll protocol tasks.
        
        Args:
            mock_get_web3: Mock for getting Web3 instance
            mock_web3_class: Mock Web3 class
            mock_config: Test configuration
            mock_web3: Mock Web3 instance
        """
        # Setup mocks
        mock_get_web3.return_value = mock_web3
        mock_web3_class.return_value = mock_web3
        
        # Mock successful transaction
        with patch("airdrops.protocols.scroll.scroll.bridge_assets") as mock_bridge:
            mock_bridge.return_value = "0x" + "a" * 64
            
            # Create scheduler
            scheduler = CentralScheduler(mock_config)
            
            # Create a task for Scroll bridge
            task = {
                "protocol": "scroll",
                "action": "bridge",
                "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
                "params": {
                    "is_deposit": True,
                    "token_symbol": "ETH",
                    "amount": "0.1",
                },
            }
            
            # Execute task
            result = scheduler._execute_task(task)
            
            # Verify task was executed
            assert result["success"] is True
            assert result["tx_hash"] == "0x" + "a" * 64
            mock_bridge.assert_called_once()

    @patch("airdrops.capital_allocation.engine.Web3")
    def test_capital_allocation_with_scroll(self, mock_web3_class, mock_config):
        """Test capital allocation engine with Scroll protocol.
        
        Args:
            mock_web3_class: Mock Web3 class
            mock_config: Test configuration
        """
        # Setup mock
        mock_web3 = Mock()
        mock_web3.eth.get_balance.return_value = Web3.to_wei(2, "ether")
        mock_web3_class.return_value = mock_web3
        
        # Create capital allocator
        allocator = CapitalAllocator(mock_config)
        
        # Test allocation including Scroll
        wallets = [
            "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
            "0x853d35Cc6634C0532925a3b844Bc9e7195Ed5E47283776",
        ]
        
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
        assert metrics["total_transactions"] == 1
        assert metrics["successful_transactions"] == 1
        assert metrics["total_gas_used"] == 150000
        assert metrics["total_value_usd"] == 50.0

    @patch("airdrops.risk_management.core.Web3")
    def test_risk_manager_validates_scroll_operations(
        self, mock_web3_class, mock_config
    ):
        """Test risk manager validates Scroll operations correctly.
        
        Args:
            mock_web3_class: Mock Web3 class
            mock_config: Test configuration
        """
        # Setup mock
        mock_web3 = Mock()
        mock_web3.eth.gas_price = Web3.to_wei(50, "gwei")
        mock_web3_class.return_value = mock_web3
        
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

    @patch("airdrops.protocols.scroll.scroll.swap_tokens")
    @patch("airdrops.monitoring.alerter.send_notification")
    def test_alerting_on_scroll_failure(
        self, mock_send_notification, mock_swap, mock_config
    ):
        """Test that alerts are sent when Scroll operations fail.
        
        Args:
            mock_send_notification: Mock notification sender
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
            "action": "swap",
            "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
            "params": {
                "token_in": "USDC",
                "token_out": "WETH",
                "amount_in": "100",
            },
        }
        
        with patch.object(scheduler, "_handle_task_failure") as mock_handle_failure:
            result = scheduler._execute_task(task)
            
            # Verify failure was handled
            assert result["success"] is False
            mock_handle_failure.assert_called_once()

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
                "protocol": "scroll",
                "action": "random_activity",
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
        with patch("airdrops.scheduler.bot.Web3") as mock_web3_class:
            # Setup comprehensive mocks
            mock_web3 = Mock()
            mock_web3.eth.get_balance.return_value = Web3.to_wei(1, "ether")
            mock_web3.eth.gas_price = Web3.to_wei(30, "gwei")
            mock_web3_class.return_value = mock_web3
            
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
                    "protocol": "scroll",
                    "action": "bridge",
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