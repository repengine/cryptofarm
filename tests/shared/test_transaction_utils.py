"""
Tests for the airdrops.shared.transaction_utils module.
"""

import pytest
from unittest.mock import MagicMock, patch

from airdrops.shared.transaction_utils import (  # type: ignore
    build_and_send_transaction,
    wait_for_transaction_receipt,
    TransactionError,
)
from web3.exceptions import TransactionNotFound, ContractLogicError


@pytest.fixture
def mock_web3():
    """Fixture for a mock Web3 instance."""
    mock = MagicMock()
    # Configure the eth attribute properly
    mock.eth = MagicMock()
    mock.eth.wait_for_transaction_receipt = MagicMock()
    return mock


@pytest.fixture
def mock_account():
    """Fixture for a mock Web3 account."""
    mock_acc = MagicMock()
    mock_acc.address = "0xMockSenderAddress"
    return mock_acc


@patch("airdrops.shared.transaction_utils.Account")
def test_build_and_send_transaction_success(mock_account_class):
    """Test successful building and sending of a transaction."""
    mock_web3 = MagicMock()
    mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 1, "gasUsed": 21000}

    mock_account = MagicMock()
    mock_account_class.from_key.return_value = mock_account
    mock_account.address = "0xMockSenderAddress"

    mock_signed_tx = MagicMock()
    mock_signed_tx.rawTransaction = b"raw_tx_bytes"
    mock_signed_tx.hash = b"0xmock_tx_hash"
    mock_account.sign_transaction.return_value = mock_signed_tx
    mock_web3.eth.send_raw_transaction.return_value = b"0xmock_tx_hash"

    transaction = {
        "to": "0xMockRecipientAddress",
        "value": 10**16,  # 0.01 ETH
        "gas": 21000,
        "gasPrice": 10**9,
        "nonce": 0,
        "chainId": 1,
    }
    private_key = "0x" + "a" * 64

    receipt = build_and_send_transaction(mock_web3, transaction, private_key)

    mock_account_class.from_key.assert_called_once_with(private_key)
    mock_account.sign_transaction.assert_called_once_with(transaction)
    mock_web3.eth.send_raw_transaction.assert_called_once_with(b"raw_tx_bytes")
    assert receipt == {"status": 1, "gasUsed": 21000}


@patch("airdrops.shared.transaction_utils.Account")
def test_build_and_send_transaction_failure(mock_account_class):
    """Test failure during building or sending of a transaction."""
    mock_web3 = MagicMock()

    mock_account = MagicMock()
    mock_account_class.from_key.return_value = mock_account
    mock_account.address = "0xMockSenderAddress"

    mock_account.sign_transaction.side_effect = Exception("Signing error")

    transaction = {
        "to": "0xMockRecipientAddress",
        "value": 10**16,
        "gas": 21000,
        "gasPrice": 10**9,
        "nonce": 0,
        "chainId": 1,
    }
    private_key = "0x" + "a" * 64

    with pytest.raises(Exception, match="Signing error"):
        build_and_send_transaction(mock_web3, transaction, private_key)

    mock_web3.eth.send_raw_transaction.assert_not_called()


def test_wait_for_transaction_receipt_success(mock_web3):
    """Test successful waiting for transaction receipt."""
    mock_receipt = {"status": 1, "gasUsed": 21000}
    mock_web3.eth.wait_for_transaction_receipt.return_value = mock_receipt

    tx_hash = "0xmock_tx_hash"
    receipt = wait_for_transaction_receipt(mock_web3, tx_hash)

    mock_web3.eth.wait_for_transaction_receipt.assert_called_once_with(tx_hash, timeout=300)
    assert receipt == mock_receipt


def test_wait_for_transaction_receipt_failure_status_0(mock_web3):
    """Test transaction failure (status 0) in receipt."""
    mock_receipt = {"status": 0, "gasUsed": 50000, "revertReason": "Out of gas"}
    mock_web3.eth.wait_for_transaction_receipt.return_value = mock_receipt

    tx_hash = "0xmock_tx_hash"
    with pytest.raises(TransactionError, match="Transaction failed with status 0: Out of gas"):
        wait_for_transaction_receipt(mock_web3, tx_hash)


def test_wait_for_transaction_receipt_not_found(mock_web3):
    """Test transaction not found error."""
    mock_web3.eth.wait_for_transaction_receipt.side_effect = TransactionNotFound("Tx not found")

    tx_hash = "0xnon_existent_tx"
    with pytest.raises(TransactionError, match="Transaction not found"):
        wait_for_transaction_receipt(mock_web3, tx_hash)


def test_wait_for_transaction_receipt_contract_logic_error(mock_web3):
    """Test contract logic error during receipt waiting."""
    mock_web3.eth.wait_for_transaction_receipt.side_effect = ContractLogicError("Invalid input")

    tx_hash = "0xcontract_tx"
    with pytest.raises(TransactionError, match="Contract logic error"):
        wait_for_transaction_receipt(mock_web3, tx_hash)


def test_wait_for_transaction_receipt_generic_exception(mock_web3):
    """Test generic exception during receipt waiting."""
    mock_web3.eth.wait_for_transaction_receipt.side_effect = Exception("Network error")

    tx_hash = "0xerror_tx"
    with pytest.raises(TransactionError, match="Error waiting for transaction receipt"):
        wait_for_transaction_receipt(mock_web3, tx_hash)
