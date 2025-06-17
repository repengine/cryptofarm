"""
Core data models for cross-chain capital management.

This module defines the fundamental data structures used for cross-chain
capital management and rebalancing operations.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

__all__ = [
    "Chain",
    "Wallet",
    "RebalancingJob",
    "JobStatus",
]


@dataclass
class Chain:
    """Represents a blockchain network configuration.
    
    This class stores chain-specific configuration data including
    network identifiers, RPC endpoints, and metadata.
    
    Example:
        >>> chain = Chain(
        ...     name="Ethereum",
        ...     chain_id=1,
        ...     rpc_url="https://eth-mainnet.alchemyapi.io/v2/your-api-key"
        ... )
        >>> print(f"Chain: {chain.name} (ID: {chain.chain_id})")
        Chain: Ethereum (ID: 1)
    """
    
    name: str
    chain_id: int
    rpc_url: str
    
    def __post_init__(self) -> None:
        """Validate chain data after initialization."""
        if not self.name:
            raise ValueError("Chain name cannot be empty")
        if self.chain_id <= 0:
            raise ValueError("Chain ID must be positive")
        if not self.rpc_url:
            raise ValueError("RPC URL cannot be empty")


@dataclass
class Wallet:
    """Represents a multi-chain wallet configuration.
    
    This class stores wallet addresses across multiple blockchain networks,
    enabling cross-chain operations and balance tracking.
    
    Example:
        >>> wallet = Wallet(
        ...     name="Main Wallet",
        ...     addresses={
        ...         "ethereum": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87",
        ...         "polygon": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        ...     }
        ... )
        >>> print(f"Wallet has {len(wallet.addresses)} addresses")
        Wallet has 2 addresses
    """
    
    name: str
    addresses: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate wallet data after initialization."""
        if not self.name:
            raise ValueError("Wallet name cannot be empty")
        if not self.addresses:
            raise ValueError("Wallet must have at least one address")
    
    def get_address(self, chain_name: str) -> Optional[str]:
        """Get wallet address for a specific chain.
        
        Args:
            chain_name: Name of the blockchain network.
            
        Returns:
            Wallet address for the chain, or None if not found.
            
        Example:
            >>> wallet = Wallet("Test", {"ethereum": "0x123..."})
            >>> addr = wallet.get_address("ethereum")
            >>> print(addr)
            0x123...
        """
        return self.addresses.get(chain_name.lower())


class JobStatus(str, Enum):
    """Enumeration of rebalancing job statuses.
    
    Defines the possible states of a cross-chain rebalancing operation
    throughout its lifecycle.
    """
    
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class RebalancingJob:
    """Represents a cross-chain capital rebalancing operation.
    
    This class tracks the state and metadata of a single cross-chain
    transfer operation from initiation to completion.
    
    Example:
        >>> job = RebalancingJob(
        ...     source_chain="ethereum",
        ...     destination_chain="polygon",
        ...     asset="USDC",
        ...     amount=Decimal("1000.00")
        ... )
        >>> print(f"Job {job.job_id}: {job.amount} {job.asset}")
        Job abc123...: 1000.00 USDC
    """
    
    source_chain: str
    destination_chain: str
    asset: str
    amount: Decimal
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self) -> None:
        """Validate rebalancing job data after initialization."""
        if not self.source_chain:
            raise ValueError("Source chain cannot be empty")
        if not self.destination_chain:
            raise ValueError("Destination chain cannot be empty")
        if not self.asset:
            raise ValueError("Asset cannot be empty")
        if self.amount <= 0:
            raise ValueError("Amount must be positive")
        if self.source_chain == self.destination_chain:
            raise ValueError("Source and destination chains must be different")
    
    def update_status(self, new_status: JobStatus) -> None:
        """Update the job status and timestamp.
        
        Args:
            new_status: The new status to set.
            
        Example:
            >>> job = RebalancingJob("eth", "polygon", "USDC", Decimal("100"))
            >>> job.update_status(JobStatus.IN_PROGRESS)
            >>> print(job.status)
            JobStatus.IN_PROGRESS
        """
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)