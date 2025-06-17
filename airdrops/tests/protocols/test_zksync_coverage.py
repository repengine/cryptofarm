"""
Additional coverage tests for the ZkSync protocol, focusing on edge cases and specific functionalities.
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from airdrops.protocols.zksync import ZkSyncProtocol  # type: ignore


@pytest.fixture
def zksync_protocol_coverage():
    """Fixture for a ZkSyncProtocol instance for coverage tests."""
    return ZkSyncProtocol(
        rpc_url="http://mock-zksync-coverage-rpc.com",
        private_key="0x" + "5" * 64,
        chain_id=280,  # ZkSync Era testnet
    )


def test_zksync_protocol_invalid_private_key(zksync_protocol_coverage):
    """Test initialization with an invalid private key format."""
    with pytest.raises(ValueError, match="Private key must be a 64-character hex string"):
        ZkSyncProtocol(
            rpc_url="http://mock-rpc.com",
            private_key="invalid_key",
            chain_id=280,
        )


def test_zksync_protocol_empty_rpc_url(zksync_protocol_coverage):
    """Test initialization with an empty RPC URL."""
    with pytest.raises(ValueError, match="RPC URL cannot be empty"):
        ZkSyncProtocol(
            rpc_url="",
            private_key="0x" + "6" * 64,
            chain_id=280,
        )


@patch("airdrops.protocols.zksync.Web3")
def test_zksync_perform_airdrop_insufficient_funds(mock_web3, zksync_protocol_coverage):
    """
    Test airdrop failure due to insufficient funds.
    """
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance

    mock_account = MagicMock()
    mock_account.address = "0xMockSenderAddress"
    mock_instance.eth.account.from_key.return_value = mock_account
    mock_instance.eth.get_balance.return_value = 0  # Insufficient balance

    mock_instance.eth.gas_price = 10**9
    mock_instance.eth.get_transaction_count.return_value = 0

    # Mock contract interaction to build transaction
    mock_contract = MagicMock()
    mock_instance.eth.contract.return_value = mock_contract
    mock_contract.functions.transfer.return_value.build_transaction.return_value = {
        "nonce": 0,
        "gasPrice": 10**9,
        "gas": 100000,
        "to": "0xMockRecipientAddress",
        "value": 0,
        "data": "0x",
    }
    mock_account.sign_transaction.return_value.rawTransaction = b"signed_tx"

    value_usd = Decimal("100")
    success = zksync_protocol_coverage.perform_airdrop(value_usd)

    assert success is False
    # Ensure send_raw_transaction was not called due to balance check
    mock_instance.eth.send_raw_transaction.assert_not_called()


@patch("airdrops.protocols.zksync.Web3")
def test_zksync_perform_airdrop_rpc_error(mock_web3, zksync_protocol_coverage):
    """
    Test airdrop failure due to RPC connection error.
    """
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance

    # Simulate RPC connection error
    mock_instance.eth.account.from_key.side_effect = Exception("RPC connection failed")

    value_usd = Decimal("100")
    success = zksync_protocol_coverage.perform_airdrop(value_usd)

    assert success is False
    mock_instance.eth.send_raw_transaction.assert_not_called()


@patch("airdrops.protocols.zksync.Web3")
def test_zksync_perform_airdrop_transaction_revert_message(mock_web3, zksync_protocol_coverage):
    """
    Test airdrop failure where transaction reverts with a specific message.
    """
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance

    mock_account = MagicMock()
    mock_account.address = "0xMockSenderAddress"
    mock_instance.eth.account.from_key.return_value = mock_account
    mock_instance.eth.get_balance.return_value = 10**18

    mock_instance.eth.gas_price = 10**9
    mock_instance.eth.get_transaction_count.return_value = 0
    mock_instance.eth.send_raw_transaction.return_value = b"0xmock_tx_hash"
    # Simulate transaction failure with a revert reason
    mock_instance.eth.wait_for_transaction_receipt.return_value = {
        "status": 0,
        "gasUsed": 50000,
        "blockHash": b"0xmock_block_hash",
        "revertReason": "ERC20: transfer amount exceeds balance",  # Example revert reason
    }

    mock_contract = MagicMock()
    mock_instance.eth.contract.return_value = mock_contract
    mock_contract.functions.transfer.return_value.build_transaction.return_value = {
        "nonce": 0,
        "gasPrice": 10**9,
        "gas": 100000,
        "to": "0xMockRecipientAddress",
        "value": 0,
        "data": "0x",
    }
    mock_account.sign_transaction.return_value.rawTransaction = b"signed_tx"

    value_usd = Decimal("10")
    success = zksync_protocol_coverage.perform_airdrop(value_usd)

    assert success is False
    mock_instance.eth.send_raw_transaction.assert_called_once()
    mock_instance.eth.wait_for_transaction_receipt.assert_called_once()


@patch("airdrops.protocols.zksync.Web3")
def test_zksync_get_balance_error_handling(mock_web3, zksync_protocol_coverage):
    """Test error handling for get_balance."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.get_balance.side_effect = Exception("Balance RPC error")

    balance = zksync_protocol_coverage.get_balance("0xMockAddress")
    assert balance == Decimal("0")  # Should return 0 on error


@patch("airdrops.protocols.zksync.Web3")
def test_zksync_get_gas_price_error_handling(mock_web3, zksync_protocol_coverage):
    """Test error handling for get_gas_price."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    type(mock_instance.eth).gas_price = MagicMock(side_effect=Exception("Gas price RPC error"))

    gas_price = zksync_protocol_coverage.get_gas_price()
    assert gas_price == Decimal("0")  # Should return 0 on error


@patch("airdrops.protocols.zksync.Web3")
def test_zksync_get_transaction_count_error_handling(mock_web3, zksync_protocol_coverage):
    """Test error handling for get_transaction_count."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.get_transaction_count.side_effect = Exception("Nonce RPC error")

    nonce = zksync_protocol_coverage.get_transaction_count("0xMockAddress")
    assert nonce == 0  # Should return 0 on error


@patch("airdrops.protocols.zksync.Web3")
def test_zksync_estimate_gas_error_handling(mock_web3, zksync_protocol_coverage):
    """Test error handling for estimate_gas."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.estimate_gas.side_effect = Exception("Estimate gas RPC error")

    tx_params = {
        "from": "0xSender",
        "to": "0xRecipient",
        "value": 100,
    }
    gas_estimate = zksync_protocol_coverage.estimate_gas(tx_params)
    assert gas_estimate == 0  # Should return 0 on error
