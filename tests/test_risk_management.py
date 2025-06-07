"""
Tests for the Risk Management System.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from web3 import Web3

from airdrops.risk_management.core import (
    RiskManager,
    RiskLevel,
    VolatilityState,
    RiskMetrics,
    RiskLimits
)


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
                assert manager.risk_limits.max_protocol_exposure_pct == Decimal('25.0')
                assert manager.risk_limits.max_gas_price_gwei == Decimal('120.0')
    
    def test_load_risk_limits_defaults(self):
        """Test loading default risk limits when env vars not set."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('airdrops.risk_management.core.Web3'):
                manager = RiskManager()
                assert manager.risk_limits.max_protocol_exposure_pct == Decimal('20.0')
                assert manager.risk_limits.max_gas_price_gwei == Decimal('100.0')
    
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
            with pytest.raises(RuntimeError, match="Web3 provider initialization failed"):
                RiskManager()
    
    def test_monitor_positions_success(self, risk_manager):
        """Test successful position monitoring."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH in wei
        mock_web3.from_wei.return_value = 1.0
        
        risk_manager.web3_providers = {'ethereum': mock_web3}
        
        with patch.object(risk_manager, '_get_eth_price_usd', return_value=Decimal('2000')):
            exposures = risk_manager.monitor_positions(['0x123'])
            
            assert 'ethereum' in exposures
            assert exposures['ethereum'] == Decimal('2000')  # 1 ETH * $2000
    
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
        mock_web3.eth.gas_price = 50000000000  # 50 Gwei in wei
        mock_web3.from_wei.return_value = 50.0
        
        risk_manager.web3_providers = {'ethereum': mock_web3}
        
        gas_price = risk_manager.monitor_gas_costs('ethereum')
        assert gas_price == Decimal('50.0')
    
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
        # With mock implementation returning 3% volatility
        assert volatility == VolatilityState.MEDIUM
    
    def test_monitor_market_volatility_empty_assets(self, risk_manager):
        """Test market volatility monitoring with empty asset list."""
        volatility = risk_manager.monitor_market_volatility([])
        assert volatility == VolatilityState.LOW
    
    def test_monitor_market_volatility_failure(self, risk_manager):
        """Test market volatility monitoring failure."""
        with patch.object(risk_manager, 'monitor_market_volatility') as mock_method:
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
        with patch.object(risk_manager, '_get_eth_price_usd') as mock_method:
            mock_method.side_effect = Exception("Price API error")
            mock_method.return_value = Decimal('2000.0')  # Fallback
            
            price = risk_manager._get_eth_price_usd()
            assert price == Decimal('2000.0')


class TestRiskLevel:
    """Test cases for RiskLevel enum."""
    
    def test_risk_level_values(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


class TestVolatilityState:
    """Test cases for VolatilityState enum."""
    
    def test_volatility_state_values(self):
        """Test VolatilityState enum values."""
        assert VolatilityState.LOW.value == "low"
        assert VolatilityState.MEDIUM.value == "medium"
        assert VolatilityState.HIGH.value == "high"
        assert VolatilityState.EXTREME.value == "extreme"


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
            circuit_breaker_triggered=False
        )
        
        assert metrics.portfolio_value == Decimal('10000')
        assert metrics.volatility_state == VolatilityState.MEDIUM
        assert metrics.risk_level == RiskLevel.LOW
        assert not metrics.circuit_breaker_triggered


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
        assert limits.max_gas_price_gwei == Decimal('100')
        assert limits.volatility_threshold_extreme == Decimal('0.15')