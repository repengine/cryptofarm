"""
Tests for the EigenLayer protocol.
"""

import pytest
from decimal import Decimal
from typing import Any
from unittest.mock import Mock, patch, PropertyMock, MagicMock

from airdrops.protocols.eigenlayer import EigenLayerProtocol
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
        self.to_checksum_address = Mock(return_value="0xMockAddress")


class TypedEthMock(Mock):
    """Type-safe Eth mock that satisfies mypy strict checking."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        
        # Mock methods with proper return types
        self.get_transaction_count = Mock(return_value=0)
        self.get_balance = Mock(return_value=Wei(10**18))  # 1 ETH
        self.gas_price = PropertyMock(return_value=Wei(10**9))  # 1 Gwei
        self.estimate_gas = Mock(return_value=100000)
        
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
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    
    # Mock eth attribute and its methods
    mock_w3.eth = MagicMock()
    mock_w3.eth.gas_price = Wei(10**9)  # 1 Gwei
    mock_w3.eth.get_transaction_count.return_value = 0
    mock_w3.eth.get_balance.return_value = Wei(10**18)  # 1 ETH
    mock_w3.eth.estimate_gas.return_value = 100000
    
    # Mock account methods
    mock_w3.eth.account = MagicMock()
    mock_account = MagicMock()
    mock_account.address = "0xMockSenderAddress"
    mock_w3.eth.account.from_key.return_value = mock_account
    
    # Mock utility methods
    mock_w3.to_wei.return_value = Wei(50000000000000000)  # 0.05 ETH in wei
    mock_w3.from_wei.return_value = 1.0  # 1 ETH
    mock_w3.to_checksum_address.return_value = "0xMockAddress"
    
    return mock_w3


@pytest.fixture
def eigenlayer_protocol(mock_web3: MagicMock) -> EigenLayerProtocol:
    """Fixture for an EigenLayerProtocol instance."""
    # Mock Web3 during protocol initialization to prevent real network calls
    with patch("airdrops.protocols.eigenlayer.eigenlayer.Web3") as mock_web3_class:
        mock_web3_class.return_value = mock_web3
        
        protocol = EigenLayerProtocol(
            rpc_url="http://mock-eigenlayer-rpc.com",
            private_key="0x" + "3" * 64,
            chain_id=17000,  # Goerli testnet for EigenLayer
        )
        # Store the mock for use in tests
        protocol.w3 = mock_web3
        return protocol


@patch("airdrops.protocols.eigenlayer.eigenlayer.Web3")
def test_eigenlayer_protocol_initialization(mock_web3: Any) -> None:
    """Test that the EigenLayerProtocol initializes correctly."""
    mock_instance = MagicMock()
    mock_instance.is_connected.return_value = True
    mock_web3.return_value = mock_instance
    
    protocol = EigenLayerProtocol(
        rpc_url="http://mock-eigenlayer-rpc.com",
        private_key="0x" + "3" * 64,
        chain_id=17000,
    )
    
    assert protocol.rpc_url == "http://mock-eigenlayer-rpc.com"
    assert protocol.chain_id == 17000
    assert protocol.w3 is not None
    mock_web3.assert_called_once_with(mock_web3.HTTPProvider("http://mock-eigenlayer-rpc.com"))
    mock_instance.is_connected.assert_called_once()


def test_eigenlayer_perform_airdrop_not_implemented(eigenlayer_protocol: EigenLayerProtocol) -> None:
    """
    Test that perform_airdrop is not yet implemented.
    """
    value_usd = Decimal("100")
    recipient = "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
    
    # The method should raise NotImplementedError
    with pytest.raises(NotImplementedError, match="Airdrop functionality not yet implemented"):
        eigenlayer_protocol.perform_airdrop(
            web3=eigenlayer_protocol.w3,
            private_key=eigenlayer_protocol.private_key,
            amount=value_usd,
            recipient=recipient
        )


def test_eigenlayer_perform_airdrop_legacy_success(eigenlayer_protocol: EigenLayerProtocol) -> None:
    """
    Test successful legacy airdrop execution on EigenLayer.
    Mocks Web3 interactions.
    """
    # Mock build_and_send_transaction
    with patch("airdrops.protocols.eigenlayer.eigenlayer.build_and_send_transaction") as mock_build_send:
        mock_receipt = MagicMock()
        mock_receipt.status = 1
        mock_receipt.transactionHash = b"0xmock_tx_hash"
        mock_build_send.return_value = mock_receipt

        # Perform legacy airdrop
        value_usd = Decimal("100")
        success = eigenlayer_protocol.perform_airdrop_legacy(value_usd)

        assert success is True
        mock_build_send.assert_called_once()
        mock_build_send.assert_called_once()


def test_eigenlayer_get_balance(eigenlayer_protocol: EigenLayerProtocol) -> None:
    """Test getting account balance."""
    balance = eigenlayer_protocol.get_balance("0xMockAddress")
    assert balance == Decimal("1.0")  # The mock returns 10**18 wei = 1 ETH


def test_eigenlayer_get_gas_price(eigenlayer_protocol: EigenLayerProtocol) -> None:
    """Test getting current gas price."""
    gas_price = eigenlayer_protocol.get_gas_price()
    assert gas_price == Decimal("1.0")  # The mock returns 10**9 wei = 1 Gwei


def test_eigenlayer_get_transaction_count(eigenlayer_protocol: EigenLayerProtocol) -> None:
    """Test getting transaction count (nonce)."""
    # Update mock for this specific test
    eigenlayer_protocol.w3.eth.get_transaction_count.return_value = 15

    nonce = eigenlayer_protocol.get_transaction_count("0xMockAddress")
    assert nonce == 15


def test_eigenlayer_estimate_gas(eigenlayer_protocol: EigenLayerProtocol) -> None:
    """Test gas estimation."""
    # Update mock for this specific test
    eigenlayer_protocol.w3.eth.estimate_gas.return_value = 100000

    tx_params: TxParams = {
        "from": "0xSender",
        "to": "0xRecipient",
        "value": Wei(100),
    }
    gas_estimate = eigenlayer_protocol.estimate_gas(tx_params)
    assert gas_estimate == 100000
