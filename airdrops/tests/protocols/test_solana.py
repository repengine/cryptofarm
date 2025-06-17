"""
Tests for the Solana protocol.
"""

import pytest
from unittest.mock import Mock, patch

from airdrops.protocols.solana import SolanaProtocol, SolanaError


@pytest.fixture
def mock_solana_client():
    """Mock Solana client for testing."""
    with patch('airdrops.protocols.solana.solana.Client') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_keypair():
    """Mock Solana keypair for testing."""
    with patch('airdrops.protocols.solana.solana.Keypair') as mock_keypair_class:
        mock_keypair = Mock()
        mock_keypair.pubkey.return_value = Mock()
        mock_keypair.pubkey.return_value.__str__ = Mock(return_value="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM")
        mock_keypair_class.from_base58_string.return_value = mock_keypair
        yield mock_keypair


@pytest.fixture
def solana_protocol(mock_solana_client, mock_keypair):
    """Fixture for a SolanaProtocol instance."""
    return SolanaProtocol(
        rpc_url="https://api.devnet.solana.com",
        private_key="5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtrzLwGNf2n",
        commitment="confirmed",
    )


def test_solana_protocol_initialization(solana_protocol):
    """Test that the SolanaProtocol initializes correctly."""
    assert solana_protocol.rpc_url == "https://api.devnet.solana.com"
    assert solana_protocol.private_key == "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtrzLwGNf2n"
    assert solana_protocol.commitment == "confirmed"
    assert hasattr(solana_protocol, 'client')
    assert hasattr(solana_protocol, 'keypair')


def test_solana_protocol_initialization_empty_rpc_url():
    """Test that SolanaProtocol raises error with empty RPC URL."""
    with pytest.raises(SolanaError, match="RPC URL cannot be empty"):
        SolanaProtocol(
            rpc_url="",
            private_key="test_key",
        )


def test_solana_protocol_initialization_empty_private_key():
    """Test that SolanaProtocol raises error with empty private key."""
    with pytest.raises(SolanaError, match="Private key cannot be empty"):
        SolanaProtocol(
            rpc_url="https://api.devnet.solana.com",
            private_key="",
        )


def test_solana_protocol_default_commitment(mock_solana_client, mock_keypair):
    """Test that SolanaProtocol uses default commitment level."""
    protocol = SolanaProtocol(
        rpc_url="https://api.devnet.solana.com",
        private_key="5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtrzLwGNf2n",
    )
    assert protocol.commitment == "confirmed"


def test_solana_protocol_initialization_invalid_private_key():
    """Test that SolanaProtocol raises error with invalid private key."""
    with patch('airdrops.protocols.solana.solana.Client'):
        with patch('airdrops.protocols.solana.solana.Keypair.from_base58_string', side_effect=Exception("Invalid key")):
            with pytest.raises(SolanaError, match="Failed to initialize Solana protocol"):
                SolanaProtocol(
                    rpc_url="https://api.devnet.solana.com",
                    private_key="invalid_key",
                )


def test_get_balance_success(solana_protocol):
    """Test successful balance retrieval."""
    # Mock the balance response
    mock_response = Mock()
    mock_response.value = 1500000000  # 1.5 SOL in lamports
    solana_protocol.client.get_balance.return_value = mock_response
    
    balance = solana_protocol.get_balance()
    
    assert balance == 1.5
    solana_protocol.client.get_balance.assert_called_once()


def test_get_balance_none_response(solana_protocol):
    """Test balance retrieval with None response."""
    mock_response = Mock()
    mock_response.value = None
    solana_protocol.client.get_balance.return_value = mock_response
    
    with pytest.raises(SolanaError, match="Failed to retrieve balance"):
        solana_protocol.get_balance()


def test_get_balance_client_error(solana_protocol):
    """Test balance retrieval with client error."""
    solana_protocol.client.get_balance.side_effect = Exception("Network error")
    
    with pytest.raises(SolanaError, match="Failed to get balance"):
        solana_protocol.get_balance()


def test_transfer_sol_success(solana_protocol):
    """Test successful SOL transfer."""
    # Mock the transaction response
    mock_response = Mock()
    mock_response.value = "signature123"
    solana_protocol.client.send_transaction.return_value = mock_response
    
    with patch('airdrops.protocols.solana.solana.Pubkey') as mock_pubkey:
        with patch('airdrops.protocols.solana.solana.transfer') as mock_transfer:
            with patch('airdrops.protocols.solana.solana.Transaction') as mock_transaction:
                mock_tx = Mock()
                mock_transaction.new_with_payer.return_value = mock_tx
                
                signature = solana_protocol.transfer_sol(
                    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
                    0.5
                )
                
                assert signature == "signature123"
                mock_pubkey.from_string.assert_called_once_with("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM")
                mock_transfer.assert_called_once()
                solana_protocol.client.send_transaction.assert_called_once()


def test_transfer_sol_invalid_recipient(solana_protocol):
    """Test SOL transfer with invalid recipient address."""
    with patch('airdrops.protocols.solana.solana.Pubkey.from_string', side_effect=Exception("Invalid address")):
        with pytest.raises(SolanaError, match="Invalid recipient address"):
            solana_protocol.transfer_sol("invalid_address", 0.5)


def test_transfer_sol_negative_amount(solana_protocol):
    """Test SOL transfer with negative amount."""
    with pytest.raises(SolanaError, match="Transfer amount must be positive"):
        solana_protocol.transfer_sol(
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
            -0.5
        )


def test_transfer_sol_zero_amount(solana_protocol):
    """Test SOL transfer with zero amount."""
    with pytest.raises(SolanaError, match="Transfer amount must be positive"):
        solana_protocol.transfer_sol(
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
            0.0
        )


def test_transfer_sol_transaction_failure(solana_protocol):
    """Test SOL transfer with transaction failure."""
    mock_response = Mock()
    mock_response.value = None
    solana_protocol.client.send_transaction.return_value = mock_response
    
    with patch('airdrops.protocols.solana.solana.Pubkey'):
        with patch('airdrops.protocols.solana.solana.transfer'):
            with patch('airdrops.protocols.solana.solana.Transaction'):
                with pytest.raises(SolanaError, match="Transaction failed to send"):
                    solana_protocol.transfer_sol(
                        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
                        0.5
                    )


def test_transfer_sol_client_error(solana_protocol):
    """Test SOL transfer with client error."""
    solana_protocol.client.send_transaction.side_effect = Exception("Network error")
    
    with patch('airdrops.protocols.solana.solana.Pubkey'):
        with patch('airdrops.protocols.solana.solana.transfer'):
            with patch('airdrops.protocols.solana.solana.Transaction'):
                with pytest.raises(SolanaError, match="Failed to transfer SOL"):
                    solana_protocol.transfer_sol(
                        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
                        0.5
                    )


def test_get_connection_info(solana_protocol):
    """Test getting connection information."""
    info = solana_protocol.get_connection_info()
    
    assert isinstance(info, dict)
    assert info["rpc_url"] == "https://api.devnet.solana.com"
    assert info["commitment"] == "confirmed"
    assert "public_key" in info
    assert "private_key" not in info  # Should not expose private key


def test_solana_error_creation():
    """Test SolanaError exception creation."""
    error = SolanaError("Test error message")
    assert str(error) == "Test error message"
    assert error.message == "Test error message"
    assert error.context is None


def test_solana_error_with_context():
    """Test SolanaError exception with context."""
    context = {"transaction_id": "abc123"}
    error = SolanaError("Test error with context", context=context)
    assert str(error) == "Test error with context"
    assert error.message == "Test error with context"
    assert error.context == context