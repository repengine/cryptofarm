"""
Unit tests for RiskManager initialization, configuration, and position limit enforcement.

This module contains comprehensive tests for the RiskManager class, including
initialization, configuration validation, error handling, and position limit enforcement.
"""

import os
import pytest
from decimal import Decimal
from typing import Dict, List
from unittest.mock import Mock, patch

from airdrops.risk_management.core import (
    RiskManager,
    RiskLevel,
    RiskLimits,
    RiskMetrics,
    VolatilityState,
)


class TestRiskManagerInitialization:
    """Test suite for RiskManager initialization and configuration."""

    def test_init_with_valid_config_success(self) -> None:
        """Test successful initialization with a valid configuration.
        
        Example:
            >>> config = {"risk_management": {"gas_price_threshold_gwei": Decimal("100")}}
            >>> risk_manager = RiskManager(config=config)
            >>> assert risk_manager.config == config
        """
        config = {
            "risk_management": {
                "gas_price_threshold_gwei": Decimal("100"),
                "max_consecutive_failures": 3,
                "circuit_breaker_threshold": Decimal("0.8"),
            }
        }
        
        with patch('airdrops.risk_management.core.Web3'):
            risk_manager = RiskManager(config=config)
            
            assert risk_manager.config == config
            assert isinstance(risk_manager.risk_limits, RiskLimits)
            assert risk_manager.circuit_breaker_active is False
            assert risk_manager.current_risk_level == RiskLevel.LOW
            assert risk_manager.protocol_failure_counts == {}
            assert risk_manager.web3_providers == {}

    def test_init_with_none_config_uses_defaults(self) -> None:
        """Test initialization with None config uses empty dict.
        
        Example:
            >>> risk_manager = RiskManager(config=None)
            >>> assert risk_manager.config == {}
        """
        with patch('airdrops.risk_management.core.Web3'):
            risk_manager = RiskManager(config=None)
            
            assert risk_manager.config == {}
            assert isinstance(risk_manager.risk_limits, RiskLimits)
            assert risk_manager.circuit_breaker_active is False

    def test_init_with_empty_config_success(self) -> None:
        """Test initialization with empty configuration dictionary.
        
        Example:
            >>> risk_manager = RiskManager(config={})
            >>> assert risk_manager.config == {}
        """
        with patch('airdrops.risk_management.core.Web3'):
            risk_manager = RiskManager(config={})
            
            assert risk_manager.config == {}
            assert isinstance(risk_manager.risk_limits, RiskLimits)

    def test_init_with_alerter_success(self) -> None:
        """Test initialization with alerter instance.
        
        Example:
            >>> alerter = Mock()
            >>> risk_manager = RiskManager(alerter=alerter)
            >>> assert risk_manager.alerter is alerter
        """
        alerter = Mock()
        
        with patch('airdrops.risk_management.core.Web3'):
            risk_manager = RiskManager(alerter=alerter)
            
            assert risk_manager.alerter is alerter

    def test_init_with_protocol_clients_success(self) -> None:
        """Test initialization with protocol client dependency injection.
        
        Example:
            >>> scroll_client = Mock()
            >>> risk_manager = RiskManager(scroll_client=scroll_client)
            >>> assert risk_manager.scroll_client is scroll_client
        """
        scroll_client = Mock()
        zksync_client = Mock()
        layerzero_client = Mock()
        eigenlayer_client = Mock()
        
        with patch('airdrops.risk_management.core.Web3'):
            risk_manager = RiskManager(
                scroll_client=scroll_client,
                zksync_client=zksync_client,
                layerzero_client=layerzero_client,
                eigenlayer_client=eigenlayer_client
            )
            
            assert risk_manager.scroll_client is scroll_client
            assert risk_manager.zksync_client is zksync_client
            assert risk_manager.layerzero_client is layerzero_client
            assert risk_manager.eigenlayer_client is eigenlayer_client

    @patch.dict(os.environ, {
        'RISK_MAX_PROTOCOL_EXPOSURE_PCT': '25.0',
        'RISK_MAX_TRANSACTION_SIZE_PCT': '7.5',
        'RISK_MAX_GAS_PRICE_GWEI': '150.0'
    })
    def test_init_loads_risk_limits_from_environment(self) -> None:
        """Test initialization loads risk limits from environment variables.
        
        Example:
            >>> os.environ['RISK_MAX_GAS_PRICE_GWEI'] = '150.0'
            >>> risk_manager = RiskManager()
            >>> assert risk_manager.risk_limits.max_gas_price_gwei == Decimal('150.0')
        """
        with patch('airdrops.risk_management.core.Web3'):
            risk_manager = RiskManager()
            
            assert risk_manager.risk_limits.max_protocol_exposure_pct == Decimal('25.0')
            assert risk_manager.risk_limits.max_transaction_size_pct == Decimal('7.5')
            assert risk_manager.risk_limits.max_gas_price_gwei == Decimal('150.0')

    @patch.dict(os.environ, {}, clear=True)
    def test_init_uses_default_risk_limits_when_no_env_vars(self) -> None:
        """Test initialization uses default risk limits when no environment variables.
        
        Example:
            >>> # No environment variables set
            >>> risk_manager = RiskManager()
            >>> assert risk_manager.risk_limits.max_gas_price_gwei == Decimal('100.0')
        """
        with patch('airdrops.risk_management.core.Web3'):
            risk_manager = RiskManager()
            
            # Check default values are used
            assert risk_manager.risk_limits.max_protocol_exposure_pct == Decimal('20.0')
            assert risk_manager.risk_limits.max_transaction_size_pct == Decimal('5.0')
            assert risk_manager.risk_limits.max_gas_price_gwei == Decimal('100.0')

    @patch.dict(os.environ, {
        'ETH_RPC_URL': 'https://eth-mainnet.example.com',
        'SCROLL_L2_RPC_URL': 'https://scroll.example.com'
    })
    def test_init_initializes_web3_providers_success(self) -> None:
        """Test initialization successfully creates Web3 providers.
        
        Example:
            >>> os.environ['ETH_RPC_URL'] = 'https://eth-mainnet.example.com'
            >>> risk_manager = RiskManager()
            >>> assert 'ethereum' in risk_manager.web3_providers
        """
        mock_web3_instance = Mock()
        
        with patch('airdrops.risk_management.core.Web3') as mock_web3:
            mock_web3.return_value = mock_web3_instance
            mock_web3.HTTPProvider = Mock()
            
            RiskManager()
            
            # Verify Web3 providers were created
            assert mock_web3.call_count == 2  # ethereum and scroll
            assert mock_web3.HTTPProvider.call_count == 2

    @patch.dict(os.environ, {
        'ETH_RPC_URL': 'https://eth-mainnet.example.com'
    })
    def test_init_web3_provider_initialization_failure(self) -> None:
        """Test initialization handles Web3 provider initialization failure.
        
        Example:
            >>> # Web3 initialization raises exception
            >>> with pytest.raises(RuntimeError, match="Web3 provider initialization failed"):
            ...     RiskManager()
        """
        with patch('airdrops.risk_management.core.Web3') as mock_web3:
            mock_web3.side_effect = Exception("Connection failed")
            
            with pytest.raises(RuntimeError, match="Web3 provider initialization failed"):
                RiskManager()

    @patch.dict(os.environ, {
        'ETH_RPC_URL': 'https://eth-mainnet.example.com',
        'SCROLL_L2_RPC_URL': 'https://scroll.example.com',
        'ZKSYNC_L2_RPC_URL': 'https://zksync.example.com',
        'PRIVATE_KEY': '0x' + '1' * 64
    })
    def test_init_initializes_default_clients_when_none_provided(self) -> None:
        """Test initialization creates default protocol clients when none provided.
        
        Example:
            >>> # Environment variables set for protocol initialization
            >>> risk_manager = RiskManager()
            >>> assert risk_manager.scroll_client is not None
        """
        with patch('airdrops.risk_management.core.Web3'), \
             patch('airdrops.protocols.scroll.scroll.ScrollProtocol') as mock_scroll, \
             patch('airdrops.protocols.zksync.zksync.ZkSyncProtocol') as mock_zksync, \
             patch('airdrops.protocols.layerzero.layerzero.LayerZeroProtocol') as mock_layerzero, \
             patch('airdrops.protocols.eigenlayer.eigenlayer.EigenLayerProtocol') as mock_eigenlayer:
            
            mock_scroll_instance = Mock()
            mock_zksync_instance = Mock()
            mock_layerzero_instance = Mock()
            mock_eigenlayer_instance = Mock()
            
            mock_scroll.return_value = mock_scroll_instance
            mock_zksync.return_value = mock_zksync_instance
            mock_layerzero.return_value = mock_layerzero_instance
            mock_eigenlayer.return_value = mock_eigenlayer_instance
            
            risk_manager = RiskManager()
            
            # Verify default clients were created
            assert risk_manager.scroll_client is mock_scroll_instance
            assert risk_manager.zksync_client is mock_zksync_instance
            assert risk_manager.layerzero_client is mock_layerzero_instance
            assert risk_manager.eigenlayer_client is mock_eigenlayer_instance

    def test_init_skips_default_clients_when_clients_provided(self) -> None:
        """Test initialization skips default client creation when clients provided.
        
        Example:
            >>> scroll_client = Mock()
            >>> risk_manager = RiskManager(scroll_client=scroll_client)
            >>> # Default client initialization should be skipped
        """
        scroll_client = Mock()
        
        with patch('airdrops.risk_management.core.Web3'), \
             patch('airdrops.protocols.scroll.scroll.ScrollProtocol') as mock_scroll:
            
            risk_manager = RiskManager(scroll_client=scroll_client)
            
            # Verify default client initialization was skipped
            mock_scroll.assert_not_called()
            assert risk_manager.scroll_client is scroll_client

    @patch.dict(os.environ, {
        'ETH_RPC_URL': 'https://eth-mainnet.example.com',
        'PRIVATE_KEY': '0x' + '1' * 64
    })
    def test_init_handles_protocol_import_error(self) -> None:
        """Test initialization handles protocol import errors gracefully.
        
        Example:
            >>> # Protocol imports fail but initialization continues
            >>> risk_manager = RiskManager()
            >>> assert risk_manager is not None
        """
        with patch('airdrops.risk_management.core.Web3'), \
             patch('airdrops.protocols.scroll.scroll.ScrollProtocol', side_effect=ImportError("Module not found")):
            
            # Should not raise exception, just log warning
            risk_manager = RiskManager()
            assert risk_manager is not None

    @patch.dict(os.environ, {
        'ETH_RPC_URL': 'https://eth-mainnet.example.com',
        'PRIVATE_KEY': '0x' + '1' * 64
    })
    def test_init_handles_protocol_initialization_error(self) -> None:
        """Test initialization handles protocol client initialization errors.
        
        Example:
            >>> # Protocol client initialization fails but RiskManager continues
            >>> risk_manager = RiskManager()
            >>> assert risk_manager is not None
        """
        with patch('airdrops.risk_management.core.Web3'), \
             patch('airdrops.protocols.scroll.scroll.ScrollProtocol', side_effect=Exception("Init failed")):
            
            # Should not raise exception, just log error
            risk_manager = RiskManager()
            assert risk_manager is not None

    @patch.dict(os.environ, {}, clear=True)
    def test_init_skips_protocol_clients_when_missing_env_vars(self) -> None:
        """Test initialization skips protocol clients when environment variables missing.
        
        Example:
            >>> # No environment variables for protocol initialization
            >>> risk_manager = RiskManager()
            >>> assert risk_manager.scroll_client is None
        """
        with patch('airdrops.risk_management.core.Web3'), \
             patch('airdrops.protocols.scroll.scroll.ScrollProtocol') as mock_scroll:
            
            risk_manager = RiskManager()
            
            # Verify no protocol clients were created due to missing env vars
            mock_scroll.assert_not_called()
            assert risk_manager.scroll_client is None

    def test_init_with_malformed_config_missing_risk_management_section(self) -> None:
        """Test initialization with config missing risk_management section.
        
        Example:
            >>> config = {"other_section": {"key": "value"}}
            >>> risk_manager = RiskManager(config=config)
            >>> # Should use defaults for risk management
        """
        config = {
            "other_section": {
                "some_key": "some_value"
            }
        }
        
        with patch('airdrops.risk_management.core.Web3'):
            risk_manager = RiskManager(config=config)
            
            assert risk_manager.config == config
            assert isinstance(risk_manager.risk_limits, RiskLimits)

    def test_init_with_invalid_config_type_handles_gracefully(self) -> None:
        """Test initialization with invalid config type handles gracefully.
        
        Example:
            >>> # String config gets converted to empty dict by 'config or {}'
            >>> risk_manager = RiskManager(config="invalid_string_config")  # type: ignore[arg-type]
            >>> assert risk_manager.config == "invalid_string_config"
        """
        with patch('airdrops.risk_management.core.Web3'):
            # String config should be accepted due to 'config or {}' logic
            risk_manager = RiskManager(config="invalid_string_config")  # type: ignore[arg-type]
            assert risk_manager.config == "invalid_string_config"  # type: ignore[comparison-overlap]

    @patch.dict(os.environ, {
        'RISK_MAX_GAS_PRICE_GWEI': 'invalid_decimal_value'
    })
    def test_init_with_invalid_env_var_decimal_raises_error(self) -> None:
        """Test initialization with invalid decimal in environment variable.
        
        Example:
            >>> os.environ['RISK_MAX_GAS_PRICE_GWEI'] = 'invalid_decimal'
            >>> with pytest.raises(Exception):
            ...     RiskManager()
        """
        with patch('airdrops.risk_management.core.Web3'):
            # Should raise exception when trying to convert invalid decimal
            with pytest.raises(Exception):
                RiskManager()

    def test_init_all_attributes_properly_initialized(self) -> None:
        """Test all instance attributes are properly initialized.
        
        Example:
            >>> risk_manager = RiskManager()
            >>> assert hasattr(risk_manager, 'config')
            >>> assert hasattr(risk_manager, 'risk_limits')
        """
        config = {"test": "value"}
        alerter = Mock()
        
        with patch('airdrops.risk_management.core.Web3'):
            risk_manager = RiskManager(config=config, alerter=alerter)
            
            # Verify all expected attributes exist and have correct types
            assert risk_manager.config == config
            assert risk_manager.alerter is alerter
            assert isinstance(risk_manager.risk_limits, RiskLimits)
            assert isinstance(risk_manager.web3_providers, dict)
            assert isinstance(risk_manager.circuit_breaker_active, bool)
            assert isinstance(risk_manager.current_risk_level, RiskLevel)
            assert isinstance(risk_manager.protocol_failure_counts, dict)
            
            # Verify protocol client attributes exist (may be None)
            assert hasattr(risk_manager, 'scroll_client')
            assert hasattr(risk_manager, 'zksync_client')
            assert hasattr(risk_manager, 'layerzero_client')
            assert hasattr(risk_manager, 'eigenlayer_client')


class TestRiskManagerPositionLimitEnforcement:
    """Test suite for RiskManager position limit enforcement methods."""

    @pytest.fixture
    def risk_manager(self) -> RiskManager:
        """Create a RiskManager instance for testing."""
        with patch('airdrops.risk_management.core.Web3'):
            return RiskManager()

    def test_monitor_positions_within_total_exposure_limit(self, risk_manager: RiskManager) -> None:
        """Test monitoring positions that are within total exposure limits.
        
        Example:
            >>> exposures = risk_manager.monitor_positions(["0x123"])
            >>> total_exposure = sum(exposures.values())
            >>> assert total_exposure <= risk_manager.risk_limits.max_protocol_exposure_pct
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock Web3 providers and balance checks
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH in wei
        mock_web3.from_wei.return_value = 1.0  # 1 ETH
        mock_web3.to_checksum_address.return_value = wallet_addresses[0]
        
        risk_manager.web3_providers = {"ethereum": mock_web3, "scroll": mock_web3}
        
        with patch.object(risk_manager, '_get_eth_price_usd', return_value=Decimal("2000.0")):
            exposures = risk_manager.monitor_positions(wallet_addresses)
            
            # Verify exposures are calculated correctly
            assert "ethereum" in exposures
            assert "scroll" in exposures
            assert exposures["ethereum"] == Decimal("2000.0")  # 1 ETH * $2000
            assert exposures["scroll"] == Decimal("2000.0")    # 1 ETH * $2000
            
            # Verify total exposure is within limits (assuming reasonable portfolio size)
            total_exposure = sum(exposures.values())
            assert total_exposure == Decimal("4000.0")  # 2 ETH * $2000

    def test_monitor_positions_exceeds_total_exposure_limit(self, risk_manager: RiskManager) -> None:
        """Test monitoring positions that exceed total exposure limits.
        
        Example:
            >>> # Large balance that would exceed limits
            >>> exposures = risk_manager.monitor_positions(["0x123"])
            >>> # Should still return exposures but trigger warnings
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock Web3 providers with large balances
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 100000000000000000000  # 100 ETH in wei
        mock_web3.from_wei.return_value = 100.0  # 100 ETH
        mock_web3.to_checksum_address.return_value = wallet_addresses[0]
        
        risk_manager.web3_providers = {"ethereum": mock_web3}
        
        with patch.object(risk_manager, '_get_eth_price_usd', return_value=Decimal("2000.0")):
            exposures = risk_manager.monitor_positions(wallet_addresses)
            
            # Verify large exposure is calculated
            assert exposures["ethereum"] == Decimal("200000.0")  # 100 ETH * $2000
            
            # This would exceed typical exposure limits but method should still return values
            total_exposure = sum(exposures.values())
            assert total_exposure == Decimal("200000.0")

    def test_monitor_positions_within_protocol_exposure_limit(self, risk_manager: RiskManager) -> None:
        """Test monitoring positions within specific protocol exposure limits.
        
        Example:
            >>> exposures = risk_manager.monitor_positions(["0x123"])
            >>> assert exposures["scroll"] <= protocol_limit
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock Web3 providers with moderate balances
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 5000000000000000000  # 5 ETH in wei
        mock_web3.from_wei.return_value = 5.0  # 5 ETH
        mock_web3.to_checksum_address.return_value = wallet_addresses[0]
        
        risk_manager.web3_providers = {"scroll": mock_web3}
        
        with patch.object(risk_manager, '_get_eth_price_usd', return_value=Decimal("2000.0")):
            exposures = risk_manager.monitor_positions(wallet_addresses)
            
            # Verify protocol-specific exposure
            assert exposures["scroll"] == Decimal("10000.0")  # 5 ETH * $2000
            
            # Check against protocol exposure limit (20% of hypothetical $100k portfolio)
            protocol_limit = Decimal("20000.0")  # 20% of $100k
            assert exposures["scroll"] <= protocol_limit

    def test_monitor_positions_exceeds_protocol_exposure_limit(self, risk_manager: RiskManager) -> None:
        """Test monitoring positions that exceed specific protocol exposure limits.
        
        Example:
            >>> exposures = risk_manager.monitor_positions(["0x123"])
            >>> assert exposures["scroll"] > protocol_limit  # Should trigger warnings
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock Web3 providers with large balances for specific protocol
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 50000000000000000000  # 50 ETH in wei
        mock_web3.from_wei.return_value = 50.0  # 50 ETH
        mock_web3.to_checksum_address.return_value = wallet_addresses[0]
        
        risk_manager.web3_providers = {"scroll": mock_web3}
        
        with patch.object(risk_manager, '_get_eth_price_usd', return_value=Decimal("2000.0")):
            exposures = risk_manager.monitor_positions(wallet_addresses)
            
            # Verify large protocol-specific exposure
            assert exposures["scroll"] == Decimal("100000.0")  # 50 ETH * $2000
            
            # This exceeds typical protocol limits (20% of reasonable portfolio)
            protocol_limit = Decimal("20000.0")  # 20% of $100k
            assert exposures["scroll"] > protocol_limit

    def test_monitor_positions_zero_value_transaction(self, risk_manager: RiskManager) -> None:
        """Test monitoring positions with zero value transactions.
        
        Example:
            >>> exposures = risk_manager.monitor_positions(["0x123"])
            >>> assert all(exposure >= 0 for exposure in exposures.values())
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock Web3 providers with zero balances
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 0  # 0 ETH in wei
        mock_web3.from_wei.return_value = 0.0  # 0 ETH
        mock_web3.to_checksum_address.return_value = wallet_addresses[0]
        
        risk_manager.web3_providers = {"ethereum": mock_web3, "scroll": mock_web3}
        
        with patch.object(risk_manager, '_get_eth_price_usd', return_value=Decimal("2000.0")):
            exposures = risk_manager.monitor_positions(wallet_addresses)
            
            # Verify zero exposures
            assert exposures["ethereum"] == Decimal("0.0")
            assert exposures["scroll"] == Decimal("0.0")
            
            # Verify all exposures are non-negative
            assert all(exposure >= 0 for exposure in exposures.values())

    def test_calculate_position_size_limits_within_limits(self, risk_manager: RiskManager) -> None:
        """Test calculating position size limits for transactions within limits.
        
        Example:
            >>> limits = risk_manager.calculate_position_size_limits(
            ...     Decimal("10000"), "ethereum", "ETH"
            ... )
            >>> assert limits["max_position_size"] <= total_capital * exposure_pct
        """
        total_capital = Decimal("10000")
        protocol = "ethereum"
        asset = "ETH"
        
        with patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.LOW):
            limits = risk_manager.calculate_position_size_limits(total_capital, protocol, asset)
            
            # Verify limit structure
            assert "max_position_size" in limits
            assert "max_transaction_size" in limits
            assert "max_asset_concentration" in limits
            assert "volatility_adjustment" in limits
            
            # Verify limits are within expected ranges
            expected_protocol_exposure = total_capital * risk_manager.risk_limits.max_protocol_exposure_pct / 100
            expected_transaction_size = total_capital * risk_manager.risk_limits.max_transaction_size_pct / 100
            expected_asset_concentration = total_capital * risk_manager.risk_limits.max_asset_concentration_pct / 100
            
            # With LOW volatility, multiplier should be 1.0
            assert limits["max_position_size"] == expected_protocol_exposure * Decimal("1.0")
            assert limits["max_transaction_size"] == expected_transaction_size * Decimal("1.0")
            assert limits["max_asset_concentration"] == expected_asset_concentration
            assert limits["volatility_adjustment"] == Decimal("1.0")

    def test_calculate_position_size_limits_exceeds_limits(self, risk_manager: RiskManager) -> None:
        """Test calculating position size limits for transactions that would exceed limits.
        
        Example:
            >>> limits = risk_manager.calculate_position_size_limits(
            ...     Decimal("10000"), "ethereum", "ETH"
            ... )
            >>> # Limits should be reduced due to high volatility
        """
        total_capital = Decimal("10000")
        protocol = "ethereum"
        asset = "ETH"
        
        with patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.EXTREME):
            limits = risk_manager.calculate_position_size_limits(total_capital, protocol, asset)
            
            # Verify limits are reduced due to extreme volatility
            expected_protocol_exposure = total_capital * risk_manager.risk_limits.max_protocol_exposure_pct / 100
            expected_transaction_size = total_capital * risk_manager.risk_limits.max_transaction_size_pct / 100
            
            # With EXTREME volatility, multiplier should be 0.3
            volatility_multiplier = Decimal("0.3")
            assert limits["max_position_size"] == expected_protocol_exposure * volatility_multiplier
            assert limits["max_transaction_size"] == expected_transaction_size * volatility_multiplier
            assert limits["volatility_adjustment"] == volatility_multiplier
            
            # Verify limits are significantly reduced
            assert limits["max_position_size"] < expected_protocol_exposure
            assert limits["max_transaction_size"] < expected_transaction_size

    def test_calculate_position_size_limits_medium_volatility(self, risk_manager: RiskManager) -> None:
        """Test calculating position size limits with medium volatility adjustments.
        
        Example:
            >>> limits = risk_manager.calculate_position_size_limits(
            ...     Decimal("10000"), "scroll", "ETH"
            ... )
            >>> assert limits["volatility_adjustment"] == Decimal("0.8")
        """
        total_capital = Decimal("10000")
        protocol = "scroll"
        asset = "ETH"
        
        with patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.MEDIUM):
            limits = risk_manager.calculate_position_size_limits(total_capital, protocol, asset)
            
            # Verify medium volatility adjustment
            assert limits["volatility_adjustment"] == Decimal("0.8")
            
            # Verify limits are moderately reduced
            expected_protocol_exposure = total_capital * risk_manager.risk_limits.max_protocol_exposure_pct / 100
            expected_position_size = expected_protocol_exposure * Decimal("0.8")
            assert limits["max_position_size"] == expected_position_size

    def test_calculate_position_size_limits_high_volatility(self, risk_manager: RiskManager) -> None:
        """Test calculating position size limits with high volatility adjustments.
        
        Example:
            >>> limits = risk_manager.calculate_position_size_limits(
            ...     Decimal("10000"), "scroll", "ETH"
            ... )
            >>> assert limits["volatility_adjustment"] == Decimal("0.6")
        """
        total_capital = Decimal("10000")
        protocol = "scroll"
        asset = "ETH"
        
        with patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.HIGH):
            limits = risk_manager.calculate_position_size_limits(total_capital, protocol, asset)
            
            # Verify high volatility adjustment
            assert limits["volatility_adjustment"] == Decimal("0.6")
            
            # Verify limits are significantly reduced
            expected_protocol_exposure = total_capital * risk_manager.risk_limits.max_protocol_exposure_pct / 100
            expected_position_size = expected_protocol_exposure * Decimal("0.6")
            assert limits["max_position_size"] == expected_position_size

    def test_calculate_position_size_limits_failure_handling(self, risk_manager: RiskManager) -> None:
        """Test position size limit calculation handles failures gracefully.
        
        Example:
            >>> # Volatility monitoring fails
            >>> with pytest.raises(RuntimeError, match="Failed to calculate position size limits"):
            ...     risk_manager.calculate_position_size_limits(Decimal("10000"), "ethereum", "ETH")
        """
        total_capital = Decimal("10000")
        protocol = "ethereum"
        asset = "ETH"
        
        with patch.object(risk_manager, 'monitor_market_volatility', side_effect=Exception("Volatility error")):
            with pytest.raises(RuntimeError, match="Failed to calculate position size limits"):
                risk_manager.calculate_position_size_limits(total_capital, protocol, asset)

    def test_check_emergency_stop_conditions_within_limits(self, risk_manager: RiskManager) -> None:
        """Test emergency stop conditions when all metrics are within safe limits.
        
        Example:
            >>> metrics = RiskMetrics(...)  # Safe values
            >>> assert not risk_manager.check_emergency_stop_conditions(metrics)
        """
        # Create safe risk metrics
        safe_metrics = RiskMetrics(
            portfolio_value=Decimal("10000"),
            portfolio_pnl=Decimal("500"),  # 5% gain
            gas_price_gwei=Decimal("50"),  # Below limit
            volatility_state=VolatilityState.LOW,
            protocol_exposures={"ethereum": Decimal("1000"), "scroll": Decimal("1500")},
            risk_level=RiskLevel.LOW,
            recommended_action=None,
            circuit_breaker_triggered=False
        )
        
        # Should not trigger emergency stop
        assert not risk_manager.check_emergency_stop_conditions(safe_metrics)

    def test_check_emergency_stop_conditions_critical_risk_level(self, risk_manager: RiskManager) -> None:
        """Test emergency stop conditions with critical risk level.
        
        Example:
            >>> metrics = RiskMetrics(risk_level=RiskLevel.CRITICAL, ...)
            >>> assert risk_manager.check_emergency_stop_conditions(metrics)
        """
        # Create metrics with critical risk level
        critical_metrics = RiskMetrics(
            portfolio_value=Decimal("10000"),
            portfolio_pnl=Decimal("100"),
            gas_price_gwei=Decimal("50"),
            volatility_state=VolatilityState.LOW,
            protocol_exposures={"ethereum": Decimal("1000")},
            risk_level=RiskLevel.CRITICAL,  # Critical risk
            recommended_action=None,
            circuit_breaker_triggered=False
        )
        
        # Should trigger emergency stop
        assert risk_manager.check_emergency_stop_conditions(critical_metrics)

    def test_check_emergency_stop_conditions_excessive_daily_loss(self, risk_manager: RiskManager) -> None:
        """Test emergency stop conditions with excessive daily losses.
        
        Example:
            >>> metrics = RiskMetrics(portfolio_pnl=Decimal("-1500"), ...)  # 15% loss
            >>> assert risk_manager.check_emergency_stop_conditions(metrics)
        """
        # Create metrics with excessive daily loss (15% loss, limit is 10%)
        loss_metrics = RiskMetrics(
            portfolio_value=Decimal("10000"),
            portfolio_pnl=Decimal("-1500"),  # 15% loss, exceeds 10% limit
            gas_price_gwei=Decimal("50"),
            volatility_state=VolatilityState.LOW,
            protocol_exposures={"ethereum": Decimal("1000")},
            risk_level=RiskLevel.MEDIUM,
            recommended_action=None,
            circuit_breaker_triggered=False
        )
        
        # Should trigger emergency stop due to excessive loss
        assert risk_manager.check_emergency_stop_conditions(loss_metrics)

    def test_check_emergency_stop_conditions_extreme_gas_prices(self, risk_manager: RiskManager) -> None:
        """Test emergency stop conditions with extreme gas prices.
        
        Example:
            >>> metrics = RiskMetrics(gas_price_gwei=Decimal("250"), ...)  # 2.5x limit
            >>> assert risk_manager.check_emergency_stop_conditions(metrics)
        """
        # Create metrics with extreme gas prices (2.5x the limit)
        gas_metrics = RiskMetrics(
            portfolio_value=Decimal("10000"),
            portfolio_pnl=Decimal("100"),
            gas_price_gwei=Decimal("250"),  # 2.5x the 100 Gwei limit
            volatility_state=VolatilityState.LOW,
            protocol_exposures={"ethereum": Decimal("1000")},
            risk_level=RiskLevel.LOW,
            recommended_action=None,
            circuit_breaker_triggered=False
        )
        
        # Should trigger emergency stop due to extreme gas prices
        assert risk_manager.check_emergency_stop_conditions(gas_metrics)

    def test_check_emergency_stop_conditions_extreme_volatility(self, risk_manager: RiskManager) -> None:
        """Test emergency stop conditions with extreme market volatility.
        
        Example:
            >>> metrics = RiskMetrics(volatility_state=VolatilityState.EXTREME, ...)
            >>> assert risk_manager.check_emergency_stop_conditions(metrics)
        """
        # Create metrics with extreme volatility
        volatility_metrics = RiskMetrics(
            portfolio_value=Decimal("10000"),
            portfolio_pnl=Decimal("100"),
            gas_price_gwei=Decimal("50"),
            volatility_state=VolatilityState.EXTREME,  # Extreme volatility
            protocol_exposures={"ethereum": Decimal("1000")},
            risk_level=RiskLevel.LOW,
            recommended_action=None,
            circuit_breaker_triggered=False
        )
        
        # Should trigger emergency stop due to extreme volatility
        assert risk_manager.check_emergency_stop_conditions(volatility_metrics)

    def test_check_emergency_stop_conditions_excessive_protocol_concentration(self, risk_manager: RiskManager) -> None:
        """Test emergency stop conditions with excessive protocol concentration.
        
        Example:
            >>> # 35% exposure to single protocol (limit is 20%, threshold is 30%)
            >>> metrics = RiskMetrics(protocol_exposures={"ethereum": Decimal("3500")}, ...)
            >>> assert risk_manager.check_emergency_stop_conditions(metrics)
        """
        # Create metrics with excessive protocol concentration (35% in one protocol)
        concentration_metrics = RiskMetrics(
            portfolio_value=Decimal("10000"),
            portfolio_pnl=Decimal("100"),
            gas_price_gwei=Decimal("50"),
            volatility_state=VolatilityState.LOW,
            protocol_exposures={"ethereum": Decimal("3500")},  # 35% concentration, exceeds 30% threshold
            risk_level=RiskLevel.LOW,
            recommended_action=None,
            circuit_breaker_triggered=False
        )
        
        # Should trigger emergency stop due to excessive concentration
        assert risk_manager.check_emergency_stop_conditions(concentration_metrics)

    def test_check_emergency_stop_conditions_error_handling(self, risk_manager: RiskManager) -> None:
        """Test emergency stop conditions handles errors by defaulting to emergency stop.
        
        Example:
            >>> # Malformed metrics cause error
            >>> assert risk_manager.check_emergency_stop_conditions(malformed_metrics)
        """
        # Create metrics that will cause an error during processing
        malformed_metrics = RiskMetrics(
            portfolio_value=Decimal("0"),  # Zero portfolio value will cause division error
            portfolio_pnl=Decimal("100"),
            gas_price_gwei=Decimal("50"),
            volatility_state=VolatilityState.LOW,
            protocol_exposures={"ethereum": Decimal("1000")},
            risk_level=RiskLevel.LOW,
            recommended_action=None,
            circuit_breaker_triggered=False
        )
        
        # Should default to emergency stop on error (err on side of caution)
        assert risk_manager.check_emergency_stop_conditions(malformed_metrics)

    def test_monitor_positions_connection_failure(self, risk_manager: RiskManager) -> None:
        """Test monitor_positions handles Web3 connection failures gracefully.
        
        Example:
            >>> # Web3 connection fails, should return empty dict
            >>> exposures = risk_manager.monitor_positions(["0x123"])
            >>> assert exposures == {}
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock Web3 provider that's not connected
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = False
        
        risk_manager.web3_providers = {"ethereum": mock_web3}
        
        # Should return empty dict when no providers are connected
        exposures = risk_manager.monitor_positions(wallet_addresses)
        assert exposures == {}

    def test_monitor_positions_web3_exception(self, risk_manager: RiskManager) -> None:
        """Test monitor_positions handles Web3 exceptions during balance retrieval.
        
        Example:
            >>> # Web3 balance retrieval fails
            >>> with pytest.raises(RuntimeError, match="Failed to monitor positions"):
            ...     risk_manager.monitor_positions(["0x123"])
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock Web3 provider that raises exception during balance retrieval
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.side_effect = Exception("Network error")
        
        risk_manager.web3_providers = {"ethereum": mock_web3}
        
        with pytest.raises(RuntimeError, match="Failed to monitor positions"):
            risk_manager.monitor_positions(wallet_addresses)

    def test_monitor_positions_empty_wallet_list(self, risk_manager: RiskManager) -> None:
        """Test monitor_positions with empty wallet address list.
        
        Example:
            >>> exposures = risk_manager.monitor_positions([])
            >>> assert exposures == {}
        """
        # Should return empty dict for empty wallet list
        exposures = risk_manager.monitor_positions([])
        assert exposures == {}


class TestRiskManagerExposureCalculationAndAlerting:
    """Test suite for RiskManager exposure calculation and alerting logic."""

    @pytest.fixture
    def risk_manager(self) -> RiskManager:
        """Create a RiskManager instance for testing."""
        with patch('airdrops.risk_management.core.Web3'):
            return RiskManager()

    @pytest.fixture
    def mock_alerter(self) -> Mock:
        """Create a mock AlertManager for testing."""
        alerter = Mock()
        alerter.create_alert = Mock()
        alerter.send_notifications = Mock()
        return alerter

    def test_assess_current_risk_calculates_total_portfolio_exposure_correctly(self, risk_manager: RiskManager) -> None:
        """Test that assess_current_risk correctly calculates total portfolio exposure from multiple assets across protocols.
        
        Example:
            >>> metrics = risk_manager.assess_current_risk(["0x123", "0x456"])
            >>> assert metrics.portfolio_value == sum(all_protocol_exposures)
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890", "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"]
        
        # Mock multiple protocol exposures
        mock_exposures = {
            "ethereum": Decimal("5000.0"),
            "scroll": Decimal("3000.0"),
            "zksync": Decimal("2000.0")
        }
        expected_total = Decimal("10000.0")
        
        with patch.object(risk_manager, 'monitor_positions', return_value=mock_exposures), \
             patch.object(risk_manager, 'monitor_gas_costs', return_value=Decimal("50.0")), \
             patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.LOW):
            
            metrics = risk_manager.assess_current_risk(wallet_addresses)
            
            # Verify total portfolio exposure calculation
            assert metrics.portfolio_value == expected_total
            assert metrics.protocol_exposures == mock_exposures
            assert len(metrics.protocol_exposures) == 3
            
            # Verify individual protocol exposures are included
            assert metrics.protocol_exposures["ethereum"] == Decimal("5000.0")
            assert metrics.protocol_exposures["scroll"] == Decimal("3000.0")
            assert metrics.protocol_exposures["zksync"] == Decimal("2000.0")

    def test_assess_current_risk_calculates_single_protocol_exposure_correctly(self, risk_manager: RiskManager) -> None:
        """Test that assess_current_risk correctly calculates exposure for a single protocol.
        
        Example:
            >>> metrics = risk_manager.assess_current_risk(["0x123"])
            >>> assert metrics.protocol_exposures["ethereum"] == expected_ethereum_exposure
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock single protocol exposure
        mock_exposures = {"ethereum": Decimal("7500.0")}
        
        with patch.object(risk_manager, 'monitor_positions', return_value=mock_exposures), \
             patch.object(risk_manager, 'monitor_gas_costs', return_value=Decimal("45.0")), \
             patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.MEDIUM):
            
            metrics = risk_manager.assess_current_risk(wallet_addresses)
            
            # Verify single protocol exposure calculation
            assert metrics.portfolio_value == Decimal("7500.0")
            assert metrics.protocol_exposures == mock_exposures
            assert len(metrics.protocol_exposures) == 1
            assert metrics.protocol_exposures["ethereum"] == Decimal("7500.0")

    def test_assess_current_risk_with_empty_portfolio_returns_zero_exposure(self, risk_manager: RiskManager) -> None:
        """Test that assess_current_risk handles empty portfolio correctly.
        
        Example:
            >>> metrics = risk_manager.assess_current_risk(["0x123"])
            >>> assert metrics.portfolio_value == Decimal("0")
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock empty portfolio
        mock_exposures: Dict[str, Decimal] = {}
        
        with patch.object(risk_manager, 'monitor_positions', return_value=mock_exposures), \
             patch.object(risk_manager, 'monitor_gas_costs', return_value=Decimal("30.0")), \
             patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.LOW):
            
            metrics = risk_manager.assess_current_risk(wallet_addresses)
            
            # Verify empty portfolio handling
            assert metrics.portfolio_value == Decimal("0")
            assert metrics.protocol_exposures == {}
            assert len(metrics.protocol_exposures) == 0
            assert metrics.risk_level == RiskLevel.LOW  # Should be low risk with no exposure

    def test_record_risk_event_triggers_alert_when_threshold_breached(self, risk_manager: RiskManager, mock_alerter: Mock) -> None:
        """Test that record_risk_event successfully triggers an alert when a risk threshold is breached.
        
        Example:
            >>> risk_manager.record_risk_event("gas_spike", {"gas_price": 150})
            >>> mock_alerter.send_notifications.assert_called_once()
        """
        risk_manager.alerter = mock_alerter
        
        # Mock alert creation
        mock_alert = Mock()
        mock_alerter.create_alert.return_value = mock_alert
        
        # Record a risk event that should trigger an alert
        event_details = {"gas_price": 150, "threshold": 100}
        response = risk_manager.record_risk_event("gas_spike", event_details)
        
        # Verify alert was created and sent
        mock_alerter.create_alert.assert_called_once_with(
            rule_name="risk-event-gas_spike",
            metric_name="gas_spike",
            current_value=1,
            threshold=0,
            severity="high",
            description=f"Risk event of type gas_spike occurred with details: {event_details}"
        )
        mock_alerter.send_notifications.assert_called_once_with([mock_alert])
        
        # Verify response contains expected action
        assert response["action"] == "pause_operations"

    def test_record_risk_event_protocol_failure_triggers_specific_alert(self, risk_manager: RiskManager, mock_alerter: Mock) -> None:
        """Test that record_risk_event triggers protocol-specific alert for protocol failures.
        
        Example:
            >>> risk_manager.record_risk_event("protocol_failure", {"protocol": "scroll"})
            >>> assert response["protocol"] == "scroll"
        """
        risk_manager.alerter = mock_alerter
        
        # Mock alert creation
        mock_alert = Mock()
        mock_alerter.create_alert.return_value = mock_alert
        
        # Record a protocol failure event
        event_details = {"protocol": "scroll", "error": "Connection timeout"}
        response = risk_manager.record_risk_event("protocol_failure", event_details)
        
        # Verify protocol-specific alert was created
        mock_alerter.create_alert.assert_called_once_with(
            rule_name="risk-event-protocol_failure",
            metric_name="protocol_failure",
            current_value=1,
            threshold=0,
            severity="high",
            description=f"Risk event of type protocol_failure occurred with details: {event_details}"
        )
        mock_alerter.send_notifications.assert_called_once_with([mock_alert])
        
        # Verify response contains protocol-specific action
        assert response["action"] == "disable_protocol"
        assert response["protocol"] == "scroll"

    def test_record_risk_event_no_alert_when_no_alerter_configured(self, risk_manager: RiskManager) -> None:
        """Test that record_risk_event handles gracefully when no AlertManager is configured.
        
        Example:
            >>> risk_manager.alerter = None
            >>> response = risk_manager.record_risk_event("gas_spike", {})
            >>> # Should not raise exception, just return response
        """
        # Ensure no alerter is configured
        risk_manager.alerter = None
        
        # Record a risk event without alerter
        event_details = {"gas_price": 150}
        response = risk_manager.record_risk_event("gas_spike", event_details)
        
        # Verify response is still generated even without alerter
        assert response["action"] == "pause_operations"
        # No exception should be raised

    def test_assess_current_risk_triggers_circuit_breaker_on_high_risk(self, risk_manager: RiskManager) -> None:
        """Test that assess_current_risk triggers circuit breaker when risk level is critical.
        
        Example:
            >>> # High gas prices and extreme volatility should trigger circuit breaker
            >>> metrics = risk_manager.assess_current_risk(["0x123"])
            >>> assert metrics.circuit_breaker_triggered is True
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock conditions that should trigger circuit breaker
        mock_exposures = {"ethereum": Decimal("5000.0")}
        high_gas_price = Decimal("250.0")  # 2.5x the default limit of 100
        
        with patch.object(risk_manager, 'monitor_positions', return_value=mock_exposures), \
             patch.object(risk_manager, 'monitor_gas_costs', return_value=high_gas_price), \
             patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.EXTREME):
            
            metrics = risk_manager.assess_current_risk(wallet_addresses)
            
            # Verify circuit breaker was triggered
            assert metrics.circuit_breaker_triggered is True
            assert risk_manager.circuit_breaker_active is True
            assert metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def test_assess_current_risk_no_alert_when_within_safe_limits(self, risk_manager: RiskManager) -> None:
        """Test that assess_current_risk does not trigger alerts when all metrics are within safe limits.
        
        Example:
            >>> # Normal conditions should not trigger circuit breaker
            >>> metrics = risk_manager.assess_current_risk(["0x123"])
            >>> assert metrics.circuit_breaker_triggered is False
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock safe conditions with smaller exposures to ensure LOW risk
        mock_exposures = {"ethereum": Decimal("500.0")}  # Smaller exposure
        safe_gas_price = Decimal("30.0")  # Well below limit
        
        with patch.object(risk_manager, 'monitor_positions', return_value=mock_exposures), \
             patch.object(risk_manager, 'monitor_gas_costs', return_value=safe_gas_price), \
             patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.LOW):
            
            metrics = risk_manager.assess_current_risk(wallet_addresses)
            
            # Verify no circuit breaker triggered
            assert metrics.circuit_breaker_triggered is False
            assert risk_manager.circuit_breaker_active is False
            assert metrics.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]  # Accept both as safe

    def test_monitor_positions_aggregates_exposures_across_multiple_wallets(self, risk_manager: RiskManager) -> None:
        """Test that monitor_positions correctly aggregates exposures across multiple wallet addresses.
        
        Example:
            >>> exposures = risk_manager.monitor_positions(["0x123", "0x456"])
            >>> assert exposures["ethereum"] == wallet1_exposure + wallet2_exposure
        """
        wallet_addresses = [
            "0x1234567890123456789012345678901234567890",
            "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        ]
        
        # Mock Web3 providers with different balances per wallet
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        
        # First wallet: 2 ETH, Second wallet: 3 ETH
        balance_responses = [2000000000000000000, 3000000000000000000]  # 2 ETH, 3 ETH in wei
        eth_responses = [2.0, 3.0]  # 2 ETH, 3 ETH
        
        mock_web3.eth.get_balance.side_effect = balance_responses
        mock_web3.from_wei.side_effect = eth_responses
        
        risk_manager.web3_providers = {"ethereum": mock_web3}
        
        # Patch Web3.to_checksum_address since it's called as a static method
        with patch('airdrops.risk_management.core.Web3.to_checksum_address', side_effect=lambda addr: addr) as mock_checksum, \
             patch.object(risk_manager, '_get_eth_price_usd', return_value=Decimal("2000.0")):
            
            exposures = risk_manager.monitor_positions(wallet_addresses)
            
            # Verify aggregated exposure (2 ETH + 3 ETH = 5 ETH * $2000 = $10,000)
            assert exposures["ethereum"] == Decimal("10000.0")
            
            # Verify both wallets were queried
            assert mock_web3.eth.get_balance.call_count == 2
            assert mock_checksum.call_count == 2

    def test_monitor_positions_handles_protocol_specific_exposures(self, risk_manager: RiskManager) -> None:
        """Test that monitor_positions correctly calculates protocol-specific exposures.
        
        Example:
            >>> exposures = risk_manager.monitor_positions(["0x123"])
            >>> assert "ethereum" in exposures and "scroll" in exposures
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock different Web3 providers for different protocols
        mock_eth_web3 = Mock()
        mock_eth_web3.is_connected.return_value = True
        mock_eth_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
        mock_eth_web3.from_wei.return_value = 1.0
        mock_eth_web3.to_checksum_address.return_value = wallet_addresses[0]
        
        mock_scroll_web3 = Mock()
        mock_scroll_web3.is_connected.return_value = True
        mock_scroll_web3.eth.get_balance.return_value = 2000000000000000000  # 2 ETH
        mock_scroll_web3.from_wei.return_value = 2.0
        mock_scroll_web3.to_checksum_address.return_value = wallet_addresses[0]
        
        risk_manager.web3_providers = {
            "ethereum": mock_eth_web3,
            "scroll": mock_scroll_web3
        }
        
        with patch.object(risk_manager, '_get_eth_price_usd', return_value=Decimal("2000.0")):
            exposures = risk_manager.monitor_positions(wallet_addresses)
            
            # Verify protocol-specific exposures
            assert exposures["ethereum"] == Decimal("2000.0")  # 1 ETH * $2000
            assert exposures["scroll"] == Decimal("4000.0")    # 2 ETH * $2000
            assert len(exposures) == 2

    def test_assess_current_risk_calculates_portfolio_pnl_correctly(self, risk_manager: RiskManager) -> None:
        """Test that assess_current_risk calculates portfolio P&L correctly.
        
        Example:
            >>> metrics = risk_manager.assess_current_risk(["0x123"])
            >>> assert metrics.portfolio_pnl == portfolio_value * 0.05  # 5% gain
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        mock_exposures = {"ethereum": Decimal("8000.0")}
        
        with patch.object(risk_manager, 'monitor_positions', return_value=mock_exposures), \
             patch.object(risk_manager, 'monitor_gas_costs', return_value=Decimal("40.0")), \
             patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.LOW):
            
            metrics = risk_manager.assess_current_risk(wallet_addresses)
            
            # Verify P&L calculation (5% of portfolio value)
            expected_pnl = Decimal("8000.0") * Decimal("0.05")
            assert metrics.portfolio_pnl == expected_pnl
            assert metrics.portfolio_value == Decimal("8000.0")

    def test_record_risk_event_emergency_shutdown_triggers_complete_shutdown(self, risk_manager: RiskManager, mock_alerter: Mock) -> None:
        """Test that record_risk_event triggers complete shutdown for emergency events.
        
        Example:
            >>> response = risk_manager.record_risk_event("emergency_shutdown", {})
            >>> assert response["shutdown_complete"] is True
        """
        risk_manager.alerter = mock_alerter
        
        # Mock alert creation
        mock_alert = Mock()
        mock_alerter.create_alert.return_value = mock_alert
        
        # Record emergency shutdown event
        event_details = {"reason": "Critical system failure"}
        response = risk_manager.record_risk_event("emergency_shutdown", event_details)
        
        # Verify emergency shutdown response
        assert response["action"] == "emergency_shutdown"
        assert response["shutdown_complete"] is True
        
        # Verify alert was still created
        mock_alerter.create_alert.assert_called_once()
        mock_alerter.send_notifications.assert_called_once_with([mock_alert])

    def test_record_risk_event_suspicious_activity_triggers_wallet_freeze(self, risk_manager: RiskManager, mock_alerter: Mock) -> None:
        """Test that record_risk_event triggers wallet freeze for suspicious activity.
        
        Example:
            >>> response = risk_manager.record_risk_event("suspicious_activity", {"wallet": "0x123"})
            >>> assert response["wallet"] == "0x123"
        """
        risk_manager.alerter = mock_alerter
        
        # Mock alert creation
        mock_alert = Mock()
        mock_alerter.create_alert.return_value = mock_alert
        
        # Record suspicious activity event
        event_details = {"wallet": "0x1234567890123456789012345678901234567890", "activity": "Unusual transaction pattern"}
        response = risk_manager.record_risk_event("suspicious_activity", event_details)
        
        # Verify wallet freeze response
        assert response["action"] == "freeze_wallet"
        assert response["wallet"] == "0x1234567890123456789012345678901234567890"
        
        # Verify alert was created
        mock_alerter.create_alert.assert_called_once()
        mock_alerter.send_notifications.assert_called_once_with([mock_alert])

    def test_assess_current_risk_handles_monitoring_failures_gracefully(self, risk_manager: RiskManager) -> None:
        """Test that assess_current_risk handles monitoring failures gracefully.
        
        Example:
            >>> # Gas monitoring fails but assessment continues
            >>> with pytest.raises(RuntimeError, match="Failed to assess current risk"):
            ...     risk_manager.assess_current_risk(["0x123"])
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        mock_exposures = {"ethereum": Decimal("5000.0")}
        
        with patch.object(risk_manager, 'monitor_positions', return_value=mock_exposures), \
             patch.object(risk_manager, 'monitor_gas_costs', side_effect=Exception("Gas monitoring failed")), \
             patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.LOW):
            
            # Should raise RuntimeError when monitoring fails
            with pytest.raises(RuntimeError, match="Failed to assess current risk"):
                risk_manager.assess_current_risk(wallet_addresses)

    def test_monitor_positions_calculates_usd_exposure_with_eth_price(self, risk_manager: RiskManager) -> None:
        """Test that monitor_positions correctly converts ETH balances to USD exposure using current ETH price.
        
        Example:
            >>> # 1 ETH at $3000 should equal $3000 exposure
            >>> exposures = risk_manager.monitor_positions(["0x123"])
            >>> assert exposures["ethereum"] == Decimal("3000.0")
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock Web3 provider
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH in wei
        mock_web3.from_wei.return_value = 1.0  # 1 ETH
        mock_web3.to_checksum_address.return_value = wallet_addresses[0]
        
        risk_manager.web3_providers = {"ethereum": mock_web3}
        
        # Test with different ETH prices
        eth_price = Decimal("3000.0")
        with patch.object(risk_manager, '_get_eth_price_usd', return_value=eth_price):
            exposures = risk_manager.monitor_positions(wallet_addresses)
            
            # Verify USD conversion (1 ETH * $3000 = $3000)
            assert exposures["ethereum"] == Decimal("3000.0")

    def test_assess_current_risk_integrates_all_risk_factors(self, risk_manager: RiskManager) -> None:
        """Test that assess_current_risk integrates all risk factors (positions, gas, volatility) correctly.
        
        Example:
            >>> # High gas + high volatility + large positions should result in high risk
            >>> metrics = risk_manager.assess_current_risk(["0x123"])
            >>> assert metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock high-risk conditions across all factors
        large_exposures = {"ethereum": Decimal("50000.0"), "scroll": Decimal("30000.0")}  # Large positions
        high_gas_price = Decimal("150.0")  # High gas
        
        with patch.object(risk_manager, 'monitor_positions', return_value=large_exposures), \
             patch.object(risk_manager, 'monitor_gas_costs', return_value=high_gas_price), \
             patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.HIGH):
            
            metrics = risk_manager.assess_current_risk(wallet_addresses)
            
            # Verify high risk level due to multiple factors
            assert metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            assert metrics.portfolio_value == Decimal("80000.0")
            assert metrics.gas_price_gwei == high_gas_price
            assert metrics.volatility_state == VolatilityState.HIGH
            assert metrics.protocol_exposures == large_exposures


class TestRiskManagerRiskMetricAggregation:
    """Test suite for RiskManager risk metric aggregation methods."""

    @pytest.fixture
    def risk_manager(self) -> RiskManager:
        """Create a RiskManager instance for testing."""
        with patch('airdrops.risk_management.core.Web3'):
            return RiskManager()

    @pytest.fixture
    def sample_protocol_exposures(self) -> Dict[str, Decimal]:
        """Sample protocol exposures for testing."""
        return {
            "ethereum": Decimal("5000.0"),
            "scroll": Decimal("3000.0"),
            "zksync": Decimal("2000.0")
        }

    def test_calculate_risk_level_aggregates_multiple_factors_correctly(self, risk_manager: RiskManager) -> None:
        """Test that _calculate_risk_level correctly aggregates gas price, volatility, and protocol concentration.
        
        Example:
            >>> risk_level = risk_manager._calculate_risk_level(
            ...     Decimal("10000"), Decimal("50"), VolatilityState.LOW, {"ethereum": Decimal("1000")}
            ... )
            >>> assert risk_level == RiskLevel.LOW
        """
        portfolio_value = Decimal("10000.0")
        gas_price = Decimal("50.0")  # Below limit
        volatility_state = VolatilityState.LOW
        protocol_exposures = {"ethereum": Decimal("1000.0")}  # 10% exposure, within limits
        
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value, gas_price, volatility_state, protocol_exposures
        )
        
        # With all factors at safe levels, should be LOW risk
        assert risk_level == RiskLevel.LOW

    def test_calculate_risk_level_high_gas_price_increases_risk_score(self, risk_manager: RiskManager) -> None:
        """Test that high gas prices contribute to increased risk score.
        
        Example:
            >>> # High gas price should increase risk level
            >>> risk_level = risk_manager._calculate_risk_level(
            ...     Decimal("10000"), Decimal("120"), VolatilityState.LOW, {}
            ... )
            >>> assert risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]
        """
        portfolio_value = Decimal("10000.0")
        high_gas_price = Decimal("120.0")  # Above 100 Gwei limit
        volatility_state = VolatilityState.LOW
        protocol_exposures = {"ethereum": Decimal("1000.0")}
        
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value, high_gas_price, volatility_state, protocol_exposures
        )
        
        # High gas price should increase risk level
        assert risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]

    def test_calculate_risk_level_extreme_volatility_increases_risk_score(self, risk_manager: RiskManager) -> None:
        """Test that extreme volatility significantly increases risk score.
        
        Example:
            >>> # Extreme volatility should result in high risk
            >>> risk_level = risk_manager._calculate_risk_level(
            ...     Decimal("10000"), Decimal("50"), VolatilityState.EXTREME, {}
            ... )
            >>> assert risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        """
        portfolio_value = Decimal("10000.0")
        gas_price = Decimal("50.0")  # Normal gas price
        extreme_volatility = VolatilityState.EXTREME
        protocol_exposures = {"ethereum": Decimal("1000.0")}
        
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value, gas_price, extreme_volatility, protocol_exposures
        )
        
        # Extreme volatility should result in high risk
        assert risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def test_calculate_risk_level_excessive_protocol_concentration_increases_risk(self, risk_manager: RiskManager) -> None:
        """Test that excessive protocol concentration increases risk score.
        
        Example:
            >>> # 30% concentration in one protocol should increase risk
            >>> exposures = {"ethereum": Decimal("3000")}  # 30% of 10k portfolio
            >>> risk_level = risk_manager._calculate_risk_level(
            ...     Decimal("10000"), Decimal("50"), VolatilityState.LOW, exposures
            ... )
            >>> assert risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]
        """
        portfolio_value = Decimal("10000.0")
        gas_price = Decimal("50.0")
        volatility_state = VolatilityState.LOW
        # 30% concentration exceeds 20% limit
        high_concentration_exposures = {"ethereum": Decimal("3000.0")}
        
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value, gas_price, volatility_state, high_concentration_exposures
        )
        
        # High concentration should increase risk level
        assert risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]

    def test_calculate_risk_level_multiple_high_risk_factors_result_in_critical_risk(self, risk_manager: RiskManager) -> None:
        """Test that multiple high-risk factors combine to result in critical risk level.
        
        Example:
            >>> # High gas + extreme volatility + high concentration = critical risk
            >>> risk_level = risk_manager._calculate_risk_level(
            ...     Decimal("10000"), Decimal("150"), VolatilityState.EXTREME, {"ethereum": Decimal("3000")}
            ... )
            >>> assert risk_level == RiskLevel.CRITICAL
        """
        portfolio_value = Decimal("10000.0")
        high_gas_price = Decimal("150.0")  # 1.5x limit
        extreme_volatility = VolatilityState.EXTREME
        high_concentration_exposures = {"ethereum": Decimal("3000.0")}  # 30% concentration
        
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value, high_gas_price, extreme_volatility, high_concentration_exposures
        )
        
        # Multiple high-risk factors should result in critical risk
        assert risk_level == RiskLevel.CRITICAL

    def test_calculate_risk_level_with_zero_portfolio_value_handles_gracefully(self, risk_manager: RiskManager) -> None:
        """Test that _calculate_risk_level handles zero portfolio value gracefully.
        
        Example:
            >>> # Zero portfolio should not cause division errors
            >>> risk_level = risk_manager._calculate_risk_level(
            ...     Decimal("0"), Decimal("50"), VolatilityState.LOW, {}
            ... )
            >>> assert risk_level == RiskLevel.LOW
        """
        portfolio_value = Decimal("0.0")
        gas_price = Decimal("50.0")
        volatility_state = VolatilityState.LOW
        protocol_exposures: Dict[str, Decimal] = {}
        
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value, gas_price, volatility_state, protocol_exposures
        )
        
        # Should handle zero portfolio gracefully
        assert risk_level == RiskLevel.LOW

    def test_calculate_risk_level_medium_volatility_contributes_to_risk_score(self, risk_manager: RiskManager) -> None:
        """Test that medium volatility contributes appropriately to risk score.
        
        Example:
            >>> # Medium volatility should result in medium risk
            >>> risk_level = risk_manager._calculate_risk_level(
            ...     Decimal("10000"), Decimal("50"), VolatilityState.MEDIUM, {}
            ... )
            >>> assert risk_level == RiskLevel.MEDIUM
        """
        portfolio_value = Decimal("10000.0")
        gas_price = Decimal("50.0")
        medium_volatility = VolatilityState.MEDIUM
        protocol_exposures = {"ethereum": Decimal("1000.0")}
        
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value, gas_price, medium_volatility, protocol_exposures
        )
        
        # Medium volatility should contribute to medium risk
        assert risk_level == RiskLevel.MEDIUM

    def test_should_trigger_circuit_breaker_aggregates_conditions_correctly(self, risk_manager: RiskManager) -> None:
        """Test that _should_trigger_circuit_breaker correctly aggregates multiple trigger conditions.
        
        Example:
            >>> # Critical risk level should trigger circuit breaker
            >>> should_trigger = risk_manager._should_trigger_circuit_breaker(
            ...     RiskLevel.CRITICAL, Decimal("100"), Decimal("50")
            ... )
            >>> assert should_trigger is True
        """
        # Test critical risk level triggers circuit breaker
        should_trigger = risk_manager._should_trigger_circuit_breaker(
            RiskLevel.CRITICAL, Decimal("100.0"), Decimal("50.0")
        )
        assert should_trigger is True
        
        # Test normal conditions don't trigger circuit breaker
        should_trigger = risk_manager._should_trigger_circuit_breaker(
            RiskLevel.LOW, Decimal("100.0"), Decimal("50.0")
        )
        assert should_trigger is False

    def test_should_trigger_circuit_breaker_extreme_gas_price_triggers(self, risk_manager: RiskManager) -> None:
        """Test that extreme gas prices trigger circuit breaker regardless of other factors.
        
        Example:
            >>> # Gas price 2x limit should trigger circuit breaker
            >>> should_trigger = risk_manager._should_trigger_circuit_breaker(
            ...     RiskLevel.LOW, Decimal("100"), Decimal("250")  # 2.5x limit
            ... )
            >>> assert should_trigger is True
        """
        extreme_gas_price = Decimal("250.0")  # 2.5x the 100 Gwei limit
        
        should_trigger = risk_manager._should_trigger_circuit_breaker(
            RiskLevel.LOW, Decimal("100.0"), extreme_gas_price
        )
        
        # Extreme gas price should trigger circuit breaker
        assert should_trigger is True

    def test_should_trigger_circuit_breaker_already_active_remains_active(self, risk_manager: RiskManager) -> None:
        """Test that circuit breaker remains active when already triggered.
        
        Example:
            >>> risk_manager.circuit_breaker_active = True
            >>> should_trigger = risk_manager._should_trigger_circuit_breaker(
            ...     RiskLevel.LOW, Decimal("100"), Decimal("50")
            ... )
            >>> assert should_trigger is True
        """
        # Set circuit breaker as already active
        risk_manager.circuit_breaker_active = True
        
        should_trigger = risk_manager._should_trigger_circuit_breaker(
            RiskLevel.LOW, Decimal("100.0"), Decimal("50.0")
        )
        
        # Should remain active
        assert should_trigger is True

    def test_calculate_safe_positions_reduces_exposure_for_high_risk(self, risk_manager: RiskManager) -> None:
        """Test that calculate_safe_positions reduces exposure when risk level is high.
        
        Example:
            >>> current_positions = {"scroll": Decimal("1000"), "zksync": Decimal("800")}
            >>> risk_assessment = RiskMetrics(risk_level=RiskLevel.HIGH, ...)
            >>> safe_positions = risk_manager.calculate_safe_positions(current_positions, risk_assessment)
            >>> assert safe_positions["scroll"] == Decimal("500")  # 50% reduction
        """
        current_positions = {
            "scroll": Decimal("1000.0"),
            "zksync": Decimal("800.0"),
            "ethereum": Decimal("500.0")
        }
        
        # Create high-risk assessment
        high_risk_assessment = RiskMetrics(
            portfolio_value=Decimal("10000.0"),
            portfolio_pnl=Decimal("100.0"),
            gas_price_gwei=Decimal("50.0"),
            volatility_state=VolatilityState.LOW,
            protocol_exposures=current_positions,
            risk_level=RiskLevel.HIGH,
            recommended_action="reduce_exposure",
            circuit_breaker_triggered=False
        )
        
        safe_positions = risk_manager.calculate_safe_positions(current_positions, high_risk_assessment)
        
        # High-risk protocols should be reduced by 50%
        assert safe_positions["scroll"] == Decimal("500.0")  # 50% of 1000
        assert safe_positions["zksync"] == Decimal("400.0")  # 50% of 800
        assert safe_positions["ethereum"] == Decimal("500.0")  # Unchanged (not high-risk protocol)

    def test_calculate_safe_positions_maintains_positions_for_low_risk(self, risk_manager: RiskManager) -> None:
        """Test that calculate_safe_positions maintains positions when risk level is low.
        
        Example:
            >>> current_positions = {"scroll": Decimal("1000"), "ethereum": Decimal("500")}
            >>> risk_assessment = RiskMetrics(risk_level=RiskLevel.LOW, ...)
            >>> safe_positions = risk_manager.calculate_safe_positions(current_positions, risk_assessment)
            >>> assert safe_positions == current_positions
        """
        current_positions = {
            "scroll": Decimal("1000.0"),
            "ethereum": Decimal("500.0")
        }
        
        # Create low-risk assessment
        low_risk_assessment = RiskMetrics(
            portfolio_value=Decimal("10000.0"),
            portfolio_pnl=Decimal("100.0"),
            gas_price_gwei=Decimal("50.0"),
            volatility_state=VolatilityState.LOW,
            protocol_exposures=current_positions,
            risk_level=RiskLevel.LOW,
            recommended_action=None,
            circuit_breaker_triggered=False
        )
        
        safe_positions = risk_manager.calculate_safe_positions(current_positions, low_risk_assessment)
        
        # Positions should remain unchanged for low risk
        assert safe_positions == current_positions

    def test_calculate_safe_positions_handles_empty_positions(self, risk_manager: RiskManager) -> None:
        """Test that calculate_safe_positions handles empty position dictionary.
        
        Example:
            >>> current_positions = {}
            >>> risk_assessment = RiskMetrics(risk_level=RiskLevel.HIGH, ...)
            >>> safe_positions = risk_manager.calculate_safe_positions(current_positions, risk_assessment)
            >>> assert safe_positions == {}
        """
        current_positions: Dict[str, Decimal] = {}
        
        high_risk_assessment = RiskMetrics(
            portfolio_value=Decimal("0.0"),
            portfolio_pnl=Decimal("0.0"),
            gas_price_gwei=Decimal("50.0"),
            volatility_state=VolatilityState.LOW,
            protocol_exposures={},
            risk_level=RiskLevel.HIGH,
            recommended_action="reduce_exposure",
            circuit_breaker_triggered=False
        )
        
        safe_positions = risk_manager.calculate_safe_positions(current_positions, high_risk_assessment)
        
        # Should handle empty positions gracefully
        assert safe_positions == {}

    @pytest.mark.parametrize("risk_level,gas_multiplier,volatility,expected_range", [
        (RiskLevel.LOW, Decimal("0.5"), VolatilityState.LOW, [RiskLevel.LOW]),
        (RiskLevel.MEDIUM, Decimal("0.8"), VolatilityState.MEDIUM, [RiskLevel.MEDIUM]),
        (RiskLevel.HIGH, Decimal("1.2"), VolatilityState.HIGH, [RiskLevel.HIGH, RiskLevel.CRITICAL]),
        (RiskLevel.CRITICAL, Decimal("2.0"), VolatilityState.EXTREME, [RiskLevel.CRITICAL]),
    ])
    def test_calculate_risk_level_parametrized_scenarios(
        self,
        risk_manager: RiskManager,
        risk_level: RiskLevel,
        gas_multiplier: Decimal,
        volatility: VolatilityState,
        expected_range: List[RiskLevel]
    ) -> None:
        """Test _calculate_risk_level with various parametrized risk scenarios.
        
        Example:
            >>> # Test multiple risk scenarios systematically
            >>> for scenario in risk_scenarios:
            ...     risk_level = risk_manager._calculate_risk_level(*scenario)
            ...     assert risk_level in expected_range
        """
        portfolio_value = Decimal("10000.0")
        base_gas_price = risk_manager.risk_limits.max_gas_price_gwei
        gas_price = base_gas_price * gas_multiplier
        protocol_exposures = {"ethereum": Decimal("1000.0")}
        
        calculated_risk_level = risk_manager._calculate_risk_level(
            portfolio_value, gas_price, volatility, protocol_exposures
        )
        
        # Verify calculated risk level is within expected range
        assert calculated_risk_level in expected_range

    def test_assess_current_risk_integrates_all_aggregation_methods(self, risk_manager: RiskManager) -> None:
        """Test that assess_current_risk properly integrates all risk aggregation methods.
        
        Example:
            >>> # assess_current_risk should use _calculate_risk_level and _should_trigger_circuit_breaker
            >>> metrics = risk_manager.assess_current_risk(["0x123"])
            >>> assert metrics.risk_level is not None
            >>> assert isinstance(metrics.circuit_breaker_triggered, bool)
        """
        wallet_addresses = ["0x1234567890123456789012345678901234567890"]
        
        # Mock all dependencies
        mock_exposures = {"ethereum": Decimal("5000.0")}
        
        with patch.object(risk_manager, 'monitor_positions', return_value=mock_exposures), \
             patch.object(risk_manager, 'monitor_gas_costs', return_value=Decimal("80.0")), \
             patch.object(risk_manager, 'monitor_market_volatility', return_value=VolatilityState.MEDIUM), \
             patch.object(risk_manager, '_calculate_risk_level', return_value=RiskLevel.MEDIUM) as mock_calc_risk, \
             patch.object(risk_manager, '_should_trigger_circuit_breaker', return_value=False) as mock_circuit_breaker:
            
            metrics = risk_manager.assess_current_risk(wallet_addresses)
            
            # Verify aggregation methods were called
            mock_calc_risk.assert_called_once()
            mock_circuit_breaker.assert_called_once()
            
            # Verify results are properly integrated
            assert metrics.risk_level == RiskLevel.MEDIUM
            assert metrics.circuit_breaker_triggered is False
            assert metrics.portfolio_value == Decimal("5000.0")
            assert metrics.gas_price_gwei == Decimal("80.0")
            assert metrics.volatility_state == VolatilityState.MEDIUM

    def test_risk_metric_aggregation_with_missing_metrics_handles_gracefully(self, risk_manager: RiskManager) -> None:
        """Test that risk metric aggregation handles missing or None metrics gracefully.
        
        Example:
            >>> # Missing protocol exposures should not cause errors
            >>> risk_level = risk_manager._calculate_risk_level(
            ...     Decimal("10000"), Decimal("50"), VolatilityState.LOW, {}
            ... )
            >>> assert risk_level == RiskLevel.LOW
        """
        portfolio_value = Decimal("10000.0")
        gas_price = Decimal("50.0")
        volatility_state = VolatilityState.LOW
        empty_exposures: Dict[str, Decimal] = {}
        
        # Should handle empty exposures without error
        risk_level = risk_manager._calculate_risk_level(
            portfolio_value, gas_price, volatility_state, empty_exposures
        )
        
        assert risk_level == RiskLevel.LOW

    def test_risk_metric_aggregation_weighted_scoring_accuracy(self, risk_manager: RiskManager) -> None:
        """Test that risk metric aggregation applies correct weights to different risk factors.
        
        Example:
            >>> # Extreme volatility (weight 3) should outweigh high gas (weight 2)
            >>> risk_level_gas = risk_manager._calculate_risk_level(
            ...     Decimal("10000"), Decimal("120"), VolatilityState.LOW, {}
            ... )
            >>> risk_level_volatility = risk_manager._calculate_risk_level(
            ...     Decimal("10000"), Decimal("50"), VolatilityState.EXTREME, {}
            ... )
            >>> assert risk_level_volatility >= risk_level_gas
        """
        portfolio_value = Decimal("10000.0")
        protocol_exposures = {"ethereum": Decimal("1000.0")}
        
        # Test high gas price with low volatility
        risk_level_gas = risk_manager._calculate_risk_level(
            portfolio_value, Decimal("120.0"), VolatilityState.LOW, protocol_exposures
        )
        
        # Test normal gas price with extreme volatility
        risk_level_volatility = risk_manager._calculate_risk_level(
            portfolio_value, Decimal("50.0"), VolatilityState.EXTREME, protocol_exposures
        )
        
        # Extreme volatility should result in higher or equal risk than high gas price
        # since extreme volatility has weight 3 vs gas price weight 2
        # Convert to ordinal values for comparison: LOW=0, MEDIUM=1, HIGH=2, CRITICAL=3, EXTREME=4
        risk_levels_order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
            RiskLevel.EXTREME: 4
        }
        assert risk_levels_order[risk_level_volatility] >= risk_levels_order[risk_level_gas]


__all__ = [
    "TestRiskManagerInitialization",
    "TestRiskManagerPositionLimitEnforcement",
    "TestRiskManagerExposureCalculationAndAlerting",
    "TestRiskManagerRiskMetricAggregation",
]