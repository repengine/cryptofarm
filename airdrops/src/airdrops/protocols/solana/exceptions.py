"""Custom exceptions for the Solana protocol module."""

from typing import Optional, Any


class SolanaError(Exception):
    """Base exception for Solana protocol errors.
    
    This is the base class for all Solana-specific exceptions in the protocol module.
    It provides a foundation for more specific error types that may be needed as the
    module develops.
    
    Args:
        message: Human-readable error message describing the issue.
        context: Optional additional context about the error.
        
    Example:
        >>> try:
        ...     # Some Solana operation
        ...     pass
        ... except SolanaError as e:
        ...     print(f"Solana error occurred: {e}")
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.context: Optional[Any] = context

    def __str__(self) -> str:
        """Return string representation of the exception."""
        return self.message