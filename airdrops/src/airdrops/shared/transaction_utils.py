from web3 import Web3
from web3.types import TxReceipt
from eth_account import Account
from eth_account.signers.local import LocalAccount
from typing import Any, Dict


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
    tx_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
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