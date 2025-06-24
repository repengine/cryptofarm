"""
Lending Adapter Pattern for zkSync Protocol.

This module implements the adapter pattern for integrating multiple lending protocols
on zkSync Era, starting with Zerolend (Aave v3 fork).
"""

import logging
from abc import ABC, abstractmethod

from web3 import Web3
from web3.contract import Contract
from web3.types import TxParams, Wei


logger = logging.getLogger(__name__)

# Zerolend contract addresses on zkSync Era
ZEROLEND_POOL_ADDRESS_ZKSYNC = "0x4d9429246EA989C9CeE203B43F6d1C7D83e3B8F8"  # Zerolend Pool
ZEROLEND_WETH_GATEWAY_ADDRESS_ZKSYNC = "0x1908e2BF4a88F91E4eF0DC72f02b8Ea36BEa2319"  # WETH Gateway

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ETH_SYMBOL = "ETH"
WETH_SYMBOL = "WETH"

__all__ = [
    "ZkSyncLendingAdapter",
    "ZerolendAdapter"
]


class ZkSyncLendingAdapter(ABC):
    """Abstract interface for a Lending Protocol on zkSync Era.
    
    This abstract base class defines the contract that all lending protocol adapters
    must implement to provide a consistent interface for lending operations
    across different protocols on zkSync Era.
    
    Example:
        >>> adapter = ZerolendAdapter(web3_l2)
        >>> tx_params = adapter.lend(
        ...     token_address="0x...",
        ...     amount=1000000000000000000,  # 1 ETH
        ...     from_address="0x..."
        ... )
        >>> # Execute transaction...
    """

    PROTOCOL_NAME: str

    def __init__(self, web3_l2: Web3) -> None:
        """Initialize the lending adapter.
        
        Args:
            web3_l2: Web3 instance for zkSync L2 network.
        """
        self.web3_l2 = web3_l2

    @abstractmethod
    def lend(self, token_address: str, amount: int, from_address: str) -> TxParams:
        """Construct the raw transaction to supply assets to the protocol.
        
        Args:
            token_address: Address of the token to lend.
            amount: Amount to lend (in wei/smallest unit).
            from_address: Address of the lender.
            
        Returns:
            Transaction parameters ready for signing and sending.
        """
        pass

    @abstractmethod
    def withdraw(self, token_address: str, amount: int, from_address: str) -> TxParams:
        """Construct the raw transaction to withdraw assets from the protocol.
        
        Args:
            token_address: Address of the token to withdraw.
            amount: Amount to withdraw (in wei/smallest unit).
            from_address: Address of the withdrawer.
            
        Returns:
            Transaction parameters ready for signing and sending.
        """
        pass

    @abstractmethod
    def borrow(self, token_address: str, amount: int, from_address: str) -> TxParams:
        """Construct the raw transaction to borrow assets from the protocol.
        
        Args:
            token_address: Address of the token to borrow.
            amount: Amount to borrow (in wei/smallest unit).
            from_address: Address of the borrower.
            
        Returns:
            Transaction parameters ready for signing and sending.
        """
        pass

    @abstractmethod
    def repay(self, token_address: str, amount: int, from_address: str) -> TxParams:
        """Construct the raw transaction to repay a borrowed asset.
        
        Args:
            token_address: Address of the token to repay.
            amount: Amount to repay (in wei/smallest unit).
            from_address: Address of the repayer.
            
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


class ZerolendAdapter(ZkSyncLendingAdapter):
    """Zerolend lending protocol adapter for zkSync Era.
    
    This adapter implements Zerolend-specific logic for lending operations.
    Zerolend is a fork of Aave v3, so it follows similar patterns and interfaces.
    """

    PROTOCOL_NAME = "zerolend"

    def lend(self, token_address: str, amount: int, from_address: str) -> TxParams:
        """Construct transaction to supply assets to Zerolend.
        
        For ETH, uses the WETH Gateway. For other tokens, uses the Pool directly.
        """
        logger.info(f"Building Zerolend lend transaction: {amount} of {token_address}")
        
        # Check if this is ETH (use WETH Gateway)
        weth_address = self._get_l2_token_address(WETH_SYMBOL)
        is_eth = token_address == weth_address
        
        if is_eth:
            # Use WETH Gateway for ETH deposits
            gateway_contract = self._get_contract(
                "ZerolendWETHGateway", 
                ZEROLEND_WETH_GATEWAY_ADDRESS_ZKSYNC
            )
            
            tx_params: TxParams = {
                "from": from_address,
                "to": ZEROLEND_WETH_GATEWAY_ADDRESS_ZKSYNC,
                "value": Wei(amount),  # Send ETH value
                "gas": 300000,  # Default gas limit for lending
            }
            
            # Call depositETH function
            return gateway_contract.functions.depositETH(
                ZEROLEND_POOL_ADDRESS_ZKSYNC,  # pool
                from_address,  # onBehalfOf
                0  # referralCode
            ).build_transaction(tx_params)
        else:
            # Use Pool contract for ERC20 tokens
            pool_contract = self._get_contract(
                "ZerolendPool", 
                ZEROLEND_POOL_ADDRESS_ZKSYNC
            )
            
            tx_params = {
                "from": from_address,
                "to": ZEROLEND_POOL_ADDRESS_ZKSYNC,
                "gas": 300000,  # Default gas limit for lending
            }
            
            # Call supply function (Aave v3 pattern)
            return pool_contract.functions.supply(
                token_address,  # asset
                amount,  # amount
                from_address,  # onBehalfOf
                0  # referralCode
            ).build_transaction(tx_params)

    def withdraw(self, token_address: str, amount: int, from_address: str) -> TxParams:
        """Construct transaction to withdraw assets from Zerolend."""
        logger.info(f"Building Zerolend withdraw transaction: {amount} of {token_address}")
        
        # Check if this is ETH (use WETH Gateway)
        weth_address = self._get_l2_token_address(WETH_SYMBOL)
        is_eth = token_address == weth_address
        
        if is_eth:
            # Use WETH Gateway for ETH withdrawals
            gateway_contract = self._get_contract(
                "ZerolendWETHGateway", 
                ZEROLEND_WETH_GATEWAY_ADDRESS_ZKSYNC
            )
            
            tx_params: TxParams = {
                "from": from_address,
                "to": ZEROLEND_WETH_GATEWAY_ADDRESS_ZKSYNC,
                "gas": 300000,  # Default gas limit
            }
            
            # Call withdrawETH function
            return gateway_contract.functions.withdrawETH(
                ZEROLEND_POOL_ADDRESS_ZKSYNC,  # pool
                amount,  # amount
                from_address  # to
            ).build_transaction(tx_params)
        else:
            # Use Pool contract for ERC20 tokens
            pool_contract = self._get_contract(
                "ZerolendPool", 
                ZEROLEND_POOL_ADDRESS_ZKSYNC
            )
            
            tx_params = {
                "from": from_address,
                "to": ZEROLEND_POOL_ADDRESS_ZKSYNC,
                "gas": 300000,  # Default gas limit
            }
            
            # Call withdraw function (Aave v3 pattern)
            return pool_contract.functions.withdraw(
                token_address,  # asset
                amount,  # amount
                from_address  # to
            ).build_transaction(tx_params)

    def borrow(self, token_address: str, amount: int, from_address: str) -> TxParams:
        """Construct transaction to borrow assets from Zerolend."""
        logger.info(f"Building Zerolend borrow transaction: {amount} of {token_address}")
        
        # Check if this is ETH (use WETH Gateway)
        weth_address = self._get_l2_token_address(WETH_SYMBOL)
        is_eth = token_address == weth_address
        
        if is_eth:
            # Use WETH Gateway for ETH borrowing
            gateway_contract = self._get_contract(
                "ZerolendWETHGateway", 
                ZEROLEND_WETH_GATEWAY_ADDRESS_ZKSYNC
            )
            
            tx_params: TxParams = {
                "from": from_address,
                "to": ZEROLEND_WETH_GATEWAY_ADDRESS_ZKSYNC,
                "gas": 400000,  # Higher gas limit for borrowing
            }
            
            # Call borrowETH function
            return gateway_contract.functions.borrowETH(
                ZEROLEND_POOL_ADDRESS_ZKSYNC,  # pool
                amount,  # amount
                2,  # interestRateMode (2 = variable rate)
                0  # referralCode
            ).build_transaction(tx_params)
        else:
            # Use Pool contract for ERC20 tokens
            pool_contract = self._get_contract(
                "ZerolendPool", 
                ZEROLEND_POOL_ADDRESS_ZKSYNC
            )
            
            tx_params = {
                "from": from_address,
                "to": ZEROLEND_POOL_ADDRESS_ZKSYNC,
                "gas": 400000,  # Higher gas limit for borrowing
            }
            
            # Call borrow function (Aave v3 pattern)
            return pool_contract.functions.borrow(
                token_address,  # asset
                amount,  # amount
                2,  # interestRateMode (2 = variable rate)
                0,  # referralCode
                from_address  # onBehalfOf
            ).build_transaction(tx_params)

    def repay(self, token_address: str, amount: int, from_address: str) -> TxParams:
        """Construct transaction to repay borrowed assets to Zerolend."""
        logger.info(f"Building Zerolend repay transaction: {amount} of {token_address}")
        
        # Check if this is ETH (use WETH Gateway)
        weth_address = self._get_l2_token_address(WETH_SYMBOL)
        is_eth = token_address == weth_address
        
        if is_eth:
            # Use WETH Gateway for ETH repayment
            gateway_contract = self._get_contract(
                "ZerolendWETHGateway", 
                ZEROLEND_WETH_GATEWAY_ADDRESS_ZKSYNC
            )
            
            tx_params: TxParams = {
                "from": from_address,
                "to": ZEROLEND_WETH_GATEWAY_ADDRESS_ZKSYNC,
                "value": Wei(amount),  # Send ETH value for repayment
                "gas": 300000,  # Default gas limit
            }
            
            # Call repayETH function
            return gateway_contract.functions.repayETH(
                ZEROLEND_POOL_ADDRESS_ZKSYNC,  # pool
                amount,  # amount
                2,  # interestRateMode (2 = variable rate)
                from_address  # onBehalfOf
            ).build_transaction(tx_params)
        else:
            # Use Pool contract for ERC20 tokens
            pool_contract = self._get_contract(
                "ZerolendPool", 
                ZEROLEND_POOL_ADDRESS_ZKSYNC
            )
            
            tx_params = {
                "from": from_address,
                "to": ZEROLEND_POOL_ADDRESS_ZKSYNC,
                "gas": 300000,  # Default gas limit
            }
            
            # Call repay function (Aave v3 pattern)
            return pool_contract.functions.repay(
                token_address,  # asset
                amount,  # amount
                2,  # interestRateMode (2 = variable rate)
                from_address  # onBehalfOf
            ).build_transaction(tx_params)