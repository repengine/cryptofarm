"""Custom exceptions for the ZkSync protocol module."""

from typing import Optional, Any
from web3.types import TxReceipt


class ZkSyncBridgeError(Exception):
    """Base exception for ZkSync bridge errors."""
    pass


class InsufficientBalanceError(ZkSyncBridgeError):
    """Raised when an account has insufficient balance for a transaction."""
    pass


class TransactionRevertedError(ZkSyncBridgeError):
    """Raised when a transaction is reverted on-chain."""
    def __init__(
        self,
        message: str,
        receipt: Optional[TxReceipt] = None,
        tx_hash: Optional[str] = None,
        data: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.receipt: Optional[TxReceipt] = receipt
        self.tx_hash: Optional[str] = tx_hash
        self.data: Optional[Any] = data


class RPCError(ZkSyncBridgeError):
    """Raised for issues communicating with the L1/L2 RPC."""
    pass


class ApprovalError(TransactionRevertedError):
    """Raised specifically if an ERC20 approval transaction fails."""
    pass


class GasEstimationError(ZkSyncBridgeError):
    """Raised if gas estimation fails or returns unreasonable values."""
    pass


class MaxRetriesExceededError(ZkSyncBridgeError):
    """Raised if a transaction fails after multiple retries."""
    pass


class TransactionBuildError(ZkSyncBridgeError):
    """Raised if there's an error building a transaction."""
    pass


class TransactionSendError(ZkSyncBridgeError):
    """Raised if there's an error sending a transaction."""
    pass


class TransactionReceiptError(ZkSyncBridgeError):
    """Raised if there's an error fetching a transaction receipt or the receipt is invalid."""
    pass

# --- Swap Specific Exceptions ---


class ZkSyncValueError(ZkSyncBridgeError):
    """Base class for value-related errors in ZkSync operations."""
    pass


class TokenNotSupportedError(ZkSyncValueError):
    """Raised when a token symbol is not supported or configured for an operation."""
    pass


class ZkSyncSwapError(ZkSyncBridgeError):
    """Base exception for ZkSync SyncSwap specific errors."""
    def __init__(self, message: str, tx_data: Optional[Any] = None):
        super().__init__(message)
        self.tx_data = tx_data


class InsufficientLiquidityError(ZkSyncSwapError):
    """Raised if liquidity is insufficient for a swap or no path is found."""
    pass


class PoolNotFoundError(ZkSyncSwapError):
    """Raised when a SyncSwap pool is not found."""
    pass


class ZkSyncRandomActivityError(ZkSyncBridgeError):
    """Raised for errors specific to the perform_random_activity_zksync orchestration."""
    pass