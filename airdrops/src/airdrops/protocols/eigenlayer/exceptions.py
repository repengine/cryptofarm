"""Custom exceptions for EigenLayer protocol operations."""


class EigenLayerRestakeError(Exception):
    """Base exception for EigenLayer restaking operations."""
    pass


class UnsupportedLSTError(EigenLayerRestakeError):
    """Raised when an unsupported LST symbol is provided."""
    pass


class DepositCapReachedError(EigenLayerRestakeError):
    """Raised when deposit would exceed strategy cap."""
    pass