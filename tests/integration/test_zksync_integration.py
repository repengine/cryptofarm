"""
Integration tests for the ZkSync protocol.
"""

import pytest
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock # Import PropertyMock
from web3 import Web3 # Import Web3

from airdrops.protocols.zksync import ZkSyncProtocol
from airdrops.protocols.zksync.exceptions import TransactionRevertedError


@pytest.fixture
def zksync_protocol() -> ZkSyncProtocol:
    """Fixture for a ZkSyncProtocol instance with mocked Web3."""
    mock_web3_l1 = MagicMock(spec=Web3)
    mock_web3_l2 = MagicMock(spec=Web3)

    # Mock the .eth attribute and its methods
    mock_web3_l1.eth = MagicMock()
    mock_web3_l1.eth.get_balance.return_value = 1000 * (10**18)  # Sufficient ETH for test
    type(mock_web3_l1.eth).gas_price = PropertyMock(return_value=10**9)  # 1 Gwei
    mock_web3_l1.eth.get_transaction_count.return_value = 0
    mock_web3_l1.eth.estimate_gas.return_value = 21000
    mock_web3_l1.eth.account.from_key.return_value.address = "0xMockL1Address"
    mock_web3_l1.to_checksum_address.side_effect = lambda x: x  # Passthrough for checksum addresses
    mock_web3_l1.to_wei.side_effect = lambda x, unit: int(x * (10**18)) if unit == "ether" else x
    mock_web3_l1.eth.wait_for_transaction_receipt.return_value = {"status": 1}
    mock_web3_l1.eth.send_raw_transaction.return_value = b"0xmock_tx_hash"
    mock_web3_l1.eth.contract.return_value = MagicMock()  # For ERC20 approvals

    mock_web3_l2.eth = MagicMock()
    mock_web3_l2.eth.get_balance.return_value = 5 * (10**18)  # 5 ETH for get_balance test
    type(mock_web3_l2.eth).gas_price = PropertyMock(return_value=20 * (10**9))  # 20 Gwei for get_gas_price test
    mock_web3_l2.eth.get_transaction_count.return_value = 15  # 15 for get_transaction_count test
    mock_web3_l2.eth.estimate_gas.return_value = 100000  # 100000 for estimate_gas test
    mock_web3_l2.eth.account.from_key.return_value.address = "0xMockL2Address"
    mock_web3_l2.to_checksum_address.side_effect = lambda x: x  # Passthrough for checksum addresses
    mock_web3_l2.eth.wait_for_transaction_receipt.return_value = {"status": 1}
    mock_web3_l2.eth.send_raw_transaction.return_value = b"0xmock_tx_hash"
    mock_web3_l2.eth.contract.return_value = MagicMock()  # For ERC20 approvals

    protocol = ZkSyncProtocol(
        l1_rpc_url="http://mock-l1-rpc.com",
        l2_rpc_url="http://mock-zksync-rpc.com",
        private_key="0x" + "2" * 64,
        web3_l1=mock_web3_l1,
        web3_l2=mock_web3_l2
    )
    return protocol


def test_zksync_protocol_initialization(zksync_protocol: Any) -> None:
    """Test that the ZkSyncProtocol initializes correctly."""
    assert zksync_protocol.l1_rpc_url == "http://mock-l1-rpc.com"
    assert zksync_protocol.l2_rpc_url == "http://mock-zksync-rpc.com"
    assert zksync_protocol.web3_l1 is not None
    assert zksync_protocol.web3_l2 is not None
    # Ensure that the injected mocks are used
    assert isinstance(zksync_protocol.web3_l1, MagicMock)
    assert isinstance(zksync_protocol.web3_l2, MagicMock)


def test_zksync_perform_airdrop_success(zksync_protocol: Any) -> None:
    """
    Test successful airdrop execution on ZkSync.
    Uses injected mocked Web3 instances.
    """
    # Configure specific mocks for this test if needed,
    # otherwise rely on the fixture's general mocks.
    # For instance, if a specific contract call is expected:
    mock_l1_bridge_contract = MagicMock()
    zksync_protocol.web3_l1.eth.contract.return_value = mock_l1_bridge_contract
    mock_l1_bridge_contract.functions.requestL2Transaction.return_value.build_transaction.return_value = {
        "from": "0xMockL1Address",
        "to": "0xMockL1BridgeAddress",
        "value": 100 * (10**18),
        "gasPrice": 10**9,
        "nonce": 0,
        "gas": 21000,
    }
    zksync_protocol.web3_l1.eth.account.sign_transaction.return_value.rawTransaction = b"signed_tx"
    zksync_protocol.web3_l1.eth.send_raw_transaction.return_value = b"0xmock_tx_hash_success_bytes"
    zksync_protocol.web3_l1.eth.wait_for_transaction_receipt.return_value = {"status": 1}

    value_usd = Decimal("100")
    
    # Since perform_airdrop is deprecated, we test bridge_assets
    # We mock the internal transaction sending method to avoid real network calls
    with patch("airdrops.protocols.zksync.zksync._build_and_send_tx_zksync", return_value="0xmock_tx_hash_success") as mock_send:
        # The bridge_assets method in ZkSyncProtocol calls the module-level bridge_assets
        # which in turn calls _build_and_send_tx_zksync.
        # The return value of ZkSyncProtocol.bridge_assets is the tx hash.
        tx_hash = zksync_protocol.bridge_assets(
            zksync_protocol.web3_l1,
            zksync_protocol.web3_l2,
            zksync_protocol.private_key,
            "ETH",
            value_usd,
            "deposit"
        )

    assert tx_hash == "0xmock_tx_hash_success"
    mock_send.assert_called_once()


def test_zksync_perform_airdrop_failure(zksync_protocol: Any) -> None:
    """
    Test failed airdrop execution on ZkSync (e.g., transaction revert).
    Uses injected mocked Web3 instances.
    """
    # Configure specific mocks for this test to simulate failure
    mock_l1_bridge_contract = MagicMock()
    zksync_protocol.web3_l1.eth.contract.return_value = mock_l1_bridge_contract
    mock_l1_bridge_contract.functions.requestL2Transaction.return_value.build_transaction.return_value = {
        "from": "0xMockL1Address",
        "to": "0xMockL1BridgeAddress",
        "value": 100 * (10**18),
        "gasPrice": 10**9,
        "nonce": 0,
        "gas": 21000,
    }
    zksync_protocol.web3_l1.eth.account.sign_transaction.return_value.rawTransaction = b"signed_tx"
    # Simulate transaction failure by making wait_for_transaction_receipt return status 0
    zksync_protocol.web3_l1.eth.wait_for_transaction_receipt.return_value = {"status": 0}
    zksync_protocol.web3_l1.eth.send_raw_transaction.return_value = b"0xmock_tx_hash_failure_bytes"

    value_usd = Decimal("0.05")  # ETH value for bridging
    with patch("airdrops.protocols.zksync.zksync._build_and_send_tx_zksync", side_effect=TransactionRevertedError("Mock transaction reverted")) as mock_send_tx:
        with pytest.raises(TransactionRevertedError):
            zksync_protocol.bridge_assets(
                zksync_protocol.web3_l1,
                zksync_protocol.web3_l2,
                zksync_protocol.private_key,
                "ETH",
                value_usd,
                "deposit"
            )

    mock_send_tx.assert_called_once()


def test_zksync_get_balance(zksync_protocol: Any) -> None:
    """Test getting account balance."""
    balance = zksync_protocol.web3_l2.eth.get_balance("0xMockAddress")
    assert balance == 5 * (10**18)  # Balance is in wei
    zksync_protocol.web3_l2.eth.get_balance.assert_called_once_with("0xMockAddress")


def test_zksync_get_gas_price(zksync_protocol: Any) -> None:
    """Test getting current gas price."""
    gas_price = zksync_protocol.web3_l2.eth.gas_price
    assert gas_price == 20 * (10**9)  # Gas price is in wei
    # No assert_called_once_with for properties like gas_price


def test_zksync_get_transaction_count(zksync_protocol: Any) -> None:
    """Test getting transaction count (nonce)."""
    nonce = zksync_protocol.web3_l2.eth.get_transaction_count("0xMockAddress")
    assert nonce == 15
    zksync_protocol.web3_l2.eth.get_transaction_count.assert_called_once_with("0xMockAddress")


def test_zksync_estimate_gas(zksync_protocol: Any) -> None:
    """Test gas estimation."""
    tx_params = {
        "from": "0xSender",
        "to": "0xRecipient",
        "value": 100,
    }
    gas_estimate = zksync_protocol.web3_l2.eth.estimate_gas(tx_params)
    assert gas_estimate == 100000
    zksync_protocol.web3_l2.eth.estimate_gas.assert_called_once_with(tx_params)
