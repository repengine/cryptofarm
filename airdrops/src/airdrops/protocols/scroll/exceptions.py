"""Custom exceptions for the Scroll protocol module."""

from typing import Optional, Any
from web3.types import TxReceipt


class ScrollBridgeError(Exception):
    """Base exception for Scroll bridge errors."""

    pass


class InsufficientBalanceError(ScrollBridgeError):
    """Raised when an account has insufficient balance for a transaction."""

    pass


class TransactionRevertedError(ScrollBridgeError):
    """Raised when a transaction is reverted on-chain."""

    def __init__(
        self,
        message: str,
        receipt: Optional[TxReceipt] = None,
        tx_hash: Optional[str] = None, # Added to match base class if needed, or for more info
        data: Optional[Any] = None, # Added to store revert data
    ):
        super().__init__(message)
        self.receipt: Optional[TxReceipt] = receipt
        self.tx_hash: Optional[str] = tx_hash
        self.data: Optional[Any] = data


class RPCError(ScrollBridgeError):
    """Raised for issues communicating with the L1/L2 RPC."""

    pass


class ApprovalError(TransactionRevertedError):
    """Raised specifically if an ERC20 approval transaction fails."""

    pass


class GasEstimationError(ScrollBridgeError):
    """Raised if gas estimation fails or returns unreasonable values."""

    pass


class MaxRetriesExceededError(ScrollBridgeError):
    """Raised if a transaction fails after multiple retries."""

    pass


class TransactionBuildError(ScrollBridgeError):
    """Raised if there's an error building a transaction."""

    pass


class TransactionSendError(ScrollBridgeError):
    """Raised if there's an error sending a transaction."""

    pass


class TransactionReceiptError(ScrollBridgeError):
    """Raised if there's an error fetching a transaction receipt or the receipt is invalid."""

    pass


# --- Swap Specific Exceptions ---


class ScrollValueError(
    ScrollBridgeError
):  # Changed base to ScrollBridgeError for consistency
    """Base class for value-related errors in Scroll operations."""

    pass


class TokenNotSupportedError(ScrollValueError):
    """Raised when a token symbol is not supported or configured for an operation."""

    pass


class ScrollSwapError(ScrollBridgeError):  # Changed base to ScrollBridgeError
    """Base exception for Scroll SyncSwap specific errors."""

    def __init__(self, message: str, tx_data: Optional[Any] = None):
        super().__init__(message)
        self.tx_data = tx_data


class InsufficientLiquidityError(ScrollSwapError):
    """Raised if liquidity is insufficient for a swap or no path is found."""

    pass


# Note: SlippageTooHighError was considered but is generally handled by amountOutMin.
# If specific post-tx slippage detection is added later, it could be defined here.


# --- Lending Specific Exceptions ---


class ScrollLendingError(ScrollBridgeError):
    """Base exception for Scroll lending protocol errors."""

    pass


class InsufficientCollateralError(ScrollLendingError):
    """Raised when account has insufficient collateral for borrowing."""

    pass


class MarketNotEnteredError(ScrollLendingError):
    """Raised when trying to use a market that hasn't been entered."""

    pass


class RepayAmountExceedsDebtError(ScrollLendingError):
    """Raised when repay amount exceeds current debt."""

    pass


class LayerBankComptrollerRejectionError(ScrollLendingError):
    """Raised when LayerBank Comptroller rejects an operation."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        super().__init__(message)
        self.error_code = error_code


class ScrollRandomActivityError(ScrollBridgeError):
    """Raised for errors specific to the perform_random_activity_scroll orchestration."""

    pass
