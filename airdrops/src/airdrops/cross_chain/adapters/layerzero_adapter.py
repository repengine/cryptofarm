"""
LayerZero Bridge Adapter Implementation.

This module provides a concrete implementation of the BridgeAdapter interface
for the LayerZero cross-chain protocol, enabling standardized bridging operations
across supported blockchain networks.
"""

import logging
from decimal import Decimal
from typing import List

from airdrops.cross_chain.bridge_adapter import BridgeAdapter
from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol
from airdrops.shared.constants import (
    LAYERZERO_ENDPOINT_ADDRESSES,
    LAYERZERO_TOKEN_ADDRESSES,
)

__all__ = [
    "LayerZeroBridgeAdapter",
]

# Configure logging for this module
logger = logging.getLogger(__name__)


class LayerZeroBridgeAdapter(BridgeAdapter):
    """LayerZero implementation of the BridgeAdapter interface.

    This adapter provides a standardized interface for cross-chain bridging
    operations using the LayerZero protocol. It wraps the LayerZeroProtocol
    to provide consistent bridge functionality across different chains.

    Example:
        >>> from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol
        >>> protocol = LayerZeroProtocol("https://eth.llamarpc.com", "0x...", 1)
        >>> adapter = LayerZeroBridgeAdapter(protocol)
        >>> chains = adapter.get_supported_chains()
        >>> print(chains)
        ['ethereum', 'arbitrum', 'optimism']
    """

    def __init__(self, layerzero_protocol: LayerZeroProtocol) -> None:
        """Initialize the LayerZero bridge adapter.

        Args:
            layerzero_protocol: An initialized LayerZeroProtocol instance.

        Raises:
            ValueError: If the protocol instance is None.

        Example:
            >>> protocol = LayerZeroProtocol("https://eth.llamarpc.com", "0x...", 1)
            >>> adapter = LayerZeroBridgeAdapter(protocol)
        """
        if layerzero_protocol is None:
            raise ValueError("LayerZeroProtocol instance cannot be None")

        self._protocol = layerzero_protocol
        logger.info("LayerZeroBridgeAdapter initialized successfully")

    def get_supported_chains(self) -> List[str]:
        """Returns a list of chain names supported by LayerZero.

        This method returns the canonical names of all blockchain networks
        that the LayerZero protocol can facilitate transfers between, based
        on the configured endpoint addresses.

        Returns:
            List[str]: A list of supported chain names.

        Example:
            >>> adapter = LayerZeroBridgeAdapter(protocol)
            >>> chains = adapter.get_supported_chains()
            >>> print(chains)
            ['ethereum', 'arbitrum', 'optimism']
        """
        supported_chains = list(LAYERZERO_ENDPOINT_ADDRESSES.keys())
        logger.debug(
            f"LayerZero supports {len(supported_chains)} chains: "
            f"{supported_chains}"
        )
        return supported_chains

    def get_supported_assets(self, chain: str) -> List[str]:
        """Returns a list of asset symbols supported on LayerZero.

        This method returns the asset symbols that can be bridged
        using the LayerZero protocol. Currently, LayerZero supports
        the same assets across all chains.

        Args:
            chain: The name of the blockchain network to query.

        Returns:
            List[str]: A list of supported asset symbols.

        Raises:
            ValueError: If the chain is not supported by LayerZero.

        Example:
            >>> adapter = LayerZeroBridgeAdapter(protocol)
            >>> assets = adapter.get_supported_assets("ethereum")
            >>> print(assets)
            ['USDC', 'USDT', 'WETH']
        """
        if chain not in LAYERZERO_ENDPOINT_ADDRESSES:
            raise ValueError(f"Chain '{chain}' is not supported by LayerZero")

        supported_assets = list(LAYERZERO_TOKEN_ADDRESSES.keys())
        logger.debug(
            f"LayerZero supports {len(supported_assets)} assets on {chain}: "
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
        """Estimates the fee for a LayerZero bridge transaction.

        This method calculates and returns the estimated fee for bridging
        the specified amount of an asset from the source chain to the destination
        chain using LayerZero protocol.

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
            >>> adapter = LayerZeroBridgeAdapter(protocol)
            >>> fee = adapter.estimate_bridge_fee(
            ...     "ethereum", "arbitrum", "USDC", Decimal("100")
            ... )
            >>> print(f"Bridge fee: {fee} ETH")
            Bridge fee: 0.001 ETH
        """
        # Validate inputs
        if source_chain not in LAYERZERO_ENDPOINT_ADDRESSES:
            raise ValueError(
                f"Source chain '{source_chain}' is not supported by LayerZero"
            )
        if destination_chain not in LAYERZERO_ENDPOINT_ADDRESSES:
            raise ValueError(
                f"Destination chain '{destination_chain}' is not supported by "
                f"LayerZero"
            )
        if asset not in LAYERZERO_TOKEN_ADDRESSES:
            raise ValueError(f"Asset '{asset}' is not supported by LayerZero")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if source_chain == destination_chain:
            raise ValueError("Source and destination chains must be different")

        # For LayerZero, we use a simplified fee estimation
        # In a real implementation, this would call the LayerZero endpoint's
        # estimateFees function
        base_fee = Decimal("0.001")  # Base fee in ETH
        amount_factor = amount / Decimal("1000")  # Scale with amount
        fee = base_fee + (amount_factor * Decimal("0.0001"))

        logger.debug(
            f"Estimated LayerZero bridge fee: {fee} ETH for {amount} {asset} "
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
        """Initiates a LayerZero bridge transaction.

        This method executes the actual bridge transaction, transferring
        the specified amount of an asset from the source chain to the destination
        chain for the given recipient address using LayerZero protocol.

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
            >>> adapter = LayerZeroBridgeAdapter(protocol)
            >>> tx_hash = adapter.bridge_assets(
            ...     "ethereum", "arbitrum", "USDC", Decimal("100"),
            ...     "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            ... )
            >>> print(f"Bridge transaction: {tx_hash}")
            Bridge transaction: 0x123abc...def789
        """
        # Validate inputs
        if source_chain not in LAYERZERO_ENDPOINT_ADDRESSES:
            raise ValueError(
                f"Source chain '{source_chain}' is not supported by LayerZero"
            )
        if destination_chain not in LAYERZERO_ENDPOINT_ADDRESSES:
            raise ValueError(
                f"Destination chain '{destination_chain}' is not supported by "
                f"LayerZero"
            )
        if asset not in LAYERZERO_TOKEN_ADDRESSES:
            raise ValueError(f"Asset '{asset}' is not supported by LayerZero")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if source_chain == destination_chain:
            raise ValueError("Source and destination chains must be different")
        if not recipient_address or not recipient_address.startswith("0x"):
            raise ValueError("Invalid recipient address format")

        try:
            # Map chain names to LayerZero chain IDs (simplified mapping)
            chain_id_map = {
                "ethereum": 1,
                "arbitrum": 42161,
                "optimism": 10
            }

            destination_chain_id = chain_id_map.get(destination_chain)
            if destination_chain_id is None:
                raise ValueError(
                    f"No chain ID mapping for destination chain "
                    f"'{destination_chain}'"
                )

            # Create a simple payload for the bridge message
            message_payload = (
                f"Bridge {amount} {asset} to {recipient_address}"
            ).encode('utf-8')

            # Use the LayerZero protocol's send_message method
            tx_hash = self._protocol.send_message(
                destination_chain_id=destination_chain_id,
                recipient_address=recipient_address,
                payload=message_payload,
                value=int(float(amount) * 10**18)  # Convert to Wei
            )

            logger.info(f"LayerZero bridge transaction initiated: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"Failed to initiate LayerZero bridge transaction: {e}")
            raise RuntimeError(f"Bridge transaction failed: {e}") from e
