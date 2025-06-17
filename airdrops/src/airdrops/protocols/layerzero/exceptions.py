"""Custom exceptions for the LayerZero protocol module."""

from typing import Optional, Any
from web3.types import TxReceipt


class LayerZeroBridgeError(Exception):
    """Base exception for LayerZero bridge errors."""
    pass


class LayerZeroError(LayerZeroBridgeError):
    """Generic LayerZero error."""
    pass


class InsufficientBalanceError(LayerZeroBridgeError):
    """Raised when an account has insufficient balance for a transaction."""
    pass


class TransactionRevertedError(LayerZeroBridgeError):
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


class RPCError(LayerZeroBridgeError):
    """Raised for issues communicating with the L1/L2 RPC."""
    pass


class ApprovalError(TransactionRevertedError):
    """Raised specifically if an ERC20 approval transaction fails."""
    pass


class GasEstimationError(LayerZeroBridgeError):
    """Raised if gas estimation fails or returns unreasonable values."""
    pass


class MaxRetriesExceededError(LayerZeroBridgeError):
    """Raised if a transaction fails after multiple retries."""
    pass


class TransactionBuildError(LayerZeroBridgeError):
    """Raised if there's an error building a transaction."""
    pass


class TransactionSendError(LayerZeroBridgeError):
    """Raised if there's an error sending a transaction."""
    pass


class TransactionReceiptError(LayerZeroBridgeError):
    """Raised if there's an error fetching a transaction receipt or the receipt is invalid."""
    pass


class LayerZeroRandomActivityError(LayerZeroBridgeError):
    """Raised for errors specific to the perform_random_activity_layerzero orchestration."""
    pass


class UnsupportedChainError(LayerZeroBridgeError):
    """Raised when attempting to use an unsupported blockchain network.

    This exception is thrown when a chain ID is not configured or supported
    by the LayerZero protocol configuration.

    Example:
        >>> if chain_id not in supported_chains:
        ...     raise UnsupportedChainError(f"Chain ID {chain_id} not supported")
    """
    pass


class MessageSendError(LayerZeroBridgeError):
    """Raised when there's an error sending a LayerZero message."""
    pass


class MessageReceiveError(LayerZeroBridgeError):
    """Raised when there's an error receiving a LayerZero message."""
    pass