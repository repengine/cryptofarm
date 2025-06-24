"""
DEX Adapter Pattern for zkSync Protocol.

This module implements the adapter pattern for integrating multiple DEXs
on zkSync Era, including SyncSwap, Mute, and SpaceFi.
"""

import logging
from abc import ABC, abstractmethod

from web3 import Web3
from web3.contract import Contract
from web3.types import TxParams, Wei

from airdrops.shared.constants import (
    SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC
)
from .exceptions import (
    ZkSyncSwapError,
    InsufficientLiquidityError
)

logger = logging.getLogger(__name__)

# Placeholder addresses for Mute and SpaceFi - to be updated with actual values
MUTE_ROUTER_ADDRESS_ZKSYNC = "0x8B791913eB07C32779a16750e3868aA8495F5964"  # Placeholder
SPACEFI_ROUTER_ADDRESS_ZKSYNC = "0x18b71386418A9FCa5Ae7165E31c385a5130011b6"  # Placeholder

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ETH_SYMBOL = "ETH"
WETH_SYMBOL = "WETH"

__all__ = [
    "ZkSyncDEXAdapter",
    "SyncSwapAdapter", 
    "MuteAdapter",
    "SpaceFiAdapter"
]


class ZkSyncDEXAdapter(ABC):
    """Abstract interface for a DEX on zkSync Era.
    
    This abstract base class defines the contract that all DEX adapters
    must implement to provide a consistent interface for token swapping
    across different DEXs on zkSync Era.
    
    Example:
        >>> adapter = SyncSwapAdapter(web3_l2)
        >>> quote = adapter.get_quote(
        ...     token_in_address="0x...",
        ...     token_out_address="0x...",
        ...     amount_in=1000000
        ... )
        >>> if quote > 0:
        ...     tx_params = adapter.build_swap_transaction(
        ...         token_in_address="0x...",
        ...         token_out_address="0x...",
        ...         amount_in=1000000,
        ...         recipient_address="0x...",
        ...         slippage_percent=0.5,
        ...         deadline_seconds=1800
        ...     )
    """

    DEX_NAME: str

    def __init__(self, web3_l2: Web3) -> None:
        """Initialize the DEX adapter.
        
        Args:
            web3_l2: Web3 instance for zkSync L2 network.
        """
        self.web3_l2 = web3_l2

    @abstractmethod
    def get_quote(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: int
    ) -> int:
        """Get the estimated amount of output tokens for a given input amount.
        
        Args:
            token_in_address: Address of the input token.
            token_out_address: Address of the output token.
            amount_in: Amount of input tokens (in wei/smallest unit).
            
        Returns:
            Estimated amount of output tokens (in wei/smallest unit).
            Returns 0 if the pair is not supported or has insufficient liquidity.
        """
        pass

    @abstractmethod
    def build_swap_transaction(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build the transaction parameters for the swap.
        
        Args:
            token_in_address: Address of the input token.
            token_out_address: Address of the output token.
            amount_in: Amount of input tokens (in wei/smallest unit).
            recipient_address: Address to receive the output tokens.
            slippage_percent: Maximum allowed slippage percentage.
            deadline_seconds: Transaction deadline in seconds from now.
            
        Returns:
            Transaction parameters ready for signing and sending.
        """
        pass

    @abstractmethod
    def add_liquidity(
        self,
        token_a_address: str,
        token_b_address: str,
        amount_a: int,
        amount_b: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build the transaction parameters for adding liquidity to a DEX pool.
        
        Args:
            token_a_address: Address of the first token.
            token_b_address: Address of the second token.
            amount_a: Amount of first token (in wei/smallest unit).
            amount_b: Amount of second token (in wei/smallest unit).
            recipient_address: Address to receive the LP tokens.
            slippage_percent: Maximum allowed slippage percentage.
            deadline_seconds: Transaction deadline in seconds from now.
            
        Returns:
            Transaction parameters ready for signing and sending.
        """
        pass

    @abstractmethod
    def remove_liquidity(
        self,
        token_a_address: str,
        token_b_address: str,
        liquidity: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build the transaction parameters for removing liquidity from a DEX pool.
        
        Args:
            token_a_address: Address of the first token.
            token_b_address: Address of the second token.
            liquidity: Amount of LP tokens to burn.
            recipient_address: Address to receive the underlying tokens.
            slippage_percent: Maximum allowed slippage percentage.
            deadline_seconds: Transaction deadline in seconds from now.
            
        Returns:
            Transaction parameters ready for signing and sending.
        """
        pass

    def _get_contract(self, contract_name: str, contract_address: str) -> Contract:
        """Load ABI and return contract instance.
        
        Args:
            contract_name: Name of contract for ABI loading.
            contract_address: Contract address.
            
        Returns:
            Web3 Contract instance.
        """
        from . import zksync  # Import here to avoid circular imports
        return zksync._get_contract_zksync(self.web3_l2, contract_name, contract_address)

    def _get_l2_token_address(self, token_symbol: str) -> str:
        """Get L2 address for a token symbol.
        
        Args:
            token_symbol: Token symbol (e.g., "ETH", "WETH", "USDC").
            
        Returns:
            L2 token address as a string.
        """
        from . import zksync  # Import here to avoid circular imports
        return zksync._get_l2_token_address_zksync(token_symbol)


class SyncSwapAdapter(ZkSyncDEXAdapter):
    """SyncSwap DEX adapter for zkSync Era.
    
    This adapter implements the SyncSwap-specific logic for token swapping,
    including pool discovery, quote calculation, and transaction building.
    """

    DEX_NAME = "syncswap"

    def get_quote(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: int
    ) -> int:
        """Get quote from SyncSwap pools."""
        try:
            from . import zksync  # Import here to avoid circular imports
            
            # Use existing SyncSwap quote logic
            weth_address = self._get_l2_token_address(WETH_SYMBOL)
            sender_address = "0x0000000000000000000000000000000000000001"  # Dummy address for quote
            
            return zksync._get_expected_amount_out_syncswap_zksync(
                self.web3_l2,
                token_in_address,
                token_out_address,
                amount_in,
                sender_address,
                weth_address
            )
        except Exception as e:
            logger.warning(f"SyncSwap quote failed for {token_in_address}->{token_out_address}: {e}")
            return 0

    def build_swap_transaction(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build SyncSwap swap transaction."""
        from . import zksync  # Import here to avoid circular imports
        
        # Get current block timestamp and calculate deadline
        current_block = self.web3_l2.eth.get_block("latest")
        deadline = current_block["timestamp"] + deadline_seconds
        
        # Get expected amount out for slippage calculation
        expected_amount_out = self.get_quote(token_in_address, token_out_address, amount_in)
        if expected_amount_out == 0:
            raise InsufficientLiquidityError(
                f"No liquidity available for {token_in_address} -> {token_out_address}"
            )
        
        amount_out_min = int(expected_amount_out * (1 - slippage_percent / 100.0))
        
        # Get router contract
        router_contract = self._get_contract(
            "SyncSwapRouter", 
            SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC
        )
        
        # Construct swap paths
        weth_address = self._get_l2_token_address(WETH_SYMBOL)
        
        # Determine if this is an ETH input swap
        is_eth_input = token_in_address == weth_address
        
        swap_paths = zksync._construct_syncswap_paths_zksync(
            self.web3_l2,
            token_in_address,
            token_out_address,
            amount_in,
            recipient_address,
            weth_address,
            router_contract,
            ETH_SYMBOL if token_out_address == weth_address else "TOKEN"
        )
        
        # Build transaction parameters
        tx_value = Wei(amount_in) if is_eth_input else Wei(0)
        
        tx_params: TxParams = {
            "from": recipient_address,
            "to": SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC,
            "value": tx_value,
            "gas": Wei(600000),  # Default gas limit
        }
        
        # Build the swap function call
        swap_function = router_contract.functions.swap(
            swap_paths, amount_out_min, deadline
        )
        
        return swap_function.build_transaction(tx_params)

    def add_liquidity(
        self,
        token_a_address: str,
        token_b_address: str,
        amount_a: int,
        amount_b: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build SyncSwap add liquidity transaction."""
        from . import zksync  # Import here to avoid circular imports
        
        # Get router contract
        router_contract = self._get_contract(
            "SyncSwapRouter",
            SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC
        )
        
        # Get pool address for the token pair
        pool_address = zksync._get_syncswap_pool_address_zksync(
            self.web3_l2, token_a_address, token_b_address
        )
        if not pool_address:
            raise InsufficientLiquidityError(
                f"No SyncSwap pool found for {token_a_address} and {token_b_address}"
            )
        
        # Calculate minimum liquidity based on slippage
        # For simplicity, we'll use a conservative estimate
        min_liquidity = 1  # Minimum 1 wei of LP tokens
        
        # Determine if ETH is involved
        weth_address = self._get_l2_token_address(WETH_SYMBOL)
        
        # Build token inputs array
        token_inputs = []
        tx_value = Wei(0)
        
        if token_a_address == weth_address:
            # Token A is ETH/WETH
            tx_value = Wei(amount_a)
            token_inputs.append({
                "token": token_a_address,
                "amount": amount_a
            })
        else:
            token_inputs.append({
                "token": token_a_address,
                "amount": amount_a
            })
            
        if token_b_address == weth_address:
            # Token B is ETH/WETH
            tx_value = Wei(amount_b)
            token_inputs.append({
                "token": token_b_address,
                "amount": amount_b
            })
        else:
            token_inputs.append({
                "token": token_b_address,
                "amount": amount_b
            })
        
        # Build transaction parameters
        tx_params: TxParams = {
            "from": recipient_address,
            "to": SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC,
            "value": tx_value,
            "gas": Wei(800000),  # Higher gas limit for liquidity operations
        }
        
        # Build the addLiquidity function call
        add_liquidity_function = router_contract.functions.addLiquidity(
            pool_address,
            token_inputs,
            b"",  # data parameter (empty for basic operations)
            min_liquidity,
            ZERO_ADDRESS,  # callback
            b""  # callbackData
        )
        
        return add_liquidity_function.build_transaction(tx_params)

    def remove_liquidity(
        self,
        token_a_address: str,
        token_b_address: str,
        liquidity: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build SyncSwap remove liquidity transaction."""
        from . import zksync  # Import here to avoid circular imports
        
        # Get router contract
        router_contract = self._get_contract(
            "SyncSwapRouter",
            SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC
        )
        
        # Get pool address for the token pair
        pool_address = zksync._get_syncswap_pool_address_zksync(
            self.web3_l2, token_a_address, token_b_address
        )
        if not pool_address:
            raise InsufficientLiquidityError(
                f"No SyncSwap pool found for {token_a_address} and {token_b_address}"
            )
        
        # Calculate minimum amounts based on slippage
        # For simplicity, we'll use conservative estimates
        min_amounts = [1, 1]  # Minimum 1 wei for each token
        
        # Build transaction parameters
        tx_params: TxParams = {
            "from": recipient_address,
            "to": SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC,
            "value": Wei(0),
            "gas": Wei(800000),  # Higher gas limit for liquidity operations
        }
        
        # Build the burnLiquidity function call
        burn_liquidity_function = router_contract.functions.burnLiquidity(
            pool_address,
            liquidity,
            b"",  # data parameter (empty for basic operations)
            min_amounts,
            ZERO_ADDRESS,  # callback
            b""  # callbackData
        )
        
        return burn_liquidity_function.build_transaction(tx_params)


class MuteAdapter(ZkSyncDEXAdapter):
    """Mute.io DEX adapter for zkSync Era.
    
    This adapter implements Mute-specific logic for token swapping.
    Note: This is a placeholder implementation that needs to be updated
    with actual Mute contract addresses and ABI when available.
    """

    DEX_NAME = "mute"

    def get_quote(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: int
    ) -> int:
        """Get quote from Mute DEX."""
        try:
            # Placeholder implementation - needs actual Mute contract integration
            logger.warning("Mute adapter not fully implemented - using placeholder")
            return 0
        except Exception as e:
            logger.warning(f"Mute quote failed for {token_in_address}->{token_out_address}: {e}")
            return 0

    def build_swap_transaction(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build Mute swap transaction."""
        # Placeholder implementation
        raise ZkSyncSwapError("Mute adapter not fully implemented")

    def add_liquidity(
        self,
        token_a_address: str,
        token_b_address: str,
        amount_a: int,
        amount_b: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build Mute add liquidity transaction."""
        # Placeholder implementation
        raise ZkSyncSwapError("Mute adapter not fully implemented")

    def remove_liquidity(
        self,
        token_a_address: str,
        token_b_address: str,
        liquidity: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build Mute remove liquidity transaction."""
        # Placeholder implementation
        raise ZkSyncSwapError("Mute adapter not fully implemented")


class SpaceFiAdapter(ZkSyncDEXAdapter):
    """SpaceFi DEX adapter for zkSync Era.
    
    This adapter implements SpaceFi-specific logic for token swapping.
    Note: This is a placeholder implementation that needs to be updated
    with actual SpaceFi contract addresses and ABI when available.
    """

    DEX_NAME = "spacefi"

    def get_quote(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: int
    ) -> int:
        """Get quote from SpaceFi DEX."""
        try:
            # Placeholder implementation - needs actual SpaceFi contract integration
            logger.warning("SpaceFi adapter not fully implemented - using placeholder")
            return 0
        except Exception as e:
            logger.warning(f"SpaceFi quote failed for {token_in_address}->{token_out_address}: {e}")
            return 0

    def build_swap_transaction(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build SpaceFi swap transaction."""
        # Placeholder implementation
        raise ZkSyncSwapError("SpaceFi adapter not fully implemented")

    def add_liquidity(
        self,
        token_a_address: str,
        token_b_address: str,
        amount_a: int,
        amount_b: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build SpaceFi add liquidity transaction."""
        # Placeholder implementation
        raise ZkSyncSwapError("SpaceFi adapter not fully implemented")

    def remove_liquidity(
        self,
        token_a_address: str,
        token_b_address: str,
        liquidity: int,
        recipient_address: str,
        slippage_percent: float,
        deadline_seconds: int
    ) -> TxParams:
        """Build SpaceFi remove liquidity transaction."""
        # Placeholder implementation
        raise ZkSyncSwapError("SpaceFi adapter not fully implemented")