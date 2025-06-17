"""
Tests for the EigenLayer protocol.
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from airdrops.protocols.eigenlayer import EigenLayerProtocol  # type: ignore
# No longer needed: from airdrops.shared.transaction_utils import wait_for_transaction_receipt


@pytest.fixture
def eigenlayer_protocol():
    """Fixture for an EigenLayerProtocol instance."""
    # In a real integration test, this would connect to a testnet or mock RPC
    # For now, we'll mock the internal web3 calls if necessary.
    return EigenLayerProtocol(
        rpc_url="http://mock-eigenlayer-rpc.com",
        private_key="0x" + "3" * 64,
        chain_id=17000,  # Goerli testnet for EigenLayer
    )


def test_eigenlayer_protocol_initialization(eigenlayer_protocol):
    """Test that the EigenLayerProtocol initializes correctly."""
    assert eigenlayer_protocol.rpc_url == "http://mock-eigenlayer-rpc.com"
    assert eigenlayer_protocol.chain_id == 17000
    assert eigenlayer_protocol.w3 is not None


@patch("airdrops.protocols.eigenlayer.Web3")
def test_eigenlayer_perform_airdrop_success(mock_web3, eigenlayer_protocol):
    """
    Test successful airdrop execution on EigenLayer.
    Mocks Web3 interactions.
    """
    # Mock Web3 instance and its methods
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance

    # Mock account and balance
    mock_account = MagicMock()
    mock_account.address = "0xMockSenderAddress"
    mock_instance.eth.account.from_key.return_value = mock_account
    mock_instance.eth.get_balance.return_value = 10**18  # 1 ETH in wei

    # Mock transaction building and sending
    mock_instance.eth.gas_price = 10**9  # 1 Gwei
    mock_instance.eth.get_transaction_count.return_value = 0
    mock_instance.eth.send_raw_transaction.return_value = b"0xmock_tx_hash"
    mock_instance.eth.wait_for_transaction_receipt.return_value = {
        "status": 1,
        "gasUsed": 21000,
        "blockHash": b"0xmock_block_hash",
    }

    # Mock contract interaction if any (for token transfers, etc.)
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

    # Perform airdrop
    value_usd = Decimal("100")
    success = eigenlayer_protocol.perform_airdrop(value_usd)

    assert success is True
    mock_web3.assert_called_once_with(mock_web3.HTTPProvider(eigenlayer_protocol.rpc_url))
    mock_instance.eth.account.from_key.assert_called_once_with(eigenlayer_protocol.private_key)
    mock_instance.eth.send_raw_transaction.assert_called_once()
    mock_instance.eth.wait_for_transaction_receipt.assert_called_once()


@patch("airdrops.protocols.eigenlayer.Web3")
def test_eigenlayer_perform_airdrop_failure(mock_web3, eigenlayer_protocol):
    """
    Test failed airdrop execution on EigenLayer (e.g., transaction revert).
    Mocks Web3 interactions.
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
    # Simulate transaction failure
    mock_instance.eth.wait_for_transaction_receipt.return_value = {
        "status": 0,  # Failed transaction
        "gasUsed": 50000,
        "blockHash": b"0xmock_block_hash",
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

    value_usd = Decimal("50")
    success = eigenlayer_protocol.perform_airdrop(value_usd)

    assert success is False
    mock_instance.eth.send_raw_transaction.assert_called_once()
    mock_instance.eth.wait_for_transaction_receipt.assert_called_once()


@patch("airdrops.protocols.eigenlayer.Web3")
def test_eigenlayer_get_balance(mock_web3, eigenlayer_protocol):
    """Test getting account balance."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.get_balance.return_value = 5 * (10**18)  # 5 ETH

    balance = eigenlayer_protocol.get_balance("0xMockAddress")
    assert balance == Decimal("5")
    mock_instance.eth.get_balance.assert_called_once_with("0xMockAddress")


@patch("airdrops.protocols.eigenlayer.Web3")
def test_eigenlayer_get_gas_price(mock_web3, eigenlayer_protocol):
    """Test getting current gas price."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.gas_price = 20 * (10**9)  # 20 Gwei

    gas_price = eigenlayer_protocol.get_gas_price()
    assert gas_price == Decimal("20")
    # No direct assert for eth.gas_price as it's an attribute access


@patch("airdrops.protocols.eigenlayer.Web3")
def test_eigenlayer_get_transaction_count(mock_web3, eigenlayer_protocol):
    """Test getting transaction count (nonce)."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.get_transaction_count.return_value = 15

    nonce = eigenlayer_protocol.get_transaction_count("0xMockAddress")
    assert nonce == 15
    mock_instance.eth.get_transaction_count.assert_called_once_with("0xMockAddress")


@patch("airdrops.protocols.eigenlayer.Web3")
def test_eigenlayer_estimate_gas(mock_web3, eigenlayer_protocol):
    """Test gas estimation."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.estimate_gas.return_value = 100000

    tx_params = {
        "from": "0xSender",
        "to": "0xRecipient",
        "value": 100,
    }
    gas_estimate = eigenlayer_protocol.estimate_gas(tx_params)
    assert gas_estimate == 100000
    mock_instance.eth.estimate_gas.assert_called_once_with(tx_params)
