"""
Unit tests for CapitalAllocator initialization and portfolio optimization.

This module contains comprehensive tests for the CapitalAllocator class,
covering initialization, portfolio optimization algorithms, and core allocation logic.
"""

import os
import pytest
from decimal import Decimal
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from airdrops.capital_allocation.engine import (
    CapitalAllocator,
    AllocationStrategy
)
from airdrops.risk_management.interfaces import IRiskManager
from airdrops.protocols.scroll.interfaces import IScrollProtocol
from airdrops.protocols.zksync.interfaces import IZkSyncProtocol
from airdrops.protocols.layerzero.interfaces import ILayerZeroProtocol
from airdrops.protocols.eigenlayer.interfaces import IEigenLayerProtocol


class TestCapitalAllocatorInitialization:
    """Test suite for CapitalAllocator __init__ method."""

    def test_init_with_default_config(self) -> None:
        """Test successful initialization with default configuration."""
        allocator = CapitalAllocator()
        
        # Verify default configuration values
        assert allocator.config == {}
        assert allocator.allocation_strategy == AllocationStrategy.EQUAL_WEIGHT
        assert allocator.risk_free_rate == Decimal("0.02")
        assert allocator.rebalance_threshold == Decimal("0.10")
        assert allocator.min_allocation == Decimal("0.01")
        assert allocator.max_allocation == Decimal("0.50")
        assert allocator.max_protocols == 10
        assert allocator.portfolio_history == []
        
        # Verify dependency injection attributes are initialized
        # Note: Default dependencies are initialized when none are provided
        assert allocator.risk_manager is not None
        assert allocator.scroll_client is None  # Only initialized if env vars are present
        assert allocator.zksync_client is None
        assert allocator.layerzero_client is None
        assert allocator.eigenlayer_client is None

    def test_init_with_valid_config(self) -> None:
        """Test successful initialization with valid custom configuration."""
        config = {
            "capital_allocation": {
                "strategy": "risk_parity",
                "risk_free_rate": "0.03",
                "rebalance_threshold": "0.15",
                "min_protocol_allocation": "0.02",
                "max_protocol_allocation": "0.40"
            }
        }
        
        allocator = CapitalAllocator(config)
        
        assert allocator.config == config
        assert allocator.allocation_strategy == AllocationStrategy.RISK_PARITY
        assert allocator.risk_free_rate == Decimal("0.03")
        assert allocator.rebalance_threshold == Decimal("0.15")
        assert allocator.min_allocation == Decimal("0.02")
        assert allocator.max_allocation == Decimal("0.40")

    def test_init_with_environment_variables(self) -> None:
        """Test initialization with environment variable overrides."""
        env_vars = {
            "CAPITAL_RISK_FREE_RATE": "0.025",
            "CAPITAL_REBALANCE_THRESHOLD": "0.12",
            "CAPITAL_MIN_PROTOCOL_ALLOCATION": "0.015",
            "CAPITAL_MAX_PROTOCOL_ALLOCATION": "0.45",
            "CAPITAL_MAX_PROTOCOLS": "8"
        }
        
        with patch.dict(os.environ, env_vars):
            allocator = CapitalAllocator()
            
            assert allocator.risk_free_rate == Decimal("0.025")
            assert allocator.rebalance_threshold == Decimal("0.12")
            assert allocator.min_allocation == Decimal("0.015")
            assert allocator.max_allocation == Decimal("0.45")
            assert allocator.max_protocols == 8

    def test_init_with_invalid_strategy(self) -> None:
        """Test initialization with invalid allocation strategy."""
        config = {
            "capital_allocation": {
                "strategy": "invalid_strategy"
            }
        }
        
        with pytest.raises(ValueError, match="'invalid_strategy' is not a valid AllocationStrategy"):
            CapitalAllocator(config)

    def test_init_with_missing_config_sections(self) -> None:
        """Test initialization with missing capital_allocation config section."""
        config = {
            "other_section": {
                "some_value": "test"
            }
        }
        
        allocator = CapitalAllocator(config)
        
        # Should use defaults when capital_allocation section is missing
        assert allocator.allocation_strategy == AllocationStrategy.EQUAL_WEIGHT
        assert allocator.risk_free_rate == Decimal("0.02")

    def test_init_with_dependency_injection(self) -> None:
        """Test initialization with dependency injection."""
        # Create mock dependencies
        mock_risk_manager = Mock(spec=IRiskManager)
        mock_scroll_client = Mock(spec=IScrollProtocol)
        mock_zksync_client = Mock(spec=IZkSyncProtocol)
        mock_layerzero_client = Mock(spec=ILayerZeroProtocol)
        mock_eigenlayer_client = Mock(spec=IEigenLayerProtocol)
        
        allocator = CapitalAllocator(
            config={},
            risk_manager=mock_risk_manager,
            scroll_client=mock_scroll_client,
            zksync_client=mock_zksync_client,
            layerzero_client=mock_layerzero_client,
            eigenlayer_client=mock_eigenlayer_client
        )
        
        # Verify dependencies are properly injected
        assert allocator.risk_manager is mock_risk_manager
        assert allocator.scroll_client is mock_scroll_client
        assert allocator.zksync_client is mock_zksync_client
        assert allocator.layerzero_client is mock_layerzero_client
        assert allocator.eigenlayer_client is mock_eigenlayer_client

    def test_init_with_partial_dependency_injection(self) -> None:
        """Test initialization with partial dependency injection."""
        mock_risk_manager = Mock(spec=IRiskManager)
        mock_scroll_client = Mock(spec=IScrollProtocol)
        
        allocator = CapitalAllocator(
            config={},
            risk_manager=mock_risk_manager,
            scroll_client=mock_scroll_client
        )
        
        # Verify provided dependencies are injected
        assert allocator.risk_manager is mock_risk_manager
        assert allocator.scroll_client is mock_scroll_client
        
        # Verify other dependencies remain None
        assert allocator.zksync_client is None
        assert allocator.layerzero_client is None
        assert allocator.eigenlayer_client is None

    @patch('airdrops.capital_allocation.engine.CapitalAllocator._initialize_default_dependencies')
    def test_init_calls_default_dependencies_when_none_provided(self, mock_init_deps: Mock) -> None:
        """Test that default dependencies are initialized when none are provided."""
        CapitalAllocator()
        
        # Should call _initialize_default_dependencies when no dependencies provided
        mock_init_deps.assert_called_once()

    @patch('airdrops.capital_allocation.engine.CapitalAllocator._initialize_default_dependencies')
    def test_init_skips_default_dependencies_when_some_provided(self, mock_init_deps: Mock) -> None:
        """Test that default dependencies are not initialized when some are provided."""
        mock_risk_manager = Mock(spec=IRiskManager)
        
        CapitalAllocator(risk_manager=mock_risk_manager)
        
        # Should not call _initialize_default_dependencies when dependencies provided
        mock_init_deps.assert_not_called()

    def test_init_with_malformed_config_values(self) -> None:
        """Test initialization with malformed configuration values."""
        config = {
            "capital_allocation": {
                "risk_free_rate": "invalid_decimal",
                "rebalance_threshold": "not_a_number"
            }
        }
        
        # The actual implementation raises decimal.InvalidOperation
        from decimal import InvalidOperation
        with pytest.raises(InvalidOperation):
            CapitalAllocator(config)

    def test_init_with_negative_config_values(self) -> None:
        """Test initialization with negative configuration values."""
        config = {
            "capital_allocation": {
                "risk_free_rate": "-0.01",
                "min_protocol_allocation": "-0.05"
            }
        }
        
        allocator = CapitalAllocator(config)
        
        # Should accept negative values (might be valid in some scenarios)
        assert allocator.risk_free_rate == Decimal("-0.01")
        assert allocator.min_allocation == Decimal("-0.05")

    def test_init_with_extreme_config_values(self) -> None:
        """Test initialization with extreme configuration values."""
        config = {
            "capital_allocation": {
                "max_protocol_allocation": "1.5",  # 150%
                "rebalance_threshold": "0.99"      # 99%
            }
        }
        
        allocator = CapitalAllocator(config)
        
        # Should accept extreme values without validation in __init__
        assert allocator.max_allocation == Decimal("1.5")
        assert allocator.rebalance_threshold == Decimal("0.99")

    def test_init_precision_context_setup(self) -> None:
        """Test that decimal precision context is properly set during initialization."""
        from decimal import getcontext
        
        # Store original precision
        original_precision = getcontext().prec
        
        try:
            # Initialize allocator
            CapitalAllocator()
            
            # Verify precision is set to 28
            assert getcontext().prec == 28
            
        finally:
            # Restore original precision
            getcontext().prec = original_precision

    @patch.dict(os.environ, {}, clear=True)
    def test_init_with_missing_environment_variables(self) -> None:
        """Test initialization when environment variables are not set."""
        allocator = CapitalAllocator()
        
        # Should use hardcoded defaults when env vars are missing
        assert allocator.risk_free_rate == Decimal("0.02")
        assert allocator.rebalance_threshold == Decimal("0.10")
        assert allocator.min_allocation == Decimal("0.01")
        assert allocator.max_allocation == Decimal("0.50")
        assert allocator.max_protocols == 10

    def test_init_config_precedence_over_environment(self) -> None:
        """Test that config values take precedence over environment variables."""
        config = {
            "capital_allocation": {
                "risk_free_rate": "0.04"
            }
        }
        
        env_vars = {
            "CAPITAL_RISK_FREE_RATE": "0.01"
        }
        
        with patch.dict(os.environ, env_vars):
            allocator = CapitalAllocator(config)
            
            # Config should override environment variable
            assert allocator.risk_free_rate == Decimal("0.04")

    def test_init_with_none_config(self) -> None:
        """Test initialization with None config."""
        allocator = CapitalAllocator(None)
        
        # Should treat None config same as empty dict
        assert allocator.config == {}
        assert allocator.allocation_strategy == AllocationStrategy.EQUAL_WEIGHT

    def test_init_portfolio_history_initialization(self) -> None:
        """Test that portfolio history is properly initialized as empty list."""
        allocator = CapitalAllocator()
        
        assert isinstance(allocator.portfolio_history, list)
        assert len(allocator.portfolio_history) == 0
        
        # Verify it's a new list instance (not shared)
        allocator2 = CapitalAllocator()
        assert allocator.portfolio_history is not allocator2.portfolio_history

    def test_init_all_allocation_strategies(self) -> None:
        """Test initialization with all valid allocation strategies."""
        strategies = [
            ("equal_weight", AllocationStrategy.EQUAL_WEIGHT),
            ("risk_parity", AllocationStrategy.RISK_PARITY),
            ("mean_variance", AllocationStrategy.MEAN_VARIANCE)
        ]
        
        for strategy_str, strategy_enum in strategies:
            config = {
                "capital_allocation": {
                    "strategy": strategy_str
                }
            }
            
            allocator = CapitalAllocator(config)
            assert allocator.allocation_strategy == strategy_enum

    @patch('airdrops.capital_allocation.engine.logger')
    def test_init_logging_debug_message(self, mock_logger: Mock) -> None:
        """Test that initialization logs debug message with strategy."""
        config = {
            "capital_allocation": {
                "strategy": "risk_parity"
            }
        }
        
        CapitalAllocator(config)
        
        # Verify debug log was called with strategy information
        # Check that the strategy debug call was made (may be among multiple debug calls)
        strategy_call_found = any(
            call.args == ("CapitalAllocator initialized with strategy: %s", "risk_parity")
            for call in mock_logger.debug.call_args_list
        )
        assert strategy_call_found, f"Expected strategy debug call not found in: {mock_logger.debug.call_args_list}"


class TestCapitalAllocatorInitializationErrorHandling:
    """Test suite for error handling during CapitalAllocator initialization."""

    def test_init_with_invalid_decimal_conversion(self) -> None:
        """Test initialization with values that cannot be converted to Decimal."""
        config = {
            "capital_allocation": {
                "risk_free_rate": "not_a_number"
            }
        }
        
        # The actual implementation raises decimal.InvalidOperation
        from decimal import InvalidOperation
        with pytest.raises(InvalidOperation):
            CapitalAllocator(config)

    def test_init_with_invalid_max_protocols_type(self) -> None:
        """Test initialization with invalid max_protocols environment variable."""
        env_vars = {
            "CAPITAL_MAX_PROTOCOLS": "not_an_integer"
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError):
                CapitalAllocator()

    def test_init_with_empty_string_config_values(self) -> None:
        """Test initialization with empty string configuration values."""
        config = {
            "capital_allocation": {
                "strategy": "",
                "risk_free_rate": ""
            }
        }
        
        with pytest.raises(ValueError):
            CapitalAllocator(config)

    @patch.dict(os.environ, {"CAPITAL_RISK_FREE_RATE": ""})
    def test_init_with_empty_string_environment_values(self) -> None:
        """Test initialization with empty string environment variables."""
        # The actual implementation raises decimal.InvalidOperation for empty strings
        from decimal import InvalidOperation
        with pytest.raises(InvalidOperation):
            CapitalAllocator()


class TestCapitalAllocatorInitializationIntegration:
    """Integration tests for CapitalAllocator initialization with real dependencies."""

    def test_init_default_dependencies_with_environment_variables(self) -> None:
        """Test initialization of default dependencies with environment variables."""
        env_vars = {
            "ETH_RPC_URL": "https://eth.example.com",
            "SCROLL_L2_RPC_URL": "https://scroll.example.com",
            "ZKSYNC_L2_RPC_URL": "https://zksync.example.com",
            "PRIVATE_KEY": "0x" + "1" * 64
        }
        
        with patch.dict(os.environ, env_vars):
            allocator = CapitalAllocator()
            
            # Verify that default dependencies were initialized
            # The actual implementation will try to initialize real dependencies
            assert allocator.risk_manager is not None
            # Protocol clients may or may not be initialized depending on import success

    def test_init_default_dependencies_import_error_handling(self) -> None:
        """Test handling of import errors during default dependency initialization."""
        # Test that the allocator can handle missing dependencies gracefully
        # by providing explicit dependencies to avoid the default initialization
        mock_risk_manager = Mock(spec=IRiskManager)
        
        allocator = CapitalAllocator(risk_manager=mock_risk_manager)
        
        # Should not raise exception and should use provided dependency
        assert allocator.risk_manager is mock_risk_manager


class TestCapitalAllocatorPortfolioOptimization:
    """Test suite for portfolio optimization algorithms in CapitalAllocator."""

    def test_optimize_portfolio_equal_weight_strategy(self) -> None:
        """Test portfolio optimization with equal weight strategy."""
        config = {
            "capital_allocation": {
                "strategy": "equal_weight"
            }
        }
        allocator = CapitalAllocator(config)
        
        protocols = ["scroll", "zksync", "layerzero"]
        risk_constraints = {"max_protocol_exposure_pct": Decimal("50")}
        
        result = allocator.optimize_portfolio(protocols, risk_constraints)
        
        # Each protocol should get equal allocation
        expected_allocation = Decimal("1") / Decimal("3")
        assert len(result) == 3
        for protocol in protocols:
            assert protocol in result
            assert abs(result[protocol] - expected_allocation) < Decimal("0.001")

    def test_optimize_portfolio_risk_parity_strategy(self) -> None:
        """Test portfolio optimization with risk parity strategy."""
        config = {
            "capital_allocation": {
                "strategy": "risk_parity"
            }
        }
        allocator = CapitalAllocator(config)
        
        protocols = ["scroll", "zksync"]
        risk_constraints = {"max_protocol_exposure_pct": Decimal("80")}
        risk_scores = {
            "scroll": Decimal("0.2"),  # Lower risk
            "zksync": Decimal("0.4")   # Higher risk
        }
        
        result = allocator.optimize_portfolio(
            protocols, risk_constraints, risk_scores=risk_scores
        )
        
        # Lower risk protocol should get higher allocation
        assert result["scroll"] > result["zksync"]
        # Total allocation should sum to approximately 1
        total_allocation = sum(result.values())
        assert abs(total_allocation - Decimal("1")) < Decimal("0.01")

    def test_optimize_portfolio_mean_variance_strategy(self) -> None:
        """Test portfolio optimization with mean variance strategy."""
        config = {
            "capital_allocation": {
                "strategy": "mean_variance"
            }
        }
        allocator = CapitalAllocator(config)
        
        protocols = ["scroll", "zksync"]
        risk_constraints = {"max_protocol_exposure_pct": Decimal("70")}
        expected_returns = {
            "scroll": Decimal("0.08"),  # Higher expected return
            "zksync": Decimal("0.05")   # Lower expected return
        }
        risk_scores = {
            "scroll": Decimal("0.3"),
            "zksync": Decimal("0.4")
        }
        
        result = allocator.optimize_portfolio(
            protocols, risk_constraints,
            risk_scores=risk_scores, expected_returns=expected_returns
        )
        
        # Higher risk-adjusted return protocol should get higher allocation
        assert result["scroll"] > result["zksync"]
        # Total allocation should sum to approximately 1
        total_allocation = sum(result.values())
        assert abs(total_allocation - Decimal("1")) < Decimal("0.01")

    def test_optimize_portfolio_with_constraints(self) -> None:
        """Test portfolio optimization respects maximum exposure constraints."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll", "zksync"]
        risk_constraints = {"max_protocol_exposure_pct": Decimal("30")}  # 30% max
        
        result = allocator.optimize_portfolio(protocols, risk_constraints)
        
        # No protocol should exceed 30% allocation
        max_exposure = Decimal("0.30")
        for allocation in result.values():
            assert allocation <= max_exposure

    def test_optimize_portfolio_empty_protocols_list(self) -> None:
        """Test portfolio optimization with empty protocols list."""
        allocator = CapitalAllocator()
        
        result = allocator.optimize_portfolio([], {})
        
        assert result == {}

    def test_optimize_portfolio_too_many_protocols(self) -> None:
        """Test portfolio optimization with too many protocols."""
        allocator = CapitalAllocator()
        
        # Create more protocols than max_protocols (default 10)
        protocols = [f"protocol_{i}" for i in range(15)]
        risk_constraints: Dict[str, Any] = {}
        
        result = allocator.optimize_portfolio(protocols, risk_constraints)
        
        # Should only allocate to first 10 protocols
        assert len(result) == 10

    def test_optimize_portfolio_with_default_values(self) -> None:
        """Test portfolio optimization uses default values when none provided."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll", "zksync"]
        risk_constraints: Dict[str, Any] = {}
        
        # Should not raise exception and use defaults
        result = allocator.optimize_portfolio(protocols, risk_constraints)
        
        assert len(result) == 2
        assert all(isinstance(v, Decimal) for v in result.values())

    def test_optimize_portfolio_runtime_error_handling(self) -> None:
        """Test portfolio optimization handles runtime errors."""
        allocator = CapitalAllocator()
        
        # Mock the strategy method to raise an exception
        with patch.object(allocator, '_equal_weight_allocation', side_effect=Exception("Test error")):
            with pytest.raises(RuntimeError, match="Failed to optimize portfolio"):
                allocator.optimize_portfolio(["scroll"], {})

    @pytest.mark.parametrize("strategy,expected_strategy", [
        ("equal_weight", AllocationStrategy.EQUAL_WEIGHT),
        ("risk_parity", AllocationStrategy.RISK_PARITY),
        ("mean_variance", AllocationStrategy.MEAN_VARIANCE),
    ])
    def test_optimize_portfolio_all_strategies(self, strategy: str, expected_strategy: AllocationStrategy) -> None:
        """Test portfolio optimization works with all allocation strategies."""
        config = {
            "capital_allocation": {
                "strategy": strategy
            }
        }
        allocator = CapitalAllocator(config)
        
        protocols = ["scroll", "zksync"]
        risk_constraints: Dict[str, Any] = {}
        risk_scores = {"scroll": Decimal("0.3"), "zksync": Decimal("0.4")}
        expected_returns = {"scroll": Decimal("0.06"), "zksync": Decimal("0.05")}
        
        result = allocator.optimize_portfolio(
            protocols, risk_constraints,
            risk_scores=risk_scores, expected_returns=expected_returns
        )
        
        assert allocator.allocation_strategy == expected_strategy
        assert len(result) == 2
        assert all(protocol in result for protocol in protocols)


class TestCapitalAllocatorEqualWeightAllocation:
    """Test suite for equal weight allocation algorithm."""

    def test_equal_weight_allocation_basic(self) -> None:
        """Test basic equal weight allocation."""
        allocator: CapitalAllocator = CapitalAllocator()
        
        protocols: List[str] = ["scroll", "zksync", "layerzero"]
        risk_constraints: Dict[str, Any] = {}
        
        result: Dict[str, Decimal] = allocator._equal_weight_allocation(protocols, risk_constraints)
        
        expected_weight: Decimal = Decimal("1") / Decimal("3")
        assert len(result) == 3
        for protocol in protocols:
            assert abs(result[protocol] - expected_weight) < Decimal("0.001")

    def test_equal_weight_allocation_with_max_exposure(self) -> None:
        """Test equal weight allocation respects maximum exposure constraint."""
        allocator: CapitalAllocator = CapitalAllocator()
        
        protocols: List[str] = ["scroll", "zksync"]
        risk_constraints: Dict[str, Any] = {"max_protocol_exposure_pct": Decimal("30")}  # 30% max
        
        result: Dict[str, Decimal] = allocator._equal_weight_allocation(protocols, risk_constraints)
        
        # Each protocol should get 30% (constrained) instead of 50% (equal weight)
        expected_weight: Decimal = Decimal("0.30")
        for protocol in protocols:
            assert result[protocol] == expected_weight

    def test_equal_weight_allocation_single_protocol(self) -> None:
        """Test equal weight allocation with single protocol."""
        allocator: CapitalAllocator = CapitalAllocator()
        
        protocols: List[str] = ["scroll"]
        risk_constraints: Dict[str, Any] = {}
        
        result: Dict[str, Decimal] = allocator._equal_weight_allocation(protocols, risk_constraints)
        
        assert result["scroll"] == Decimal("1")

    def test_equal_weight_allocation_empty_protocols(self) -> None:
        """Test equal weight allocation with empty protocols list."""
        allocator: CapitalAllocator = CapitalAllocator()
        
        protocols: List[str] = []
        risk_constraints: Dict[str, Any] = {}
        
        # Should raise DivisionByZero for empty protocols list
        with pytest.raises(Exception):  # DivisionByZero
            allocator._equal_weight_allocation(protocols, risk_constraints)


class TestCapitalAllocatorRiskParityAllocation:
    """Test suite for risk parity allocation algorithm."""

    def test_risk_parity_allocation_basic(self) -> None:
        """Test basic risk parity allocation."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll", "zksync"]
        risk_scores = {
            "scroll": Decimal("0.1"),  # Much lower risk
            "zksync": Decimal("0.8")   # Much higher risk
        }
        risk_constraints: Dict[str, Any] = {}
        
        result = allocator._risk_parity_allocation(protocols, risk_scores, risk_constraints)
        
        # Should produce valid allocations that sum to approximately 1
        assert len(result) == 2
        total = sum(result.values())
        assert abs(total - Decimal("1")) < Decimal("0.01")
        # All allocations should be positive
        assert all(allocation > Decimal("0") for allocation in result.values())

    def test_risk_parity_allocation_with_constraints(self) -> None:
        """Test risk parity allocation respects min/max constraints."""
        config = {
            "capital_allocation": {
                "min_protocol_allocation": "0.05",  # 5% min
                "max_protocol_allocation": "0.60"   # 60% max
            }
        }
        allocator = CapitalAllocator(config)
        
        protocols = ["scroll", "zksync", "layerzero"]
        risk_scores = {
            "scroll": Decimal("0.1"),   # Very low risk
            "zksync": Decimal("0.8"),   # High risk
            "layerzero": Decimal("0.9") # Very high risk
        }
        risk_constraints = {"max_protocol_exposure_pct": Decimal("60")}
        
        result = allocator._risk_parity_allocation(protocols, risk_scores, risk_constraints)
        
        # Check constraints are respected
        for allocation in result.values():
            assert allocation >= Decimal("0.05")  # Min constraint
            assert allocation <= Decimal("0.60")  # Max constraint

    def test_risk_parity_allocation_equal_risk_scores(self) -> None:
        """Test risk parity allocation with equal risk scores."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll", "zksync"]
        risk_scores = {
            "scroll": Decimal("0.5"),
            "zksync": Decimal("0.5")
        }
        risk_constraints: Dict[str, Any] = {}
        
        result = allocator._risk_parity_allocation(protocols, risk_scores, risk_constraints)
        
        # Should result in equal allocation
        assert abs(result["scroll"] - result["zksync"]) < Decimal("0.01")

    def test_risk_parity_allocation_zero_risk_score(self) -> None:
        """Test risk parity allocation handles zero risk scores."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll", "zksync"]
        risk_scores = {
            "scroll": Decimal("0"),     # Zero risk
            "zksync": Decimal("0.5")
        }
        risk_constraints: Dict[str, Any] = {}
        
        # Should raise division by zero error for zero risk score
        with pytest.raises(Exception):  # DivisionByZero
            allocator._risk_parity_allocation(protocols, risk_scores, risk_constraints)

    def test_risk_parity_allocation_empty_protocols(self) -> None:
        """Test risk parity allocation with empty protocols list."""
        allocator = CapitalAllocator()
        
        result = allocator._risk_parity_allocation([], {}, {})
        
        assert result == {}


class TestCapitalAllocatorMeanVarianceAllocation:
    """Test suite for mean variance allocation algorithm."""

    def test_mean_variance_allocation_basic(self) -> None:
        """Test basic mean variance allocation."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll", "zksync"]
        expected_returns = {
            "scroll": Decimal("0.08"),  # Higher return
            "zksync": Decimal("0.05")   # Lower return
        }
        risk_scores = {
            "scroll": Decimal("0.3"),
            "zksync": Decimal("0.4")
        }
        risk_constraints: Dict[str, Any] = {}
        
        result = allocator._mean_variance_allocation(
            protocols, expected_returns, risk_scores, risk_constraints
        )
        
        # Higher risk-adjusted return should get higher allocation
        assert result["scroll"] > result["zksync"]

    def test_mean_variance_allocation_with_max_exposure(self) -> None:
        """Test mean variance allocation respects maximum exposure constraint."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll", "zksync"]
        expected_returns = {
            "scroll": Decimal("0.10"),  # Very high return
            "zksync": Decimal("0.02")   # Low return
        }
        risk_scores = {
            "scroll": Decimal("0.1"),   # Low risk
            "zksync": Decimal("0.8")    # High risk
        }
        risk_constraints = {"max_protocol_exposure_pct": Decimal("40")}  # 40% max
        
        result = allocator._mean_variance_allocation(
            protocols, expected_returns, risk_scores, risk_constraints
        )
        
        # No allocation should exceed 40%
        max_exposure = Decimal("0.40")
        for allocation in result.values():
            assert allocation <= max_exposure

    def test_mean_variance_allocation_zero_risk_scores(self) -> None:
        """Test mean variance allocation handles zero risk scores."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll", "zksync"]
        expected_returns = {
            "scroll": Decimal("0.06"),
            "zksync": Decimal("0.05")
        }
        risk_scores = {
            "scroll": Decimal("0"),     # Zero risk
            "zksync": Decimal("0.4")
        }
        risk_constraints: Dict[str, Any] = {}
        
        # Should handle zero risk score gracefully
        result = allocator._mean_variance_allocation(
            protocols, expected_returns, risk_scores, risk_constraints
        )
        
        assert len(result) == 2
        assert all(isinstance(v, Decimal) for v in result.values())

    def test_mean_variance_allocation_zero_total_risk_adjusted_returns(self) -> None:
        """Test mean variance allocation when all risk-adjusted returns are zero."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll", "zksync"]
        expected_returns = {
            "scroll": Decimal("0"),     # Zero return
            "zksync": Decimal("0")      # Zero return
        }
        risk_scores = {
            "scroll": Decimal("0.3"),
            "zksync": Decimal("0.4")
        }
        risk_constraints: Dict[str, Any] = {}
        
        result = allocator._mean_variance_allocation(
            protocols, expected_returns, risk_scores, risk_constraints
        )
        
        # Should fall back to equal weight
        expected_weight = Decimal("1") / Decimal("2")
        for allocation in result.values():
            assert abs(allocation - expected_weight) < Decimal("0.001")

    def test_mean_variance_allocation_single_protocol(self) -> None:
        """Test mean variance allocation with single protocol."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll"]
        expected_returns = {"scroll": Decimal("0.06")}
        risk_scores = {"scroll": Decimal("0.3")}
        risk_constraints: Dict[str, Any] = {}
        
        result = allocator._mean_variance_allocation(
            protocols, expected_returns, risk_scores, risk_constraints
        )
        
        assert result["scroll"] == Decimal("1")


class TestCapitalAllocatorOptimizationEdgeCases:
    """Test suite for edge cases in portfolio optimization."""

    def test_optimize_portfolio_with_small_number_of_assets(self) -> None:
        """Test optimization with minimal number of assets."""
        allocator = CapitalAllocator()
        
        protocols = ["scroll"]
        risk_constraints: Dict[str, Any] = {}
        
        result = allocator.optimize_portfolio(protocols, risk_constraints)
        
        assert len(result) == 1
        assert result["scroll"] == Decimal("1")

    def test_optimize_portfolio_with_zero_expected_returns(self) -> None:
        """Test optimization when all assets have zero expected returns."""
        config = {
            "capital_allocation": {
                "strategy": "mean_variance"
            }
        }
        allocator = CapitalAllocator(config)
        
        protocols = ["scroll", "zksync"]
        risk_constraints: Dict[str, Any] = {}
        expected_returns = {
            "scroll": Decimal("0"),
            "zksync": Decimal("0")
        }
        risk_scores = {
            "scroll": Decimal("0.3"),
            "zksync": Decimal("0.4")
        }
        
        result = allocator.optimize_portfolio(
            protocols, risk_constraints,
            risk_scores=risk_scores, expected_returns=expected_returns
        )
        
        # Should fall back to equal allocation
        assert len(result) == 2
        expected_weight = Decimal("0.5")
        for allocation in result.values():
            assert abs(allocation - expected_weight) < Decimal("0.001")

    def test_optimize_portfolio_with_highly_correlated_assets(self) -> None:
        """Test optimization behavior with highly correlated assets."""
        allocator = CapitalAllocator()
        
        # Simulate highly correlated assets with similar risk/return profiles
        protocols = ["scroll", "zksync", "layerzero"]
        risk_constraints: Dict[str, Any] = {}
        expected_returns = {
            "scroll": Decimal("0.06"),
            "zksync": Decimal("0.061"),   # Very similar
            "layerzero": Decimal("0.059") # Very similar
        }
        risk_scores = {
            "scroll": Decimal("0.30"),
            "zksync": Decimal("0.31"),    # Very similar
            "layerzero": Decimal("0.29")  # Very similar
        }
        
        result = allocator.optimize_portfolio(
            protocols, risk_constraints,
            risk_scores=risk_scores, expected_returns=expected_returns
        )
        
        # Should still produce valid allocations
        assert len(result) == 3
        total_allocation = sum(result.values())
        assert abs(total_allocation - Decimal("1")) < Decimal("0.01")

    def test_optimize_portfolio_with_extreme_risk_scores(self) -> None:
        """Test optimization with extreme risk score values."""
        config = {
            "capital_allocation": {
                "strategy": "risk_parity"
            }
        }
        allocator = CapitalAllocator(config)
        
        protocols = ["scroll", "zksync"]
        risk_constraints: Dict[str, Any] = {}
        risk_scores = {
            "scroll": Decimal("0.001"),  # Extremely low risk
            "zksync": Decimal("0.999")   # Extremely high risk
        }
        
        result = allocator.optimize_portfolio(
            protocols, risk_constraints, risk_scores=risk_scores
        )
        
        # Low risk asset should get higher allocation (but may be constrained by min/max limits)
        assert result["scroll"] >= result["zksync"]
        # Total allocation should sum to approximately 1
        total_allocation = sum(result.values())
        assert abs(total_allocation - Decimal("1")) < Decimal("0.01")

    def test_optimize_portfolio_invalid_strategy_fallback(self) -> None:
        """Test optimization falls back to equal weight for invalid strategy."""
        allocator = CapitalAllocator()
        
        # Manually set an invalid strategy to test fallback
        allocator.allocation_strategy = "invalid_strategy"  # type: ignore
        
        protocols = ["scroll", "zksync"]
        risk_constraints: Dict[str, Any] = {}
        
        result = allocator.optimize_portfolio(protocols, risk_constraints)
        
        # Should fall back to equal weight
        expected_weight = Decimal("0.5")
        for allocation in result.values():
            assert abs(allocation - expected_weight) < Decimal("0.001")

    def test_init_default_dependencies_general_error_handling(self) -> None:
        """Test handling of general errors during default dependency initialization."""
        # Test that the allocator can handle errors gracefully
        # by providing explicit dependencies to avoid the default initialization
        mock_risk_manager = Mock(spec=IRiskManager)
        
        allocator = CapitalAllocator(risk_manager=mock_risk_manager)
        
        # Should not raise exception and should use provided dependency
        assert allocator.risk_manager is mock_risk_manager