"""
Scroll Bridge Adapter Implementation.

This module provides a concrete implementation of the BridgeAdapter interface
for the Scroll cross-chain protocol, enabling standardized bridging operations
between Ethereum L1 and Scroll L2 networks.
"""

from decimal import Decimal
from typing import List, Any

from airdrops.cross_chain.bridge_adapter import BridgeAdapter
from airdrops.protocols.scroll.scroll import bridge_assets
from airdrops.shared.constants import SCROLL_TOKEN_ADDRESSES
from airdrops.shared.logger import logger

__all__ = [
    "ScrollBridgeAdapter",
]


class ScrollBridgeAdapter(BridgeAdapter):
    """Scroll implementation of the BridgeAdapter interface.

    This adapter provides a standardized interface for cross-chain bridging
    operations using the Scroll protocol. It wraps the Scroll protocol's
    bridge_assets function to provide consistent bridge functionality between
    Ethereum L1 and Scroll L2.

    Example:
        >>> from web3 import Web3
        >>> web3_l1 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))
        >>> web3_l2 = Web3(Web3.HTTPProvider("https://rpc.scroll.io"))
        >>> adapter = ScrollBridgeAdapter(web3_l1, web3_l2, "0x...")
        >>> chains = adapter.get_supported_chains()
        >>> print(chains)
        ['ethereum', 'scroll']
    """

    def __init__(self, web3_l1: Any, web3_l2: Any, private_key: str) -> None:
        """Initialize the Scroll bridge adapter.

        Args:
            web3_l1: Web3 instance for Ethereum L1.
            web3_l2: Web3 instance for Scroll L2.
            private_key: Private key for signing transactions.

        Example:
            >>> from web3 import Web3
            >>> web3_l1 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))
            >>> web3_l2 = Web3(Web3.HTTPProvider("https://rpc.scroll.io"))
            >>> adapter = ScrollBridgeAdapter(web3_l1, web3_l2, "0x...")
        """
        self.web3_l1 = web3_l1
        self.web3_l2 = web3_l2
        self.private_key = private_key

    def get_supported_chains(self) -> List[str]:
        """Returns a list of chain names supported by the Scroll bridge.

        Returns:
            List of supported chain names.

        Example:
            >>> adapter = ScrollBridgeAdapter(web3_l1, web3_l2, "0x...")
            >>> chains = adapter.get_supported_chains()
            >>> print(chains)
            ['ethereum', 'scroll']
        """
        return ["ethereum", "scroll"]

    def get_supported_assets(self, chain: str) -> List[str]:
        """Returns a list of asset symbols supported on a given chain.

        Args:
            chain: The name of the blockchain network to query.

        Returns:
            List of supported asset symbols.

        Raises:
            ValueError: If the chain is not supported by Scroll.

        Example:
            >>> adapter = ScrollBridgeAdapter(web3_l1, web3_l2, "0x...")
            >>> assets = adapter.get_supported_assets("ethereum")
            >>> print(assets)
            ['ETH', 'USDC', 'USDT', 'WETH', 'DAI']
        """
        if chain not in self.get_supported_chains():
            raise ValueError(f"Chain '{chain}' is not supported by Scroll")

        # ETH is natively supported, plus configured ERC20 tokens
        supported_assets = ["ETH"]
        supported_assets.extend(SCROLL_TOKEN_ADDRESSES.keys())

        return supported_assets

    def estimate_bridge_fee(
        self,
        source_chain: str,
        destination_chain: str,
        asset: str,
        amount: Decimal
    ) -> Decimal:
        """Estimates the fee for a bridge transaction.

        Args:
            source_chain: The name of the source blockchain network.
            destination_chain: The name of the destination blockchain network.
            asset: The symbol of the asset to bridge.
            amount: The amount of the asset to bridge.

        Returns:
            The estimated bridge fee in ETH.

        Raises:
            ValueError: If any of the parameters are invalid or unsupported.

        Example:
            >>> adapter = ScrollBridgeAdapter(web3_l1, web3_l2, "0x...")
            >>> fee = adapter.estimate_bridge_fee("ethereum", "scroll", "ETH", Decimal("1.0"))
            >>> print(f"Bridge fee: {fee} ETH")
            Bridge fee: 0.001 ETH
        """
        # Validate chains
        if source_chain == destination_chain:
            raise ValueError("Source and destination chains must be different")

        supported_chains = self.get_supported_chains()
        if source_chain not in supported_chains:
            raise ValueError(f"Source chain '{source_chain}' is not supported by Scroll")
        if destination_chain not in supported_chains:
            raise ValueError(f"Destination chain '{destination_chain}' is not supported by Scroll")

        # Validate asset
        if asset not in self.get_supported_assets(source_chain):
            raise ValueError(f"Asset '{asset}' is not supported on {source_chain}")

        # Validate amount
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Estimate fees based on bridge direction
        if source_chain == "ethereum" and destination_chain == "scroll":
            # L1 to L2 (deposit) - lower fees
            if asset == "ETH":
                fee = Decimal("0.001")  # ~$3-4 at current ETH prices
            else:
                fee = Decimal("0.0015")  # Slightly higher for ERC20
        elif source_chain == "scroll" and destination_chain == "ethereum":
            # L2 to L1 (withdrawal) - higher fees due to proof generation
            if asset == "ETH":
                fee = Decimal("0.005")  # ~$15-20 at current ETH prices
            else:
                fee = Decimal("0.007")  # Higher for ERC20 withdrawals
        else:
            raise ValueError(
                f"Invalid bridge direction: {source_chain} to {destination_chain}"
            )

        logger.debug(
            f"Estimated Scroll bridge fee: {fee} ETH for {amount} {asset} "
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
        """Initiates a Scroll bridge transaction.

        This method executes the actual bridge transaction, transferring
        the specified amount of an asset between Ethereum L1 and Scroll L2
        for the given recipient address using the Scroll protocol.

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
            >>> adapter = ScrollBridgeAdapter(web3_l1, web3_l2, "0x...")
            >>> tx_hash = adapter.bridge_assets(
            ...     "ethereum", "scroll", "ETH", Decimal("0.1"),
            ...     "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            ... )
            >>> print(f"Transaction hash: {tx_hash}")
            Transaction hash: 0x123abc...def789
        """
        # Validate parameters using estimate_bridge_fee (which does all validation)
        self.estimate_bridge_fee(source_chain, destination_chain, asset, amount)

        # Validate recipient address
        if not recipient_address:
            raise ValueError("Invalid recipient address format")
        if not recipient_address.startswith("0x"):
            raise ValueError("Recipient address must start with '0x'")
        if len(recipient_address) != 42:
            raise ValueError("Invalid recipient address format")

        # Determine bridge direction
        if source_chain == "ethereum" and destination_chain == "scroll":
            direction = "deposit"  # L1 to L2
        elif source_chain == "scroll" and destination_chain == "ethereum":
            direction = "withdraw"  # L2 to L1
        else:
            raise ValueError(
                f"Invalid bridge direction: {source_chain} to "
                f"{destination_chain}"
            )

        # Convert amount to appropriate units
        if asset == "ETH":
            # Convert ETH to Wei (10^18)
            amount_in_units = int(amount * Decimal("10") ** 18)
        else:
            # For ERC20 tokens, convert to smallest units
            # Most tokens use 6 decimals (USDC, USDT) or 18 decimals (WETH, DAI)
            if asset in ["USDC", "USDT"]:
                decimals = 6
            else:
                decimals = 18
            amount_in_units = int(amount * Decimal("10") ** decimals)

        # Execute bridge operation using the Scroll protocol
        try:
            tx_hash = bridge_assets(
                web3_l1=self.web3_l1,
                web3_l2=self.web3_l2,
                private_key=self.private_key,
                token_symbol=asset,
                amount=Decimal(str(amount_in_units)),
                direction=direction
            )

            logger.info(f"Scroll bridge transaction initiated: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"Scroll bridge transaction failed: {e}")
            raise RuntimeError(f"Bridge transaction failed: {str(e)}") from e