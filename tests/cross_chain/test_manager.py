"""
Tests for cross-chain capital management functionality.

This module contains comprehensive tests for the cross-chain capital management
system including data models and the CrossChainManager class.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from unittest.mock import Mock

from airdrops.cross_chain.models import Chain, Wallet, RebalancingJob, JobStatus
from airdrops.cross_chain.manager import CrossChainManager
from airdrops.cross_chain.bridge_adapter import BridgeAdapter


class TestChain:
    """Test cases for the Chain data model."""
    
    def test_chain_creation_valid(self) -> None:
        """Test successful creation of a Chain instance."""
        chain = Chain(
            name="Ethereum",
            chain_id=1,
            rpc_url="https://eth-mainnet.alchemyapi.io/v2/test-key"
        )
        
        assert chain.name == "Ethereum"
        assert chain.chain_id == 1
        assert chain.rpc_url == "https://eth-mainnet.alchemyapi.io/v2/test-key"
    
    def test_chain_creation_empty_name(self) -> None:
        """Test Chain creation fails with empty name."""
        with pytest.raises(ValueError, match="Chain name cannot be empty"):
            Chain(
                name="",
                chain_id=1,
                rpc_url="https://eth-mainnet.alchemyapi.io/v2/test-key"
            )
    
    def test_chain_creation_invalid_chain_id(self) -> None:
        """Test Chain creation fails with invalid chain ID."""
        with pytest.raises(ValueError, match="Chain ID must be positive"):
            Chain(
                name="Ethereum",
                chain_id=0,
                rpc_url="https://eth-mainnet.alchemyapi.io/v2/test-key"
            )
    
    def test_chain_creation_empty_rpc_url(self) -> None:
        """Test Chain creation fails with empty RPC URL."""
        with pytest.raises(ValueError, match="RPC URL cannot be empty"):
            Chain(
                name="Ethereum",
                chain_id=1,
                rpc_url=""
            )


class TestWallet:
    """Test cases for the Wallet data model."""
    
    def test_wallet_creation_valid(self) -> None:
        """Test successful creation of a Wallet instance."""
        addresses = {
            "ethereum": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87",
            "polygon": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        }
        wallet = Wallet(name="Main Wallet", addresses=addresses)
        
        assert wallet.name == "Main Wallet"
        assert len(wallet.addresses) == 2
        assert wallet.addresses["ethereum"] == "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
    
    def test_wallet_creation_empty_name(self) -> None:
        """Test Wallet creation fails with empty name."""
        with pytest.raises(ValueError, match="Wallet name cannot be empty"):
            Wallet(name="", addresses={"ethereum": "0x123"})
    
    def test_wallet_creation_no_addresses(self) -> None:
        """Test Wallet creation fails with no addresses."""
        with pytest.raises(ValueError, match="Wallet must have at least one address"):
            Wallet(name="Test Wallet", addresses={})
    
    def test_wallet_get_address_existing(self) -> None:
        """Test getting an existing address from wallet."""
        wallet = Wallet(
            name="Test",
            addresses={"ethereum": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"}
        )
        
        address = wallet.get_address("ethereum")
        assert address == "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
    
    def test_wallet_get_address_case_insensitive(self) -> None:
        """Test getting address is case insensitive."""
        wallet = Wallet(
            name="Test",
            addresses={"ethereum": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"}
        )
        
        address = wallet.get_address("ETHEREUM")
        assert address == "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
    
    def test_wallet_get_address_nonexistent(self) -> None:
        """Test getting a non-existent address returns None."""
        wallet = Wallet(
            name="Test",
            addresses={"ethereum": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"}
        )
        
        address = wallet.get_address("polygon")
        assert address is None


class TestRebalancingJob:
    """Test cases for the RebalancingJob data model."""
    
    def test_rebalancing_job_creation_valid(self) -> None:
        """Test successful creation of a RebalancingJob instance."""
        job = RebalancingJob(
            source_chain="ethereum",
            destination_chain="polygon",
            asset="USDC",
            amount=Decimal("1000.00")
        )
        
        assert job.source_chain == "ethereum"
        assert job.destination_chain == "polygon"
        assert job.asset == "USDC"
        assert job.amount == Decimal("1000.00")
        assert job.status == JobStatus.PENDING
        assert isinstance(job.job_id, str)
        assert len(job.job_id) > 0
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)
    
    def test_rebalancing_job_empty_source_chain(self) -> None:
        """Test RebalancingJob creation fails with empty source chain."""
        with pytest.raises(ValueError, match="Source chain cannot be empty"):
            RebalancingJob(
                source_chain="",
                destination_chain="polygon",
                asset="USDC",
                amount=Decimal("1000.00")
            )
    
    def test_rebalancing_job_empty_destination_chain(self) -> None:
        """Test RebalancingJob creation fails with empty destination chain."""
        with pytest.raises(ValueError, match="Destination chain cannot be empty"):
            RebalancingJob(
                source_chain="ethereum",
                destination_chain="",
                asset="USDC",
                amount=Decimal("1000.00")
            )
    
    def test_rebalancing_job_empty_asset(self) -> None:
        """Test RebalancingJob creation fails with empty asset."""
        with pytest.raises(ValueError, match="Asset cannot be empty"):
            RebalancingJob(
                source_chain="ethereum",
                destination_chain="polygon",
                asset="",
                amount=Decimal("1000.00")
            )
    
    def test_rebalancing_job_negative_amount(self) -> None:
        """Test RebalancingJob creation fails with negative amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            RebalancingJob(
                source_chain="ethereum",
                destination_chain="polygon",
                asset="USDC",
                amount=Decimal("-100.00")
            )
    
    def test_rebalancing_job_same_chains(self) -> None:
        """Test RebalancingJob creation fails with same source and destination."""
        with pytest.raises(ValueError, match="Source and destination chains must be different"):
            RebalancingJob(
                source_chain="ethereum",
                destination_chain="ethereum",
                asset="USDC",
                amount=Decimal("1000.00")
            )
    
    def test_rebalancing_job_update_status(self) -> None:
        """Test updating job status updates timestamp."""
        job = RebalancingJob(
            source_chain="ethereum",
            destination_chain="polygon",
            asset="USDC",
            amount=Decimal("1000.00")
        )
        
        original_updated_at = job.updated_at
        job.update_status(JobStatus.IN_PROGRESS)
        
        assert job.status == JobStatus.IN_PROGRESS
        assert job.updated_at > original_updated_at


class TestCrossChainManager:
    """Test cases for the CrossChainManager class."""
    
    def test_manager_initialization_no_adapters(self) -> None:
        """Test successful initialization of CrossChainManager without adapters."""
        manager = CrossChainManager()
        
        assert isinstance(manager._chains, dict)
        assert isinstance(manager._wallets, dict)
        assert isinstance(manager._liquidity_thresholds, dict)
        assert isinstance(manager._active_jobs, dict)
        assert isinstance(manager._bridge_adapters, list)
        assert len(manager._chains) == 0
        assert len(manager._wallets) == 0
        assert len(manager._liquidity_thresholds) == 0
        assert len(manager._active_jobs) == 0
        assert len(manager._bridge_adapters) == 0
    
    def test_manager_initialization_with_adapters(self) -> None:
        """Test successful initialization of CrossChainManager with adapters."""
        mock_adapter = Mock(spec=BridgeAdapter)
        manager = CrossChainManager([mock_adapter])
        
        assert len(manager._bridge_adapters) == 1
        assert manager._bridge_adapters[0] == mock_adapter
    
    def test_add_chain_valid(self) -> None:
        """Test adding a valid chain to the manager."""
        manager = CrossChainManager()
        chain = Chain("Ethereum", 1, "https://eth-mainnet.alchemyapi.io/v2/test-key")
        
        manager.add_chain(chain)
        
        assert "ethereum" in manager._chains
        assert manager._chains["ethereum"] == chain
    
    def test_add_chain_invalid_type(self) -> None:
        """Test adding invalid chain type raises TypeError."""
        manager = CrossChainManager()
        
        with pytest.raises(TypeError, match="Expected Chain instance"):
            manager.add_chain("not a chain")  # type: ignore
    
    def test_add_wallet_valid(self) -> None:
        """Test adding a valid wallet to the manager."""
        manager = CrossChainManager()
        wallet = Wallet("Main", {"ethereum": "0x123"})
        
        manager.add_wallet(wallet)
        
        assert "main" in manager._wallets
        assert manager._wallets["main"] == wallet
    
    def test_add_wallet_invalid_type(self) -> None:
        """Test adding invalid wallet type raises TypeError."""
        manager = CrossChainManager()
        
        with pytest.raises(TypeError, match="Expected Wallet instance"):
            manager.add_wallet("not a wallet")  # type: ignore
    
    def test_set_liquidity_thresholds_valid(self) -> None:
        """Test setting valid liquidity thresholds."""
        manager = CrossChainManager()
        thresholds = {
            "ethereum": Decimal("1000"),
            "polygon": Decimal("500")
        }
        
        manager.set_liquidity_thresholds(thresholds)
        
        assert len(manager._liquidity_thresholds) == 2
        assert manager._liquidity_thresholds["ethereum"] == Decimal("1000")
        assert manager._liquidity_thresholds["polygon"] == Decimal("500")
    
    def test_set_liquidity_thresholds_invalid_type(self) -> None:
        """Test setting invalid threshold type raises TypeError."""
        manager = CrossChainManager()
        
        with pytest.raises(TypeError, match="Expected dictionary of thresholds"):
            manager.set_liquidity_thresholds("not a dict")  # type: ignore
    
    def test_set_liquidity_thresholds_invalid_threshold_type(self) -> None:
        """Test setting threshold with invalid value type raises TypeError."""
        manager = CrossChainManager()
        
        with pytest.raises(TypeError, match="Threshold for ethereum must be Decimal"):
            manager.set_liquidity_thresholds({"ethereum": 1000})  # type: ignore
    
    def test_set_liquidity_thresholds_negative_value(self) -> None:
        """Test setting negative threshold raises ValueError."""
        manager = CrossChainManager()
        
        with pytest.raises(ValueError, match="Threshold for ethereum must be non-negative"):
            manager.set_liquidity_thresholds({"ethereum": Decimal("-100")})
    
    def test_check_liquidity_thresholds(self) -> None:
        """Test checking liquidity thresholds returns boolean."""
        manager = CrossChainManager()
        
        result = manager.check_liquidity_thresholds()
        
        assert isinstance(result, bool)
        assert result is False  # Placeholder implementation returns False
    
    def test_initiate_rebalancing_no_adapters(self) -> None:
        """Test initiating rebalancing with no adapters fails."""
        manager = CrossChainManager()
        
        with pytest.raises(RuntimeError, match="Rebalancing operation failed: No bridge adapters configured"):
            manager.initiate_rebalancing(
                "ethereum", "arbitrum", "USDC", Decimal("1000"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_initiate_rebalancing_empty_source_chain(self) -> None:
        """Test initiating rebalancing with empty source chain fails."""
        manager = CrossChainManager()
        
        with pytest.raises(ValueError, match="Source and destination chains must be specified"):
            manager.initiate_rebalancing("", "arbitrum", "USDC", Decimal("1000"))
    
    def test_initiate_rebalancing_empty_asset(self) -> None:
        """Test initiating rebalancing with empty asset fails."""
        manager = CrossChainManager()
        
        with pytest.raises(ValueError, match="Asset must be specified"):
            manager.initiate_rebalancing("ethereum", "arbitrum", "", Decimal("1000"))
    
    def test_initiate_rebalancing_negative_amount(self) -> None:
        """Test initiating rebalancing with negative amount fails."""
        manager = CrossChainManager()
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            manager.initiate_rebalancing("ethereum", "arbitrum", "USDC", Decimal("-100"))
    
    def test_get_rebalancing_status_existing_job(self) -> None:
        """Test getting status of existing rebalancing job."""
        # Create a mock adapter for this test
        mock_adapter = Mock(spec=BridgeAdapter)
        mock_adapter.get_supported_chains.return_value = ["ethereum", "polygon"]
        mock_adapter.get_supported_assets.return_value = ["USDC", "USDT", "ETH"]
        mock_adapter.bridge_assets.return_value = "0x123...abc"
        
        manager = CrossChainManager([mock_adapter])
        
        # Add a wallet for the destination chain
        wallet = Wallet("test_wallet", {"polygon": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"})
        manager.add_wallet(wallet)
        
        job = manager.initiate_rebalancing("ethereum", "polygon", "USDC", Decimal("1000"))
        
        status = manager.get_rebalancing_status(job.job_id)
        
        assert status == JobStatus.COMPLETED
    
    def test_get_rebalancing_status_nonexistent_job(self) -> None:
        """Test getting status of non-existent job returns None."""
        manager = CrossChainManager()
        
        status = manager.get_rebalancing_status("nonexistent-job-id")
        
        assert status is None
    
    def test_get_rebalancing_status_empty_job_id(self) -> None:
        """Test getting status with empty job ID raises ValueError."""
        manager = CrossChainManager()
        
        with pytest.raises(ValueError, match="Job ID must be specified"):
            manager.get_rebalancing_status("")
    
    def test_get_active_jobs_empty(self) -> None:
        """Test getting active jobs when none exist."""
        manager = CrossChainManager()
        
        jobs = manager.get_active_jobs()
        
        assert isinstance(jobs, list)
        assert len(jobs) == 0
    
class TestCrossChainManagerBridgeAdapterIntegration:
    """Test cases for CrossChainManager integration with BridgeAdapter framework."""
    
    def create_mock_layerzero_adapter(self) -> Mock:
        """Create a mock LayerZero adapter for testing."""
        adapter = Mock(spec=BridgeAdapter)
        adapter.get_supported_chains.return_value = ["ethereum", "arbitrum", "optimism"]
        adapter.get_supported_assets.return_value = ["USDC", "USDT", "WETH"]
        adapter.bridge_assets.return_value = "0x123abc456def789"
        return adapter
    
    def create_mock_zksync_adapter(self) -> Mock:
        """Create a mock ZkSync adapter for testing."""
        adapter = Mock(spec=BridgeAdapter)
        adapter.get_supported_chains.return_value = ["ethereum", "zksync"]
        adapter.get_supported_assets.return_value = ["ETH", "USDC", "USDT", "WETH", "DAI"]
        adapter.bridge_assets.return_value = "0xabc123def456789"
        return adapter
    
    def create_mock_scroll_adapter(self) -> Mock:
        """Create a mock Scroll adapter for testing."""
        adapter = Mock(spec=BridgeAdapter)
        adapter.get_supported_chains.return_value = ["ethereum", "scroll"]
        adapter.get_supported_assets.return_value = ["ETH", "USDC", "USDT", "WETH", "DAI"]
        adapter.bridge_assets.return_value = "0xdef456abc123789"
        return adapter
    
    def test_get_adapter_for_job_layerzero_success(self) -> None:
        """Test manager correctly selects LayerZero adapter for LayerZero job."""
        layerzero_adapter = self.create_mock_layerzero_adapter()
        zksync_adapter = self.create_mock_zksync_adapter()
        
        manager = CrossChainManager([layerzero_adapter, zksync_adapter])
        job = RebalancingJob("ethereum", "arbitrum", "USDC", Decimal("100"))
        
        adapter = manager._get_adapter_for_job(job)
        
        assert adapter == layerzero_adapter
        layerzero_adapter.get_supported_chains.assert_called_once()
        layerzero_adapter.get_supported_assets.assert_called()
    
    def test_get_adapter_for_job_zksync_success(self) -> None:
        """Test manager correctly selects ZkSync adapter for ZkSync job."""
        layerzero_adapter = self.create_mock_layerzero_adapter()
        zksync_adapter = self.create_mock_zksync_adapter()
        
        manager = CrossChainManager([layerzero_adapter, zksync_adapter])
        job = RebalancingJob("ethereum", "zksync", "ETH", Decimal("0.1"))
        
        adapter = manager._get_adapter_for_job(job)
        
        assert adapter == zksync_adapter
        zksync_adapter.get_supported_chains.assert_called_once()
        zksync_adapter.get_supported_assets.assert_called()
    
    def test_get_adapter_for_job_scroll_success(self) -> None:
        """Test manager correctly selects Scroll adapter for Scroll job."""
        layerzero_adapter = self.create_mock_layerzero_adapter()
        scroll_adapter = self.create_mock_scroll_adapter()
        
        manager = CrossChainManager([layerzero_adapter, scroll_adapter])
        job = RebalancingJob("ethereum", "scroll", "ETH", Decimal("0.5"))
        
        adapter = manager._get_adapter_for_job(job)
        
        assert adapter == scroll_adapter
        scroll_adapter.get_supported_chains.assert_called_once()
        scroll_adapter.get_supported_assets.assert_called()
    
    def test_get_adapter_for_job_no_suitable_adapter(self) -> None:
        """Test manager raises error when no suitable adapter can be found."""
        layerzero_adapter = self.create_mock_layerzero_adapter()
        
        manager = CrossChainManager([layerzero_adapter])
        job = RebalancingJob("ethereum", "polygon", "USDC", Decimal("100"))
        
        with pytest.raises(ValueError, match="No suitable bridge adapter found"):
            manager._get_adapter_for_job(job)
    
    def test_get_adapter_for_job_unsupported_asset(self) -> None:
        """Test manager raises error when adapter doesn't support the asset."""
        adapter = Mock(spec=BridgeAdapter)
        adapter.get_supported_chains.return_value = ["ethereum", "arbitrum"]
        adapter.get_supported_assets.return_value = ["USDC", "USDT"]  # No WBTC
        
        manager = CrossChainManager([adapter])
        job = RebalancingJob("ethereum", "arbitrum", "WBTC", Decimal("0.1"))
        
        with pytest.raises(ValueError, match="No suitable bridge adapter found"):
            manager._get_adapter_for_job(job)
    
    def test_get_adapter_for_job_adapter_exception(self) -> None:
        """Test manager handles adapter exceptions gracefully."""
        adapter1 = Mock(spec=BridgeAdapter)
        adapter1.get_supported_chains.side_effect = Exception("Network error")
        
        adapter2 = self.create_mock_layerzero_adapter()
        
        manager = CrossChainManager([adapter1, adapter2])
        job = RebalancingJob("ethereum", "arbitrum", "USDC", Decimal("100"))
        
        # Should skip the failing adapter and use the working one
        adapter = manager._get_adapter_for_job(job)
        assert adapter == adapter2
    
    def test_initiate_rebalancing_with_layerzero_adapter(self) -> None:
        """Test successful rebalancing with LayerZero adapter."""
        layerzero_adapter = self.create_mock_layerzero_adapter()
        
        manager = CrossChainManager([layerzero_adapter])
        
        # Add a wallet for recipient address
        wallet = Wallet("test", {"arbitrum": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"})
        manager.add_wallet(wallet)
        
        job = manager.initiate_rebalancing(
            "ethereum", "arbitrum", "USDC", Decimal("1000")
        )
        
        assert isinstance(job, RebalancingJob)
        assert job.source_chain == "ethereum"
        assert job.destination_chain == "arbitrum"
        assert job.asset == "USDC"
        assert job.amount == Decimal("1000")
        assert job.status == JobStatus.COMPLETED
        assert job.job_id in manager._active_jobs
        
        layerzero_adapter.bridge_assets.assert_called_once_with(
            source_chain="ethereum",
            destination_chain="arbitrum",
            asset="USDC",
            amount=Decimal("1000"),
            recipient_address="0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
    
    def test_initiate_rebalancing_with_zksync_adapter(self) -> None:
        """Test successful rebalancing with ZkSync adapter."""
        zksync_adapter = self.create_mock_zksync_adapter()
        
        manager = CrossChainManager([zksync_adapter])
        
        job = manager.initiate_rebalancing(
            "ethereum", "zksync", "ETH", Decimal("0.1"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert isinstance(job, RebalancingJob)
        assert job.source_chain == "ethereum"
        assert job.destination_chain == "zksync"
        assert job.asset == "ETH"
        assert job.amount == Decimal("0.1")
        assert job.status == JobStatus.COMPLETED
        
        zksync_adapter.bridge_assets.assert_called_once_with(
            source_chain="ethereum",
            destination_chain="zksync",
            asset="ETH",
            amount=Decimal("0.1"),
            recipient_address="0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
    
    def test_initiate_rebalancing_with_scroll_adapter(self) -> None:
        """Test successful rebalancing with Scroll adapter."""
        scroll_adapter = self.create_mock_scroll_adapter()
        
        manager = CrossChainManager([scroll_adapter])
        
        job = manager.initiate_rebalancing(
            "ethereum", "scroll", "ETH", Decimal("0.5"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert isinstance(job, RebalancingJob)
        assert job.source_chain == "ethereum"
        assert job.destination_chain == "scroll"
        assert job.asset == "ETH"
        assert job.amount == Decimal("0.5")
        assert job.status == JobStatus.COMPLETED
        
        scroll_adapter.bridge_assets.assert_called_once_with(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("0.5"),
            recipient_address="0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
    
    def test_initiate_rebalancing_no_recipient_address_no_wallet(self) -> None:
        """Test rebalancing fails when no recipient address and no wallet configured."""
        layerzero_adapter = self.create_mock_layerzero_adapter()
        
        manager = CrossChainManager([layerzero_adapter])
        
        with pytest.raises(RuntimeError, match="Rebalancing operation failed"):
            manager.initiate_rebalancing(
                "ethereum", "arbitrum", "USDC", Decimal("1000")
            )
    
    def test_initiate_rebalancing_bridge_failure(self) -> None:
        """Test rebalancing handles bridge adapter failures."""
        adapter = Mock(spec=BridgeAdapter)
        adapter.get_supported_chains.return_value = ["ethereum", "arbitrum"]
        adapter.get_supported_assets.return_value = ["USDC", "USDT"]
        adapter.bridge_assets.side_effect = Exception("Bridge transaction failed")
        
        manager = CrossChainManager([adapter])
        
        with pytest.raises(RuntimeError, match="Rebalancing operation failed"):
            manager.initiate_rebalancing(
                "ethereum", "arbitrum", "USDC", Decimal("1000"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
        
        # Job should still be tracked even if it failed
        jobs = manager.get_active_jobs()
        assert len(jobs) == 1
        assert jobs[0].status == JobStatus.FAILED
    
    def test_initiate_rebalancing_multiple_adapters_selection(self) -> None:
        """Test manager selects correct adapter when multiple are available."""
        layerzero_adapter = self.create_mock_layerzero_adapter()
        zksync_adapter = self.create_mock_zksync_adapter()
        scroll_adapter = self.create_mock_scroll_adapter()
        
        manager = CrossChainManager([layerzero_adapter, zksync_adapter, scroll_adapter])
        
        # Test LayerZero selection
        job1 = manager.initiate_rebalancing(
            "ethereum", "arbitrum", "USDC", Decimal("100"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        assert job1.status == JobStatus.COMPLETED
        layerzero_adapter.bridge_assets.assert_called_once()
        
        # Test ZkSync selection
        job2 = manager.initiate_rebalancing(
            "ethereum", "zksync", "ETH", Decimal("0.1"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        assert job2.status == JobStatus.COMPLETED
        zksync_adapter.bridge_assets.assert_called_once()
        
        # Test Scroll selection
        job3 = manager.initiate_rebalancing(
            "ethereum", "scroll", "ETH", Decimal("0.2"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        assert job3.status == JobStatus.COMPLETED
        scroll_adapter.bridge_assets.assert_called_once()


class TestCrossChainManagerRiskAndAlertingIntegration:
    """Test cases for CrossChainManager integration with RiskManager and Alerter."""
    
    def create_mock_risk_manager(self, risk_level: str = "low", circuit_breaker_active: bool = False) -> Mock:
        """Create a mock RiskManager for testing."""
        risk_manager = Mock()
        
        # Create mock risk assessment
        risk_assessment = Mock()
        risk_assessment.overall_risk_level.value = risk_level
        risk_assessment.circuit_breaker_active = circuit_breaker_active
        
        risk_manager.get_overall_risk_assessment.return_value = risk_assessment
        return risk_manager
    
    def create_mock_alerter(self) -> Mock:
        """Create a mock Alerter for testing."""
        alerter = Mock()
        
        # Create mock alert
        mock_alert = Mock()
        alerter.create_alert.return_value = mock_alert
        alerter.send_notifications.return_value = None
        
        return alerter
    
    def create_mock_adapter(self) -> Mock:
        """Create a mock bridge adapter for testing."""
        adapter = Mock(spec=BridgeAdapter)
        adapter.get_supported_chains.return_value = ["ethereum", "arbitrum"]
        adapter.get_supported_assets.return_value = ["USDC", "USDT"]
        adapter.bridge_assets.return_value = "0x123abc456def789"
        return adapter
    
    def test_manager_initialization_with_risk_manager_and_alerter(self) -> None:
        """Test CrossChainManager initialization with RiskManager and Alerter."""
        risk_manager = self.create_mock_risk_manager()
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        assert manager._risk_manager == risk_manager
        assert manager._alerter == alerter
        assert len(manager._bridge_adapters) == 1
    
    def test_manager_initialization_without_risk_manager_and_alerter(self) -> None:
        """Test CrossChainManager initialization without RiskManager and Alerter."""
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter])
        
        assert manager._risk_manager is None
        assert manager._alerter is None
        assert len(manager._bridge_adapters) == 1
    
    def test_rebalancing_postponed_due_to_high_risk(self) -> None:
        """Test rebalancing is postponed when risk level is high."""
        risk_manager = self.create_mock_risk_manager(risk_level="high")
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        with pytest.raises(RuntimeError, match="Rebalancing operation postponed due to high risk level"):
            manager.initiate_rebalancing(
                "ethereum", "arbitrum", "USDC", Decimal("1000"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
        
        # Verify risk assessment was called
        risk_manager.get_overall_risk_assessment.assert_called_once()
        
        # Verify postponed alert was sent
        alerter.create_alert.assert_called_once()
        alerter.send_notifications.assert_called_once()
        
        # Verify bridge was not called
        adapter.bridge_assets.assert_not_called()
    
    def test_rebalancing_postponed_due_to_extreme_risk(self) -> None:
        """Test rebalancing is postponed when risk level is extreme."""
        risk_manager = self.create_mock_risk_manager(risk_level="extreme", circuit_breaker_active=True)
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        with pytest.raises(RuntimeError, match="Rebalancing operation postponed due to extreme risk level"):
            manager.initiate_rebalancing(
                "ethereum", "arbitrum", "USDC", Decimal("1000"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
        
        # Verify risk assessment was called
        risk_manager.get_overall_risk_assessment.assert_called_once()
        
        # Verify postponed alert was sent
        alerter.create_alert.assert_called_once()
        alerter.send_notifications.assert_called_once()
        
        # Verify bridge was not called
        adapter.bridge_assets.assert_not_called()
    
    def test_rebalancing_proceeds_with_low_risk(self) -> None:
        """Test rebalancing proceeds when risk level is low."""
        risk_manager = self.create_mock_risk_manager(risk_level="low")
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        job = manager.initiate_rebalancing(
            "ethereum", "arbitrum", "USDC", Decimal("1000"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        # Verify job was created and completed
        assert isinstance(job, RebalancingJob)
        assert job.status == JobStatus.COMPLETED
        
        # Verify risk assessment was called
        risk_manager.get_overall_risk_assessment.assert_called_once()
        
        # Verify success alert was sent
        assert alerter.create_alert.call_count == 1
        assert alerter.send_notifications.call_count == 1
        
        # Verify bridge was called
        adapter.bridge_assets.assert_called_once()
    
    def test_rebalancing_proceeds_with_medium_risk(self) -> None:
        """Test rebalancing proceeds when risk level is medium."""
        risk_manager = self.create_mock_risk_manager(risk_level="medium")
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        job = manager.initiate_rebalancing(
            "ethereum", "arbitrum", "USDC", Decimal("1000"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        # Verify job was created and completed
        assert isinstance(job, RebalancingJob)
        assert job.status == JobStatus.COMPLETED
        
        # Verify risk assessment was called
        risk_manager.get_overall_risk_assessment.assert_called_once()
        
        # Verify success alert was sent
        assert alerter.create_alert.call_count == 1
        assert alerter.send_notifications.call_count == 1
        
        # Verify bridge was called
        adapter.bridge_assets.assert_called_once()
    
    def test_success_alert_sent_on_successful_rebalancing(self) -> None:
        """Test success alert is sent when rebalancing completes successfully."""
        risk_manager = self.create_mock_risk_manager(risk_level="low")
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        job = manager.initiate_rebalancing(
            "ethereum", "arbitrum", "USDC", Decimal("1000"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        # Verify success alert was created with correct parameters
        alerter.create_alert.assert_called_once_with(
            rule_name="rebalancing-success",
            metric_name="cross_chain_rebalancing_completed",
            current_value=1.0,
            threshold=0.0,
            severity="low",
            description=(
                f"Cross-chain rebalancing completed successfully: "
                f"{job.amount} {job.asset} from {job.source_chain} to {job.destination_chain}. "
                f"Job ID: {job.job_id}, Transaction: 0x123abc456def789"
            )
        )
        
        # Verify notification was sent
        alerter.send_notifications.assert_called_once()
    
    def test_failure_alert_sent_on_failed_rebalancing(self) -> None:
        """Test failure alert is sent when rebalancing fails."""
        risk_manager = self.create_mock_risk_manager(risk_level="low")
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        # Make bridge operation fail
        adapter.bridge_assets.side_effect = Exception("Bridge transaction failed")
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        with pytest.raises(RuntimeError, match="Rebalancing operation failed"):
            manager.initiate_rebalancing(
                "ethereum", "arbitrum", "USDC", Decimal("1000"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
        
        # Verify failure alert was created with correct parameters
        alerter.create_alert.assert_called_once_with(
            rule_name="rebalancing-failure",
            metric_name="cross_chain_rebalancing_failed",
            current_value=1.0,
            threshold=0.0,
            severity="critical",
            description=(
                f"Cross-chain rebalancing failed: "
                f"1000 USDC from ethereum to arbitrum. "
                f"Job ID: {manager.get_active_jobs()[0].job_id}, Error: Bridge transaction failed"
            )
        )
        
        # Verify notification was sent
        alerter.send_notifications.assert_called_once()
    
    def test_warning_alert_sent_on_postponed_rebalancing(self) -> None:
        """Test warning alert is sent when rebalancing is postponed due to high risk."""
        risk_manager = self.create_mock_risk_manager(risk_level="high")
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        with pytest.raises(RuntimeError, match="Rebalancing operation postponed"):
            manager.initiate_rebalancing(
                "ethereum", "arbitrum", "USDC", Decimal("1000"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
        
        # Verify postponed alert was created with correct parameters
        alerter.create_alert.assert_called_once_with(
            rule_name="rebalancing-postponed",
            metric_name="cross_chain_rebalancing_postponed",
            current_value=1.0,
            threshold=0.0,
            severity="medium",
            description=(
                "Cross-chain rebalancing postponed due to high risk level: "
                "1000 USDC from ethereum to arbitrum. "
                "Operation will be retried when risk conditions improve."
            )
        )
        
        # Verify notification was sent
        alerter.send_notifications.assert_called_once()
    
    def test_rebalancing_continues_when_risk_assessment_fails(self) -> None:
        """Test rebalancing continues when risk assessment fails (fail-open approach)."""
        risk_manager = Mock()
        risk_manager.get_overall_risk_assessment.side_effect = Exception("Risk assessment failed")
        
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        job = manager.initiate_rebalancing(
            "ethereum", "arbitrum", "USDC", Decimal("1000"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        # Verify job was created and completed despite risk assessment failure
        assert isinstance(job, RebalancingJob)
        assert job.status == JobStatus.COMPLETED
        
        # Verify risk assessment was attempted
        risk_manager.get_overall_risk_assessment.assert_called_once()
        
        # Verify bridge was called
        adapter.bridge_assets.assert_called_once()
    
    def test_rebalancing_without_risk_manager(self) -> None:
        """Test rebalancing works when no risk manager is provided."""
        alerter = self.create_mock_alerter()
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], None, alerter)
        
        job = manager.initiate_rebalancing(
            "ethereum", "arbitrum", "USDC", Decimal("1000"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        # Verify job was created and completed
        assert isinstance(job, RebalancingJob)
        assert job.status == JobStatus.COMPLETED
        
        # Verify bridge was called
        adapter.bridge_assets.assert_called_once()
        
        # Verify success alert was sent
        alerter.create_alert.assert_called_once()
        alerter.send_notifications.assert_called_once()
    
    def test_rebalancing_without_alerter(self) -> None:
        """Test rebalancing works when no alerter is provided."""
        risk_manager = self.create_mock_risk_manager(risk_level="low")
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, None)
        
        job = manager.initiate_rebalancing(
            "ethereum", "arbitrum", "USDC", Decimal("1000"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        # Verify job was created and completed
        assert isinstance(job, RebalancingJob)
        assert job.status == JobStatus.COMPLETED
        
        # Verify risk assessment was called
        risk_manager.get_overall_risk_assessment.assert_called_once()
        
        # Verify bridge was called
        adapter.bridge_assets.assert_called_once()
    
    def test_alert_sending_handles_exceptions_gracefully(self) -> None:
        """Test that alert sending exceptions don't break rebalancing operations."""
        risk_manager = self.create_mock_risk_manager(risk_level="low")
        alerter = Mock()
        alerter.create_alert.side_effect = Exception("Alert creation failed")
        adapter = self.create_mock_adapter()
        
        manager = CrossChainManager([adapter], risk_manager, alerter)
        
        # Should complete successfully despite alert failure
        job = manager.initiate_rebalancing(
            "ethereum", "arbitrum", "USDC", Decimal("1000"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        # Verify job was created and completed
        assert isinstance(job, RebalancingJob)
        assert job.status == JobStatus.COMPLETED
        
        # Verify bridge was called
        adapter.bridge_assets.assert_called_once()
        
        # Verify alert creation was attempted
        alerter.create_alert.assert_called_once()