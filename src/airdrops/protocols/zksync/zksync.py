"""
ZkSync Protocol Module.

This module provides functionalities to interact with the ZkSync Era network,
including bridging ETH and ERC20 tokens between Ethereum (L1) and ZkSync (L2),
and swapping tokens on SyncSwap DEX (L2).
"""

import json
import logging
import time
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional, Any, cast, Sequence, List
from requests.exceptions import ConnectionError, Timeout

from eth_abi.abi import encode as abi_encode
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.types import TxParams, Wei, TxReceipt

from airdrops.shared.constants import (
    ZKSYNC_L1_BRIDGE_ADDRESS,
    ZKSYNC_L2_BRIDGE_ADDRESS,
    SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC,
    SYNC_SWAP_CLASSIC_POOL_FACTORY_ADDRESS_ZKSYNC,
    ZKSYNC_TOKEN_ADDRESSES
)

from airdrops.shared import constants
from ...shared.random_activity_utils import select_activity_by_weight, generate_random_amount, select_random_tokens
from .exceptions import (
    ZkSyncBridgeError,
    InsufficientBalanceError,
    TransactionRevertedError,
    ApprovalError,
    GasEstimationError,
    MaxRetriesExceededError,
    TransactionBuildError,
    TransactionSendError,
    ZkSyncSwapError,
    InsufficientLiquidityError,
    TokenNotSupportedError,
    ZkSyncRandomActivityError,
    ZkSyncLendingError,
)


# Configure logging for this module
logger = logging.getLogger(__name__)

# Contract addresses are imported from constants module above

# ABI Names
L1_BRIDGE_ABI_NAME = "L1Bridge"
L2_BRIDGE_ABI_NAME = "L2Bridge"
ERC20_ABI_NAME = "ERC20"
SYNC_SWAP_ROUTER_ABI_NAME = "SyncSwapRouter"
SYNC_SWAP_CLASSIC_POOL_FACTORY_ABI_NAME = "SyncSwapClassicPoolFactory"
SYNC_SWAP_CLASSIC_POOL_ABI_NAME = "SyncSwapClassicPool"

# Default gas limits and constants
DEFAULT_L2_GAS_LIMIT = 200000  # For bridging
DEFAULT_SWAP_L2_GAS_LIMIT = 600000
DEFAULT_GAS_MULTIPLIER = 1.2
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ETH_SYMBOL = "ETH"
WETH_SYMBOL = "WETH"


def _load_abi_zksync(contract_name: str) -> Sequence[Dict[str, Any]]:
    """
    Load ABI JSON from the abi directory.

    Args:
    contract_name: Name of the contract (e.g., 'L1Bridge')

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


def _get_account_zksync(private_key: str, web3_instance: Web3) -> LocalAccount:
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


def _get_l1_token_address_zksync(token_symbol: str) -> str:
    """
    Get L1 address for a token symbol from shared config.

    Args:
    token_symbol: Token symbol (e.g., "USDC").

    Returns:
    L1 token address as a string.

    Raises:
    TokenNotSupportedError: If token symbol is not configured or L1 address
            is missing.
    """
    if token_symbol not in ZKSYNC_TOKEN_ADDRESSES:
        logger.error(f"Token symbol '{token_symbol}' not found in configuration.")
        raise TokenNotSupportedError(f"Token symbol '{token_symbol}' not supported.")
    token_config_entry = ZKSYNC_TOKEN_ADDRESSES[token_symbol]
    token_info: Dict[str, Any] = cast(Dict[str, Any], token_config_entry)
    l1_address = token_info.get("L1")
    if l1_address is None:
        logger.error(f"L1 address for token '{token_symbol}' is not configured.")
        raise TokenNotSupportedError(
            f"L1 address for token '{token_symbol}' not configured."
        )
    return cast(str, l1_address)


def _get_l2_token_address_zksync(token_symbol: str) -> str:
    """
    Get L2 address for a token symbol from shared config.

    Args:
    token_symbol: Token symbol (e.g., "ETH", "WETH", "USDC").

    Returns:
    L2 token address as a string.

    Raises:
    TokenNotSupportedError: If token symbol is not configured or L2 address
            is missing.
    """
    if token_symbol not in constants.ZKSYNC_TOKEN_ADDRESSES:
        logger.error(f"Token symbol '{token_symbol}' not found in configuration.")
        raise TokenNotSupportedError(f"Token symbol '{token_symbol}' not supported.")
    token_config_entry = constants.ZKSYNC_TOKEN_ADDRESSES[token_symbol]
    # Cast to Dict to help mypy understand .get() and indexing
    token_info: Dict[str, Any] = cast(Dict[str, Any], token_config_entry)
    l2_address = token_info.get("L2")
    if (
        l2_address is None and token_symbol != ETH_SYMBOL
    ):  # ETH L2 is None, handled by WETH
        logger.error(f"L2 address for token '{token_symbol}' is not configured.")
        raise TokenNotSupportedError(
            f"L2 address for token '{token_symbol}' not configured."
        )
    # For ETH, we typically use WETH address in contracts
    if token_symbol == ETH_SYMBOL:
        weth_config_entry = constants.ZKSYNC_TOKEN_ADDRESSES.get(WETH_SYMBOL)
        if not weth_config_entry:
            raise TokenNotSupportedError(
                "WETH symbol not found in ZKSYNC_TOKEN_ADDRESSES."
            )
        weth_info: Dict[str, Any] = cast(Dict[str, Any], weth_config_entry)
        weth_l2 = weth_info.get("L2")
        if not weth_l2:
            raise TokenNotSupportedError(
                "WETH L2 address not configured, required for ETH operations."
            )
        return cast(str, weth_l2)
    return cast(str, l2_address)


def _get_contract_zksync(
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
    abi = _load_abi_zksync(contract_name)
    checksum_address = Web3.to_checksum_address(contract_address)
    return web3_instance.eth.contract(address=checksum_address, abi=abi)


def _build_and_send_tx_zksync(
    web3_instance: Web3, private_key: str, tx_params: TxParams
) -> str:
    """
    Build, sign, send, and wait for a transaction, with retry logic for
    transient errors.
    """
    account = _get_account_zksync(private_key, web3_instance)
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
    raise ZkSyncBridgeError(
        "Transaction processing finished in an unexpected state after retries."
    )


class ZkSyncProtocol:
    """
    ZkSyncProtocol handles interactions with the ZkSync Era network.
    
    This class provides a high-level interface for bridging assets and swapping tokens
    on the ZkSync Era network, encapsulating the functionality provided by the module-level
    functions in a convenient class-based API.
    """

    def __init__(
        self,
        l1_rpc_url: str,
        l2_rpc_url: str,
        private_key: str,
        web3_l1: Optional[Web3] = None,
        web3_l2: Optional[Web3] = None
    ) -> None:
        """
        Initialize the ZkSyncProtocol.

        Args:
            l1_rpc_url: The RPC URL for the Ethereum L1 network.
            l2_rpc_url: The RPC URL for the ZkSync L2 network.
            private_key: The private key of the wallet to use.
            web3_l1: Optional pre-configured Web3 instance for L1. If None, creates new instance.
            web3_l2: Optional pre-configured Web3 instance for L2. If None, creates new instance.
            
        Example:
            >>> protocol = ZkSyncProtocol(
            ...     "https://eth-mainnet.alchemyapi.io/v2/...",
            ...     "https://mainnet.era.zksync.io",
            ...     "0x123..."
            ... )
        """
        if not l1_rpc_url:
            raise ValueError("L1 RPC URL cannot be empty")
        if not l2_rpc_url:
            raise ValueError("L2 RPC URL cannot be empty")
        if not private_key or not private_key.startswith("0x") or len(private_key) != 66:
            raise ValueError("Private key must be a 64-character hex string prefixed with '0x'")

        self.l1_rpc_url = l1_rpc_url
        self.l2_rpc_url = l2_rpc_url
        self.private_key = private_key
        self.web3_l1 = web3_l1 if web3_l1 else Web3(Web3.HTTPProvider(l1_rpc_url))
        self.web3_l2 = web3_l2 if web3_l2 else Web3(Web3.HTTPProvider(l2_rpc_url))
        
        # Initialize lending adapters
        from .lending_adapter import ZerolendAdapter
        self.lending_adapters = {
            "zerolend": ZerolendAdapter(self.web3_l2),
        }

    def bridge_assets(
        self,
        web3_l1: Web3,
        web3_l2: Web3,
        private_key: str,
        token_symbol: str,
        amount: Decimal,
        direction: str
    ) -> str:
        """Bridge assets between Ethereum L1 and ZkSync L2.
        
        Args:
            web3_l1: Web3 instance for Ethereum L1.
            web3_l2: Web3 instance for ZkSync L2.
            private_key: Private key for signing transactions.
            token_symbol: Symbol of the token to bridge (e.g., "ETH", "USDC").
            amount: Amount to bridge as a Decimal.
            direction: Bridge direction ("deposit" for L1->L2, "withdraw" for L2->L1).
            
        Returns:
            Transaction hash of the bridge operation.
            
        Raises:
            ValueError: If parameters are invalid or unsupported.
            RuntimeError: If the bridge transaction fails.
        """
        # Convert Decimal to int (wei for ETH)
        if token_symbol.upper() == "ETH":
            amount_wei = int(web3_l1.to_wei(amount, "ether"))
        else:
            # For other tokens, assume 18 decimals
            amount_wei = int(amount * (10 ** 18))
            
        return bridge_assets(
            web3_l1,
            web3_l2,
            private_key,
            token_symbol,
            amount_wei,
            direction
        )
    
    def swap_tokens(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        slippage_percent: float = 0.5,
        deadline_seconds: int = 1800,
        dex: str = "auto"
    ) -> str:
        """Swap tokens on ZkSync network using the DEX aggregator.
        
        Note: This method delegates to the module-level swap_tokens function which
        provides full DEX aggregation functionality including SyncSwap support.
        
        Args:
            token_in: Symbol of input token (e.g., "ETH", "USDC").
            token_out: Symbol of output token (e.g., "USDC", "WETH").
            amount_in: Amount of input token to swap.
            slippage_percent: Maximum allowed slippage percentage.
            deadline_seconds: Transaction deadline in seconds from now.
            dex: DEX to use ("auto", "syncswap", "mute", "spacefi").
            
        Returns:
            Transaction hash of the swap operation.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the swap transaction fails.
            
        Example:
            >>> protocol = ZkSyncProtocol("https://...", "https://...", "0x...")
            >>> tx_hash = protocol.swap_tokens(
            ...     token_in="ETH",
            ...     token_out="USDC",
            ...     amount_in=Decimal("1.0"),
            ...     dex="auto"
            ... )
        """
        # Convert Decimal to int (wei for ETH, smallest unit for others)
        if token_in.upper() == "ETH":
            amount_wei = int(self.web3_l2.to_wei(amount_in, "ether"))
        else:
            # For other tokens, assume appropriate decimals based on token
            # This is a simplification - in production, you'd want to query token decimals
            amount_wei = int(amount_in * (10 ** 18))  # Assume 18 decimals
            
        return swap_tokens(
            web3_zksync=self.web3_l2,
            private_key=self.private_key,
            token_in_symbol=token_in,
            token_out_symbol=token_out,
            amount_in=amount_wei,
            slippage_percent=slippage_percent,
            deadline_seconds=deadline_seconds,
            dex=dex
        )

    def lend(self, token: str, amount: Decimal, protocol: str = "zerolend") -> str:
        """Lend tokens to a specified lending protocol on zkSync.
        
        Args:
            token: Symbol of token to lend (e.g., "ETH", "USDC").
            amount: Amount of token to lend.
            protocol: Lending protocol to use (default: "zerolend").
            
        Returns:
            Transaction hash of the lending operation.
            
        Raises:
            ValueError: If parameters are invalid.
            ZkSyncLendingError: If the lending transaction fails.
            
        Example:
            >>> protocol = ZkSyncProtocol("https://...", "https://...", "0x...")
            >>> tx_hash = protocol.lend(
            ...     token="ETH",
            ...     amount=Decimal("1.0"),
            ...     protocol="zerolend"
            ... )
        """
        return lend_borrow(
            web3_zksync=self.web3_l2,
            private_key=self.private_key,
            action="lend",
            token_symbol=token,
            amount=amount,
            protocol=protocol
        )

    def withdraw(self, token: str, amount: Decimal, protocol: str = "zerolend") -> str:
        """Withdraw tokens from a specified lending protocol on zkSync.
        
        Args:
            token: Symbol of token to withdraw (e.g., "ETH", "USDC").
            amount: Amount of token to withdraw.
            protocol: Lending protocol to withdraw from (default: "zerolend").
            
        Returns:
            Transaction hash of the withdrawal operation.
            
        Raises:
            ValueError: If parameters are invalid.
            ZkSyncLendingError: If the withdrawal transaction fails.
        """
        return lend_borrow(
            web3_zksync=self.web3_l2,
            private_key=self.private_key,
            action="withdraw",
            token_symbol=token,
            amount=amount,
            protocol=protocol
        )

    def borrow(self, token: str, amount: Decimal, protocol: str = "zerolend") -> str:
        """Borrow tokens from a specified lending protocol on zkSync.
        
        Args:
            token: Symbol of token to borrow (e.g., "ETH", "USDC").
            amount: Amount of token to borrow.
            protocol: Lending protocol to borrow from (default: "zerolend").
            
        Returns:
            Transaction hash of the borrowing operation.
            
        Raises:
            ValueError: If parameters are invalid.
            ZkSyncLendingError: If the borrowing transaction fails.
        """
        return lend_borrow(
            web3_zksync=self.web3_l2,
            private_key=self.private_key,
            action="borrow",
            token_symbol=token,
            amount=amount,
            protocol=protocol
        )

    def repay(self, token: str, amount: Decimal, protocol: str = "zerolend") -> str:
        """Repay borrowed tokens to a specified lending protocol on zkSync.
        
        Args:
            token: Symbol of token to repay (e.g., "ETH", "USDC").
            amount: Amount of token to repay.
            protocol: Lending protocol to repay to (default: "zerolend").
            
        Returns:
            Transaction hash of the repayment operation.
            
        Raises:
            ValueError: If parameters are invalid.
            ZkSyncLendingError: If the repayment transaction fails.
        """
        return lend_borrow(
            web3_zksync=self.web3_l2,
            private_key=self.private_key,
            action="repay",
            token_symbol=token,
            amount=amount,
            protocol=protocol
        )

    def provide_liquidity(
        self,
        token_a: str,
        token_b: str,
        amount_a: Decimal,
        amount_b: Decimal,
        dex: str = "syncswap",
        slippage_percent: float = 0.5,
        deadline_seconds: int = 1800
    ) -> str:
        """Provide liquidity to a specified DEX on zkSync.
        
        Args:
            token_a: Symbol of first token (e.g., "ETH", "USDC").
            token_b: Symbol of second token (e.g., "USDC", "WETH").
            amount_a: Amount of first token to provide.
            amount_b: Amount of second token to provide.
            dex: DEX to use (default: "syncswap").
            slippage_percent: Maximum allowed slippage percentage.
            deadline_seconds: Transaction deadline in seconds from now.
            
        Returns:
            Transaction hash of the liquidity provision operation.
            
        Raises:
            ValueError: If parameters are invalid.
            ZkSyncSwapError: If the liquidity transaction fails.
            
        Example:
            >>> protocol = ZkSyncProtocol("https://...", "https://...", "0x...")
            >>> tx_hash = protocol.provide_liquidity(
            ...     token_a="ETH",
            ...     token_b="USDC",
            ...     amount_a=Decimal("1.0"),
            ...     amount_b=Decimal("2000.0"),
            ...     dex="syncswap"
            ... )
        """
        # Convert Decimal to int (wei for ETH, smallest unit for others)
        if token_a.upper() == "ETH":
            amount_a_wei = int(self.web3_l2.to_wei(amount_a, "ether"))
        else:
            # For other tokens, assume appropriate decimals based on token
            amount_a_wei = int(amount_a * (10 ** 18))  # Assume 18 decimals
            
        if token_b.upper() == "ETH":
            amount_b_wei = int(self.web3_l2.to_wei(amount_b, "ether"))
        else:
            # For other tokens, assume appropriate decimals based on token
            amount_b_wei = int(amount_b * (10 ** 18))  # Assume 18 decimals
            
        return provide_liquidity(
            web3_zksync=self.web3_l2,
            private_key=self.private_key,
            token_a_symbol=token_a,
            token_b_symbol=token_b,
            amount_a=amount_a_wei,
            amount_b=amount_b_wei,
            dex=dex,
            slippage_percent=slippage_percent,
            deadline_seconds=deadline_seconds
        )

    def remove_liquidity(
        self,
        token_a: str,
        token_b: str,
        liquidity_percent: float,
        dex: str = "syncswap",
        slippage_percent: float = 0.5,
        deadline_seconds: int = 1800
    ) -> str:
        """Remove liquidity from a specified DEX on zkSync.
        
        Args:
            token_a: Symbol of first token (e.g., "ETH", "USDC").
            token_b: Symbol of second token (e.g., "USDC", "WETH").
            liquidity_percent: Percentage of liquidity to remove (0-100).
            dex: DEX to remove from (default: "syncswap").
            slippage_percent: Maximum allowed slippage percentage.
            deadline_seconds: Transaction deadline in seconds from now.
            
        Returns:
            Transaction hash of the liquidity removal operation.
            
        Raises:
            ValueError: If parameters are invalid.
            ZkSyncSwapError: If the liquidity transaction fails.
            
        Example:
            >>> protocol = ZkSyncProtocol("https://...", "https://...", "0x...")
            >>> tx_hash = protocol.remove_liquidity(
            ...     token_a="ETH",
            ...     token_b="USDC",
            ...     liquidity_percent=50.0,
            ...     dex="syncswap"
            ... )
        """
        return remove_liquidity(
            web3_zksync=self.web3_l2,
            private_key=self.private_key,
            token_a_symbol=token_a,
            token_b_symbol=token_b,
            liquidity_percent=liquidity_percent,
            dex=dex,
            slippage_percent=slippage_percent,
            deadline_seconds=deadline_seconds
        )


def _approve_erc20_zksync(
    web3_instance: Web3,
    private_key: str,
    token_address: str,
    spender_address: str,
    amount: int,
) -> str:
    """Approve ERC20 token for spending by a spender on ZkSync L2."""
    logger.info(
        f"Approving {amount} of token {token_address} for spender {spender_address}"
    )
    account = _get_account_zksync(private_key, web3_instance)
    contract = _get_contract_zksync(web3_instance, ERC20_ABI_NAME, token_address)

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
        return _build_and_send_tx_zksync(web3_instance, private_key, approve_tx)

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


def _get_syncswap_classic_pool_factory_contract_zksync(web3_zksync: Web3) -> Contract:
    """Get the SyncSwap Classic Pool Factory contract instance."""
    return _get_contract_zksync(
        web3_zksync,
        SYNC_SWAP_CLASSIC_POOL_FACTORY_ABI_NAME,
        SYNC_SWAP_CLASSIC_POOL_FACTORY_ADDRESS_ZKSYNC,
    )


def _get_syncswap_pool_address_zksync(
    web3_zksync: Web3, token0_address: str, token1_address: str
) -> Optional[str]:
    """Get pool address for a token pair using SyncSwap Classic Pool Factory."""
    factory = _get_syncswap_classic_pool_factory_contract_zksync(web3_zksync)
    try:
        token0_checksum = Web3.to_checksum_address(token0_address)
        token1_checksum = Web3.to_checksum_address(token1_address)

        pool_address_any = factory.functions.getPool(
            token0_checksum, token1_checksum
        ).call()
        pool_address = cast(str, pool_address_any)
        if pool_address == ZERO_ADDRESS:
            pool_address_reversed_any = factory.functions.getPool(
                token1_checksum, token0_checksum
            ).call()
            pool_address_reversed = cast(str, pool_address_reversed_any)
            if pool_address_reversed != ZERO_ADDRESS:
                return pool_address_reversed
            logger.info(
                f"No SyncSwap Classic pool found for {token0_checksum} and "
                f"{token1_checksum}"
            )
            return None
        return pool_address
    except Exception as e:
        logger.warning(
            f"Error getting pool for {token0_address}-{token1_address}: {e}"
        )
        return None
        return None


def _get_syncswap_classic_pool_contract_zksync(
    web3_zksync: Web3, pool_address: str
) -> Contract:
    """Get a SyncSwap Classic Pool contract instance given its address."""
    return _get_contract_zksync(
        web3_zksync, SYNC_SWAP_CLASSIC_POOL_ABI_NAME, pool_address
    )


def _get_syncswap_router_contract_zksync(web3_zksync: Web3) -> Contract:
    """Get the SyncSwap Router contract instance."""
    return _get_contract_zksync(
        web3_zksync, SYNC_SWAP_ROUTER_ABI_NAME, SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC
    )


def _get_expected_amount_out_syncswap_zksync(
    web3_zksync: Web3,
    token_in_address: str,
    token_out_address: str,
    amount_in: int,
    sender_address: str,
    weth_address: str,
) -> int:
    """
    Get the expected output amount for a swap.
    Tries direct pool, then via WETH if applicable.
    """
    logger.info(
        f"Getting expected amount out for {amount_in} of {token_in_address} to "
        f"{token_out_address}"
    )

    direct_pool_address = _get_syncswap_pool_address_zksync(
        web3_zksync, token_in_address, token_out_address
    )
    if direct_pool_address:
        try:
            pool_contract = _get_syncswap_classic_pool_contract_zksync(
                web3_zksync, direct_pool_address
            )
            expected_out = pool_contract.functions.getAmountOut(
                Web3.to_checksum_address(token_in_address),
                amount_in,
                Web3.to_checksum_address(sender_address),
            ).call()
            logger.info(
                f"Direct pool {direct_pool_address} quote: {expected_out} of "
                f"{token_out_address}"
            )
            return cast(int, expected_out)
        except Exception as e:
            logger.warning(
                f"Failed to get quote from direct pool {direct_pool_address}: {e}"
            )

    if (
        token_in_address != weth_address
        and token_out_address != weth_address
    ):
        logger.info(f"No direct pool, trying via WETH ({weth_address})")
        pool1_address = _get_syncswap_pool_address_zksync(
            web3_zksync, token_in_address, weth_address
        )
        pool2_address = _get_syncswap_pool_address_zksync(
            web3_zksync, weth_address, token_out_address
        )

        if pool1_address and pool2_address:
            try:
                pool1_contract = _get_syncswap_classic_pool_contract_zksync(
                    web3_zksync, pool1_address
                )
                amount_weth_out = pool1_contract.functions.getAmountOut(
                    Web3.to_checksum_address(token_in_address),
                    amount_in,
                    Web3.to_checksum_address(sender_address),
                ).call()
                logger.info(
                    f"Pool1 ({token_in_address}->WETH) quote: {amount_weth_out} WETH"
                )

                if amount_weth_out == 0:
                    raise InsufficientLiquidityError(
                        "First leg of WETH hop (token_in -> WETH) results in 0 output."
                    )

                pool2_contract = _get_syncswap_classic_pool_contract_zksync(
                    web3_zksync, pool2_address
                )
                final_amount_out = pool2_contract.functions.getAmountOut(
                    Web3.to_checksum_address(weth_address),
                    cast(int, amount_weth_out),
                    Web3.to_checksum_address(sender_address),
                ).call()
                logger.info(
                    f"Pool2 (WETH->{token_out_address}) quote: {final_amount_out} "
                    f"{token_out_address}"
                )
                return cast(int, final_amount_out)
            except InsufficientLiquidityError as e:
                # Re-raise specific liquidity errors from the hop
                raise e
            except Exception as e:
                logger.warning(f"Failed to get quote via WETH hop: {e}")
                return 0  # Return 0 on other WETH hop failures

    logger.error(
        f"Could not find a valid path or pool for swapping {token_in_address} to "
        f"{token_out_address}"
    )
    raise InsufficientLiquidityError(
        f"No liquidity or path found for swapping {token_in_address} to "
        f"{token_out_address} on SyncSwap."
    )


def _calculate_amount_out_min_syncswap_zksync(
    expected_amount_out: int, slippage_percent: float
) -> int:
    """Calculate the minimum amount_out based on expected_amount_out and slippage."""
    if not 0 <= slippage_percent <= 100:
        raise ValueError("Slippage percent must be between 0 and 100.")
    amount_out_min = int(expected_amount_out * (1 - slippage_percent / 100.0))
    logger.info(
        f"Calculated amountOutMin: {amount_out_min} from expected "
        f"{expected_amount_out} with {slippage_percent}% slippage"
    )
    return amount_out_min


def _encode_swap_step_data_zksync(
    token_in_for_step: str, to_address_for_step: str, withdraw_mode: int
) -> HexBytes:
    """ABI encodes the data for a SwapStep."""
    encoded_data = abi_encode(
        ["address", "address", "uint8"],
        [
            Web3.to_checksum_address(token_in_for_step),
            Web3.to_checksum_address(to_address_for_step),
            withdraw_mode,
        ],
    )
    return HexBytes(encoded_data)


def _construct_syncswap_paths_zksync(
    web3_zksync: Web3,
    token_in_start_address: str,
    token_out_final_address: str,
    amount_in_start: int,
    final_recipient_address: str,
    weth_address: str,
    router_contract: Contract,
    actual_token_out_symbol: str,
) -> List[Dict[str, Any]]:
    """
    Constructs the 'paths' parameter for SyncSwap router's swap function.
    Handles direct (A->B) and single-hop via WETH (A->WETH->B).
    """
    logger.info(
        f"Constructing SyncSwap path: {token_in_start_address} -> "
        f"{token_out_final_address} for amount {amount_in_start}"
    )
    paths: List[Dict[str, Any]] = []

    try:
        vault_address = router_contract.functions.vault().call()
        logger.info(f"SyncSwap Vault address: {vault_address}")
    except Exception as e:
        logger.error(f"Could not fetch vault address from SyncSwap Router: {e}")
        raise ZkSyncSwapError(
            f"Could not fetch vault address from SyncSwap Router: {e}"
        )

    direct_pool_address = _get_syncswap_pool_address_zksync(
        web3_zksync, token_in_start_address, token_out_final_address
    )
    if direct_pool_address:
        logger.info(f"Direct path found via pool: {direct_pool_address}")
        withdraw_mode: int
        if actual_token_out_symbol == ETH_SYMBOL:
            withdraw_mode = 1
        elif token_out_final_address == weth_address:
            withdraw_mode = 2
        else:
            withdraw_mode = 0

        step_data = _encode_swap_step_data_zksync(
            token_in_start_address, final_recipient_address, withdraw_mode
        )
        step = {
            "pool": Web3.to_checksum_address(direct_pool_address),
            "data": step_data,
            "callback": ZERO_ADDRESS,
            "callbackData": HexBytes("0x"),
        }
        path_obj = {
            "steps": [step],
            "tokenIn": Web3.to_checksum_address(token_in_start_address),
            "amountIn": amount_in_start,
        }
        paths.append(path_obj)
        return paths

    if (
        token_in_start_address != weth_address
        and token_out_final_address != weth_address
    ):
        logger.info(
            f"No direct path, trying via WETH: {token_in_start_address} -> "
            f"{weth_address} -> {token_out_final_address}"
        )
        pool1_address = _get_syncswap_pool_address_zksync(
            web3_zksync, token_in_start_address, weth_address
        )
        pool2_address = _get_syncswap_pool_address_zksync(
            web3_zksync, weth_address, token_out_final_address
        )

        if pool1_address and pool2_address:
            logger.info(
                f"Found WETH hop: Pool1 ({token_in_start_address}->WETH): "
                f"{pool1_address}, Pool2 (WETH->{token_out_final_address}): "
                f"{pool2_address}"
            )
            step1_data = _encode_swap_step_data_zksync(
                token_in_start_address, vault_address, 2
            )
            step1 = {
                "pool": Web3.to_checksum_address(pool1_address),
                "data": step1_data,
                "callback": ZERO_ADDRESS,
                "callbackData": HexBytes("0x"),
            }

            final_withdraw_mode: int
            if actual_token_out_symbol == ETH_SYMBOL:
                final_withdraw_mode = 1
            elif token_out_final_address == weth_address:
                final_withdraw_mode = 2
            else:
                final_withdraw_mode = 0

            step2_data = _encode_swap_step_data_zksync(
                weth_address, final_recipient_address, final_withdraw_mode
            )
            step2 = {
                "pool": Web3.to_checksum_address(pool2_address),
                "data": step2_data,
                "callback": ZERO_ADDRESS,
                "callbackData": HexBytes("0x"),
            }

            path_obj = {
                "steps": [step1, step2],
                "tokenIn": Web3.to_checksum_address(token_in_start_address),
                "amountIn": amount_in_start,
            }
            paths.append(path_obj)
            return paths

    if not paths:
        logger.error(
            f"Could not construct any swap path for {token_in_start_address} -> "
            f"{token_out_final_address}"
        )
        raise InsufficientLiquidityError(
            f"No swap path found for {token_in_start_address} to "
            f"{token_out_final_address} on SyncSwap."
        )
    return paths


def swap_tokens(
    web3_zksync: Web3,
    private_key: str,
    token_in_symbol: str,
    token_out_symbol: str,
    amount_in: int,
    slippage_percent: float = 0.5,
    deadline_seconds: int = 1800,
    dex: str = "auto",
) -> str:
    """
    Swaps tokens on zkSync Era DEXs with automatic DEX selection or manual DEX specification.

    This function acts as a DEX aggregator, automatically selecting the best DEX
    for the swap based on available liquidity and rates, or using a specified DEX.

    Args:
        web3_zksync: Web3 instance for ZkSync L2.
        private_key: Private key of the account performing the swap.
        token_in_symbol: Symbol of the token to swap from (e.g., "ETH", "USDC").
        token_out_symbol: Symbol of the token to swap to (e.g., "USDC", "WETH").
        amount_in: Amount of token_in to swap (in Wei or smallest unit).
        slippage_percent: Allowed slippage percentage (e.g., 0.5 for 0.5%).
        deadline_seconds: Transaction deadline in seconds from now.
        dex: DEX to use for the swap. Options: "auto", "syncswap", "mute", "spacefi".
             "auto" will automatically select the best DEX based on quotes.

    Returns:
        Transaction hash of the swap operation.

    Raises:
        ZkSyncSwapError: For general swap-related errors.
        InsufficientLiquidityError: If liquidity is insufficient for the swap or
                no path found.
        TokenNotSupportedError: If one of the token symbols is not configured.
        ApprovalError: If token approval fails.
        TransactionRevertedError: If the swap transaction is reverted.
        GasEstimationError: If gas estimation fails.
        ValueError: For invalid inputs like slippage or unsupported DEX.

    Example:
        >>> # Auto-select best DEX
        >>> tx_hash = swap_tokens(
        ...     web3_zksync=web3_l2,
        ...     private_key="0x...",
        ...     token_in_symbol="ETH",
        ...     token_out_symbol="USDC",
        ...     amount_in=1000000000000000000,  # 1 ETH
        ...     dex="auto"
        ... )
        >>> # Use specific DEX
        >>> tx_hash = swap_tokens(
        ...     web3_zksync=web3_l2,
        ...     private_key="0x...",
        ...     token_in_symbol="USDC",
        ...     token_out_symbol="ETH",
        ...     amount_in=1000000000,  # 1000 USDC
        ...     dex="syncswap"
        ... )
    """
    # Import DEX adapters
    from .dex_adapter import ZkSyncDEXAdapter, SyncSwapAdapter, MuteAdapter, SpaceFiAdapter
    
    logger.info(
        f"Initiating zkSync swap: {amount_in} {token_in_symbol} -> "
        f"{token_out_symbol} with {slippage_percent}% slippage, "
        f"deadline {deadline_seconds}s, DEX: {dex}."
    )

    if amount_in <= 0:
        raise ValueError("Amount to swap must be positive.")
    
    if dex not in ["auto", "syncswap", "mute", "spacefi"]:
        raise ValueError(f"Unsupported DEX: {dex}. Supported: auto, syncswap, mute, spacefi")

    account = _get_account_zksync(private_key, web3_zksync)
    sender_address = account.address
    recipient_address = sender_address

    # Get token addresses
    token_in_address_actual = _get_l2_token_address_zksync(token_in_symbol)
    token_out_address_actual = _get_l2_token_address_zksync(token_out_symbol)
    
    # Check balances
    is_eth_input = token_in_symbol == ETH_SYMBOL
    if is_eth_input:
        eth_balance = web3_zksync.eth.get_balance(Web3.to_checksum_address(sender_address))
        if eth_balance < amount_in:
            raise InsufficientBalanceError(
                f"Insufficient ETH balance for swap: have {eth_balance}, need {amount_in}"
            )
    else:
        token_in_contract = _get_contract_zksync(
            web3_zksync, ERC20_ABI_NAME, token_in_address_actual
        )
        erc20_balance = token_in_contract.functions.balanceOf(
            Web3.to_checksum_address(sender_address)
        ).call()
        if erc20_balance < amount_in:
            raise InsufficientBalanceError(
                f"Insufficient {token_in_symbol} balance for swap: "
                f"have {erc20_balance}, need {amount_in}"
            )

    # Initialize DEX adapters
    dex_adapters = {
        "syncswap": SyncSwapAdapter(web3_zksync),
        "mute": MuteAdapter(web3_zksync),
        "spacefi": SpaceFiAdapter(web3_zksync),
    }

    # Select DEX and get transaction
    selected_dex: str
    selected_adapter: ZkSyncDEXAdapter
    
    if dex == "auto":
        # Get quotes from all adapters and select the best one
        best_quote = 0
        best_dex = "syncswap"  # Default fallback
        
        logger.info("Getting quotes from all DEXs for auto-selection...")
        for dex_name, adapter in dex_adapters.items():
            try:
                quote = adapter.get_quote(
                    token_in_address_actual,
                    token_out_address_actual,
                    amount_in
                )
                logger.info(f"{dex_name} quote: {quote}")
                if quote > best_quote:
                    best_quote = quote
                    best_dex = dex_name
            except Exception as e:
                logger.warning(f"Failed to get quote from {dex_name}: {e}")
        
        if best_quote == 0:
            raise InsufficientLiquidityError(
                f"No DEX has sufficient liquidity for {token_in_symbol} -> {token_out_symbol}"
            )
        
        selected_dex = best_dex
        selected_adapter = dex_adapters[best_dex]
        logger.info(f"Auto-selected DEX: {selected_dex} with quote: {best_quote}")
    else:
        # Use specified DEX
        selected_dex = dex
        selected_adapter = dex_adapters[dex]
        
        # Verify the DEX has liquidity
        quote = selected_adapter.get_quote(
            token_in_address_actual,
            token_out_address_actual,
            amount_in
        )
        if quote == 0:
            raise InsufficientLiquidityError(
                f"No liquidity available on {dex} for {token_in_symbol} -> {token_out_symbol}"
            )
        logger.info(f"Using specified DEX: {selected_dex} with quote: {quote}")

    # Handle token approval for ERC20 tokens
    if not is_eth_input:
        # Get the appropriate router address for approval
        if selected_dex == "syncswap":
            router_address = SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC
        elif selected_dex == "mute":
            from .dex_adapter import MUTE_ROUTER_ADDRESS_ZKSYNC
            router_address = MUTE_ROUTER_ADDRESS_ZKSYNC
        elif selected_dex == "spacefi":
            from .dex_adapter import SPACEFI_ROUTER_ADDRESS_ZKSYNC
            router_address = SPACEFI_ROUTER_ADDRESS_ZKSYNC
        else:
            raise ZkSyncSwapError(f"Unknown DEX for approval: {selected_dex}")
            
        logger.info(
            f"Approving {selected_dex} router {router_address} to spend "
            f"{amount_in} of {token_in_symbol} ({token_in_address_actual})"
        )
        try:
            _approve_erc20_zksync(
                web3_zksync,
                private_key,
                token_in_address_actual,
                router_address,
                amount_in,
            )
            logger.info(f"Approval successful for {token_in_symbol} on {selected_dex}.")
        except ApprovalError as e:
            logger.error(f"ERC20 approval for {token_in_symbol} on {selected_dex} failed: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during ERC20 approval for {token_in_symbol} on {selected_dex}: {e}"
            )
            raise ApprovalError(
                f"Unexpected error during ERC20 approval for {token_in_symbol} on {selected_dex}: {e}"
            ) from e

    # Build and send the swap transaction
    try:
        swap_tx = selected_adapter.build_swap_transaction(
            token_in_address_actual,
            token_out_address_actual,
            amount_in,
            recipient_address,
            slippage_percent,
            deadline_seconds
        )
        
        logger.info(f"Built {selected_dex} swap transaction: {swap_tx}")
        return _build_and_send_tx_zksync(web3_zksync, private_key, swap_tx)

    except ContractLogicError as e:
        logger.error(f"{selected_dex} contract logic error: {e.message} - Data: {e.data}")
        if "TooLittleReceived" in str(e) or (e.data and "0x087229a4" in e.data):
            raise InsufficientLiquidityError(
                f"Swap likely to result in too little received (slippage or liquidity): {e.message}",
                tx_data=e.data
            )
        if "Expired" in str(e) or (e.data and "0x414432ea" in e.data):
            raise ZkSyncSwapError(
                f"Swap transaction expired: {e.message}", tx_data=e.data
            )
        raise TransactionRevertedError(
            f"{selected_dex} swap reverted with logic error: {e.message}",
            receipt=None,
            tx_hash=None,
        ) from e
    except GasEstimationError as e:
        logger.error(f"Gas estimation failed for {selected_dex} swap transaction: {e}")
        raise
    except ApprovalError as e: # Added explicit catch for ApprovalError
        logger.error(f"Approval error during {selected_dex} swap transaction: {e}")
        raise # Re-raise the ApprovalError
    except Exception as e:
        logger.error(f"Unexpected error preparing or sending {selected_dex} swap transaction: {e}")
        raise ZkSyncSwapError(f"Failed to execute {selected_dex} swap: {e}") from e


def bridge_assets(
    web3_l1: Web3,
    web3_l2: Web3,
    private_key: str,
    token_symbol: str,
    amount: int,
    direction: str,
    l2_gas_limit: int = DEFAULT_L2_GAS_LIMIT,
    l2_gas_price: Optional[int] = None,
) -> str:
    """
    Bridges ETH or ERC20 tokens between L1 (Ethereum) and L2 (ZkSync Era).

    Args:
    web3_l1: Web3 instance for L1 (Ethereum).
    web3_l2: Web3 instance for L2 (ZkSync Era).
    private_key: Private key of the account.
    token_symbol: Symbol of the token to bridge (e.g., "ETH", "USDC").
    amount: Amount of token to bridge (in Wei for ETH, smallest unit for ERC20).
    direction: "deposit" (L1 to L2) or "withdraw" (L2 to L1).
    l2_gas_limit: Gas limit for the L2 transaction (for deposits).
    l2_gas_price: Gas price for the L2 transaction (for deposits).

    Returns:
    Transaction hash of the bridge operation.

    Raises:
    ZkSyncBridgeError: For general bridging errors.
    InsufficientBalanceError: If account balance is insufficient.
    TokenNotSupportedError: If token symbol is not configured.
    ApprovalError: If ERC20 approval fails.
    GasEstimationError: If gas estimation fails.
    TransactionRevertedError: If the transaction is reverted.
    ValueError: For invalid inputs.
    """
    logger.info(
        f"Initiating ZkSync bridge: {amount} {token_symbol} {direction}."
    )

    if direction not in ("deposit", "withdraw"):
        raise ValueError("Direction must be 'deposit' or 'withdraw'.")
    if amount <= 0:
        raise ValueError("Amount must be positive.")

    account_l1 = _get_account_zksync(private_key, web3_l1)
    account_l2 = _get_account_zksync(private_key, web3_l2)
    l1_address = account_l1.address
    l2_address = account_l2.address

    if token_symbol == ETH_SYMBOL:
        return _bridge_eth_zksync(
            web3_l1,
            web3_l2,
            private_key,
            amount,
            direction,
            Web3.to_checksum_address(l1_address),
            Web3.to_checksum_address(l2_address),
            l2_gas_limit,
            l2_gas_price,
        )
    else:
        return _bridge_erc20_zksync(
            web3_l1,
            web3_l2,
            private_key,
            token_symbol,
            amount,
            direction,
            Web3.to_checksum_address(l1_address),
            Web3.to_checksum_address(l2_address),
            l2_gas_limit,
            l2_gas_price,
        )


def _bridge_eth_zksync(
    web3_l1: Web3,
    web3_l2: Web3,
    private_key: str,
    amount: int,
    direction: str,
    l1_address: str,
    l2_address: str,
    l2_gas_limit: int,
    l2_gas_price: Optional[int] = None,
) -> str:
    """
    Bridge ETH between L1 and L2.
    """
    logger.info(f"Bridging ETH: {amount} {direction} from {l1_address} to {l2_address}")

    if direction == "deposit":
        # L1 to L2 ETH deposit
        l1_bridge = _get_contract_zksync(
            web3_l1, L1_BRIDGE_ABI_NAME, ZKSYNC_L1_BRIDGE_ADDRESS
        )

        # Check L1 balance
        l1_balance = web3_l1.eth.get_balance(Web3.to_checksum_address(l1_address))
        print(f"DEBUG: _bridge_eth_zksync (deposit) - l1_balance: {l1_balance}, amount: {amount}") # DEBUG
        if l1_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient L1 ETH balance for deposit: have {l1_balance}, "
                f"need {amount}"
            )

        tx_params: TxParams = {
            "from": l1_address,
            "value": Wei(amount),
            "gasPrice": web3_l1.eth.gas_price,
        }
        deposit_tx = l1_bridge.functions.requestL2Transaction(
            l2_address,
            Wei(amount),
            b"",  # calldata
            l2_gas_limit,
            l2_gas_price or web3_l2.eth.gas_price,
            [],  # factoryDeps
            l2_address,  # refundRecipient
        ).build_transaction(tx_params)

        tx_hash = _build_and_send_tx_zksync(web3_l1, private_key, deposit_tx)
        if tx_hash is None:
            raise ZkSyncBridgeError(
                "Transaction processing finished in an unexpected state (tx_hash is None)"
            )
        return tx_hash

    elif direction == "withdraw":
        # L2 to L1 ETH withdrawal
        l2_bridge = _get_contract_zksync(
            web3_l2, L2_BRIDGE_ABI_NAME, ZKSYNC_L2_BRIDGE_ADDRESS
        )

        # Check L2 balance
        l2_balance = web3_l2.eth.get_balance(Web3.to_checksum_address(l2_address))
        print(f"DEBUG: _bridge_eth_zksync (withdraw) - l2_balance: {l2_balance}, amount: {amount}") # DEBUG
        if l2_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient L2 ETH balance for withdrawal: have {l2_balance}, "
                f"need {amount}"
            )

        withdraw_tx_params: TxParams = {
            "from": l2_address,
            "value": Wei(amount),
            "gasPrice": web3_l2.eth.gas_price,
        }
        withdraw_tx = l2_bridge.functions.withdraw(
            l1_address, amount
        ).build_transaction(withdraw_tx_params)

        return _build_and_send_tx_zksync(web3_l2, private_key, withdraw_tx)
    return ""


def provide_liquidity(
    web3_zksync: Web3,
    private_key: str,
    token_a_symbol: str,
    token_b_symbol: str,
    amount_a: int,
    amount_b: int,
    dex: str = "syncswap",
    slippage_percent: float = 0.5,
    deadline_seconds: int = 1800
) -> str:
    """
    Provide liquidity to a DEX pool on zkSync Era.

    This function adds liquidity to a specified DEX pool by providing both tokens
    in the pair. The user receives LP tokens representing their share of the pool.

    Args:
        web3_zksync: Web3 instance for ZkSync L2.
        private_key: Private key of the account providing liquidity.
        token_a_symbol: Symbol of the first token (e.g., "ETH", "USDC").
        token_b_symbol: Symbol of the second token (e.g., "USDC", "WETH").
        amount_a: Amount of first token (in wei/smallest unit).
        amount_b: Amount of second token (in wei/smallest unit).
        dex: DEX to use for liquidity provision (default: "syncswap").
        slippage_percent: Maximum allowed slippage percentage.
        deadline_seconds: Transaction deadline in seconds from now.

    Returns:
        Transaction hash of the liquidity provision operation.

    Raises:
        ZkSyncSwapError: For general liquidity-related errors.
        InsufficientLiquidityError: If no pool exists for the token pair.
        TokenNotSupportedError: If one of the token symbols is not configured.
        ApprovalError: If token approval fails.
        ValueError: For invalid inputs.

    Example:
        >>> tx_hash = provide_liquidity(
        ...     web3_zksync=web3_l2,
        ...     private_key="0x...",
        ...     token_a_symbol="ETH",
        ...     token_b_symbol="USDC",
        ...     amount_a=1000000000000000000,  # 1 ETH
        ...     amount_b=2000000000,  # 2000 USDC (6 decimals)
        ...     dex="syncswap"
        ... )
    """
    # Import DEX adapters
    from .dex_adapter import SyncSwapAdapter, MuteAdapter, SpaceFiAdapter
    
    logger.info(
        f"Initiating zkSync liquidity provision: {amount_a} {token_a_symbol} + "
        f"{amount_b} {token_b_symbol} on {dex} with {slippage_percent}% slippage"
    )

    if amount_a <= 0 or amount_b <= 0:
        raise ValueError("Token amounts must be positive.")
    
    if dex not in ["syncswap", "mute", "spacefi"]:
        raise ValueError(f"Unsupported DEX: {dex}. Supported: syncswap, mute, spacefi")

    account = _get_account_zksync(private_key, web3_zksync)
    sender_address = account.address
    recipient_address = sender_address

    # Get token addresses
    token_a_address = _get_l2_token_address_zksync(token_a_symbol)
    token_b_address = _get_l2_token_address_zksync(token_b_symbol)
    
    # Check balances
    weth_address = _get_l2_token_address_zksync(WETH_SYMBOL)
    
    # Check token A balance
    if token_a_symbol == ETH_SYMBOL or token_a_address == weth_address:
        eth_balance = web3_zksync.eth.get_balance(Web3.to_checksum_address(sender_address))
        if eth_balance < amount_a:
            raise InsufficientBalanceError(
                f"Insufficient ETH balance for liquidity: have {eth_balance}, need {amount_a}"
            )
    else:
        token_a_contract = _get_contract_zksync(
            web3_zksync, ERC20_ABI_NAME, token_a_address
        )
        erc20_balance_a = token_a_contract.functions.balanceOf(
            Web3.to_checksum_address(sender_address)
        ).call()
        if erc20_balance_a < amount_a:
            raise InsufficientBalanceError(
                f"Insufficient {token_a_symbol} balance for liquidity: "
                f"have {erc20_balance_a}, need {amount_a}"
            )

    # Check token B balance
    if token_b_symbol == ETH_SYMBOL or token_b_address == weth_address:
        eth_balance = web3_zksync.eth.get_balance(Web3.to_checksum_address(sender_address))
        if eth_balance < amount_b:
            raise InsufficientBalanceError(
                f"Insufficient ETH balance for liquidity: have {eth_balance}, need {amount_b}"
            )
    else:
        token_b_contract = _get_contract_zksync(
            web3_zksync, ERC20_ABI_NAME, token_b_address
        )
        erc20_balance_b = token_b_contract.functions.balanceOf(
            Web3.to_checksum_address(sender_address)
        ).call()
        if erc20_balance_b < amount_b:
            raise InsufficientBalanceError(
                f"Insufficient {token_b_symbol} balance for liquidity: "
                f"have {erc20_balance_b}, need {amount_b}"
            )

    # Initialize DEX adapters
    dex_adapters = {
        "syncswap": SyncSwapAdapter(web3_zksync),
        "mute": MuteAdapter(web3_zksync),
        "spacefi": SpaceFiAdapter(web3_zksync),
    }
    
    selected_adapter = dex_adapters[dex]

    # Handle token approvals for ERC20 tokens
    router_address = SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC  # Use SyncSwap router for now
    
    # Approve token A if it's not ETH
    if token_a_symbol != ETH_SYMBOL and token_a_address != weth_address:
        logger.info(f"Approving {token_a_symbol} for liquidity provision")
        try:
            _approve_erc20_zksync(
                web3_zksync,
                private_key,
                token_a_address,
                router_address,
                amount_a,
            )
        except ApprovalError as e:
            logger.error(f"ERC20 approval for {token_a_symbol} failed: {e}")
            raise

    # Approve token B if it's not ETH
    if token_b_symbol != ETH_SYMBOL and token_b_address != weth_address:
        logger.info(f"Approving {token_b_symbol} for liquidity provision")
        try:
            _approve_erc20_zksync(
                web3_zksync,
                private_key,
                token_b_address,
                router_address,
                amount_b,
            )
        except ApprovalError as e:
            logger.error(f"ERC20 approval for {token_b_symbol} failed: {e}")
            raise

    # Build and send the liquidity transaction
    try:
        liquidity_tx = selected_adapter.add_liquidity(
            token_a_address,
            token_b_address,
            amount_a,
            amount_b,
            recipient_address,
            slippage_percent,
            deadline_seconds
        )
        
        logger.info(f"Built {dex} liquidity provision transaction: {liquidity_tx}")
        return _build_and_send_tx_zksync(web3_zksync, private_key, liquidity_tx)

    except Exception as e:
        logger.error(f"Unexpected error during {dex} liquidity provision: {e}")
        raise ZkSyncSwapError(f"Failed to provide liquidity on {dex}: {e}") from e


def remove_liquidity(
    web3_zksync: Web3,
    private_key: str,
    token_a_symbol: str,
    token_b_symbol: str,
    liquidity_percent: float,
    dex: str = "syncswap",
    slippage_percent: float = 0.5,
    deadline_seconds: int = 1800
) -> str:
    """
    Remove liquidity from a DEX pool on zkSync Era.

    This function removes a percentage of the user's liquidity from a specified
    DEX pool by burning LP tokens and receiving the underlying tokens.

    Args:
        web3_zksync: Web3 instance for ZkSync L2.
        private_key: Private key of the account removing liquidity.
        token_a_symbol: Symbol of the first token (e.g., "ETH", "USDC").
        token_b_symbol: Symbol of the second token (e.g., "USDC", "WETH").
        liquidity_percent: Percentage of liquidity to remove (0-100).
        dex: DEX to remove liquidity from (default: "syncswap").
        slippage_percent: Maximum allowed slippage percentage.
        deadline_seconds: Transaction deadline in seconds from now.

    Returns:
        Transaction hash of the liquidity removal operation.

    Raises:
        ZkSyncSwapError: For general liquidity-related errors.
        InsufficientLiquidityError: If no pool exists or insufficient LP tokens.
        TokenNotSupportedError: If one of the token symbols is not configured.
        ValueError: For invalid inputs.

    Example:
        >>> tx_hash = remove_liquidity(
        ...     web3_zksync=web3_l2,
        ...     private_key="0x...",
        ...     token_a_symbol="ETH",
        ...     token_b_symbol="USDC",
        ...     liquidity_percent=50.0,  # Remove 50% of liquidity
        ...     dex="syncswap"
        ... )
    """
    # Import DEX adapters
    from .dex_adapter import SyncSwapAdapter, MuteAdapter, SpaceFiAdapter
    
    logger.info(
        f"Initiating zkSync liquidity removal: {liquidity_percent}% of "
        f"{token_a_symbol}-{token_b_symbol} pool on {dex}"
    )

    if not 0 < liquidity_percent <= 100:
        raise ValueError("Liquidity percent must be between 0 and 100.")
    
    if dex not in ["syncswap", "mute", "spacefi"]:
        raise ValueError(f"Unsupported DEX: {dex}. Supported: syncswap, mute, spacefi")

    account = _get_account_zksync(private_key, web3_zksync)
    sender_address = account.address
    recipient_address = sender_address

    # Get token addresses
    token_a_address = _get_l2_token_address_zksync(token_a_symbol)
    token_b_address = _get_l2_token_address_zksync(token_b_symbol)
    
    # Get pool address to check LP token balance
    pool_address = _get_syncswap_pool_address_zksync(
        web3_zksync, token_a_address, token_b_address
    )
    if not pool_address:
        raise InsufficientLiquidityError(
            f"No pool found for {token_a_symbol}-{token_b_symbol} pair"
        )
    
    # Get LP token balance (pool contract acts as the LP token)
    pool_contract = _get_syncswap_classic_pool_contract_zksync(web3_zksync, pool_address)
    lp_balance = pool_contract.functions.balanceOf(
        Web3.to_checksum_address(sender_address)
    ).call()
    
    if lp_balance == 0:
        raise InsufficientLiquidityError(
            f"No LP tokens found for {token_a_symbol}-{token_b_symbol} pool"
        )
    
    # Calculate liquidity amount to remove
    liquidity_to_remove = int(lp_balance * liquidity_percent / 100.0)
    
    if liquidity_to_remove == 0:
        raise ValueError("Calculated liquidity to remove is zero")

    # Initialize DEX adapters
    dex_adapters = {
        "syncswap": SyncSwapAdapter(web3_zksync),
        "mute": MuteAdapter(web3_zksync),
        "spacefi": SpaceFiAdapter(web3_zksync),
    }
    
    selected_adapter = dex_adapters[dex]

    # Build and send the liquidity removal transaction
    try:
        remove_tx = selected_adapter.remove_liquidity(
            token_a_address,
            token_b_address,
            liquidity_to_remove,
            recipient_address,
            slippage_percent,
            deadline_seconds
        )
        
        logger.info(f"Built {dex} liquidity removal transaction: {remove_tx}")
        return _build_and_send_tx_zksync(web3_zksync, private_key, remove_tx)

    except Exception as e:
        logger.error(f"Unexpected error during {dex} liquidity removal: {e}")
        raise ZkSyncSwapError(f"Failed to remove liquidity from {dex}: {e}") from e


def lend_borrow(
    web3_zksync: Web3,
    private_key: str,
    action: str,
    token_symbol: str,
    amount: Decimal,
    protocol: str = "zerolend"
) -> str:
    """
    Perform lending/borrowing operations on zkSync Era lending protocols.

    This function provides a unified interface for lending operations across
    different protocols on zkSync Era, starting with Zerolend.

    Args:
        web3_zksync: Web3 instance for ZkSync L2.
        private_key: Private key of the account performing the operation.
        action: The lending action to perform ("lend", "withdraw", "borrow", "repay").
        token_symbol: Symbol of the token (e.g., "ETH", "USDC").
        amount: Amount of tokens for the operation.
        protocol: Lending protocol to use (default: "zerolend").

    Returns:
        Transaction hash of the lending operation.

    Raises:
        ZkSyncLendingError: For general lending-related errors.
        InsufficientBalanceError: If account balance is insufficient.
        TokenNotSupportedError: If token symbol is not configured.
        ApprovalError: If ERC20 approval fails.
        ValueError: For invalid inputs.

    Example:
        >>> # Lend 1 ETH to Zerolend
        >>> tx_hash = lend_borrow(
        ...     web3_zksync=web3_l2,
        ...     private_key="0x...",
        ...     action="lend",
        ...     token_symbol="ETH",
        ...     amount=Decimal("1.0"),
        ...     protocol="zerolend"
        ... )
        >>> # Withdraw 0.5 ETH from Zerolend
        >>> tx_hash = lend_borrow(
        ...     web3_zksync=web3_l2,
        ...     private_key="0x...",
        ...     action="withdraw",
        ...     token_symbol="ETH",
        ...     amount=Decimal("0.5"),
        ...     protocol="zerolend"
        ... )
    """
    logger.info(
        f"Initiating zkSync lending operation: {action} {amount} {token_symbol} "
        f"on {protocol}"
    )

    # Validate inputs
    if action not in ["lend", "withdraw", "borrow", "repay"]:
        raise ValueError(f"Invalid action: {action}. Must be one of: lend, withdraw, borrow, repay")
    
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    if protocol not in ["zerolend"]:
        raise ValueError(f"Unsupported protocol: {protocol}. Supported: zerolend")

    # Get account and token information
    account = _get_account_zksync(private_key, web3_zksync)
    sender_address = account.address
    
    # Get token address
    token_address = _get_l2_token_address_zksync(token_symbol)
    
    # Convert amount to wei/smallest unit
    if token_symbol == ETH_SYMBOL:
        amount_wei = int(web3_zksync.to_wei(amount, "ether"))
    else:
        # For other tokens, assume 18 decimals (can be enhanced to query token decimals)
        amount_wei = int(amount * Decimal(10**18))

    # Initialize lending adapters
    from .lending_adapter import ZerolendAdapter
    lending_adapters = {
        "zerolend": ZerolendAdapter(web3_zksync),
    }
    
    adapter = lending_adapters[protocol]
    
    # Check balances for relevant operations
    if action in ["lend", "repay"]:
        # Check if user has sufficient balance
        is_eth_input = token_symbol == ETH_SYMBOL
        if is_eth_input:
            eth_balance = web3_zksync.eth.get_balance(Web3.to_checksum_address(sender_address))
            if eth_balance < amount_wei:
                raise InsufficientBalanceError(
                    f"Insufficient ETH balance for {action}: have {eth_balance}, need {amount_wei}"
                )
        else:
            token_contract = _get_contract_zksync(
                web3_zksync, ERC20_ABI_NAME, token_address
            )
            erc20_balance = token_contract.functions.balanceOf(
                Web3.to_checksum_address(sender_address)
            ).call()
            if erc20_balance < amount_wei:
                raise InsufficientBalanceError(
                    f"Insufficient {token_symbol} balance for {action}: "
                    f"have {erc20_balance}, need {amount_wei}"
                )

    # Build transaction using the appropriate adapter method
    try:
        if action == "lend":
            tx_params = adapter.lend(token_address, amount_wei, sender_address)
        elif action == "withdraw":
            tx_params = adapter.withdraw(token_address, amount_wei, sender_address)
        elif action == "borrow":
            tx_params = adapter.borrow(token_address, amount_wei, sender_address)
        elif action == "repay":
            tx_params = adapter.repay(token_address, amount_wei, sender_address)
        else:
            raise ValueError(f"Unknown action: {action}")
            
        logger.info(f"Built {protocol} {action} transaction: {tx_params}")
        
        # Handle token approval for ERC20 tokens (except for ETH operations)
        if not (token_symbol == ETH_SYMBOL) and action in ["lend", "repay"]:
            # Get the appropriate contract address for approval
            if protocol == "zerolend":
                from .lending_adapter import ZEROLEND_POOL_ADDRESS_ZKSYNC
                spender_address = ZEROLEND_POOL_ADDRESS_ZKSYNC
            else:
                raise ZkSyncLendingError(f"Unknown protocol for approval: {protocol}")
                
            logger.info(
                f"Approving {protocol} contract {spender_address} to spend "
                f"{amount_wei} of {token_symbol} ({token_address})"
            )
            try:
                _approve_erc20_zksync(
                    web3_zksync,
                    private_key,
                    token_address,
                    spender_address,
                    amount_wei,
                )
                logger.info(f"Approval successful for {token_symbol} on {protocol}.")
            except ApprovalError as e:
                logger.error(f"ERC20 approval for {token_symbol} on {protocol} failed: {e}")
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error during ERC20 approval for {token_symbol} on {protocol}: {e}"
                )
                raise ApprovalError(
                    f"Unexpected error during ERC20 approval for {token_symbol} on {protocol}: {e}"
                ) from e

        # Send the transaction
        return _build_and_send_tx_zksync(web3_zksync, private_key, tx_params)

    except ContractLogicError as e:
        logger.error(f"{protocol} contract logic error: {e.message} - Data: {e.data}")
        raise ZkSyncLendingError(
            f"{protocol} {action} reverted with logic error: {e.message}",
            protocol=protocol
        ) from e
    except GasEstimationError as e:
        logger.error(f"Gas estimation failed for {protocol} {action} transaction: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during {protocol} {action} operation: {e}")
        raise ZkSyncLendingError(f"Failed to execute {protocol} {action}: {e}", protocol=protocol) from e


def perform_random_activity(
    user_address: str,
    private_key: str,
    config: Dict[str, Any],
    web3_l1: Optional[Web3] = None,
    web3_l2: Optional[Web3] = None
) -> List[Dict[str, Any]]:
    """
    Performs a random on-chain activity based on weighted configuration for the zkSync protocol.

    This function selects an activity (e.g., swap, bridge), generates random
    parameters for it, executes the corresponding function, and returns a
    detailed log of the actions taken. It includes fallback logic to try
    alternative activities upon failure.

    Args:
        user_address (str): The public address of the user's wallet.
        private_key (str): The private key for signing transactions.
        config (Dict[str, Any]): The configuration dictionary for this protocol's
            random activity, containing weights, parameter ranges, and retry options.
        web3_l1 (Optional[Web3]): Web3 instance for L1. Required for bridging.
        web3_l2 (Optional[Web3]): Web3 instance for the protocol's L2 network.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary
            represents an attempted activity and its outcome.

    Raises:
        ValueError: If required parameters are missing or invalid.
        ZkSyncRandomActivityError: If all activities fail after max retries.

    Example:
        >>> config = {
        ...     "random_activity": {
        ...         "zksync": {
        ...             "action_weights": [
        ...                 {"name": "swap", "weight": 50},
        ...                 {"name": "bridge", "weight": 30}
        ...             ],
        ...             "max_retries": 3,
        ...             "amount_ranges": {"swap": {"min": "0.01", "max": "0.1"}},
        ...             "token_config": {"ETH": {}, "USDC": {}}
        ...         }
        ...     }
        ... }
        >>> results = perform_random_activity(
        ...     user_address="0x123...",
        ...     private_key="0xabc...",
        ...     config=config,
        ...     web3_l1=web3_instance,
        ...     web3_l2=web3_instance
        ... )
    """
    logger.info(f"Starting random activity for user {user_address}")
    
    # Input validation
    if not user_address or not private_key:
        raise ValueError("user_address and private_key are required")
    
    if not config or "random_activity" not in config:
        raise ValueError("config must contain 'random_activity' section")
    
    if "zksync" not in config["random_activity"]:
        raise ValueError("config must contain 'random_activity.zksync' section")
    
    zksync_config = config["random_activity"]["zksync"]
    
    # Extract configuration parameters
    action_weights = zksync_config.get("action_weights", [])
    max_retries = zksync_config.get("max_retries", 3)
    amount_ranges = zksync_config.get("amount_ranges", {})
    token_config = zksync_config.get("token_config", {})
    
    if not action_weights:
        raise ValueError("action_weights cannot be empty")
    
    # Create mutable pool of activities
    activity_pool = action_weights.copy()
    results: List[Dict[str, Any]] = []
    
    for attempt in range(max_retries):
        if not activity_pool:
            logger.warning("No more activities to try")
            break
            
        try:
            # Select activity by weight
            selected_activity = select_activity_by_weight(activity_pool)
            logger.info(f"Attempt {attempt + 1}: Selected activity '{selected_activity}'")
            
            # Generate parameters based on activity type
            activity_result = _execute_zksync_activity(
                selected_activity,
                user_address,
                private_key,
                amount_ranges,
                token_config,
                web3_l1,
                web3_l2
            )
            
            # Log successful result
            results.append({
                "attempt": attempt + 1,
                "activity": selected_activity,
                "status": "success",
                "tx_hash": activity_result,
                "timestamp": time.time()
            })
            
            logger.info(f"Activity '{selected_activity}' completed successfully: {activity_result}")
            break
            
        except Exception as e:
            logger.error(f"Activity '{selected_activity}' failed: {e}")
            
            # Log failed result
            results.append({
                "attempt": attempt + 1,
                "activity": selected_activity,
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            })
            
            # Remove failed activity from pool
            activity_pool = [
                activity for activity in activity_pool
                if activity["name"] != selected_activity
            ]
            
            # Continue to next iteration for retry
            continue
    
    if not any(result["status"] == "success" for result in results):
        raise ZkSyncRandomActivityError(
            f"All random activities failed after {max_retries} attempts"
        )
    
    return results


def _execute_zksync_activity(
    activity_name: str,
    user_address: str,
    private_key: str,
    amount_ranges: Dict[str, Any],
    token_config: Dict[str, Any],
    web3_l1: Optional[Web3],
    web3_l2: Optional[Web3]
) -> str:
    """
    Execute a specific zkSync activity with generated parameters.
    
    Args:
        activity_name: Name of the activity to execute.
        user_address: User's wallet address.
        private_key: Private key for signing transactions.
        amount_ranges: Configuration for amount generation.
        token_config: Available tokens configuration.
        web3_l1: Web3 instance for L1 operations.
        web3_l2: Web3 instance for L2 operations.
        
    Returns:
        Transaction hash of the executed activity.
        
    Raises:
        ZkSyncRandomActivityError: If activity execution fails.
    """
    if activity_name == "swap":
        return _execute_swap_activity_zksync(
            user_address, private_key, amount_ranges, token_config, web3_l2
        )
    elif activity_name == "bridge":
        return _execute_bridge_activity_zksync(
            user_address, private_key, amount_ranges, token_config, web3_l1, web3_l2
        )
    else:
        raise ZkSyncRandomActivityError(f"Unknown activity: {activity_name}")


def _execute_swap_activity_zksync(
    user_address: str,
    private_key: str,
    amount_ranges: Dict[str, Any],
    token_config: Dict[str, Any],
    web3_l2: Optional[Web3]
) -> str:
    """Execute a token swap activity on zkSync."""
    if not web3_l2:
        raise ZkSyncRandomActivityError("web3_l2 is required for swap activity")
    
    # Get swap configuration
    swap_config = amount_ranges.get("swap", {})
    min_amount = Decimal(swap_config.get("min", "0.01"))
    max_amount = Decimal(swap_config.get("max", "0.1"))
    decimals = swap_config.get("decimals", 4)
    
    # Generate random amount
    amount = generate_random_amount(min_amount, max_amount, decimals)
    
    # Select random token pair
    token_in, token_out = select_random_tokens(token_config, 2)
    
    # Convert amount to wei/smallest unit
    if token_in == "ETH":
        amount_wei = int(amount * Decimal(10**18))
    else:
        amount_wei = int(amount * Decimal(10**6))  # Assume USDC-like tokens
    
    return swap_tokens(
        web3_zksync=web3_l2,
        private_key=private_key,
        token_in_symbol=token_in,
        token_out_symbol=token_out,
        amount_in=amount_wei,
        slippage_percent=0.5,
        deadline_seconds=1800
    )


def _execute_bridge_activity_zksync(
    user_address: str,
    private_key: str,
    amount_ranges: Dict[str, Any],
    token_config: Dict[str, Any],
    web3_l1: Optional[Web3],
    web3_l2: Optional[Web3]
) -> str:
    """Execute a bridge activity for zkSync."""
    if not web3_l1 or not web3_l2:
        raise ZkSyncRandomActivityError("Both web3_l1 and web3_l2 are required for bridge activity")
    
    # Get bridge configuration
    bridge_config = amount_ranges.get("bridge", {})
    min_amount = Decimal(bridge_config.get("min", "0.005"))
    max_amount = Decimal(bridge_config.get("max", "0.05"))
    decimals = bridge_config.get("decimals", 4)
    
    # Generate random amount
    amount = generate_random_amount(min_amount, max_amount, decimals)
    
    # Select random token (prefer ETH for bridging)
    available_tokens = list(token_config.keys())
    if "ETH" in available_tokens:
        token_symbol = "ETH"
    else:
        token_symbol = select_random_tokens(token_config, 1)[0]
    
    # Convert amount to wei/smallest unit
    if token_symbol == "ETH":
        amount_wei = int(amount * Decimal(10**18))
    else:
        amount_wei = int(amount * Decimal(10**6))  # Assume USDC-like tokens
    
    # Randomly choose direction (favor deposits for activity)
    import random
    direction = random.choice(["deposit", "deposit", "withdraw"])  # 2:1 ratio favoring deposits
    
    return bridge_assets(
        web3_l1=web3_l1,
        web3_l2=web3_l2,
        private_key=private_key,
        token_symbol=token_symbol,
        amount=amount_wei,
        direction=direction
    )


def _bridge_erc20_zksync(
    web3_l1: Web3,
    web3_l2: Web3,
    private_key: str,
    token_symbol: str,
    amount: int,
    direction: str,
    l1_address: str,
    l2_address: str,
    l2_gas_limit: int,
    l2_gas_price: Optional[int] = None,
) -> str:
    """
    Bridge ERC20 tokens between L1 and L2.
    """
    logger.info(f"Bridging ERC20 {token_symbol}: {amount} {direction}.")

    l1_token_address = _get_l1_token_address_zksync(token_symbol)
    l2_token_address = _get_l2_token_address_zksync(token_symbol)

    if direction == "deposit":
        # L1 to L2 ERC20 deposit
        l1_bridge = _get_contract_zksync(
            web3_l1, L1_BRIDGE_ABI_NAME, ZKSYNC_L1_BRIDGE_ADDRESS
        )
        l1_token_contract = _get_contract_zksync(
            web3_l1, ERC20_ABI_NAME, l1_token_address
        )

        # Check L1 ERC20 balance
        l1_erc20_balance = l1_token_contract.functions.balanceOf(
            Web3.to_checksum_address(l1_address)
        ).call()
        if l1_erc20_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient L1 {token_symbol} balance for deposit: have "
                f"{l1_erc20_balance}, need {amount}"
            )

        # Approve L1 Bridge to spend ERC20
        _approve_erc20_zksync(
            web3_l1, private_key, l1_token_address,
            ZKSYNC_L1_BRIDGE_ADDRESS, amount
        )

        tx_params: TxParams = {
            "from": l1_address,
            "gasPrice": web3_l1.eth.gas_price,
        }
        deposit_tx = l1_bridge.functions.requestL2Transaction(
            l2_address,
            Wei(0),  # ETH value is 0 for ERC20 deposit
            l1_token_contract.functions.transfer(l2_address, amount)._encode_transaction_data(),
            l2_gas_limit,
            l2_gas_price or web3_l2.eth.gas_price,
            [],  # factoryDeps
            l2_address,  # refundRecipient
        ).build_transaction(tx_params)

        return _build_and_send_tx_zksync(web3_l1, private_key, deposit_tx)

    elif direction == "withdraw":
        # L2 to L1 ERC20 withdrawal
        l2_bridge = _get_contract_zksync(
            web3_l2, L2_BRIDGE_ABI_NAME, ZKSYNC_L2_BRIDGE_ADDRESS
        )
        l2_token_contract = _get_contract_zksync(
            web3_l2, ERC20_ABI_NAME, l2_token_address
        )

        # Check L2 ERC20 balance
        l2_erc20_balance = l2_token_contract.functions.balanceOf(
            Web3.to_checksum_address(l2_address)
        ).call()
        if l2_erc20_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient L2 {token_symbol} balance for withdrawal: have "
                f"{l2_erc20_balance}, need {amount}"
            )

        # Approve L2 Bridge to spend ERC20
        _approve_erc20_zksync(
            web3_l2, private_key, l2_token_address,
            ZKSYNC_L2_BRIDGE_ADDRESS, amount
        )

        erc20_withdraw_tx_params: TxParams = {
            "from": l2_address,
            "gasPrice": web3_l2.eth.gas_price,
        }
        withdraw_tx = l2_bridge.functions.withdraw(
            l1_token_address, amount
        ).build_transaction(erc20_withdraw_tx_params)

        return _build_and_send_tx_zksync(web3_l2, private_key, withdraw_tx)
    return ""
