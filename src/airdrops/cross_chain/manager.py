"""
Cross-Chain Capital Management implementation.

This module provides the main CrossChainManager class that orchestrates
cross-chain capital rebalancing operations.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, TYPE_CHECKING

from airdrops.cross_chain.models import Chain, Wallet, RebalancingJob, JobStatus
from airdrops.cross_chain.bridge_adapter import BridgeAdapter

if TYPE_CHECKING:
    from airdrops.risk_management.core import RiskManager
    from airdrops.monitoring.alerter import Alerter

__all__ = [
    "CrossChainManager",
]

# Configure logging
logger = logging.getLogger(__name__)


class CrossChainManager:
    """Orchestrates cross-chain capital management and rebalancing operations.
    
    This class serves as the central coordinator for automated cross-chain
    capital rebalancing, managing liquidity thresholds, cost analysis,
    and execution of rebalancing jobs using the BridgeAdapter framework.
    
    Example:
        >>> from airdrops.cross_chain.adapters.layerzero_adapter import LayerZeroBridgeAdapter
        >>> from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol
        >>> protocol = LayerZeroProtocol("https://eth.llamarpc.com", "0x...", 1)
        >>> adapter = LayerZeroBridgeAdapter(protocol)
        >>> manager = CrossChainManager([adapter])
        >>> thresholds = {"ethereum": Decimal("1000"), "arbitrum": Decimal("500")}
        >>> manager.set_liquidity_thresholds(thresholds)
        >>> needs_rebalancing = manager.check_liquidity_thresholds()
        >>> print(f"Rebalancing needed: {needs_rebalancing}")
        Rebalancing needed: False
    """
    
    def __init__(
        self,
        bridge_adapters: Optional[List[BridgeAdapter]] = None,
        risk_manager: Optional["RiskManager"] = None,
        alerter: Optional["Alerter"] = None
    ) -> None:
        """Initialize the CrossChainManager.
        
        Sets up the manager with bridge adapters, risk management, and alerting
        capabilities that can be populated through setter methods.
        
        Args:
            bridge_adapters: List of BridgeAdapter instances for cross-chain operations.
                           If None, an empty list is used.
            risk_manager: RiskManager instance for risk assessment and control.
                         If None, risk checks will be skipped.
            alerter: Alerter instance for sending notifications about rebalancing events.
                    If None, alerts will be skipped.
        
        Example:
            >>> from airdrops.cross_chain.adapters.layerzero_adapter import LayerZeroBridgeAdapter
            >>> from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol
            >>> from airdrops.risk_management.core import RiskManager
            >>> from airdrops.monitoring.alerter import Alerter
            >>> protocol = LayerZeroProtocol("https://eth.llamarpc.com", "0x...", 1)
            >>> adapter = LayerZeroBridgeAdapter(protocol)
            >>> risk_manager = RiskManager()
            >>> alerter = Alerter()
            >>> manager = CrossChainManager([adapter], risk_manager, alerter)
        """
        self._chains: Dict[str, Chain] = {}
        self._wallets: Dict[str, Wallet] = {}
        self._liquidity_thresholds: Dict[str, Decimal] = {}
        self._active_jobs: Dict[str, RebalancingJob] = {}
        self._bridge_adapters: List[BridgeAdapter] = bridge_adapters or []
        self._risk_manager = risk_manager
        self._alerter = alerter
        logger.info(
            f"CrossChainManager initialized with "
            f"{len(self._bridge_adapters)} bridge adapters, "
            f"risk_manager={'enabled' if risk_manager else 'disabled'}, "
            f"alerter={'enabled' if alerter else 'disabled'}"
        )
    
    def add_chain(self, chain: Chain) -> None:
        """Add a blockchain network configuration.
        
        Args:
            chain: Chain configuration to add.
            
        Example:
            >>> manager = CrossChainManager()
            >>> chain = Chain("Ethereum", 1, "https://eth-mainnet.alchemyapi.io/v2/key")
            >>> manager.add_chain(chain)
        """
        if not isinstance(chain, Chain):
            raise TypeError("Expected Chain instance")
        
        self._chains[chain.name.lower()] = chain
        logger.info(f"Added chain: {chain.name} (ID: {chain.chain_id})")
    
    def add_wallet(self, wallet: Wallet) -> None:
        """Add a multi-chain wallet configuration.
        
        Args:
            wallet: Wallet configuration to add.
            
        Example:
            >>> manager = CrossChainManager()
            >>> wallet = Wallet("Main", {"ethereum": "0x123..."})
            >>> manager.add_wallet(wallet)
        """
        if not isinstance(wallet, Wallet):
            raise TypeError("Expected Wallet instance")
        
        self._wallets[wallet.name.lower()] = wallet
        logger.info(f"Added wallet: {wallet.name} with {len(wallet.addresses)} addresses")
    
    def set_liquidity_thresholds(self, thresholds: Dict[str, Decimal]) -> None:
        """Set minimum liquidity thresholds for each chain.
        
        Args:
            thresholds: Mapping of chain names to minimum liquidity amounts.
            
        Example:
            >>> manager = CrossChainManager()
            >>> thresholds = {"ethereum": Decimal("1000"), "polygon": Decimal("500")}
            >>> manager.set_liquidity_thresholds(thresholds)
        """
        if not isinstance(thresholds, dict):
            raise TypeError("Expected dictionary of thresholds")
        
        for chain_name, threshold in thresholds.items():
            if not isinstance(threshold, Decimal):
                raise TypeError(f"Threshold for {chain_name} must be Decimal")
            if threshold < 0:
                raise ValueError(f"Threshold for {chain_name} must be non-negative")
        
        self._liquidity_thresholds = {k.lower(): v for k, v in thresholds.items()}
        logger.info(f"Set liquidity thresholds for {len(thresholds)} chains")
    
    def check_liquidity_thresholds(self) -> bool:
        """Check if any chains are below their liquidity thresholds.
        
        This method would typically query actual chain balances and compare
        them against configured thresholds. For now, it returns a placeholder.
        
        Returns:
            True if rebalancing is needed, False otherwise.
            
        Example:
            >>> manager = CrossChainManager()
            >>> needs_rebalancing = manager.check_liquidity_thresholds()
            >>> print(f"Rebalancing needed: {needs_rebalancing}")
            Rebalancing needed: False
        """
        logger.info("Checking liquidity thresholds across all chains")
        
        # Placeholder implementation - would check actual balances
        # against thresholds in a real implementation
        return False
    
    def _get_adapter_for_job(self, job: RebalancingJob) -> BridgeAdapter:
        """Get the appropriate bridge adapter for a rebalancing job.
        
        This method selects the correct bridge adapter based on the job's
        source and destination chains. It checks each adapter's supported
        chains to find one that can handle the required bridge operation.
        
        Args:
            job: The rebalancing job requiring a bridge adapter.
            
        Returns:
            The appropriate BridgeAdapter instance.
            
        Raises:
            ValueError: If no suitable adapter is found for the job.
            
        Example:
            >>> job = RebalancingJob("ethereum", "arbitrum", "USDC", Decimal("100"))
            >>> adapter = manager._get_adapter_for_job(job)
            >>> print(type(adapter).__name__)
            LayerZeroBridgeAdapter
        """
        if not self._bridge_adapters:
            raise ValueError("No bridge adapters configured")
        
        for adapter in self._bridge_adapters:
            try:
                supported_chains = adapter.get_supported_chains()
                if (job.source_chain in supported_chains and
                    job.destination_chain in supported_chains):
                    # Verify the adapter supports the asset on both chains
                    source_assets = adapter.get_supported_assets(job.source_chain)
                    dest_assets = adapter.get_supported_assets(job.destination_chain)
                    if job.asset in source_assets and job.asset in dest_assets:
                        logger.debug(
                            f"Selected {type(adapter).__name__} for job {job.job_id}: "
                            f"{job.source_chain} -> {job.destination_chain}"
                        )
                        return adapter
            except Exception as e:
                logger.warning(
                    f"Error checking adapter {type(adapter).__name__}: {e}"
                )
                continue
        
        raise ValueError(
            f"No suitable bridge adapter found for {job.source_chain} -> "
            f"{job.destination_chain} with asset {job.asset}"
        )

    def initiate_rebalancing(
        self,
        source_chain: str,
        destination_chain: str,
        asset: str,
        amount: Decimal,
        recipient_address: Optional[str] = None
    ) -> RebalancingJob:
        """Initiate a cross-chain rebalancing operation.
        
        Creates and tracks a new rebalancing job for moving capital
        between chains using the appropriate bridge adapter. Integrates
        with risk management and alerting systems for safe operations.
        
        Args:
            source_chain: Name of the source blockchain.
            destination_chain: Name of the destination blockchain.
            asset: Asset symbol to transfer.
            amount: Amount to transfer.
            recipient_address: Optional recipient address. If not provided,
                             uses the wallet address for the destination chain.
            
        Returns:
            The created rebalancing job.
            
        Raises:
            ValueError: If parameters are invalid or no suitable adapter is found.
            RuntimeError: If the bridge transaction fails to initiate or risk is too high.
            
        Example:
            >>> from airdrops.cross_chain.adapters.layerzero_adapter import LayerZeroBridgeAdapter
            >>> from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol
            >>> protocol = LayerZeroProtocol("https://eth.llamarpc.com", "0x...", 1)
            >>> adapter = LayerZeroBridgeAdapter(protocol)
            >>> manager = CrossChainManager([adapter])
            >>> job = manager.initiate_rebalancing(
            ...     "ethereum", "arbitrum", "USDC", Decimal("1000"),
            ...     "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            ... )
            >>> print(f"Created job: {job.job_id}")
            Created job: abc123...
        """
        if not source_chain or not destination_chain:
            raise ValueError("Source and destination chains must be specified")
        if not asset:
            raise ValueError("Asset must be specified")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Check risk level before initiating rebalancing
        if self._risk_manager:
            try:
                risk_assessment = self._risk_manager.get_overall_risk_assessment()
                if risk_assessment.overall_risk_level.value in ["high", "extreme"]:
                    warning_msg = (
                        f"Rebalancing postponed due to {risk_assessment.overall_risk_level.value} "
                        f"risk level. Circuit breaker active: {risk_assessment.circuit_breaker_active}"
                    )
                    logger.warning(warning_msg)
                    
                    # Send warning alert if alerter is available
                    if self._alerter:
                        self._send_postponed_alert(
                            source_chain, destination_chain, asset, amount,
                            risk_assessment.overall_risk_level.value
                        )
                    
                    raise RuntimeError(
                        f"Rebalancing operation postponed due to {risk_assessment.overall_risk_level.value} risk level"
                    )
                    
                logger.info(
                    f"Risk assessment passed: {risk_assessment.overall_risk_level.value} risk level"
                )
            except RuntimeError:
                # Re-raise RuntimeError for high/extreme risk levels
                raise
            except Exception as e:
                logger.error(f"Risk assessment failed: {e}")
                # Continue with rebalancing if risk assessment fails (fail-open approach)
        
        job = RebalancingJob(
            source_chain=source_chain.lower(),
            destination_chain=destination_chain.lower(),
            asset=asset.upper(),
            amount=amount
        )
        
        # Get the appropriate bridge adapter for this job
        try:
            adapter = self._get_adapter_for_job(job)
            
            # Use a default recipient address if none provided
            if not recipient_address:
                # Try to get recipient address from configured wallets
                for wallet in self._wallets.values():
                    dest_address = wallet.get_address(job.destination_chain)
                    if dest_address:
                        recipient_address = dest_address
                        break
                
                if not recipient_address:
                    raise ValueError(
                        f"No recipient address provided and no wallet configured "
                        f"for destination chain '{job.destination_chain}'"
                    )
            
            # Update job status to in progress
            job.update_status(JobStatus.IN_PROGRESS)
            
            # Execute the bridge transaction
            tx_hash = adapter.bridge_assets(
                source_chain=job.source_chain,
                destination_chain=job.destination_chain,
                asset=job.asset,
                amount=job.amount,
                recipient_address=recipient_address
            )
            
            # Update job status to completed
            job.update_status(JobStatus.COMPLETED)
            
            logger.info(
                f"Completed rebalancing job {job.job_id}: "
                f"{amount} {asset} from {source_chain} to {destination_chain}, "
                f"tx_hash: {tx_hash}"
            )
            
            # Send success alert if alerter is available
            if self._alerter:
                self._send_success_alert(job, tx_hash)
            
        except Exception as e:
            # Update job status to failed
            job.update_status(JobStatus.FAILED)
            logger.error(
                f"Failed rebalancing job {job.job_id}: "
                f"{amount} {asset} from {source_chain} to {destination_chain}, "
                f"error: {e}"
            )
            
            # Send failure alert if alerter is available
            if self._alerter:
                self._send_failure_alert(job, str(e))
            
            raise RuntimeError(f"Rebalancing operation failed: {e}") from e
        
        finally:
            # Always track the job regardless of success/failure
            self._active_jobs[job.job_id] = job
        
        return job
    
    def get_rebalancing_status(self, job_id: str) -> Optional[JobStatus]:
        """Get the status of a rebalancing job.
        
        Args:
            job_id: Unique identifier of the rebalancing job.
            
        Returns:
            Current status of the job, or None if job not found.
            
        Example:
            >>> manager = CrossChainManager()
            >>> job = manager.initiate_rebalancing("eth", "polygon", "USDC", Decimal("100"))
            >>> status = manager.get_rebalancing_status(job.job_id)
            >>> print(status)
            JobStatus.PENDING
        """
        if not job_id:
            raise ValueError("Job ID must be specified")
        
        job = self._active_jobs.get(job_id)
        if job is None:
            logger.warning(f"Job {job_id} not found")
            return None
        
        return job.status
    
    def get_active_jobs(self) -> List[RebalancingJob]:
        """Get all active rebalancing jobs.
        
        Returns:
            List of all currently tracked rebalancing jobs.
            
        Example:
            >>> manager = CrossChainManager()
            >>> jobs = manager.get_active_jobs()
            >>> print(f"Active jobs: {len(jobs)}")
            Active jobs: 0
        """
        return list(self._active_jobs.values())
    
    def _send_success_alert(self, job: RebalancingJob, tx_hash: str) -> None:
        """Send success alert for completed rebalancing job.
        
        Args:
            job: The completed rebalancing job.
            tx_hash: Transaction hash of the successful operation.
            
        Example:
            >>> job = RebalancingJob("ethereum", "arbitrum", "USDC", Decimal("1000"))
            >>> manager._send_success_alert(job, "0x123abc...")
        """
        if not self._alerter:
            return
            
        try:
            alert = self._alerter.create_alert(
                rule_name="rebalancing-success",
                metric_name="cross_chain_rebalancing_completed",
                current_value=1.0,
                threshold=0.0,
                severity="low",
                description=(
                    f"Cross-chain rebalancing completed successfully: "
                    f"{job.amount} {job.asset} from {job.source_chain} to {job.destination_chain}. "
                    f"Job ID: {job.job_id}, Transaction: {tx_hash}"
                )
            )
            self._alerter.send_notifications([alert])
            logger.debug(f"Success alert sent for job {job.job_id}")
        except Exception as e:
            logger.error(f"Failed to send success alert for job {job.job_id}: {e}")
    
    def _send_failure_alert(self, job: RebalancingJob, error_message: str) -> None:
        """Send failure alert for failed rebalancing job.
        
        Args:
            job: The failed rebalancing job.
            error_message: Error message describing the failure.
            
        Example:
            >>> job = RebalancingJob("ethereum", "arbitrum", "USDC", Decimal("1000"))
            >>> manager._send_failure_alert(job, "Bridge adapter not found")
        """
        if not self._alerter:
            return
            
        try:
            alert = self._alerter.create_alert(
                rule_name="rebalancing-failure",
                metric_name="cross_chain_rebalancing_failed",
                current_value=1.0,
                threshold=0.0,
                severity="critical",
                description=(
                    f"Cross-chain rebalancing failed: "
                    f"{job.amount} {job.asset} from {job.source_chain} to {job.destination_chain}. "
                    f"Job ID: {job.job_id}, Error: {error_message}"
                )
            )
            self._alerter.send_notifications([alert])
            logger.debug(f"Failure alert sent for job {job.job_id}")
        except Exception as e:
            logger.error(f"Failed to send failure alert for job {job.job_id}: {e}")
    
    def _send_postponed_alert(
        self,
        source_chain: str,
        destination_chain: str,
        asset: str,
        amount: Decimal,
        risk_level: str
    ) -> None:
        """Send warning alert for postponed rebalancing due to high risk.
        
        Args:
            source_chain: Source blockchain name.
            destination_chain: Destination blockchain name.
            asset: Asset symbol.
            amount: Transfer amount.
            risk_level: Current risk level that caused postponement.
            
        Example:
            >>> manager._send_postponed_alert("ethereum", "arbitrum", "USDC", Decimal("1000"), "high")
        """
        if not self._alerter:
            return
            
        try:
            alert = self._alerter.create_alert(
                rule_name="rebalancing-postponed",
                metric_name="cross_chain_rebalancing_postponed",
                current_value=1.0,
                threshold=0.0,
                severity="medium",
                description=(
                    f"Cross-chain rebalancing postponed due to {risk_level} risk level: "
                    f"{amount} {asset} from {source_chain} to {destination_chain}. "
                    f"Operation will be retried when risk conditions improve."
                )
            )
            self._alerter.send_notifications([alert])
            logger.debug(f"Postponed alert sent for {source_chain} -> {destination_chain}")
        except Exception as e:
            logger.error(f"Failed to send postponed alert: {e}")