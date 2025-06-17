from web3 import Web3
from web3.types import TxReceipt
from web3.exceptions import TransactionNotFound, ContractLogicError, TimeExhausted
from eth_account import Account
from eth_account.signers.local import LocalAccount
from typing import Any, Dict

# Default timeout for waiting for transaction receipts (5 minutes)
DEFAULT_TRANSACTION_TIMEOUT = 300


class TransactionError(Exception):
    """Base exception for transaction-related errors."""
    pass


def build_and_send_transaction(
    w3: Web3,
    transaction: Dict[str, Any],
    private_key: str
) -> TxReceipt:
    """
    Builds, signs, and sends a transaction.
    """
    account: LocalAccount = Account.from_key(private_key)
    signed_transaction = account.sign_transaction(transaction)
    tx_hash = w3.eth.send_raw_transaction(
        signed_transaction.rawTransaction  # type: ignore[attr-defined]
    )
    return w3.eth.wait_for_transaction_receipt(tx_hash)


def send_signed_transaction(
    w3: Web3,
    signed_transaction: Any
) -> TxReceipt:
    """
    Sends an already signed transaction.
    """
    tx_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)


def wait_for_transaction_receipt(
    w3: Web3,
    tx_hash: Any,
    timeout: int = DEFAULT_TRANSACTION_TIMEOUT
) -> TxReceipt:
    """
    Wait for a transaction receipt with proper error handling.

    This function waits for a transaction to be mined and returns its receipt.
    It handles various Web3 exceptions and provides meaningful error messages.

    Args:
        w3: Web3 instance connected to an Ethereum node
        tx_hash: Transaction hash to wait for
        timeout: Maximum time to wait in seconds (default: 300)

    Returns:
        TxReceipt: The transaction receipt containing status, gas used, etc.

    Raises:
        TransactionError: If transaction fails, times out, or encounters other errors

    Example:
        >>> from web3 import Web3
        >>> w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        >>> tx_hash = "0x123..."
        >>> receipt = wait_for_transaction_receipt(w3, tx_hash)
        >>> print(f"Transaction status: {receipt['status']}")
    """
    try:
        # Wait for the transaction receipt with timeout
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

        # Check if transaction was successful (status = 1) or failed (status = 0)
        if receipt["status"] == 0:
            # Extract revert reason if available
            revert_reason = receipt.get("revertReason", "Unknown error")
            if revert_reason == "Unknown error" and receipt.get("gasUsed"):
                # Common failure patterns
                gas_used = receipt.get("gasUsed", 0)
                gas_limit = receipt.get("gas", 0)
                if isinstance(gas_used, int) and isinstance(gas_limit, int) and gas_used >= gas_limit:
                    revert_reason = "Out of gas"
            raise TransactionError(f"Transaction failed with status 0: {revert_reason}")

        return receipt

    except TimeExhausted as e:
        raise TransactionError(f"Transaction timed out after {timeout} seconds") from e
    except TransactionNotFound as e:
        raise TransactionError("Transaction not found") from e
    except ContractLogicError as e:
        raise TransactionError("Contract logic error") from e
    except Exception as e:
        raise TransactionError(f"Error waiting for transaction receipt: {str(e)}") from e


__all__ = [
    "TransactionError",
    "build_and_send_transaction",
    "send_signed_transaction",
    "wait_for_transaction_receipt",
    "DEFAULT_TRANSACTION_TIMEOUT"
]
