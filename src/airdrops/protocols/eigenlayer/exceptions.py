"""Custom exceptions for EigenLayer protocol operations."""


class EigenLayerError(Exception):
    """Base exception for EigenLayer operations."""
    pass


class EigenLayerRestakeError(EigenLayerError):
    """Base exception for EigenLayer restaking operations."""
    pass


class RestakeError(EigenLayerRestakeError):
    """Raised when restaking operation fails."""
    pass


class WithdrawalError(EigenLayerError):
    """Raised when withdrawal operation fails."""
    pass


class ClaimError(EigenLayerError):
    """Raised when claim operation fails."""
    pass


class UnsupportedLSTError(EigenLayerRestakeError):
    """Raised when an unsupported LST symbol is provided."""
    pass


class DepositCapReachedError(EigenLayerRestakeError):
    """Raised when deposit would exceed strategy cap."""
    pass
