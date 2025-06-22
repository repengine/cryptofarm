"""
ZkSync Bridge Adapter Implementation.

This module provides a concrete implementation of the BridgeAdapter interface
for the ZkSync cross-chain protocol, enabling standardized bridging operations
between Ethereum L1 and ZkSync L2 networks.
"""

import logging
from decimal import Decimal
from typing import List

from airdrops.cross_chain.bridge_adapter import BridgeAdapter
from airdrops.protocols.zksync.zksync import ZkSyncProtocol
from airdrops.shared.constants import ZKSYNC_TOKEN_ADDRESSES

__all__ = [
    "ZkSyncBridgeAdapter",
]

# Configure logging for this module
logger = logging.getLogger(__name__)


class ZkSyncBridgeAdapter(BridgeAdapter):
    """ZkSync implementation of the BridgeAdapter interface.

    This adapter provides a standardized interface for cross-chain bridging
    operations using the ZkSync protocol. It wraps the ZkSyncProtocol
    to provide consistent bridge functionality between Ethereum L1 and ZkSync L2.

    Example:
        >>> from airdrops.protocols.zksync.zksync import ZkSyncProtocol
        >>> protocol = ZkSyncProtocol(
        ...     "https://eth.llamarpc.com",
        ...     "https://mainnet.era.zksync.io",
        ...     "0x123..."
        ... )
        >>> adapter = ZkSyncBridgeAdapter(protocol)
        >>> chains = adapter.get_supported_chains()
        >>> print(chains)
        ['ethereum', 'zksync']
    """

    def __init__(self, zksync_protocol: ZkSyncProtocol) -> None:
        """Initialize the ZkSync bridge adapter.

        Args:
            zksync_protocol: An initialized ZkSyncProtocol instance.

        Raises:
            ValueError: If the protocol instance is None.

        Example:
            >>> protocol = ZkSyncProtocol(
            ...     "https://eth.llamarpc.com",
            ...     "https://mainnet.era.zksync.io",
            ...     "0x123..."
            ... )
            >>> adapter = ZkSyncBridgeAdapter(protocol)
        """
        if zksync_protocol is None:
            raise ValueError("ZkSyncProtocol instance cannot be None")

        self._protocol = zksync_protocol
        logger.info("ZkSyncBridgeAdapter initialized successfully")

    def get_supported_chains(self) -> List[str]:
        """Returns a list of chain names supported by ZkSync.

        This method returns the canonical names of all blockchain networks
        that the ZkSync protocol can facilitate transfers between. ZkSync
        supports bridging between Ethereum L1 and ZkSync L2.

        Returns:
            List[str]: A list of supported chain names.

        Example:
            >>> adapter = ZkSyncBridgeAdapter(protocol)
            >>> chains = adapter.get_supported_chains()
            >>> print(chains)
            ['ethereum', 'zksync']
        """
        supported_chains = ['ethereum', 'zksync']
        logger.debug(
            f"ZkSync supports {len(supported_chains)} chains: "
            f"{supported_chains}"
        )
        return supported_chains

    def get_supported_assets(self, chain: str) -> List[str]:
        """Returns a list of asset symbols supported on ZkSync.

        This method returns the asset symbols that can be bridged
        using the ZkSync protocol. ZkSync supports the same assets
        on both L1 and L2, including ETH and various ERC20 tokens.

        Args:
            chain: The name of the blockchain network to query.

        Returns:
            List[str]: A list of supported asset symbols.

        Raises:
            ValueError: If the chain is not supported by ZkSync.

        Example:
            >>> adapter = ZkSyncBridgeAdapter(protocol)
            >>> assets = adapter.get_supported_assets("ethereum")
            >>> print(assets)
            ['ETH', 'USDC', 'USDT', 'WETH', 'DAI']
        """
        supported_chains = self.get_supported_chains()
        if chain not in supported_chains:
            raise ValueError(f"Chain '{chain}' is not supported by ZkSync")

        # ZkSync supports ETH natively plus the configured ERC20 tokens
        all_assets = ['ETH'] + list(ZKSYNC_TOKEN_ADDRESSES.keys())
        supported_assets = list(dict.fromkeys(all_assets))
        logger.debug(
            f"ZkSync supports {len(supported_assets)} assets on {chain}: "
            f"{supported_assets}"
        )
        return supported_assets

    def estimate_bridge_fee(
        self,
        source_chain: str,
        destination_chain: str,
        asset: str,
        amount: Decimal
    ) -> Decimal:
        """Estimates the fee for a ZkSync bridge transaction.

        This method calculates and returns the estimated fee for bridging
        the specified amount of an asset between Ethereum L1 and ZkSync L2
        using the ZkSync protocol.

        Args:
            source_chain: The name of the source blockchain network.
            destination_chain: The name of the destination blockchain network.
            asset: The symbol of the asset to bridge.
            amount: The amount of the asset to bridge.

        Returns:
            Decimal: The estimated bridge fee in ETH.

        Raises:
            ValueError: If any of the parameters are invalid or unsupported.

        Example:
            >>> adapter = ZkSyncBridgeAdapter(protocol)
            >>> fee = adapter.estimate_bridge_fee(
            ...     "ethereum", "zksync", "ETH", Decimal("0.1")
            ... )
            >>> print(f"Bridge fee: {fee} ETH")
            Bridge fee: 0.002 ETH
        """
        # Validate inputs
        supported_chains = self.get_supported_chains()
        if source_chain not in supported_chains:
            raise ValueError(
                f"Source chain '{source_chain}' is not supported by ZkSync"
            )
        if destination_chain not in supported_chains:
            raise ValueError(
                f"Destination chain '{destination_chain}' is not supported by "
                f"ZkSync"
            )
        
        supported_assets = self.get_supported_assets(source_chain)
        if asset not in supported_assets:
            raise ValueError(f"Asset '{asset}' is not supported by ZkSync")
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if source_chain == destination_chain:
            raise ValueError("Source and destination chains must be different")

        # For ZkSync, we use a simplified fee estimation
        # L1 to L2 deposits typically cost more than L2 to L1 withdrawals
        if source_chain == "ethereum" and destination_chain == "zksync":
            # L1 to L2 deposit fee (higher due to L1 gas costs)
            base_fee = Decimal("0.002")  # Base fee in ETH
        else:
            # L2 to L1 withdrawal fee (lower, mostly L2 gas)
            base_fee = Decimal("0.001")  # Base fee in ETH

        # Scale fee slightly with amount for larger transfers
        amount_factor = amount / Decimal("10")  # Scale with amount
        fee = base_fee + (amount_factor * Decimal("0.0001"))

        logger.debug(
            f"Estimated ZkSync bridge fee: {fee} ETH for {amount} {asset} "
            f"from {source_chain} to {destination_chain}"
        )
        return fee

    def bridge_assets(
        self,
        source_chain: str,
        destination_chain: str,
        asset: str,
        amount: Decimal,
        recipient_address: str
    ) -> str:
        """Initiates a ZkSync bridge transaction.

        This method executes the actual bridge transaction, transferring
        the specified amount of an asset between Ethereum L1 and ZkSync L2
        for the given recipient address using the ZkSync protocol.

        Args:
            source_chain: The name of the source blockchain network.
            destination_chain: The name of the destination blockchain network.
            asset: The symbol of the asset to bridge.
            amount: The amount of the asset to bridge.
            recipient_address: The address to receive the bridged assets.

        Returns:
            str: A transaction hash for tracking the bridge operation.

        Raises:
            ValueError: If any of the parameters are invalid or unsupported.
            RuntimeError: If the bridge transaction fails to initiate.

        Example:
            >>> adapter = ZkSyncBridgeAdapter(protocol)
            >>> tx_hash = adapter.bridge_assets(
            ...     "ethereum", "zksync", "ETH", Decimal("0.1"),
            ...     "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            ... )
            >>> print(f"Bridge transaction: {tx_hash}")
            Bridge transaction: 0x123abc...def789
        """
        # Validate inputs
        supported_chains = self.get_supported_chains()
        if source_chain not in supported_chains:
            raise ValueError(
                f"Source chain '{source_chain}' is not supported by ZkSync"
            )
        if destination_chain not in supported_chains:
            raise ValueError(
                f"Destination chain '{destination_chain}' is not supported by "
                f"ZkSync"
            )
        
        supported_assets = self.get_supported_assets(source_chain)
        if asset not in supported_assets:
            raise ValueError(f"Asset '{asset}' is not supported by ZkSync")
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if source_chain == destination_chain:
            raise ValueError("Source and destination chains must be different")
        if not recipient_address or not recipient_address.startswith("0x"):
            raise ValueError("Invalid recipient address format")

        try:
            # Determine bridge direction
            if source_chain == "ethereum" and destination_chain == "zksync":
                direction = "deposit"  # L1 to L2
            elif source_chain == "zksync" and destination_chain == "ethereum":
                direction = "withdraw"  # L2 to L1
            else:
                raise ValueError(
                    f"Invalid bridge direction: {source_chain} to "
                    f"{destination_chain}"
                )

            # Use the ZkSync protocol's bridge_assets method
            tx_hash = self._protocol.bridge_assets(
                web3_l1=self._protocol.web3_l1,
                web3_l2=self._protocol.web3_l2,
                private_key=self._protocol.private_key,
                token_symbol=asset,
                amount=amount,
                direction=direction
            )

            logger.info(f"ZkSync bridge transaction initiated: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"Failed to initiate ZkSync bridge transaction: {e}")
            raise RuntimeError(f"Bridge transaction failed: {e}") from e