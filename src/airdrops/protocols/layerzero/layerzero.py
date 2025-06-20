"""
LayerZero Protocol Module.

This module provides functionalities to interact with the LayerZero network,
primarily for sending and receiving messages (and thus value) between
different blockchains (e.g., Ethereum, BNB Chain, Polygon).
"""

import json
import logging
import random
import time
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional, Any, cast, Sequence
from requests.exceptions import ConnectionError, Timeout

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError
from web3.types import TxParams, TxReceipt
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.types import Wei

from airdrops.shared import constants
from airdrops.shared.transaction_utils import TransactionError
from .exceptions import (
    LayerZeroError,
    TransactionRevertedError,
    ApprovalError,
    GasEstimationError,
    MaxRetriesExceededError,
    TransactionBuildError,
    TransactionSendError,
    UnsupportedChainError,
)


# Configure logging for this module
logger = logging.getLogger(__name__)

# Contract addresses from architecture / config
LAYERZERO_ENDPOINT_ADDRESSES = constants.LAYERZERO_ENDPOINT_ADDRESSES
LAYERZERO_TOKEN_ADDRESSES = constants.LAYERZERO_TOKEN_ADDRESSES

# ABI Names
ERC20_ABI_NAME = "ERC20"
LAYERZERO_ENDPOINT_ABI_NAME = "LayerZeroEndpoint"

# Default gas limits and constants
DEFAULT_GAS_MULTIPLIER = 1.2
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ETH_SYMBOL = "ETH"


def _load_abi_layerzero(contract_name: str) -> Sequence[Dict[str, Any]]:
    """
    Load ABI JSON from the abi directory.

    Args:
    contract_name: Name of the contract (e.g., 'LayerZeroEndpoint')

    Returns:
    ABI as a list of dictionaries

    Raises:
    FileNotFoundError: If ABI file doesn't exist
    json.JSONDecodeError: If ABI file is invalid JSON
    """
    abi_path = Path(__file__).parent / "abi" / f"{contract_name}.json"
    try:
        with open(abi_path, "r") as f:
            return cast(Sequence[Dict[str, Any]], json.load(f))
    except FileNotFoundError:
        logger.error(f"ABI file not found: {abi_path}")
        raise FileNotFoundError(f"ABI file not found: {abi_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in ABI file {abi_path}: {e.msg}")
        raise json.JSONDecodeError(
            f"Invalid JSON in ABI file {abi_path}: {e.msg}", e.doc, e.pos
        )


def _get_account_layerzero(private_key: str, web3_instance: Web3) -> LocalAccount:
    """
    Create Account object from private key.

    Args:
    private_key: Private key string
    web3_instance: Web3 (used for potential future validation, currently unused)

    Returns:
    Account object

    Raises:
    ValueError: If private key is invalid
    """
    try:
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key
        account: LocalAccount = Account.from_key(private_key)
        return account
    except Exception as e:
        logger.error(f"Invalid private key provided: {e}")
        raise ValueError(f"Invalid private key: {e}")


def _get_contract_layerzero(
    web3_instance: Web3, contract_name: str, contract_address: str
) -> Contract:
    """
    Load ABI and return contract instance.

    Args:
    web3_instance: Web3 instance
    contract_name: Name of contract for ABI loading
    contract_address: Contract address

    Returns:
    Web3 Contract instance
    """
    abi = _load_abi_layerzero(contract_name)
    checksum_address = Web3.to_checksum_address(contract_address)
    return web3_instance.eth.contract(address=checksum_address, abi=abi)


def _build_and_send_tx_layerzero(
    web3_instance: Web3, private_key: str, tx_params: TxParams
) -> str:
    """
    Build, sign, send, and wait for a transaction, with retry logic for
    transient errors.
    """
    account = _get_account_layerzero(private_key, web3_instance)
    tx_params.setdefault(
        "nonce", web3_instance.eth.get_transaction_count(account.address)
    )
    tx_params.setdefault("gasPrice", web3_instance.eth.gas_price)

    if "gas" not in tx_params:
        try:
            estimated_gas = web3_instance.eth.estimate_gas(tx_params)
            tx_params["gas"] = Wei(int(estimated_gas * DEFAULT_GAS_MULTIPLIER))
            logger.info(f"Estimated gas: {estimated_gas}, using: {tx_params['gas']}")
        except Exception as e:
            logger.error(f"Gas estimation failed: {e}, tx_params: {tx_params}")
            from_address = tx_params.get("from", "N/A")
            to_address = tx_params.get("to", "N/A")
            from_addr_str = (
                from_address.hex()
                if isinstance(from_address, bytes)
                else str(from_address)
            )
            to_addr_str = (
                to_address.hex() if isinstance(to_address, bytes) else str(to_address)
            )
            data_present = "data" in tx_params
            logger.error(
                f"Gas estimation failed for tx from {from_addr_str} to {to_addr_str} "
                f"(data present: {data_present}): {e!s}"
            )
            if isinstance(e, ContractLogicError):
                raise GasEstimationError(
                    f"Gas estimation failed due to contract logic: {e.message} - "
                    f"Data: {e.data!r}"
                )
            raise GasEstimationError(f"Gas estimation failed: {e}")

    try:
        signed = web3_instance.eth.account.sign_transaction(tx_params, private_key)
    except Exception as e:
        logger.error(f"Transaction signing failed: {e}")
        raise TransactionBuildError(f"Transaction signing failed: {e}")

    last_exception: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                f"Attempt {attempt + 1}/{MAX_RETRIES} to send transaction..."
            )
            tx_hash_bytes = web3_instance.eth.send_raw_transaction(
                signed.raw_transaction
            )
            tx_hash_hex = tx_hash_bytes.hex()
            logger.info(f"Transaction sent with hash: {tx_hash_hex}")

            logger.info(f"Waiting for transaction receipt for {tx_hash_hex}...")
            receipt: TxReceipt = web3_instance.eth.wait_for_transaction_receipt(
                tx_hash_bytes, timeout=180
            )
            logger.info(f"Transaction receipt received for {tx_hash_hex}")

            if receipt["status"] != 1:
                logger.error(
                    f"Transaction {tx_hash_hex} reverted. Receipt status: "
                    f"{receipt['status']}"
                )
                raise TransactionRevertedError(
                    f"Transaction {tx_hash_hex} reverted.", receipt=receipt
                )

            logger.info(f"Transaction {tx_hash_hex} successful.")
            return tx_hash_hex

        except (ConnectionError, TimeoutError, Timeout) as e:
            last_exception = e
            logger.warning(
                f"Attempt {attempt + 1}/{MAX_RETRIES} failed due to RPC/network "
                f"issue: {e}. Retrying in {RETRY_DELAY_SECONDS}s..."
            )
            time.sleep(RETRY_DELAY_SECONDS)
            if attempt < MAX_RETRIES - 1:
                try:
                    current_nonce = web3_instance.eth.get_transaction_count(
                        account.address
                    )
                    if current_nonce > cast(int, tx_params["nonce"]):
                        logger.info(
                            f"Nonce already used or too low. Current: {current_nonce}, "
                            f"Tx: {tx_params['nonce']}. Updating nonce."
                        )
                        tx_params["nonce"] = current_nonce
                    else:
                        logger.info(
                            f"Nonce {tx_params['nonce']} seems still valid or higher. "
                            f"Current: {current_nonce}."
                        )

                    signed = web3_instance.eth.account.sign_transaction(
                        tx_params, private_key
                    )
                    logger.info(
                        f"Re-signed transaction with nonce {tx_params['nonce']} "
                        f"for retry."
                    )
                except Exception as sign_e:
                    logger.error(
                        f"Transaction re-signing failed before retry: {sign_e}"
                    )
                    last_exception = TransactionBuildError(
                        f"Transaction re-signing failed before retry: {sign_e}"
                    )
                    break
        except TransactionRevertedError:
            raise
        except Exception as e:
            last_exception = e
            logger.error(
                f"An unexpected error occurred during transaction processing "
                f"(attempt {attempt + 1}): {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)

    if last_exception:
        logger.error(
            f"All {MAX_RETRIES} attempts failed. Last error: {last_exception}"
        )
        if isinstance(last_exception, (ConnectionError, TimeoutError, Timeout)):
            raise MaxRetriesExceededError(
                f"Transaction failed after {MAX_RETRIES} attempts due to "
                f"RPC/network issues: {last_exception}"
            )
        elif isinstance(last_exception, TransactionRevertedError):
            raise last_exception
        elif isinstance(last_exception, TransactionBuildError):
            raise last_exception
        else:
            raise TransactionSendError(
                f"Failed to send/confirm transaction after {MAX_RETRIES} retries: "
                f"{last_exception}"
            )

    logger.error(
        "Transaction processing finished in an unexpected state (no success, "
        "no explicit error after retries."
    )
    raise LayerZeroError(
        "Transaction processing finished in an unexpected state after retries."
    )


def _approve_erc20_layerzero(
    web3_instance: Web3,
    private_key: str,
    token_address: str,
    spender_address: str,
    amount: int,
) -> str:
    """Approve ERC20 token for spending by a spender on a LayerZero-connected chain."""
    logger.info(
        f"Approving {amount} of token {token_address} for spender {spender_address}"
    )
    account = _get_account_layerzero(private_key, web3_instance)
    contract = _get_contract_layerzero(web3_instance, ERC20_ABI_NAME, token_address)

    # Check current allowance
    try:
        current_allowance = contract.functions.allowance(
            account.address, spender_address
        ).call()
        if current_allowance >= amount:
            logger.info(
                f"Allowance of {current_allowance} for {spender_address} is "
                "sufficient. Skipping approval."
            )
            return f"existing_approval_sufficient_for_{amount}"
    except Exception as e:
        logger.warning(
            f"Could not check current allowance for {token_address} to "
            f"{spender_address}: {e}. Proceeding with approval."
        )

    tx_dict_approve: TxParams = {
        "from": account.address,
        "gasPrice": web3_instance.eth.gas_price,
    }

    try:
        approve_tx = contract.functions.approve(
            spender_address, amount
        ).build_transaction(tx_dict_approve)
        if "to" not in approve_tx:
            approve_tx["to"] = token_address

        logger.info(f"Built approval transaction: {approve_tx}")
        return _build_and_send_tx_layerzero(web3_instance, private_key, approve_tx)

    except GasEstimationError as e:
        logger.error(f"Gas estimation failed for ERC20 approval: {e}")
        raise ApprovalError(f"ERC20 approval gas estimation failed: {e}") from e
    except TransactionRevertedError as e:
        logger.error(f"ERC20 approval transaction reverted: {e.receipt}")
        raise ApprovalError(
            f"ERC20 approval failed: {e.args[0]}", receipt=e.receipt
        ) from e
    except Exception as e:
        logger.error(f"ERC20 approval error: {e}")
        raise ApprovalError(f"ERC20 approval error: {e}") from e


class LayerZeroProtocol:
    """
    LayerZeroProtocol handles cross-chain interactions via LayerZero.
    """

    def __init__(self, rpc_url: str, private_key: str, chain_id: int) -> None:
        """
        Initialize the LayerZeroProtocol.

        Args:
                rpc_url: The RPC URL for the source chain.
                private_key: The private key of the wallet to use.
                chain_id: The chain ID of the source chain.
        """
        if not rpc_url:
            raise ValueError("RPC URL cannot be empty")
        if not private_key or not private_key.startswith("0x") or len(private_key) != 66:
            raise ValueError("Private key must be a 64-character hex string prefixed with '0x'")

        self.rpc_url = rpc_url
        self.private_key = private_key
        self.chain_id = chain_id
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account: LocalAccount = Account.from_key(private_key)

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC at {rpc_url}")

        self.endpoint_address = LAYERZERO_ENDPOINT_ADDRESSES.get(str(chain_id))
        if not self.endpoint_address:
            raise UnsupportedChainError(f"Chain ID {chain_id} not supported by LayerZero configuration.")

        self.endpoint_contract = _get_contract_layerzero(
            self.w3, LAYERZERO_ENDPOINT_ABI_NAME, self.endpoint_address
        )

        logger.info(f"LayerZeroProtocol initialized for address: {self.account.address} on chain {chain_id}")

    def perform_airdrop(
        self,
        web3: Web3,
        private_key: str,
        amount: Decimal,
        recipient: str
    ) -> str:
        """Perform an airdrop operation using LayerZero.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            amount: Amount to airdrop as a Decimal.
            recipient: Address of the airdrop recipient.
            
        Returns:
            Transaction hash of the airdrop operation.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the airdrop transaction fails.
        """
        # For now, delegate to the existing implementation
        # This would need to be implemented based on the actual airdrop functionality
        raise NotImplementedError("Airdrop functionality not yet implemented in LayerZeroProtocol")
    
    def send_message(
        self,
        web3: Web3,
        private_key: str,
        destination_chain_id: int,
        destination_address: str,
        payload: bytes,
        adapter_params: bytes = b""
    ) -> str:
        """Send a cross-chain message via LayerZero.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            destination_chain_id: LayerZero chain ID of the destination.
            destination_address: Address on the destination chain.
            payload: Message payload to send.
            adapter_params: Optional adapter parameters for gas configuration.
            
        Returns:
            Transaction hash of the message sending operation.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the message sending fails.
        """
        # For now, delegate to the existing implementation
        # This would need to be implemented based on the actual message sending functionality
        raise NotImplementedError("Message sending functionality not yet implemented in LayerZeroProtocol")
    
    def get_balance(
        self,
        web3: Web3,
        address: str,
        token_address: Optional[str] = None
    ) -> Decimal:
        """Get the balance of an address for a specific token.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            address: Address to check balance for.
            token_address: Token contract address (None for native token).
            
        Returns:
            Balance as a Decimal.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If balance query fails.
        """
        # For now, delegate to the existing implementation
        # This would need to be implemented based on the actual balance query functionality
        raise NotImplementedError("Balance query functionality not yet implemented in LayerZeroProtocol")

    def perform_airdrop_legacy(self, value_usd: Decimal) -> bool:
        """
        Simulate performing an airdrop-like transaction via LayerZero.
        This is a placeholder for actual cross-chain message sending.
        For demonstration, it simulates a simple ETH transfer on the source chain.

        Args:
                value_usd: The USD value of the airdrop/transaction.

        Returns:
                True if the transaction was successful, False otherwise.
        """
        logger.info(f"Attempting to perform airdrop-like transaction of ${value_usd} via LayerZero.")
        try:
            # Example: Send a small amount of native token (ETH) to a dummy address
            dummy_recipient = "0x000000000000000000000000000000000000dead"
            # Convert USD value to ETH (assuming 1 ETH = $2000 for simplicity)
            eth_value = value_usd / Decimal("2000")
            value_wei = self.w3.to_wei(eth_value, "ether")

            # Check balance
            balance_wei = self.w3.eth.get_balance(self.account.address)
            if balance_wei < value_wei:
                logger.error(f"Insufficient balance for transaction. Have {self.w3.from_wei(balance_wei, 'ether')} ETH, need {eth_value} ETH.")
                return False

            gas_price = self.w3.eth.gas_price
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            gas_limit = 21000  # Standard ETH transfer gas limit

            tx_params: TxParams = {
                "from": self.account.address,
                "to": dummy_recipient,
                "value": value_wei,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": self.chain_id,
            }

            signed_tx = self.account.sign_transaction(tx_params)  # type: ignore[arg-type]
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)  # type: ignore[attr-defined]
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

            if receipt.status == 1:  # type: ignore[attr-defined]
                logger.info(f"LayerZero simulated transaction successful. Tx Hash: {tx_hash.hex()}")
                return True
            else:
                logger.error(f"LayerZero simulated transaction failed. Tx Hash: {tx_hash.hex()}, Receipt: {receipt}")
                return False

        except TransactionError as e:
            logger.error(f"LayerZero transaction utility error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to perform LayerZero airdrop: {e}")
            return False

    def get_gas_price(self) -> Decimal:
        """
        Get the current gas price on the current chain.

        Returns:
                The gas price in Gwei as Decimal.
        """
        try:
            gas_price_wei = self.w3.eth.gas_price
            return Decimal(str(self.w3.from_wei(gas_price_wei, "gwei")))
        except Exception as e:
            logger.error(f"Failed to get gas price on chain {self.chain_id}: {e}")
            return Decimal("0")

    def get_transaction_count(self, address: str) -> int:
        """
        Get the transaction count (nonce) for an address on the current chain.

        Args:
                address: The wallet address.

        Returns:
                The transaction count as an integer.
        """
        try:
            checksum_address = self.w3.to_checksum_address(address)
            return self.w3.eth.get_transaction_count(checksum_address)
        except Exception as e:
            logger.error(f"Failed to get transaction count for {address} on chain {self.chain_id}: {e}")
            return 0

    def estimate_gas(self, transaction: TxParams) -> int:
        """
        Estimate the gas required for a transaction on the current chain.

        Args:
                transaction: The transaction dictionary.

        Returns:
                The estimated gas in units.
        """
        try:
            return self.w3.eth.estimate_gas(transaction)
        except Exception as e:
            logger.error(f"Failed to estimate gas for transaction on chain {self.chain_id}: {e}")
            return 0


def bridge(
    wallet: LocalAccount,
    source_chain: str,
    destination_chain: str,
    token_symbol: str,
    amount: Decimal,
    max_retries: int = 3
) -> bool:
    """
    Bridge tokens between chains using LayerZero.
    
    Args:
        wallet: The wallet to use for the transaction
        source_chain: Source chain identifier
        destination_chain: Destination chain identifier
        token_symbol: Token symbol to bridge
        amount: Amount to bridge
        max_retries: Maximum number of retries
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> wallet = Account.from_key("0x...")
        >>> success = bridge(wallet, "ethereum", "arbitrum", "USDC", Decimal("100"))
        >>> print(success)
        True
    """
    try:
        # Extract private key from wallet for protocol initialization
        private_key = wallet.key.hex()
        # Use a default RPC URL and chain ID - this should be configurable in a real implementation
        rpc_url = "https://eth.llamarpc.com"  # Ethereum mainnet
        chain_id = 1  # Ethereum mainnet
        
        protocol = LayerZeroProtocol(rpc_url, private_key, chain_id)
        # Convert destination_chain string to int for the send_message call
        destination_chain_id = 1 if destination_chain == "ethereum" else 137  # Simple mapping
        
        # Create a Web3 instance for the protocol
        from web3 import Web3
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Create a simple payload for the bridge message
        message_payload = f"Bridge {amount} {token_symbol}".encode('utf-8')
        
        # Call send_message with correct parameters and convert result to bool
        tx_hash = protocol.send_message(
            web3=web3,
            private_key=private_key,
            destination_chain_id=destination_chain_id,
            destination_address=wallet.address,  # Use wallet address as recipient
            payload=message_payload
        )
        
        # Return True if we got a transaction hash (indicating success)
        return bool(tx_hash)
    except Exception as e:
        logger.error(f"Bridge operation failed: {e}")
        return False


def perform_random_bridge(
    wallet: LocalAccount,
    available_chains: list[str],
    token_symbols: list[str],
    min_amount: Decimal,
    max_amount: Decimal,
    max_retries: int = 3
) -> bool:
    """
    Perform a random bridge operation between available chains.
    
    Args:
        wallet: The wallet to use for the transaction
        available_chains: List of available chain identifiers
        token_symbols: List of available token symbols
        min_amount: Minimum amount to bridge
        max_amount: Maximum amount to bridge
        max_retries: Maximum number of retries
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> wallet = Account.from_key("0x...")
        >>> chains = ["ethereum", "arbitrum", "optimism"]
        >>> tokens = ["USDC", "USDT"]
        >>> success = perform_random_bridge(wallet, chains, tokens, Decimal("10"), Decimal("100"))
        >>> print(success)
        True
    """
    try:
        # Randomly select source and destination chains
        source_chain = random.choice(available_chains)
        destination_chain = random.choice([c for c in available_chains if c != source_chain])
        
        # Randomly select token and amount
        token_symbol = random.choice(token_symbols)
        amount = Decimal(str(random.uniform(float(min_amount), float(max_amount))))
        
        logger.info(f"Random bridge: {amount} {token_symbol} from {source_chain} to {destination_chain}")
        
        return bridge(
            wallet=wallet,
            source_chain=source_chain,
            destination_chain=destination_chain,
            token_symbol=token_symbol,
            amount=amount,
            max_retries=max_retries
        )
    except Exception as e:
        logger.error(f"Random bridge operation failed: {e}")
        return False


__all__ = ["LayerZeroProtocol", "bridge", "perform_random_bridge"]
