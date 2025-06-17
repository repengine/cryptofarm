"""
Solana Protocol Module.

This module provides core functionality to interact with the Solana blockchain,
including network connection, balance checking, and SOL transfers.
"""

import logging

from solana.rpc.api import Client
from solana.rpc.commitment import Commitment
from solana.rpc.types import TxOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction

from .exceptions import SolanaError

# Configure logging for this module
logger = logging.getLogger(__name__)

# Constants for conversion
LAMPORTS_PER_SOL = 1_000_000_000


class SolanaProtocol:
    """Solana blockchain protocol interface.
    
    This class provides core functionality for interacting with the Solana blockchain,
    including network connection, balance checking, and SOL transfers.
    
    Args:
        rpc_url: The Solana RPC endpoint URL (e.g., "https://api.devnet.solana.com").
        private_key: The private key for transaction signing (base58 encoded).
        commitment: The commitment level for transactions (default: "confirmed").
        
    Example:
        >>> protocol = SolanaProtocol(
        ...     rpc_url="https://api.devnet.solana.com",
        ...     private_key="your_private_key_here",
        ...     commitment="confirmed"
        ... )
        >>> balance = protocol.get_balance()
        >>> print(f"Balance: {balance} SOL")
    """
    
    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        commitment: str = "confirmed",
    ) -> None:
        """Initialize the Solana protocol interface.
        
        Args:
            rpc_url: The Solana RPC endpoint URL.
            private_key: The private key for transaction signing.
            commitment: The commitment level for transactions.
            
        Raises:
            SolanaError: If initialization parameters are invalid.
        """
        if not rpc_url:
            raise SolanaError("RPC URL cannot be empty")
        if not private_key:
            raise SolanaError("Private key cannot be empty")
            
        self.rpc_url: str = rpc_url
        self.private_key: str = private_key
        self.commitment: str = commitment
        
        try:
            # Initialize Solana client
            self.client: Client = Client(rpc_url)
            
            # Create keypair from private key
            if len(private_key) == 128:  # Hex format
                keypair = Keypair.from_bytes(bytes.fromhex(private_key))
            else:  # Base58 format
                keypair = Keypair.from_base58_string(private_key)
            
            self.keypair: Keypair = keypair
            
            logger.info(f"Initialized Solana protocol with RPC: {rpc_url}")
            
        except Exception as e:
            raise SolanaError(f"Failed to initialize Solana protocol: {str(e)}")

    def get_balance(self) -> float:
        """Get the SOL balance of the wallet.
        
        Returns:
            The SOL balance as a float.
            
        Raises:
            SolanaError: If balance retrieval fails.
            
        Example:
            >>> protocol = SolanaProtocol("https://api.devnet.solana.com", "key")
            >>> balance = protocol.get_balance()
            >>> print(f"Balance: {balance} SOL")
        """
        try:
            response = self.client.get_balance(
                self.keypair.pubkey(),
                commitment=Commitment(self.commitment)
            )
            
            if response.value is None:
                raise SolanaError("Failed to retrieve balance")
                
            # Convert lamports to SOL
            balance_sol = response.value / LAMPORTS_PER_SOL
            
            logger.debug(f"Retrieved balance: {balance_sol} SOL")
            return balance_sol
            
        except Exception as e:
            if isinstance(e, SolanaError):
                raise
            raise SolanaError(f"Failed to get balance: {str(e)}")

    def transfer_sol(self, recipient_address: str, amount_sol: float) -> str:
        """Transfer SOL to a recipient address.
        
        Args:
            recipient_address: The recipient's public key address.
            amount_sol: The amount of SOL to transfer.
            
        Returns:
            The transaction signature as a string.
            
        Raises:
            SolanaError: If the transfer fails.
            
        Example:
            >>> protocol = SolanaProtocol("https://api.devnet.solana.com", "key")
            >>> signature = protocol.transfer_sol(
            ...     "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
            ...     0.1
            ... )
            >>> print(f"Transaction signature: {signature}")
        """
        try:
            # Validate recipient address
            try:
                recipient_pubkey = Pubkey.from_string(recipient_address)
            except Exception:
                raise SolanaError(f"Invalid recipient address: {recipient_address}")
            
            # Validate amount
            if amount_sol <= 0:
                raise SolanaError("Transfer amount must be positive")
                
            # Convert SOL to lamports
            amount_lamports = int(amount_sol * LAMPORTS_PER_SOL)
            
            # Create transfer instruction
            transfer_instruction = transfer(
                TransferParams(
                    from_pubkey=self.keypair.pubkey(),
                    to_pubkey=recipient_pubkey,
                    lamports=amount_lamports
                )
            )
            
            # Create and send transaction
            transaction = Transaction.new_with_payer([transfer_instruction], self.keypair.pubkey())
            
            response = self.client.send_transaction(
                transaction,
                opts=TxOpts(
                    skip_confirmation=False,
                    preflight_commitment=Commitment(self.commitment)
                )
            )
            
            if response.value is None:
                raise SolanaError("Transaction failed to send")
                
            signature = str(response.value)
            
            logger.info(
                f"Transferred {amount_sol} SOL to {recipient_address}, "
                f"signature: {signature}"
            )
            
            return signature
            
        except Exception as e:
            if isinstance(e, SolanaError):
                raise
            raise SolanaError(f"Failed to transfer SOL: {str(e)}")

    def get_connection_info(self) -> dict[str, str]:
        """Get connection information for the Solana protocol.
        
        Returns:
            Dictionary containing connection details.
            
        Example:
            >>> protocol = SolanaProtocol("https://api.devnet.solana.com", "key")
            >>> info = protocol.get_connection_info()
            >>> print(info["rpc_url"])
            https://api.devnet.solana.com
        """
        return {
            "rpc_url": self.rpc_url,
            "commitment": self.commitment,
            "public_key": str(self.keypair.pubkey()),
        }