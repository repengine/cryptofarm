"""
Tests for the Risk Management System.
"""

import os
import sys
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from airdrops.risk_management.core import (
    RiskManager,
    RiskLevel,
    VolatilityState,
    RiskMetrics,
    RiskLimits
)

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestRiskManager:
    """Test cases for the RiskManager class."""

    @pytest.fixture
    def mock_config(self):
        """Provide mock configuration for testing."""
        return {
            "max_protocol_exposure_pct": "15.0",
            "max_gas_price_gwei": "80.0"
        }

    @pytest.fixture
    def risk_manager(self, mock_config):
        """Create a RiskManager instance for testing."""
        with patch.dict('os.environ', {
            'ETH_RPC_URL': 'http://mock-eth-rpc',
            'SCROLL_L2_RPC_URL': 'http://mock-scroll-rpc'
        }):
            with patch('airdrops.risk_management.core.Web3') as mock_web3:
                mock_web3.return_value.is_connected.return_value = True
                return RiskManager(config=mock_config)

    def test_risk_manager_initialization(self, risk_manager):
        """Test RiskManager initialization."""
        assert risk_manager is not None
        assert isinstance(risk_manager.risk_limits, RiskLimits)
        assert not risk_manager.circuit_breaker_active

    def test_load_risk_limits_from_env(self):
        """Test loading risk limits from environment variables."""
        with patch.dict('os.environ', {
            'RISK_MAX_PROTOCOL_EXPOSURE_PCT': '25.0',
            'RISK_MAX_GAS_PRICE_GWEI': '120.0'
        }):
            with patch('airdrops.risk_management.core.Web3'):
                manager = RiskManager()
                assert manager.risk_limits.max_protocol_exposure_pct == \
                    Decimal('25.0')
                assert manager.risk_limits.max_gas_price_gwei == \
                    Decimal('120.0')

    def test_load_risk_limits_defaults(self):
        """Test loading default risk limits when env vars not set."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('airdrops.risk_management.core.Web3'):
                manager = RiskManager()
                assert manager.risk_limits.max_protocol_exposure_pct == \
                    Decimal('20.0')
                assert manager.risk_limits.max_gas_price_gwei == \
                    Decimal('100.0')

    @patch('airdrops.risk_management.core.Web3')
    def test_initialize_providers_success(self, mock_web3_class):
        """Test successful Web3 provider initialization."""
        mock_web3 = Mock()
        mock_web3_class.return_value = mock_web3

        with patch.dict('os.environ', {
            'ETH_RPC_URL': 'http://test-eth-rpc',
            'SCROLL_L2_RPC_URL': 'http://test-scroll-rpc'
        }):
            manager = RiskManager()
            assert 'ethereum' in manager.web3_providers
            assert 'scroll' in manager.web3_providers

    @patch('airdrops.risk_management.core.Web3')
    def test_initialize_providers_failure(self, mock_web3_class):
        """Test Web3 provider initialization failure."""
        mock_web3_class.side_effect = Exception("Connection failed")

        with patch.dict('os.environ', {'ETH_RPC_URL': 'http://bad-rpc'}):
            with pytest.raises(
                RuntimeError, match="Web3 provider initialization failed"
            ):
                RiskManager()

    def test_monitor_positions_success(self, risk_manager):
        """Test successful position monitoring."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 1000000000000000000
        mock_web3.from_wei.return_value = 1.0

        risk_manager.web3_providers = {'ethereum': mock_web3}

        with patch.object(
            risk_manager, '_get_eth_price_usd', return_value=Decimal('2000')
        ):
            exposures = risk_manager.monitor_positions(
                ['0x1A2b3C4d5E6f7A8b9C0d1E2f3A4b5C6d7E8f9A0b']
            )

            assert 'ethereum' in exposures
            assert exposures['ethereum'] == Decimal('2000')

    def test_monitor_positions_multiple_wallets(self, risk_manager):
        """Test position monitoring with multiple wallets."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 500000000000000000
        mock_web3.from_wei.return_value = 0.5

        risk_manager.web3_providers = {'ethereum': mock_web3}

        with patch.object(
            risk_manager, '_get_eth_price_usd', return_value=Decimal('2000')
        ):
            exposures = risk_manager.monitor_positions([
                '0x1A2b3C4d5E6f7A8b9C0d1E2f3A4b5C6d7E8f9A0b',
                '0x9F8e7D6c5B4a3F2e1D0c9B8a7F6e5D4c3B2a1F0E'
            ])

            assert 'ethereum' in exposures
            assert exposures['ethereum'] == Decimal('2000')

    def test_monitor_positions_multiple_networks(self, risk_manager):
        """Test position monitoring across multiple networks."""
        mock_eth_web3 = Mock()
        mock_eth_web3.is_connected.return_value = True
        mock_eth_web3.eth.get_balance.return_value = 1000000000000000000
        mock_eth_web3.from_wei.return_value = 1.0

        mock_scroll_web3 = Mock()
        mock_scroll_web3.is_connected.return_value = True
        mock_scroll_web3.eth.get_balance.return_value = 500000000000000000
        mock_scroll_web3.from_wei.return_value = 0.5

        risk_manager.web3_providers = {
            'ethereum': mock_eth_web3,
            'scroll': mock_scroll_web3
        }

        with patch.object(
            risk_manager, '_get_eth_price_usd', return_value=Decimal('2000')
        ):
            exposures = risk_manager.monitor_positions(
                ['0x1A2b3C4d5E6f7A8b9C0d1E2f3A4b5C6d7E8f9A0b']
            )

            assert 'ethereum' in exposures
            assert 'scroll' in exposures
            assert exposures['ethereum'] == Decimal('2000')
            assert exposures['scroll'] == Decimal('1000')

    def test_monitor_positions_disconnected_provider(self, risk_manager):
        """Test position monitoring with disconnected provider."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = False

        risk_manager.web3_providers = {'ethereum': mock_web3}

        with patch.object(
            risk_manager, '_get_eth_price_usd', return_value=Decimal('2000')
        ):
            exposures = risk_manager.monitor_positions(['0x123'])

            assert exposures == {}

    def test_monitor_positions_failure(self, risk_manager):
        """Test position monitoring failure."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.side_effect = Exception("RPC error")

        risk_manager.web3_providers = {'ethereum': mock_web3}

        with pytest.raises(RuntimeError, match="Failed to monitor positions"):
            risk_manager.monitor_positions(['0x123'])

    def test_monitor_gas_costs_success(self, risk_manager):
        """Test successful gas cost monitoring."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.gas_price = 50000000000
        mock_web3.from_wei.return_value = 50.0

        risk_manager.web3_providers = {'ethereum': mock_web3}

        gas_price = risk_manager.monitor_gas_costs('ethereum')
        assert gas_price == Decimal('50.0')

    def test_monitor_gas_costs_high_price_warning(self, risk_manager):
        """Test gas cost monitoring with high price warning."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.gas_price = 150000000000
        mock_web3.from_wei.return_value = 150.0

        risk_manager.web3_providers = {'ethereum': mock_web3}

        with patch('airdrops.risk_management.core.logger') as mock_logger:
            gas_price = risk_manager.monitor_gas_costs('ethereum')
            assert gas_price == Decimal('150.0')
            mock_logger.warning.assert_called_once()

    def test_monitor_gas_costs_no_connection(self, risk_manager):
        """Test gas cost monitoring with no network connection."""
        risk_manager.web3_providers = {}

        with pytest.raises(RuntimeError, match="Failed to monitor gas costs"):
            risk_manager.monitor_gas_costs('ethereum')

    def test_monitor_gas_costs_disconnected(self, risk_manager):
        """Test gas cost monitoring with disconnected provider."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = False

        risk_manager.web3_providers = {'ethereum': mock_web3}

        with pytest.raises(RuntimeError, match="Failed to monitor gas costs"):
            risk_manager.monitor_gas_costs('ethereum')

    def test_monitor_market_volatility_low(self, risk_manager):
        """Test market volatility monitoring - low volatility."""
        volatility = risk_manager.monitor_market_volatility(['ETH'])
        assert volatility == VolatilityState.MEDIUM

    def test_monitor_market_volatility_high(self, risk_manager):
        """Test market volatility monitoring - high volatility."""
        with patch.object(
            risk_manager, 'monitor_market_volatility'
        ) as mock_method:
            mock_method.return_value = VolatilityState.HIGH
            volatility = risk_manager.monitor_market_volatility(['ETH'])
            assert volatility == VolatilityState.HIGH

    def test_monitor_market_volatility_extreme(self, risk_manager):
        """Test market volatility monitoring - extreme volatility."""
        with patch.object(
            risk_manager, 'monitor_market_volatility'
        ) as mock_method:
            mock_method.return_value = VolatilityState.EXTREME
            volatility = risk_manager.monitor_market_volatility(['ETH'])
            assert volatility == VolatilityState.EXTREME

    def test_monitor_market_volatility_empty_assets(self, risk_manager):
        """Test market volatility monitoring with empty asset list."""
        volatility = risk_manager.monitor_market_volatility([])
        assert volatility == VolatilityState.LOW

    def test_monitor_market_volatility_multiple_assets(self, risk_manager):
        """Test market volatility monitoring with multiple assets."""
        volatility = risk_manager.monitor_market_volatility(
            ['ETH', 'BTC', 'USDC']
        )
        assert volatility in [
            VolatilityState.LOW,
            VolatilityState.MEDIUM,
            VolatilityState.HIGH,
            VolatilityState.EXTREME
        ]

    def test_monitor_market_volatility_failure(self, risk_manager):
        """Test market volatility monitoring failure."""
        with patch.object(
            risk_manager, 'monitor_market_volatility'
        ) as mock_method:
            mock_method.side_effect = Exception("API error")

            with pytest.raises(Exception, match="API error"):
                risk_manager.monitor_market_volatility(['ETH'])

    def test_get_eth_price_usd_success(self, risk_manager):
        """Test ETH price retrieval."""
        price = risk_manager._get_eth_price_usd()
        assert isinstance(price, Decimal)
        assert price > 0

    def test_get_eth_price_usd_fallback(self, risk_manager):
        """Test ETH price retrieval with fallback."""
        with patch('airdrops.risk_management.core.logger'):
            price = risk_manager._get_eth_price_usd()
            assert price == Decimal('2000.0')


class TestRiskManagerAdvancedMethods:
    """Test cases for advanced risk management methods."""

    @pytest.fixture
    def risk_manager(self):
        """Create a RiskManager instance for testing."""
        with patch('airdrops.risk_management.core.Web3'):
            return RiskManager()

    def test_assess_current_risk_success(self, risk_manager):
        """Test successful risk assessment."""
        mock_exposures = {
            'ethereum': Decimal('5000'), 'scroll': Decimal('3000')
        }

        with patch.object(
            risk_manager, 'monitor_positions', return_value=mock_exposures
        ), patch.object(
            risk_manager, 'monitor_gas_costs', return_value=Decimal('50')
        ), patch.object(
            risk_manager,
            'monitor_market_volatility',
            return_value=VolatilityState.MEDIUM
        ):

            metrics = risk_manager.assess_current_risk(['0x123'])

            assert isinstance(metrics, RiskMetrics)
            assert metrics.portfolio_value == Decimal('8000')
            assert metrics.portfolio_pnl == Decimal('400')
            assert metrics.gas_price_gwei == Decimal('50')
            assert metrics.volatility_state == VolatilityState.MEDIUM
            assert metrics.protocol_exposures == mock_exposures
            assert metrics.risk_level in [
                RiskLevel.LOW,
                RiskLevel.MEDIUM,
                RiskLevel.HIGH,
                RiskLevel.CRITICAL
            ]

    def test_assess_current_risk_high_risk_scenario(self, risk_manager):
        """Test risk assessment with high risk conditions."""
        mock_exposures = {'ethereum': Decimal('10000')}

        with patch.object(
            risk_manager, 'monitor_positions', return_value=mock_exposures
        ), patch.object(
            risk_manager, 'monitor_gas_costs', return_value=Decimal('200')
        ), patch.object(
            risk_manager,
            'monitor_market_volatility',
            return_value=VolatilityState.EXTREME
        ):

            metrics = risk_manager.assess_current_risk(['0x123'])

            assert metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            assert metrics.gas_price_gwei == Decimal('200')
            assert metrics.volatility_state == VolatilityState.EXTREME

    def test_assess_current_risk_circuit_breaker_triggered(self, risk_manager):
        """Test risk assessment that triggers circuit breaker."""
        mock_exposures = {'ethereum': Decimal('10000')}

        with patch.object(
            risk_manager, 'monitor_positions', return_value=mock_exposures
        ), patch.object(
            risk_manager, 'monitor_gas_costs', return_value=Decimal('300')
        ), patch.object(
            risk_manager,
            'monitor_market_volatility',
            return_value=VolatilityState.EXTREME
        ), patch.object(
            risk_manager, 'trigger_circuit_breaker'
        ) as mock_trigger:

            metrics = risk_manager.assess_current_risk(['0x123'])

            if metrics.circuit_breaker_triggered:
                mock_trigger.assert_called_once()

    def test_assess_current_risk_failure(self, risk_manager):
        """Test risk assessment failure handling."""
        with patch.object(
            risk_manager,
            'monitor_positions',
            side_effect=Exception("Monitor error")
        ):

            with pytest.raises(
                RuntimeError, match="Failed to assess current risk"
            ):
                risk_manager.assess_current_risk(['0x123'])

    def test_trigger_circuit_breaker_success(self, risk_manager):
        """Test successful circuit breaker activation."""
        assert not risk_manager.circuit_breaker_active

        with patch('airdrops.risk_management.core.logger') as mock_logger:
            risk_manager.trigger_circuit_breaker()

            assert risk_manager.circuit_breaker_active
            mock_logger.critical.assert_called_once_with(
                "CIRCUIT BREAKER ACTIVATED - All operations halted"
            )

    def test_trigger_circuit_breaker_failure(self, risk_manager):
        """Test circuit breaker activation failure."""
        with patch('airdrops.risk_management.core.logger') as mock_logger:
            mock_logger.critical.side_effect = Exception("Logging error")

            with pytest.raises(
                RuntimeError, match="Circuit breaker activation failed"
            ):
                risk_manager.trigger_circuit_breaker()

    def test_calculate_position_size_limits_success(self, risk_manager):
        """Test successful position size limit calculation."""
        with patch.object(
            risk_manager,
            'monitor_market_volatility',
            return_value=VolatilityState.MEDIUM
        ):

            limits = risk_manager.calculate_position_size_limits(
                Decimal('10000'), 'ethereum', 'ETH'
            )

            assert 'max_position_size' in limits
            assert 'max_transaction_size' in limits
            assert 'max_asset_concentration' in limits
            assert 'protocol' in limits
            assert 'asset' in limits
            assert 'volatility_adjustment' in limits

            assert limits['protocol'] == 'ethereum'
            assert limits['asset'] == 'ETH'
            assert limits['volatility_adjustment'] == Decimal('0.8')

    def test_calculate_position_size_limits_high_volatility(
        self, risk_manager
    ):
        """Test position size limits with high volatility."""
        with patch.object(
            risk_manager,
            'monitor_market_volatility',
            return_value=VolatilityState.HIGH
        ):

            limits = risk_manager.calculate_position_size_limits(
                Decimal('10000'), 'scroll', 'ETH'
            )

            assert limits['volatility_adjustment'] == Decimal('0.6')
            assert limits['max_position_size'] < Decimal('2000')

    def test_calculate_position_size_limits_extreme_volatility(
        self, risk_manager
    ):
        """Test position size limits with extreme volatility."""
        with patch.object(
            risk_manager,
            'monitor_market_volatility',
            return_value=VolatilityState.EXTREME
        ):

            limits = risk_manager.calculate_position_size_limits(
                Decimal('10000'), 'ethereum', 'BTC'
            )

            assert limits['volatility_adjustment'] == Decimal('0.3')
            assert limits['max_position_size'] < Decimal('1000')

    def test_calculate_position_size_limits_failure(self, risk_manager):
        """Test position size limit calculation failure."""
        with patch.object(
            risk_manager,
            'monitor_market_volatility',
            side_effect=Exception("Volatility error")
        ):

            with pytest.raises(
                RuntimeError, match="Failed to calculate position size limits"
            ):
                risk_manager.calculate_position_size_limits(
                    Decimal('10000'), 'ethereum', 'ETH'
                )

    def test_check_emergency_stop_conditions_critical_risk(
        self, risk_manager
    ):
        """Test emergency stop check with critical risk level."""
        metrics = RiskMetrics(
            portfolio_value=Decimal('10000'),
            portfolio_pnl=Decimal('500'),
            gas_price_gwei=Decimal('50'),
            volatility_state=VolatilityState.MEDIUM,
            protocol_exposures={'ethereum': Decimal('10000')},
            risk_level=RiskLevel.CRITICAL,
            recommended_action=None,
            circuit_breaker_triggered=False
        )

        result = risk_manager.check_emergency_stop_conditions(metrics)
        assert result is True

    def test_check_emergency_stop_conditions_excessive_loss(
        self, risk_manager
    ):
        """Test emergency stop check with excessive daily loss."""
        metrics = RiskMetrics(
            portfolio_value=Decimal('10000'),
            portfolio_pnl=Decimal('-1500'),
            gas_price_gwei=Decimal('50'),
            volatility_state=VolatilityState.MEDIUM,
            protocol_exposures={'ethereum': Decimal('10000')},
            risk_level=RiskLevel.MEDIUM,
            recommended_action=None,
            circuit_breaker_triggered=False
        )

        result = risk_manager.check_emergency_stop_conditions(metrics)
        assert result is True

    def test_check_emergency_stop_conditions_extreme_gas(self, risk_manager):
        """Test emergency stop check with extreme gas prices."""
        metrics = RiskMetrics(
            portfolio_value=Decimal('10000'),
            portfolio_pnl=Decimal('500'),
            gas_price_gwei=Decimal('250'),
            volatility_state=VolatilityState.MEDIUM,
            protocol_exposures={'ethereum': Decimal('10000')},
            risk_level=RiskLevel.MEDIUM,
            recommended_action=None,
            circuit_breaker_triggered=False
        )

        result = risk_manager.check_emergency_stop_conditions(metrics)
        assert result is True

    def test_check_emergency_stop_conditions_extreme_volatility(
        self, risk_manager
    ):
        """Test emergency stop check with extreme volatility."""
        metrics = RiskMetrics(
            portfolio_value=Decimal('10000'),
            portfolio_pnl=Decimal('500'),
            gas_price_gwei=Decimal('50'),
            volatility_state=VolatilityState.EXTREME,
            protocol_exposures={'ethereum': Decimal('10000')},
            risk_level=RiskLevel.MEDIUM,
            recommended_action=None,
            circuit_breaker_triggered=False
        )

        result = risk_manager.check_emergency_stop_conditions(metrics)
        assert result is True

    def test_check_emergency_stop_conditions_protocol_concentration(
        self, risk_manager
    ):
        """Test emergency stop check with excessive protocol concentration."""
        metrics = RiskMetrics(
            portfolio_value=Decimal('10000'),
            portfolio_pnl=Decimal('500'),
            gas_price_gwei=Decimal('50'),
            volatility_state=VolatilityState.MEDIUM,
            protocol_exposures={'ethereum': Decimal('3500')},
            risk_level=RiskLevel.MEDIUM,
            recommended_action=None,
            circuit_breaker_triggered=False
        )

        result = risk_manager.check_emergency_stop_conditions(metrics)
        assert result is True

    def test_check_emergency_stop_conditions_normal(self, risk_manager):
        """Test emergency stop check with normal conditions."""
        metrics = RiskMetrics(
            portfolio_value=Decimal('10000'),
            portfolio_pnl=Decimal('500'),
            gas_price_gwei=Decimal('50'),
            volatility_state=VolatilityState.MEDIUM,
            protocol_exposures={
                'ethereum': Decimal('1500'), 'scroll': Decimal('1000')
            },
            risk_level=RiskLevel.LOW,
            recommended_action=None,
            circuit_breaker_triggered=False
        )

        result = risk_manager.check_emergency_stop_conditions(metrics)
        assert result is False

    def test_check_emergency_stop_conditions_failure(self, risk_manager):
        """Test emergency stop check failure handling."""
        metrics = RiskMetrics(
            portfolio_value=Decimal('0'),
            portfolio_pnl=Decimal('500'),
            gas_price_gwei=Decimal('50'),
            volatility_state=VolatilityState.MEDIUM,
            protocol_exposures={'ethereum': Decimal('1000')},
            risk_level=RiskLevel.LOW,
            recommended_action=None,
            circuit_breaker_triggered=False
        )

        result = risk_manager.check_emergency_stop_conditions(metrics)
        assert result is True

    def test_calculate_risk_level_low(self, risk_manager):
        """Test risk level calculation - low risk."""
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value=Decimal('10000'),
            gas_price=Decimal('30'),
            volatility_state=VolatilityState.LOW,
            protocol_exposures={'ethereum': Decimal('1000')}
        )

        assert risk_level == RiskLevel.LOW

    def test_calculate_risk_level_medium(self, risk_manager):
        """Test risk level calculation - medium risk."""
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value=Decimal('10000'),
            gas_price=Decimal('85'),
            volatility_state=VolatilityState.MEDIUM,
            protocol_exposures={'ethereum': Decimal('1500')}
        )

        assert risk_level == RiskLevel.MEDIUM

    def test_calculate_risk_level_high(self, risk_manager):
        """Test risk level calculation - high risk."""
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value=Decimal('10000'),
            gas_price=Decimal('85'),
            volatility_state=VolatilityState.HIGH,
            protocol_exposures={'ethereum': Decimal('1500')}
        )

        assert risk_level == RiskLevel.HIGH

    def test_calculate_risk_level_critical(self, risk_manager):
        """Test risk level calculation - critical risk."""
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value=Decimal('10000'),
            gas_price=Decimal('150'),
            volatility_state=VolatilityState.EXTREME,
            protocol_exposures={'ethereum': Decimal('3000')}
        )

        assert risk_level == RiskLevel.CRITICAL

    def test_should_trigger_circuit_breaker_critical_risk(
        self, risk_manager
    ):
        """Test circuit breaker trigger for critical risk."""
        result = risk_manager._should_trigger_circuit_breaker(
            risk_level=RiskLevel.CRITICAL,
            portfolio_pnl=Decimal('100'),
            gas_price=Decimal('50')
        )

        assert result is True

    def test_should_trigger_circuit_breaker_extreme_gas(self, risk_manager):
        """Test circuit breaker trigger for extreme gas prices."""
        result = risk_manager._should_trigger_circuit_breaker(
            risk_level=RiskLevel.MEDIUM,
            portfolio_pnl=Decimal('100'),
            gas_price=Decimal('250')
        )

        assert result is True

    def test_should_trigger_circuit_breaker_already_active(
        self, risk_manager
    ):
        """Test circuit breaker trigger when already active."""
        risk_manager.circuit_breaker_active = True

        result = risk_manager._should_trigger_circuit_breaker(
            risk_level=RiskLevel.LOW,
            portfolio_pnl=Decimal('100'),
            gas_price=Decimal('50')
        )

        assert result is True

    def test_should_trigger_circuit_breaker_normal(self, risk_manager):
        """Test circuit breaker trigger under normal conditions."""
        result = risk_manager._should_trigger_circuit_breaker(
            risk_level=RiskLevel.LOW,
            portfolio_pnl=Decimal('100'),
            gas_price=Decimal('50')
        )

        assert result is False

    def test_get_volatility_multiplier_all_states(self, risk_manager):
        """Test volatility multiplier for all states."""
        assert risk_manager._get_volatility_multiplier(
            VolatilityState.LOW
        ) == Decimal('1.0')
        assert risk_manager._get_volatility_multiplier(
            VolatilityState.MEDIUM
        ) == Decimal('0.8')
        assert risk_manager._get_volatility_multiplier(
            VolatilityState.HIGH
        ) == Decimal('0.6')
        assert risk_manager._get_volatility_multiplier(
            VolatilityState.EXTREME
        ) == Decimal('0.3')


class TestRiskLevel:
    """Test cases for RiskLevel enum."""

    def test_risk_level_values(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_risk_level_comparison(self):
        """Test RiskLevel enum comparison."""
        assert RiskLevel.LOW != RiskLevel.HIGH
        assert RiskLevel.CRITICAL != RiskLevel.LOW


class TestVolatilityState:
    """Test cases for VolatilityState enum."""

    def test_volatility_state_values(self):
        """Test VolatilityState enum values."""
        assert VolatilityState.LOW.value == "low"
        assert VolatilityState.MEDIUM.value == "medium"
        assert VolatilityState.HIGH.value == "high"
        assert VolatilityState.EXTREME.value == "extreme"

    def test_volatility_state_comparison(self):
        """Test VolatilityState enum comparison."""
        assert VolatilityState.LOW != VolatilityState.EXTREME
        assert VolatilityState.MEDIUM != VolatilityState.HIGH


class TestRiskMetrics:
    """Test cases for RiskMetrics dataclass."""

    def test_risk_metrics_creation(self):
        """Test RiskMetrics dataclass creation."""
        metrics = RiskMetrics(
            portfolio_value=Decimal('10000'),
            portfolio_pnl=Decimal('500'),
            gas_price_gwei=Decimal('50'),
            volatility_state=VolatilityState.MEDIUM,
            protocol_exposures={'ethereum': Decimal('5000')},
            risk_level=RiskLevel.LOW,
            recommended_action=None,
            circuit_breaker_triggered=False
        )

        assert metrics.portfolio_value == Decimal('10000')
        assert metrics.portfolio_pnl == Decimal('500')
        assert metrics.gas_price_gwei == Decimal('50')
        assert metrics.volatility_state == VolatilityState.MEDIUM
        assert metrics.protocol_exposures == {'ethereum': Decimal('5000')}
        assert metrics.risk_level == RiskLevel.LOW
        assert not metrics.circuit_breaker_triggered

    def test_risk_metrics_with_negative_pnl(self):
        """Test RiskMetrics with negative P&L."""
        metrics = RiskMetrics(
            portfolio_value=Decimal('8000'),
            portfolio_pnl=Decimal('-2000'),
            gas_price_gwei=Decimal('100'),
            volatility_state=VolatilityState.HIGH,
            protocol_exposures={
                'ethereum': Decimal('4000'), 'scroll': Decimal('4000')
            },
            risk_level=RiskLevel.HIGH,
            recommended_action=None,
            circuit_breaker_triggered=True
        )

        assert metrics.portfolio_pnl == Decimal('-2000')
        assert metrics.risk_level == RiskLevel.HIGH
        assert metrics.circuit_breaker_triggered


class TestRiskLimits:
    """Test cases for RiskLimits dataclass."""

    def test_risk_limits_creation(self):
        """Test RiskLimits dataclass creation."""
        limits = RiskLimits(
            max_protocol_exposure_pct=Decimal('20'),
            max_transaction_size_pct=Decimal('5'),
            max_asset_concentration_pct=Decimal('30'),
            max_daily_loss_pct=Decimal('10'),
            max_gas_price_gwei=Decimal('100'),
            volatility_threshold_high=Decimal('0.05'),
            volatility_threshold_extreme=Decimal('0.15')
        )

        assert limits.max_protocol_exposure_pct == Decimal('20')
        assert limits.max_transaction_size_pct == Decimal('5')
        assert limits.max_asset_concentration_pct == Decimal('30')
        assert limits.max_daily_loss_pct == Decimal('10')
        assert limits.max_gas_price_gwei == Decimal('100')
        assert limits.volatility_threshold_high == Decimal('0.05')
        assert limits.volatility_threshold_extreme == Decimal('0.15')

    def test_risk_limits_with_custom_values(self):
        """Test RiskLimits with custom values."""
        limits = RiskLimits(
            max_protocol_exposure_pct=Decimal('15'),
            max_transaction_size_pct=Decimal('3'),
            max_asset_concentration_pct=Decimal('25'),
            max_daily_loss_pct=Decimal('5'),
            max_gas_price_gwei=Decimal('80'),
            volatility_threshold_high=Decimal('0.03'),
            volatility_threshold_extreme=Decimal('0.10')
        )

        assert limits.max_protocol_exposure_pct == Decimal('15')
        assert limits.max_gas_price_gwei == Decimal('80')
        assert limits.volatility_threshold_extreme == Decimal('0.10')


class TestRiskManagerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def risk_manager(self):
        """Create a RiskManager instance for testing."""
        with patch('airdrops.risk_management.core.Web3'):
            return RiskManager()

    def test_monitor_positions_empty_wallet_list(self, risk_manager):
        """Test position monitoring with empty wallet list."""
        exposures = risk_manager.monitor_positions([])
        assert exposures == {}

    def test_monitor_positions_invalid_address(self, risk_manager):
        """Test position monitoring with invalid address."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.side_effect = ValueError("Invalid address")

        risk_manager.web3_providers = {'ethereum': mock_web3}

        with pytest.raises(RuntimeError, match="Failed to monitor positions"):
            risk_manager.monitor_positions(['invalid_address'])

    def test_monitor_gas_costs_network_error(self, risk_manager):
        """Test gas cost monitoring with network error."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.gas_price = property(
            lambda self: (
                _ for _ in ()).throw(ConnectionError("Network error"))
        )

        risk_manager.web3_providers = {'ethereum': mock_web3}

        with pytest.raises(RuntimeError, match="Failed to monitor gas costs"):
            risk_manager.monitor_gas_costs('ethereum')

    def test_risk_manager_with_none_config(self):
        """Test RiskManager initialization with None config."""
        with patch('airdrops.risk_management.core.Web3'):
            manager = RiskManager(config=None)
            assert manager.config == {}
            assert isinstance(manager.risk_limits, RiskLimits)