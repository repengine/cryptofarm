"""
Tests for the LayerZero protocol.
"""

import pytest
from decimal import Decimal
from typing import Any
from unittest.mock import Mock, patch, PropertyMock, MagicMock

from airdrops.protocols.layerzero import LayerZeroProtocol
from web3.types import TxParams, Wei


class TypedWeb3Mock(Mock):
    """Type-safe Web3 mock that satisfies mypy strict checking."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        
        # Configure mock attributes with proper types
        self.is_connected = Mock(return_value=True)
        self.eth = TypedEthMock()
        self.to_wei = Mock(return_value=Wei(50000000000000000))  # 0.05 ETH in wei
        self.from_wei = Mock(return_value=1.0)  # 1 ETH
        self.to_checksum_address = Mock(return_value="0x000000000000000000000000000000000000dEaD")


class TypedEthMock(Mock):
    """Type-safe Eth mock that satisfies mypy strict checking."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        
        # Mock methods with proper return types
        self.get_transaction_count = Mock(return_value=0)
        self.get_balance = Mock(return_value=Wei(10**18))  # 1 ETH
        self.gas_price = PropertyMock(return_value=Wei(10**9))  # 1 Gwei
        self.estimate_gas = Mock(return_value=100000)
        self.send_raw_transaction = Mock(return_value=b"0xmock_tx_hash")
        
        # Mock receipt as an object with attributes
        mock_receipt = Mock()
        mock_receipt.status = 1
        mock_receipt.gasUsed = 21000
        mock_receipt.blockHash = b"0xmock_block_hash"
        self.wait_for_transaction_receipt = Mock(return_value=mock_receipt)
        
        # Mock account methods
        self.account = Mock()
        mock_account = Mock()
        mock_account.address = "0xMockSenderAddress"
        self.account.from_key = Mock(return_value=mock_account)
        
        # Mock gas_price as a property-like attribute
        self._gas_price = Wei(10**9)  # 1 Gwei
    
    @property
    def gas_price(self) -> Wei:
        """Mock gas_price property."""
        return self._gas_price
    
    @gas_price.setter
    def gas_price(self, value: Wei) -> None:
        """Mock gas_price setter."""
        self._gas_price = value


@pytest.fixture
def mock_web3() -> MagicMock:
    """Fixture for a comprehensive mock Web3 instance."""
    from web3 import Web3
    
    mock_w3 = MagicMock(spec=Web3)
    mock_w3.is_connected.return_value = True
    
    # Mock eth attribute and its methods
    mock_w3.eth = MagicMock()
    mock_w3.eth.gas_price = Wei(10**9)  # 1 Gwei
    mock_w3.eth.get_transaction_count = MagicMock(return_value=0)
    mock_w3.eth.get_balance = MagicMock(return_value=Wei(10**18))  # 1 ETH
    mock_w3.eth.estimate_gas = MagicMock(return_value=100000)
    mock_w3.eth.send_raw_transaction.return_value = b"0xmock_tx_hash"
    
    # Mock receipt as an object with attributes
    mock_receipt = MagicMock()
    mock_receipt.status = 1
    mock_receipt.gasUsed = 21000
    mock_receipt.blockHash = b"0xmock_block_hash"
    mock_w3.eth.wait_for_transaction_receipt = MagicMock(return_value=mock_receipt)
    
    # Mock account methods
    mock_w3.eth.account = MagicMock()
    mock_account = MagicMock()
    mock_account.address = "0xMockSenderAddress"
    mock_w3.eth.account.from_key.return_value = mock_account
    
    # Mock utility methods
    mock_w3.to_wei.return_value = Wei(50000000000000000)  # 0.05 ETH in wei
    mock_w3.from_wei.return_value = 1.0  # 1 ETH
    mock_w3.to_checksum_address.return_value = "0x000000000000000000000000000000000000dEaD"
    
    return mock_w3


@pytest.fixture
def layerzero_protocol(mock_web3: MagicMock) -> LayerZeroProtocol:
    """Fixture for a LayerZeroProtocol instance."""
    # Mock Web3 and constants during protocol initialization to prevent real network calls
    with patch("airdrops.protocols.layerzero.layerzero.Web3") as mock_web3_class, \
         patch("airdrops.protocols.layerzero.layerzero._get_contract_layerzero") as mock_get_contract, \
         patch("airdrops.protocols.layerzero.layerzero.LAYERZERO_ENDPOINT_ADDRESSES", {"1": "0xMockEndpointAddress"}):
        mock_web3_class.return_value = mock_web3
        
        # Mock the endpoint contract
        mock_contract = MagicMock()
        mock_get_contract.return_value = mock_contract
        
        protocol = LayerZeroProtocol(
            rpc_url="http://mock-layerzero-rpc.com",
            private_key="0x" + "4" * 64,
            chain_id=1,  # Ethereum mainnet
        )
        # Store the mocks for use in tests
        protocol.w3 = mock_web3
        protocol.endpoint_contract = mock_contract
        return protocol


@patch("airdrops.protocols.layerzero.layerzero.LAYERZERO_ENDPOINT_ADDRESSES", {"1": "0xMockEndpointAddress"})
@patch("airdrops.protocols.layerzero.layerzero._get_contract_layerzero")
@patch("airdrops.protocols.layerzero.layerzero.Web3")
def test_layerzero_protocol_initialization(mock_web3: Any, mock_get_contract: Any) -> None:
    """Test that the LayerZeroProtocol initializes correctly."""
    mock_instance = MagicMock()
    mock_instance.is_connected.return_value = True
    mock_web3.return_value = mock_instance
    
    mock_contract = MagicMock()
    mock_get_contract.return_value = mock_contract
    
    protocol = LayerZeroProtocol(
        rpc_url="http://mock-layerzero-rpc.com",
        private_key="0x" + "4" * 64,
        chain_id=1,
    )
    
    assert protocol.rpc_url == "http://mock-layerzero-rpc.com"
    assert protocol.chain_id == 1
    assert protocol.w3 is not None
    mock_web3.assert_called_once_with(mock_web3.HTTPProvider("http://mock-layerzero-rpc.com"))
    mock_instance.is_connected.assert_called_once()


def test_layerzero_perform_airdrop_not_implemented(layerzero_protocol: LayerZeroProtocol) -> None:
    """
    Test that perform_airdrop is not yet implemented.
    """
    value_usd = Decimal("100")
    recipient = "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
    
    # The method should raise NotImplementedError
    with pytest.raises(NotImplementedError, match="Airdrop functionality not yet implemented"):
        layerzero_protocol.perform_airdrop(
            web3=layerzero_protocol.w3,
            private_key=layerzero_protocol.private_key,
            amount=value_usd,
            recipient=recipient
        )


def test_layerzero_perform_airdrop_legacy_success(layerzero_protocol: LayerZeroProtocol) -> None:
    """
    Test successful legacy airdrop execution on LayerZero.
    Mocks Web3 interactions.
    """
    # Mock account signing - this needs to not raise an exception
    mock_account = MagicMock()
    mock_account.address = "0xMockSenderAddress"
    mock_signed_tx = MagicMock()
    mock_signed_tx.rawTransaction = b"signed_tx"
    mock_account.sign_transaction.return_value = mock_signed_tx

    # Set the account on the protocol instance
    layerzero_protocol.account = mock_account

    # Mock successful transaction receipt
    mock_receipt = MagicMock()
    mock_receipt.status = 1  # Success
    mock_receipt.gasUsed = 21000
    mock_receipt.blockHash = b"0xmock_block_hash"
    layerzero_protocol.w3.eth.wait_for_transaction_receipt.return_value = mock_receipt  # type: ignore[attr-defined]

    # Perform legacy airdrop
    value_usd = Decimal("100")
    success = layerzero_protocol.perform_airdrop_legacy(value_usd)

    assert success is True


def test_layerzero_get_balance(layerzero_protocol: LayerZeroProtocol) -> None:
    """Test getting account balance."""
    # The get_balance method requires a web3 instance and address
    with pytest.raises(NotImplementedError, match="Balance query functionality not yet implemented"):
        layerzero_protocol.get_balance(
            web3=layerzero_protocol.w3,
            address="0xMockAddress"
        )


def test_layerzero_get_gas_price(layerzero_protocol: LayerZeroProtocol) -> None:
    """Test getting current gas price."""
    gas_price = layerzero_protocol.get_gas_price()
    assert gas_price == Decimal("1.0")  # The mock returns 10**9 wei = 1 Gwei


def test_layerzero_get_transaction_count(layerzero_protocol: LayerZeroProtocol) -> None:
    """Test getting transaction count (nonce)."""
    # Update mock for this specific test
    layerzero_protocol.w3.eth.get_transaction_count.return_value = 15  # type: ignore[attr-defined]

    nonce = layerzero_protocol.get_transaction_count("0xMockAddress")
    assert nonce == 15


def test_layerzero_estimate_gas(layerzero_protocol: LayerZeroProtocol) -> None:
    """Test gas estimation."""
    # Update mock for this specific test
    layerzero_protocol.w3.eth.estimate_gas.return_value = 100000  # type: ignore[attr-defined]

    tx_params: TxParams = {
        "from": "0xSender",
        "to": "0xRecipient",
        "value": Wei(100),
    }
    gas_estimate = layerzero_protocol.estimate_gas(tx_params)
    assert gas_estimate == 100000
