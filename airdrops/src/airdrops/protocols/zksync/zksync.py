# airdrops/src/airdrops/protocols/zksync/zksync.py
"""
zkSync Era Protocol Module.

This module provides functionalities to interact with the zkSync Era network,
including bridging, DEX swaps, and lending protocol interactions.
"""

from typing import Tuple, Dict, Any, List, Optional
import logging
import random
from decimal import Decimal
from web3 import Web3
from eth_account import Account

# Configure logging for this module
logger = logging.getLogger(__name__)

# Placeholder for configuration, to be loaded dynamically
CONFIG: Dict[str, Any] = {}

# Constants
L1_BRIDGE_ADDRESS = "0x32400084C286CF3E17e7B677ea9583e60a000324"
L2_BRIDGE_ADDRESS = "0x0000000000000000000000000000000000008006"
SYNCSWAP_ROUTER_ADDRESS = "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295"
NATIVE_ETH_ADDRESS = "0x0000000000000000000000000000000000000000"
DEFAULT_L2_GAS_LIMIT = 800000
DEFAULT_L2_GAS_PER_PUBDATA_BYTE_LIMIT = 800
DEFAULT_SLIPPAGE_BPS = 50


def _validate_bridge_inputs(
    user_address: str, private_key: str, amount_eth: Decimal, config: Dict[str, Any]
) -> None:
    """
    Validate inputs for bridge_eth function.

    Args:
        user_address: User's Ethereum address
        private_key: Private key for signing transactions
        amount_eth: Amount of ETH to bridge
        config: Configuration dictionary

    Raises:
        ValueError: If any input is invalid
    """
    if not user_address or not Web3.is_address(user_address):
        raise ValueError(f"Invalid user address: {user_address}")

    if not private_key or len(private_key) < 64:
        raise ValueError("Invalid private key provided")

    if amount_eth <= 0:
        raise ValueError(f"Amount must be positive: {amount_eth}")

    if not config:
        raise ValueError("Configuration dictionary is required")

    required_keys = ["networks"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")


def _get_web3_instance(rpc_url: str, chain_name: str) -> Web3:
    """
    Create and validate Web3 instance.

    Args:
        rpc_url: RPC endpoint URL
        chain_name: Name of the chain for logging

    Returns:
        Configured Web3 instance

    Raises:
        ConnectionError: If unable to connect to RPC
    """
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise ConnectionError(f"Failed to connect to {chain_name} RPC")
        return w3
    except Exception as e:
        raise ConnectionError(f"Error connecting to {chain_name}: {str(e)}")


def _estimate_l1_gas(
    contract_function, transaction_params: Dict[str, Any], multiplier: float = 1.2
) -> int:
    """
    Estimate gas for L1 transaction with safety multiplier.

    Args:
        contract_function: Web3 contract function
        transaction_params: Transaction parameters
        multiplier: Gas limit multiplier for safety

    Returns:
        Estimated gas limit
    """
    try:
        estimated_gas = contract_function.estimate_gas(transaction_params)
        return int(estimated_gas * multiplier)
    except Exception as e:
        logger.warning(f"Gas estimation failed: {e}, using default")
        return 200000  # Default fallback


def _build_l1_deposit_transaction(
    w3_l1: Web3,
    bridge_contract,
    user_address: str,
    amount_wei: int,
    l2_gas_limit: int,
    l2_gas_per_pubdata: int,
) -> Dict[str, Any]:
    """
    Build L1 to L2 deposit transaction.

    Args:
        w3_l1: Web3 instance for L1
        bridge_contract: L1 bridge contract instance
        user_address: User's address
        amount_wei: Amount in wei to bridge
        l2_gas_limit: L2 gas limit
        l2_gas_per_pubdata: L2 gas per pubdata byte limit

    Returns:
        Transaction dictionary
    """
    # Get current gas price
    gas_price = w3_l1.eth.gas_price

    # Build transaction for requestL2Transaction
    contract_function = bridge_contract.functions.requestL2Transaction(
        user_address,  # _contractL2 (recipient on L2)
        amount_wei,  # _l2Value
        b"",  # _calldata (empty for simple ETH transfer)
        l2_gas_limit,  # _l2GasLimit
        l2_gas_per_pubdata,  # _l2GasPerPubdataByteLimit
        [],  # _factoryDeps (empty)
        user_address,  # _refundRecipient
    )

    # Estimate L2 transaction cost
    try:
        l2_cost = bridge_contract.functions.l2TransactionBaseCost(
            gas_price, l2_gas_limit, l2_gas_per_pubdata
        ).call()
    except Exception:
        # Fallback calculation if l2TransactionBaseCost fails
        l2_cost = gas_price * l2_gas_limit

    total_value = amount_wei + l2_cost

    transaction_params = {
        "from": user_address,
        "value": total_value,
        "gasPrice": gas_price,
        "nonce": w3_l1.eth.get_transaction_count(user_address),
    }

    # Estimate gas
    gas_limit = _estimate_l1_gas(contract_function, transaction_params)
    transaction_params["gas"] = gas_limit

    # Build the transaction
    transaction = contract_function.build_transaction(transaction_params)

    return transaction


def _build_l2_withdrawal_transaction(
    w3_l2: Web3, bridge_contract, user_address: str, amount_wei: int
) -> Dict[str, Any]:
    """
    Build L2 to L1 withdrawal transaction.

    Args:
        w3_l2: Web3 instance for L2
        bridge_contract: L2 bridge contract instance
        user_address: User's address
        amount_wei: Amount in wei to withdraw

    Returns:
        Transaction dictionary
    """
    # Build transaction for withdraw function
    contract_function = bridge_contract.functions.withdraw(
        user_address, amount_wei  # _l1Receiver  # amount (as msg.value)
    )

    transaction_params = {
        "from": user_address,
        "value": amount_wei,
        "gasPrice": w3_l2.eth.gas_price,
        "nonce": w3_l2.eth.get_transaction_count(user_address),
    }

    # Estimate gas for L2
    try:
        estimated_gas = contract_function.estimate_gas(transaction_params)
        gas_limit = int(estimated_gas * 1.5)  # L2 gas multiplier
    except Exception:
        gas_limit = 100000  # Default L2 gas limit

    transaction_params["gas"] = gas_limit

    # Build the transaction
    transaction = contract_function.build_transaction(transaction_params)

    return transaction


def bridge_eth(
    user_address: str,
    private_key: str,
    amount_eth: Decimal,
    to_l2: bool,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Bridge ETH between L1 (Ethereum) and L2 (zkSync Era).

    This function handles both L1->L2 deposits and L2->L1 withdrawal
    initiation for ETH on the zkSync Era network.

    Args:
        user_address: The Ethereum address performing the bridge operation
        private_key: Private key for signing transactions (64+ chars)
        amount_eth: Amount of ETH to bridge (must be positive)
        to_l2: True for L1->L2 deposit, False for L2->L1 withdrawal
        config: Configuration dictionary containing network settings

    Returns:
        Tuple of (success: bool, message_or_tx_hash: str)

    Raises:
        ValueError: For invalid inputs
        ConnectionError: For RPC connection issues

    Example:
        >>> config = {
        ...     "networks": {
        ...         "ethereum": {
        ...             "rpc_url": "https://eth-mainnet.g.alchemy.com/...",
        ...             "bridge_address": (
        ...                 "0x32400084C286CF3E17e7B677ea9583e60a000324"
        ...             )
        ...         },
        ...         "zksync": {
        ...             "rpc_url": "https://mainnet.era.zksync.io",
        ...             "bridge_address": (
        ...                 "0x0000000000000000000000000000000000008006"
        ...             )
        ...         }
        ...     }
        ... }
        >>> success, tx_hash = bridge_eth(
        ...     "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87",
        ...     "0x" + "a" * 64,
        ...     Decimal("0.1"),
        ...     True,
        ...     config
        ... )
    """
    try:
        # Input validation
        _validate_bridge_inputs(user_address, private_key, amount_eth, config)

        action = "Depositing to" if to_l2 else "Initiating withdrawal from"
        logger.info(f"{action} zkSync Era: {amount_eth} ETH for {user_address}")

        # Convert amount to wei
        amount_wei = Web3.to_wei(amount_eth, "ether")

        if to_l2:
            # L1 -> L2 Deposit
            return _execute_l1_to_l2_deposit(
                user_address, private_key, amount_wei, config
            )
        else:
            # L2 -> L1 Withdrawal
            return _execute_l2_to_l1_withdrawal(
                user_address, private_key, amount_wei, config
            )

    except ValueError as e:
        logger.error(f"Validation error in bridge_eth: {e}")
        return False, f"Validation error: {str(e)}"
    except ConnectionError as e:
        logger.error(f"Connection error in bridge_eth: {e}")
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in bridge_eth: {e}")
        return False, f"Unexpected error: {str(e)}"


def _execute_l1_to_l2_deposit(
    user_address: str, private_key: str, amount_wei: int, config: Dict[str, Any]
) -> Tuple[bool, str]:
    """Execute L1 to L2 deposit transaction."""
    try:
        # Get L1 configuration
        l1_config = config["networks"]["ethereum"]
        l1_rpc_url = l1_config["rpc_url"]
        l1_bridge_addr = l1_config.get("bridge_address", L1_BRIDGE_ADDRESS)

        # Initialize L1 Web3
        w3_l1 = _get_web3_instance(l1_rpc_url, "Ethereum L1")

        # Load L1 bridge contract (minimal ABI for requestL2Transaction)
        l1_bridge_abi = _get_l1_bridge_abi()
        bridge_contract = w3_l1.eth.contract(address=l1_bridge_addr, abi=l1_bridge_abi)

        # Get L2 gas parameters from config or use defaults
        settings = config.get("settings", {})
        l2_gas_limit = settings.get("l2_gas_limit", DEFAULT_L2_GAS_LIMIT)
        l2_gas_per_pubdata = settings.get(
            "l2_gas_per_pubdata_byte_limit", DEFAULT_L2_GAS_PER_PUBDATA_BYTE_LIMIT
        )

        # Build transaction
        transaction = _build_l1_deposit_transaction(
            w3_l1,
            bridge_contract,
            user_address,
            amount_wei,
            l2_gas_limit,
            l2_gas_per_pubdata,
        )

        # Sign and send transaction
        account = Account.from_key(private_key)
        signed_txn = account.sign_transaction(transaction)

        tx_hash = w3_l1.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        # Wait for transaction receipt
        receipt = w3_l1.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status == 1:
            logger.info(f"L1->L2 deposit successful: {tx_hash_hex}")
            return True, tx_hash_hex
        else:
            logger.error(f"L1->L2 deposit failed: {tx_hash_hex}")
            return False, f"Transaction failed: {tx_hash_hex}"

    except Exception as e:
        logger.error(f"Error in L1->L2 deposit: {e}")
        return False, f"L1->L2 deposit error: {str(e)}"


def _execute_l2_to_l1_withdrawal(
    user_address: str, private_key: str, amount_wei: int, config: Dict[str, Any]
) -> Tuple[bool, str]:
    """Execute L2 to L1 withdrawal initiation transaction."""
    try:
        # Get L2 configuration
        l2_config = config["networks"]["zksync"]
        l2_rpc_url = l2_config["rpc_url"]
        l2_bridge_addr = l2_config.get("bridge_address", L2_BRIDGE_ADDRESS)

        # Initialize L2 Web3
        w3_l2 = _get_web3_instance(l2_rpc_url, "zkSync Era L2")

        # Load L2 bridge contract (minimal ABI for withdraw)
        l2_bridge_abi = _get_l2_bridge_abi()
        bridge_contract = w3_l2.eth.contract(address=l2_bridge_addr, abi=l2_bridge_abi)

        # Build transaction
        transaction = _build_l2_withdrawal_transaction(
            w3_l2, bridge_contract, user_address, amount_wei
        )

        # Sign and send transaction
        account = Account.from_key(private_key)
        signed_txn = account.sign_transaction(transaction)

        tx_hash = w3_l2.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        # Wait for transaction receipt
        receipt = w3_l2.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status == 1:
            logger.info(f"L2->L1 withdrawal initiated: {tx_hash_hex}")
            return True, tx_hash_hex
        else:
            logger.error(f"L2->L1 withdrawal failed: {tx_hash_hex}")
            return False, f"Transaction failed: {tx_hash_hex}"

    except Exception as e:
        logger.error(f"Error in L2->L1 withdrawal: {e}")
        return False, f"L2->L1 withdrawal error: {str(e)}"


def _get_l1_bridge_abi() -> list:
    """Get minimal ABI for L1 bridge contract."""
    return [
        {
            "inputs": [
                {"name": "_contractL2", "type": "address"},
                {"name": "_l2Value", "type": "uint256"},
                {"name": "_calldata", "type": "bytes"},
                {"name": "_l2GasLimit", "type": "uint256"},
                {"name": "_l2GasPerPubdataByteLimit", "type": "uint256"},
                {"name": "_factoryDeps", "type": "bytes[]"},
                {"name": "_refundRecipient", "type": "address"},
            ],
            "name": "requestL2Transaction",
            "outputs": [{"name": "", "type": "bytes32"}],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "_gasPrice", "type": "uint256"},
                {"name": "_l2GasLimit", "type": "uint256"},
                {"name": "_l2GasPerPubdataByteLimit", "type": "uint256"},
            ],
            "name": "l2TransactionBaseCost",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]


def _get_l2_bridge_abi() -> list:
    """Get minimal ABI for L2 bridge contract."""
    return [
        {
            "inputs": [{"name": "_l1Receiver", "type": "address"}],
            "name": "withdraw",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function",
        }
    ]


def _validate_swap_inputs(
    user_address: str,
    private_key: str,
    token_in_address: str,
    token_out_address: str,
    amount_in: int,
    dex_name: str,
    slippage_bps: int,
    config: Dict[str, Any],
) -> None:
    """
    Validate inputs for swap_tokens function.

    Args:
        user_address: User's Ethereum address
        private_key: Private key for signing transactions
        token_in_address: Address of input token
        token_out_address: Address of output token
        amount_in: Amount of input token in wei
        dex_name: Name of the DEX
        slippage_bps: Slippage tolerance in basis points
        config: Configuration dictionary

    Raises:
        ValueError: If any input is invalid
    """
    if not user_address or not Web3.is_address(user_address):
        raise ValueError(f"Invalid user address: {user_address}")

    if not private_key or len(private_key) < 64:
        raise ValueError("Invalid private key provided")

    if not Web3.is_address(token_in_address):
        raise ValueError(f"Invalid token_in_address: {token_in_address}")

    if not Web3.is_address(token_out_address):
        raise ValueError(f"Invalid token_out_address: {token_out_address}")

    if amount_in <= 0:
        raise ValueError(f"Amount must be positive: {amount_in}")

    if not dex_name or dex_name.lower() not in ["syncswap"]:
        raise ValueError(f"Unsupported DEX: {dex_name}")

    if not (0 <= slippage_bps <= 10000):
        raise ValueError(f"Invalid slippage_bps: {slippage_bps}")

    if not config:
        raise ValueError("Configuration dictionary is required")

    required_keys = ["networks"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")


def _determine_swap_path(
    token_in_address: str, token_out_address: str, weth_address: str
) -> List[str]:
    """
    Determine the swap path for token exchange.

    Args:
        token_in_address: Address of input token
        token_out_address: Address of output token
        weth_address: Address of WETH token

    Returns:
        List of token addresses representing the swap path
    """
    # Normalize addresses to lowercase for comparison
    token_in = token_in_address.lower()
    token_out = token_out_address.lower()
    native_eth = NATIVE_ETH_ADDRESS.lower()

    # Direct swap if both tokens are not native ETH
    if token_in != native_eth and token_out != native_eth:
        # Try direct path first, fallback to WETH if needed
        return [token_in_address, token_out_address]

    # ETH to token swap
    if token_in == native_eth:
        return [weth_address, token_out_address]

    # Token to ETH swap
    if token_out == native_eth:
        return [token_in_address, weth_address]

    # Should not reach here with valid inputs
    return [token_in_address, token_out_address]


def _get_syncswap_router_abi() -> List[Dict[str, Any]]:
    """Get minimal ABI for SyncSwap router contract."""
    return [
        {
            "inputs": [
                {"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMin", "type": "uint256"},
                {"name": "path", "type": "address[]"},
                {"name": "to", "type": "address"},
                {"name": "deadline", "type": "uint256"},
            ],
            "name": "swapExactTokensForTokens",
            "outputs": [{"name": "amounts", "type": "uint256[]"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "amountOutMin", "type": "uint256"},
                {"name": "path", "type": "address[]"},
                {"name": "to", "type": "address"},
                {"name": "deadline", "type": "uint256"},
            ],
            "name": "swapExactETHForTokens",
            "outputs": [{"name": "amounts", "type": "uint256[]"}],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "amountIn", "type": "uint256"},
                {"name": "path", "type": "address[]"},
            ],
            "name": "getAmountsOut",
            "outputs": [{"name": "amounts", "type": "uint256[]"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]


def _get_erc20_abi() -> List[Dict[str, Any]]:
    """Get minimal ERC20 ABI for token interactions."""
    return [
        {
            "inputs": [
                {"name": "spender", "type": "address"},
                {"name": "amount", "type": "uint256"},
            ],
            "name": "approve",
            "outputs": [{"name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "owner", "type": "address"},
                {"name": "spender", "type": "address"},
            ],
            "name": "allowance",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"name": "account", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]


def swap_tokens(
    user_address: str,
    private_key: str,
    token_in_address: str,
    token_out_address: str,
    amount_in: int,
    dex_name: str,
    slippage_bps: int,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Swap tokens on a specified DEX on zkSync Era.

    This function handles token swaps on zkSync Era DEXes, specifically
    targeting SyncSwap. It supports ETH-to-token, token-to-ETH, and
    token-to-token swaps with configurable slippage protection.

    Args:
        user_address: The Ethereum address performing the swap
        private_key: Private key for signing transactions (64+ chars)
        token_in_address: Address of the token to swap from
        token_out_address: Address of the token to swap to
        amount_in: Amount of input token in wei (must be positive)
        dex_name: Name of the DEX to use (currently supports "syncswap")
        slippage_bps: Slippage tolerance in basis points (0-10000)
        config: Configuration dictionary containing network settings

    Returns:
        Tuple of (success: bool, message_or_tx_hash: str)

    Raises:
        ValueError: For invalid inputs
        ConnectionError: For RPC connection issues

    Example:
        >>> config = {
        ...     "networks": {
        ...         "zksync": {
        ...             "rpc_url": "https://mainnet.era.zksync.io",
        ...             "dex_router_address": (
        ...                 "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295"
        ...             )
        ...         }
        ...     },
        ...     "tokens": {
        ...         "WETH": {
        ...             "address": "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"
        ...         }
        ...     }
        ... }
        >>> success, tx_hash = swap_tokens(
        ...     "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87",
        ...     "0x" + "a" * 64,
        ...     "0x0000000000000000000000000000000000000000",
        ...     "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
        ...     1000000000000000000,
        ...     "syncswap",
        ...     50,
        ...     config
        ... )
    """
    try:
        # Input validation
        _validate_swap_inputs(
            user_address,
            private_key,
            token_in_address,
            token_out_address,
            amount_in,
            dex_name,
            slippage_bps,
            config,
        )

        logger.info(
            f"Swapping {amount_in} wei of {token_in_address} for "
            f"{token_out_address} on {dex_name} for {user_address}"
        )

        # Execute the swap based on DEX
        if dex_name.lower() == "syncswap":
            return _execute_syncswap_swap(
                user_address,
                private_key,
                token_in_address,
                token_out_address,
                amount_in,
                slippage_bps,
                config,
            )
        else:
            return False, f"Unsupported DEX: {dex_name}"

    except ValueError as e:
        logger.error(f"Validation error in swap_tokens: {e}")
        return False, f"Validation error: {str(e)}"
    except ConnectionError as e:
        logger.error(f"Connection error in swap_tokens: {e}")
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in swap_tokens: {e}")
        return False, f"Unexpected error: {str(e)}"


def _execute_syncswap_swap(
    user_address: str,
    private_key: str,
    token_in_address: str,
    token_out_address: str,
    amount_in: int,
    slippage_bps: int,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Execute token swap on SyncSwap DEX."""
    try:
        # Get L2 configuration
        l2_config = config["networks"]["zksync"]
        l2_rpc_url = l2_config["rpc_url"]
        router_address = l2_config.get("dex_router_address", SYNCSWAP_ROUTER_ADDRESS)

        # Initialize L2 Web3
        w3_l2 = _get_web3_instance(l2_rpc_url, "zkSync Era L2")

        # Get WETH address from config
        weth_address = (
            config.get("tokens", {})
            .get("WETH", {})
            .get("address", "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91")
        )

        # Determine swap path
        path = _determine_swap_path(token_in_address, token_out_address, weth_address)

        # Load router contract
        router_abi = _get_syncswap_router_abi()
        router_contract = w3_l2.eth.contract(address=router_address, abi=router_abi)

        # Handle token approval if needed (non-ETH input)
        if token_in_address.lower() != NATIVE_ETH_ADDRESS.lower():
            approval_success = _handle_token_approval(
                w3_l2,
                user_address,
                private_key,
                token_in_address,
                router_address,
                amount_in,
            )
            if not approval_success:
                return False, "Token approval failed"

        # Get expected output amount and calculate minimum
        try:
            amounts_out = router_contract.functions.getAmountsOut(
                amount_in, path
            ).call()
            expected_amount_out = amounts_out[-1]
        except Exception as e:
            logger.warning(f"Failed to get amounts out: {e}")
            return False, f"Failed to get expected output amount: {str(e)}"

        amount_out_min = expected_amount_out * (10000 - slippage_bps) // 10000

        # Calculate deadline (5 minutes from now)
        deadline = w3_l2.eth.get_block("latest")["timestamp"] + 300

        # Build and execute swap transaction
        return _build_and_send_swap_transaction(
            w3_l2,
            router_contract,
            user_address,
            private_key,
            token_in_address,
            amount_in,
            amount_out_min,
            path,
            deadline,
        )

    except Exception as e:
        logger.error(f"Error in SyncSwap swap execution: {e}")
        return False, f"SyncSwap swap error: {str(e)}"


def lend_borrow(
    user_address: str,
    private_key: str,
    action: str,
    token_address: str,
    amount: int,
    lending_protocol_name: str,
    config: Dict[str, Any],
    collateral_status: bool = None,
) -> Tuple[bool, str]:
    """
    Interact with a lending protocol on zkSync Era (EraLend).

    This function handles interactions with EraLend protocol, supporting
    supply, withdraw, borrow, repay, and set_collateral actions.

    Args:
        user_address: The Ethereum address performing the lending action
        private_key: Private key for signing transactions (64+ chars)
        action: Action to perform: "supply", "withdraw", "borrow", "repay",
                "set_collateral"
        token_address: Address of the underlying token (ETH as zero address)
        amount: Amount of token in wei (ignored for set_collateral)
        lending_protocol_name: Name of lending protocol (e.g., "eralend")
        config: Configuration dictionary containing network and protocol
                settings
        collateral_status: For set_collateral action, True to enable,
                          False to disable

    Returns:
        Tuple of (success: bool, message_or_tx_hash: str)

    Raises:
        ValueError: For invalid inputs
        ConnectionError: For RPC connection issues

    Example:
        >>> config = {
        ...     "networks": {
        ...         "zksync": {
        ...             "rpc_url": "https://mainnet.era.zksync.io",
        ...             "lending_protocols": {
        ...                 "eralend": {
        ...                     "lending_pool_manager": "0x...",
        ...                     "weth_gateway": "0x...",
        ...                     "supported_assets": {
        ...                         "ETH": {
        ...                             "address": (
        ...                                 "0x0000000000000000000000000000000000000000"  # noqa: E501
        ...                             ),
        ...                             "ztoken_address": "0x..."
        ...                         }
        ...                     }
        ...                 }
        ...             }
        ...         }
        ...     }
        ... }
        >>> success, tx_hash = lend_borrow(
        ...     "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87",
        ...     "0x" + "a" * 64,
        ...     "supply",
        ...     "0x0000000000000000000000000000000000000000",
        ...     1000000000000000000,
        ...     "eralend",
        ...     config
        ... )
    """
    try:
        # Input validation
        _validate_lend_borrow_inputs(
            user_address,
            private_key,
            action,
            token_address,
            amount,
            lending_protocol_name,
            config,
            collateral_status,
        )

        logger.info(
            f"Executing {action} for {amount} wei of {token_address} "
            f"on {lending_protocol_name} for {user_address}"
        )

        # Execute the lending action
        return _execute_lending_action(
            user_address,
            private_key,
            action,
            token_address,
            amount,
            lending_protocol_name,
            config,
            collateral_status,
        )

    except ValueError as e:
        logger.error(f"Validation error in lend_borrow: {e}")
        return False, f"Validation error: {str(e)}"
    except ConnectionError as e:
        logger.error(f"Connection error in lend_borrow: {e}")
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in lend_borrow: {e}")
        return False, f"Unexpected error: {str(e)}"


def _validate_lend_borrow_inputs(
    user_address: str,
    private_key: str,
    action: str,
    token_address: str,
    amount: int,
    lending_protocol_name: str,
    config: Dict[str, Any],
    collateral_status: bool = None,
) -> None:
    """
    Validate inputs for lend_borrow function.

    Args:
        user_address: User's Ethereum address
        private_key: Private key for signing transactions
        action: Lending action to perform
        token_address: Token contract address
        amount: Amount in wei
        lending_protocol_name: Name of lending protocol
        config: Configuration dictionary
        collateral_status: Collateral status for set_collateral action

    Raises:
        ValueError: If any input is invalid
    """
    if not user_address or not Web3.is_address(user_address):
        raise ValueError(f"Invalid user address: {user_address}")

    if not private_key or len(private_key) < 64:
        raise ValueError("Invalid private key provided")

    valid_actions = ["supply", "withdraw", "borrow", "repay", "set_collateral"]
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")

    if not Web3.is_address(token_address):
        raise ValueError(f"Invalid token_address: {token_address}")

    if action != "set_collateral" and amount <= 0:
        raise ValueError(f"Amount must be positive: {amount}")

    if action == "set_collateral" and collateral_status is None:
        raise ValueError("collateral_status required for set_collateral action")

    if not lending_protocol_name:
        raise ValueError("lending_protocol_name is required")

    if not config:
        raise ValueError("Configuration dictionary is required")

    # Validate config structure
    required_keys = ["networks"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")

    if "zksync" not in config["networks"]:
        raise ValueError("Missing zksync network configuration")

    zksync_config = config["networks"]["zksync"]
    if "lending_protocols" not in zksync_config:
        raise ValueError("Missing lending_protocols in zksync configuration")

    if lending_protocol_name not in zksync_config["lending_protocols"]:
        raise ValueError(f"Protocol {lending_protocol_name} not configured")


def _execute_lending_action(
    user_address: str,
    private_key: str,
    action: str,
    token_address: str,
    amount: int,
    lending_protocol_name: str,
    config: Dict[str, Any],
    collateral_status: bool = None,
) -> Tuple[bool, str]:
    """
    Execute the specified lending action.

    Args:
        user_address: User's address
        private_key: Private key for signing
        action: Lending action to perform
        token_address: Token contract address
        amount: Amount in wei
        lending_protocol_name: Name of lending protocol
        config: Configuration dictionary
        collateral_status: Collateral status for set_collateral

    Returns:
        Tuple of (success: bool, message_or_tx_hash: str)
    """
    try:
        # Get L2 configuration
        l2_config = config["networks"]["zksync"]
        l2_rpc_url = l2_config["rpc_url"]

        # Initialize L2 Web3
        w3_l2 = _get_web3_instance(l2_rpc_url, "zkSync Era L2")

        # Get protocol configuration
        protocol_config = l2_config["lending_protocols"][lending_protocol_name]

        # Route to specific action handler
        if action == "supply":
            return _execute_supply_action(
                w3_l2, user_address, private_key, token_address, amount, protocol_config
            )
        elif action == "withdraw":
            return _execute_withdraw_action(
                w3_l2, user_address, private_key, token_address, amount, protocol_config
            )
        elif action == "borrow":
            return _execute_borrow_action(
                w3_l2, user_address, private_key, token_address, amount, protocol_config
            )
        elif action == "repay":
            return _execute_repay_action(
                w3_l2, user_address, private_key, token_address, amount, protocol_config
            )
        elif action == "set_collateral":
            return _execute_set_collateral_action(
                w3_l2,
                user_address,
                private_key,
                token_address,
                collateral_status,
                protocol_config,
            )
        else:
            return False, f"Unsupported action: {action}"

    except Exception as e:
        logger.error(f"Error executing lending action {action}: {e}")
        return False, f"Lending action error: {str(e)}"


def _execute_supply_action(
    w3_l2: Web3,
    user_address: str,
    private_key: str,
    token_address: str,
    amount: int,
    protocol_config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Execute supply action on EraLend."""
    try:
        is_eth = token_address.lower() == NATIVE_ETH_ADDRESS.lower()

        if is_eth:
            # Use WETH Gateway for ETH deposits
            gateway_address = protocol_config.get("weth_gateway")
            if not gateway_address:
                return False, "WETH Gateway address not configured"

            gateway_abi = _get_eralend_weth_gateway_abi()
            gateway_contract = w3_l2.eth.contract(
                address=gateway_address, abi=gateway_abi
            )

            # Build depositETH transaction
            pool_address = protocol_config["lending_pool_manager"]
            referral_code = protocol_config.get("referral_code", 0)

            contract_function = gateway_contract.functions.depositETH(
                pool_address, user_address, referral_code
            )

            transaction_params = {
                "from": user_address,
                "value": amount,
                "gasPrice": w3_l2.eth.gas_price,
                "nonce": w3_l2.eth.get_transaction_count(user_address),
            }
        else:
            # ERC20 token supply
            # First approve the lending pool manager
            pool_address = protocol_config["lending_pool_manager"]
            approval_success = _handle_token_approval(
                w3_l2, user_address, private_key, token_address, pool_address, amount
            )
            if not approval_success:
                return False, "Token approval failed"

            # Call supply function on lending pool manager
            pool_abi = _get_eralend_lending_pool_abi()
            pool_contract = w3_l2.eth.contract(address=pool_address, abi=pool_abi)

            referral_code = protocol_config.get("referral_code", 0)
            contract_function = pool_contract.functions.supply(
                token_address, amount, user_address, referral_code
            )

            transaction_params = {
                "from": user_address,
                "gasPrice": w3_l2.eth.gas_price,
                "nonce": w3_l2.eth.get_transaction_count(user_address),
            }

        return _build_and_send_lending_transaction(
            w3_l2, contract_function, transaction_params, user_address, private_key
        )

    except Exception as e:
        logger.error(f"Error in supply action: {e}")
        return False, f"Supply action error: {str(e)}"


def _execute_withdraw_action(
    w3_l2: Web3,
    user_address: str,
    private_key: str,
    token_address: str,
    amount: int,
    protocol_config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Execute withdraw action on EraLend."""
    try:
        is_eth = token_address.lower() == NATIVE_ETH_ADDRESS.lower()
        pool_address = protocol_config["lending_pool_manager"]

        if is_eth:
            # Use WETH Gateway for ETH withdrawals
            gateway_address = protocol_config.get("weth_gateway")
            if not gateway_address:
                return False, "WETH Gateway address not configured"

            gateway_abi = _get_eralend_weth_gateway_abi()
            gateway_contract = w3_l2.eth.contract(
                address=gateway_address, abi=gateway_abi
            )

            contract_function = gateway_contract.functions.withdrawETH(
                pool_address, amount, user_address
            )
        else:
            # ERC20 token withdrawal
            pool_abi = _get_eralend_lending_pool_abi()
            pool_contract = w3_l2.eth.contract(address=pool_address, abi=pool_abi)

            contract_function = pool_contract.functions.withdraw(
                token_address, amount, user_address
            )

        transaction_params = {
            "from": user_address,
            "gasPrice": w3_l2.eth.gas_price,
            "nonce": w3_l2.eth.get_transaction_count(user_address),
        }

        return _build_and_send_lending_transaction(
            w3_l2, contract_function, transaction_params, user_address, private_key
        )

    except Exception as e:
        logger.error(f"Error in withdraw action: {e}")
        return False, f"Withdraw action error: {str(e)}"


def _execute_borrow_action(
    w3_l2: Web3,
    user_address: str,
    private_key: str,
    token_address: str,
    amount: int,
    protocol_config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Execute borrow action on EraLend."""
    try:
        is_eth = token_address.lower() == NATIVE_ETH_ADDRESS.lower()
        pool_address = protocol_config["lending_pool_manager"]

        if is_eth:
            # Use WETH Gateway for ETH borrowing
            gateway_address = protocol_config.get("weth_gateway")
            if not gateway_address:
                return False, "WETH Gateway address not configured"

            gateway_abi = _get_eralend_weth_gateway_abi()
            gateway_contract = w3_l2.eth.contract(
                address=gateway_address, abi=gateway_abi
            )

            interest_rate_mode = protocol_config.get("interest_rate_mode", 2)
            referral_code = protocol_config.get("referral_code", 0)

            contract_function = gateway_contract.functions.borrowETH(
                pool_address, amount, interest_rate_mode, referral_code
            )
        else:
            # ERC20 token borrowing
            pool_abi = _get_eralend_lending_pool_abi()
            pool_contract = w3_l2.eth.contract(address=pool_address, abi=pool_abi)

            interest_rate_mode = protocol_config.get("interest_rate_mode", 2)
            referral_code = protocol_config.get("referral_code", 0)

            contract_function = pool_contract.functions.borrow(
                token_address, amount, interest_rate_mode, referral_code, user_address
            )

        transaction_params = {
            "from": user_address,
            "gasPrice": w3_l2.eth.gas_price,
            "nonce": w3_l2.eth.get_transaction_count(user_address),
        }

        return _build_and_send_lending_transaction(
            w3_l2, contract_function, transaction_params, user_address, private_key
        )

    except Exception as e:
        logger.error(f"Error in borrow action: {e}")
        return False, f"Borrow action error: {str(e)}"


def _execute_repay_action(
    w3_l2: Web3,
    user_address: str,
    private_key: str,
    token_address: str,
    amount: int,
    protocol_config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Execute repay action on EraLend."""
    try:
        is_eth = token_address.lower() == NATIVE_ETH_ADDRESS.lower()
        pool_address = protocol_config["lending_pool_manager"]

        if is_eth:
            # Use WETH Gateway for ETH repayment
            gateway_address = protocol_config.get("weth_gateway")
            if not gateway_address:
                return False, "WETH Gateway address not configured"

            gateway_abi = _get_eralend_weth_gateway_abi()
            gateway_contract = w3_l2.eth.contract(
                address=gateway_address, abi=gateway_abi
            )

            interest_rate_mode = protocol_config.get("interest_rate_mode", 2)

            contract_function = gateway_contract.functions.repayETH(
                pool_address, amount, interest_rate_mode, user_address
            )

            transaction_params = {
                "from": user_address,
                "value": amount,
                "gasPrice": w3_l2.eth.gas_price,
                "nonce": w3_l2.eth.get_transaction_count(user_address),
            }
        else:
            # ERC20 token repayment
            # First approve the lending pool manager
            approval_success = _handle_token_approval(
                w3_l2, user_address, private_key, token_address, pool_address, amount
            )
            if not approval_success:
                return False, "Token approval failed"

            pool_abi = _get_eralend_lending_pool_abi()
            pool_contract = w3_l2.eth.contract(address=pool_address, abi=pool_abi)

            interest_rate_mode = protocol_config.get("interest_rate_mode", 2)

            contract_function = pool_contract.functions.repay(
                token_address, amount, interest_rate_mode, user_address
            )

            transaction_params = {
                "from": user_address,
                "gasPrice": w3_l2.eth.gas_price,
                "nonce": w3_l2.eth.get_transaction_count(user_address),
            }

        return _build_and_send_lending_transaction(
            w3_l2, contract_function, transaction_params, user_address, private_key
        )

    except Exception as e:
        logger.error(f"Error in repay action: {e}")
        return False, f"Repay action error: {str(e)}"


def _execute_set_collateral_action(
    w3_l2: Web3,
    user_address: str,
    private_key: str,
    token_address: str,
    collateral_status: bool,
    protocol_config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Execute set collateral action on EraLend."""
    try:
        pool_address = protocol_config["lending_pool_manager"]
        pool_abi = _get_eralend_lending_pool_abi()
        pool_contract = w3_l2.eth.contract(address=pool_address, abi=pool_abi)

        contract_function = pool_contract.functions.setUserUseReserveAsCollateral(
            token_address, collateral_status
        )

        transaction_params = {
            "from": user_address,
            "gasPrice": w3_l2.eth.gas_price,
            "nonce": w3_l2.eth.get_transaction_count(user_address),
        }

        return _build_and_send_lending_transaction(
            w3_l2, contract_function, transaction_params, user_address, private_key
        )

    except Exception as e:
        logger.error(f"Error in set collateral action: {e}")
        return False, f"Set collateral action error: {str(e)}"


def perform_random_activity(
    user_address: str, private_key: str, config: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Perform a randomized sequence of zkSync Era activities.

    This function orchestrates a randomized sequence of zkSync Era actions
    (bridge_eth, swap_tokens, lend_borrow) based on configuration. It simulates
    diverse, human-like on-chain activity for airdrop farming.

    Args:
        user_address: The Ethereum address performing random activities
        private_key: Private key for signing transactions (64+ chars)
        config: Configuration dictionary including random_activity section

    Returns:
        Tuple of (overall_success: bool, summary_message: str)

    Raises:
        ValueError: For invalid inputs or configuration
        ConnectionError: For RPC connection issues

    Example:
        >>> config = {
        ...     "networks": {"zksync": {
        ...         "rpc_url": "https://mainnet.era.zksync.io"}},
        ...     "tokens": {"ETH": {
        ...         "address": "0x0000000000000000000000000000000000000000"}},
        ...     "random_activity": {
        ...         "enabled": True,
        ...         "num_actions_range": [2, 4],
        ...         "action_weights": {"bridge_eth": 30, "swap_tokens": 50,
        ...                            "lend_borrow": 20}
        ...     }
        ... }
        >>> success, summary = perform_random_activity(
        ...     "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87",
        ...     "0x" + "a" * 64,
        ...     config
        ... )
    """
    try:
        logger.info(f"Starting random activity sequence for {user_address}")

        # Validate inputs and configuration
        if not _validate_random_activity_config(config):
            return False, "Invalid random_activity configuration"

        random_config = config["random_activity"]
        if not random_config.get("enabled", False):
            return True, "Random activity disabled in configuration"

        # Initialize state tracking
        state = _get_initial_onchain_state(user_address, config)
        if not state:
            return False, "Failed to fetch initial on-chain state"

        # Determine number of actions to perform
        num_actions_range = random_config["num_actions_range"]
        num_total_actions = random.randint(num_actions_range[0], num_actions_range[1])

        logger.info(f"Planning to execute {num_total_actions} random actions")

        # Execute action sequence
        return _execute_action_sequence(
            user_address, private_key, config, state, num_total_actions
        )

    except ValueError as e:
        logger.error(f"Validation error in perform_random_activity: {e}")
        return False, f"Validation error: {str(e)}"
    except ConnectionError as e:
        logger.error(f"Connection error in perform_random_activity: {e}")
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in perform_random_activity: {e}")
        return False, f"Unexpected error: {str(e)}"


def _handle_token_approval(
    w3_l2: Web3,
    user_address: str,
    private_key: str,
    token_address: str,
    spender_address: str,
    amount: int,
) -> bool:
    """
    Handle token approval for DEX router if needed.

    Args:
        w3_l2: Web3 instance for L2
        user_address: User's address
        private_key: Private key for signing
        token_address: Token contract address
        spender_address: Address to approve (router)
        amount: Amount to approve

    Returns:
        True if approval successful or not needed, False otherwise
    """
    try:
        # Load token contract
        erc20_abi = _get_erc20_abi()
        token_contract = w3_l2.eth.contract(address=token_address, abi=erc20_abi)

        # Check current allowance
        current_allowance = token_contract.functions.allowance(
            user_address, spender_address
        ).call()

        if current_allowance >= amount:
            logger.info(f"Sufficient allowance: {current_allowance}")
            return True

        # Need to approve
        logger.info(f"Approving {amount} tokens for {spender_address}")

        # Build approval transaction
        approve_function = token_contract.functions.approve(spender_address, amount)

        transaction_params = {
            "from": user_address,
            "gasPrice": w3_l2.eth.gas_price,
            "nonce": w3_l2.eth.get_transaction_count(user_address),
        }

        # Estimate gas
        try:
            estimated_gas = approve_function.estimate_gas(transaction_params)
            gas_limit = int(estimated_gas * 1.5)  # L2 gas multiplier
        except Exception:
            gas_limit = 100000  # Default gas limit

        transaction_params["gas"] = gas_limit

        # Build and sign transaction
        transaction = approve_function.build_transaction(transaction_params)
        account = Account.from_key(private_key)
        signed_txn = account.sign_transaction(transaction)

        # Send transaction
        tx_hash = w3_l2.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = w3_l2.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status == 1:
            logger.info(f"Token approval successful: {tx_hash.hex()}")
            return True
        else:
            logger.error(f"Token approval failed: {tx_hash.hex()}")
            return False

    except Exception as e:
        logger.error(f"Error in token approval: {e}")
        return False


def _build_and_send_swap_transaction(
    w3_l2: Web3,
    router_contract,
    user_address: str,
    private_key: str,
    token_in_address: str,
    amount_in: int,
    amount_out_min: int,
    path: List[str],
    deadline: int,
) -> Tuple[bool, str]:
    """
    Build and send the swap transaction.

    Args:
        w3_l2: Web3 instance for L2
        router_contract: Router contract instance
        user_address: User's address
        private_key: Private key for signing
        token_in_address: Input token address
        amount_in: Input amount in wei
        amount_out_min: Minimum output amount
        path: Swap path
        deadline: Transaction deadline

    Returns:
        Tuple of (success: bool, message_or_tx_hash: str)
    """
    try:
        # Determine if this is an ETH swap
        is_eth_input = token_in_address.lower() == NATIVE_ETH_ADDRESS.lower()

        # Build transaction based on input type
        if is_eth_input:
            # ETH to token swap
            contract_function = router_contract.functions.swapExactETHForTokens(
                amount_out_min, path, user_address, deadline
            )
            msg_value = amount_in
        else:
            # Token to token/ETH swap
            contract_function = router_contract.functions.swapExactTokensForTokens(
                amount_in, amount_out_min, path, user_address, deadline
            )
            msg_value = 0

        # Build transaction parameters
        transaction_params = {
            "from": user_address,
            "value": msg_value,
            "gasPrice": w3_l2.eth.gas_price,
            "nonce": w3_l2.eth.get_transaction_count(user_address),
        }

        # Estimate gas
        try:
            estimated_gas = contract_function.estimate_gas(transaction_params)
            gas_limit = int(estimated_gas * 1.5)  # L2 gas multiplier
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}, using default")
            gas_limit = 300000  # Default gas limit for swaps

        transaction_params["gas"] = gas_limit

        # Build transaction
        transaction = contract_function.build_transaction(transaction_params)

        # Sign and send transaction
        account = Account.from_key(private_key)
        signed_txn = account.sign_transaction(transaction)

        tx_hash = w3_l2.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        # Wait for transaction receipt
        receipt = w3_l2.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status == 1:
            logger.info(f"Swap transaction successful: {tx_hash_hex}")
            return True, tx_hash_hex
        else:
            logger.error(f"Swap transaction failed: {tx_hash_hex}")
            return False, f"Transaction failed: {tx_hash_hex}"

    except Exception as e:
        logger.error(f"Error in swap transaction: {e}")
        return False, f"Swap transaction error: {str(e)}"


def _build_and_send_lending_transaction(
    w3_l2: Web3,
    contract_function,
    transaction_params: Dict[str, Any],
    user_address: str,
    private_key: str,
) -> Tuple[bool, str]:
    """
    Build and send lending transaction.

    Args:
        w3_l2: Web3 instance for L2
        contract_function: Contract function to call
        transaction_params: Transaction parameters
        user_address: User's address
        private_key: Private key for signing

    Returns:
        Tuple of (success: bool, message_or_tx_hash: str)
    """
    try:
        # Estimate gas
        try:
            estimated_gas = contract_function.estimate_gas(transaction_params)
            gas_limit = int(estimated_gas * 1.5)  # L2 gas multiplier
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}, using default")
            gas_limit = 300000  # Default gas limit for lending operations

        transaction_params["gas"] = gas_limit

        # Build transaction
        transaction = contract_function.build_transaction(transaction_params)

        # Sign and send transaction
        account = Account.from_key(private_key)
        signed_txn = account.sign_transaction(transaction)

        tx_hash = w3_l2.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        # Wait for transaction receipt
        receipt = w3_l2.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status == 1:
            logger.info(f"Lending transaction successful: {tx_hash_hex}")
            return True, tx_hash_hex
        else:
            logger.error(f"Lending transaction failed: {tx_hash_hex}")
            return False, f"Transaction failed: {tx_hash_hex}"

    except Exception as e:
        logger.error(f"Error in lending transaction: {e}")
        return False, f"Lending transaction error: {str(e)}"


def _get_eralend_lending_pool_abi() -> List[Dict[str, Any]]:
    """Get minimal ABI for EraLend Lending Pool Manager contract."""
    return [
        {
            "inputs": [
                {"name": "asset", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "onBehalfOf", "type": "address"},
                {"name": "referralCode", "type": "uint16"},
            ],
            "name": "supply",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "asset", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "to", "type": "address"},
            ],
            "name": "withdraw",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "asset", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "interestRateMode", "type": "uint256"},
                {"name": "referralCode", "type": "uint16"},
                {"name": "onBehalfOf", "type": "address"},
            ],
            "name": "borrow",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "asset", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "rateMode", "type": "uint256"},
                {"name": "onBehalfOf", "type": "address"},
            ],
            "name": "repay",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "asset", "type": "address"},
                {"name": "useAsCollateral", "type": "bool"},
            ],
            "name": "setUserUseReserveAsCollateral",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]


def _get_eralend_weth_gateway_abi() -> List[Dict[str, Any]]:
    """Get minimal ABI for EraLend WETH Gateway contract."""
    return [
        {
            "inputs": [
                {"name": "lendingPool", "type": "address"},
                {"name": "onBehalfOf", "type": "address"},
                {"name": "referralCode", "type": "uint16"},
            ],
            "name": "depositETH",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "lendingPool", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "to", "type": "address"},
            ],
            "name": "withdrawETH",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "lendingPool", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "interestRateMode", "type": "uint256"},
                {"name": "referralCode", "type": "uint16"},
            ],
            "name": "borrowETH",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "lendingPool", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "rateMode", "type": "uint256"},
                {"name": "onBehalfOf", "type": "address"},
            ],
            "name": "repayETH",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "payable",
            "type": "function",
        },
    ]


def _validate_random_activity_config(config: Dict[str, Any]) -> bool:
    """
    Validate random_activity configuration structure.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        if "random_activity" not in config:
            logger.error("Missing random_activity section in config")
            return False

        random_config = config["random_activity"]
        required_keys = ["enabled", "num_actions_range", "action_weights"]

        for key in required_keys:
            if key not in random_config:
                logger.error(f"Missing required key in random_activity: {key}")
                return False

        # Validate num_actions_range
        num_range = random_config["num_actions_range"]
        if (
            not isinstance(num_range, list)
            or len(num_range) != 2
            or num_range[0] < 0
            or num_range[1] < num_range[0]
        ):
            logger.error("Invalid num_actions_range format")
            return False

        # Validate action_weights
        weights = random_config["action_weights"]
        if not isinstance(weights, dict) or not weights:
            logger.error("Invalid action_weights format")
            return False

        return True

    except Exception as e:
        logger.error(f"Error validating random_activity config: {e}")
        return False


def _get_initial_onchain_state(
    user_address: str, config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Fetch initial L2 balances and lending positions.

    Args:
        user_address: User's Ethereum address
        config: Configuration dictionary

    Returns:
        Dictionary containing initial state or None if failed
    """
    try:
        # Get L2 configuration
        l2_config = config["networks"]["zksync"]
        l2_rpc_url = l2_config["rpc_url"]

        # Initialize L2 Web3
        w3_l2 = _get_web3_instance(l2_rpc_url, "zkSync Era L2")

        # Initialize state tracking
        state = {"l2_balances": {}, "eralend_positions": {}}

        # Get tokens to track from config
        tokens_to_track = (
            config.get("random_activity", {})
            .get("initial_state_fetch", {})
            .get("tokens_to_track_balance", ["ETH"])
        )

        # Fetch L2 balances
        for token_symbol in tokens_to_track:
            try:
                if token_symbol == "ETH":
                    # Get native ETH balance
                    balance_wei = w3_l2.eth.get_balance(user_address)
                    balance_ether = Decimal(str(balance_wei)) / Decimal(10**18)
                else:
                    # Get ERC20 token balance
                    token_config = config.get("tokens", {}).get(token_symbol)
                    if token_config:
                        token_address = token_config["address"]
                        decimals = token_config.get("decimals", 18)

                        erc20_abi = _get_erc20_abi()
                        token_contract = w3_l2.eth.contract(
                            address=token_address, abi=erc20_abi
                        )
                        balance_wei = token_contract.functions.balanceOf(
                            user_address
                        ).call()
                        balance_ether = Decimal(str(balance_wei)) / Decimal(
                            10**decimals
                        )
                    else:
                        balance_ether = Decimal("0")

                state["l2_balances"][token_symbol] = balance_ether
                logger.info(f"L2 {token_symbol} balance: {balance_ether}")

            except Exception as e:
                logger.warning(f"Failed to fetch {token_symbol} balance: {e}")
                state["l2_balances"][token_symbol] = Decimal("0")

        # Initialize lending positions (simplified for now)
        for token_symbol in tokens_to_track:
            state["eralend_positions"][token_symbol] = {
                "supplied": Decimal("0"),
                "borrowed": Decimal("0"),
                "is_collateral": False,
            }

        return state

    except Exception as e:
        logger.error(f"Error fetching initial on-chain state: {e}")
        return None


def _execute_action_sequence(
    user_address: str,
    private_key: str,
    config: Dict[str, Any],
    state: Dict[str, Any],
    num_total_actions: int,
) -> Tuple[bool, str]:
    """
    Execute the sequence of random actions.

    Args:
        user_address: User's Ethereum address
        private_key: Private key for signing transactions
        config: Configuration dictionary
        state: Current on-chain state
        num_total_actions: Number of actions to perform

    Returns:
        Tuple of (overall_success: bool, summary_message: str)
    """
    random_config = config["random_activity"]
    successful_actions_count = 0
    executed_actions_log = []
    stop_on_failure = random_config.get("stop_on_first_failure", False)

    for action_index in range(num_total_actions):
        logger.info(f"Executing action {action_index + 1}/{num_total_actions}")

        # Select and execute action
        action_result = _select_and_execute_action(
            user_address, private_key, config, state
        )

        executed_actions_log.append(action_result)

        if action_result["success"]:
            successful_actions_count += 1
            # Update state based on successful action
            _update_internal_state(state, action_result)
        else:
            logger.warning(f"Action failed: {action_result['error']}")
            if stop_on_failure:
                logger.info("Stopping sequence due to failure")
                break

    # Compile summary
    summary_parts = []
    for i, result in enumerate(executed_actions_log):
        status = "SUCCESS" if result["success"] else "FAILED"
        summary_parts.append(f"Action {i+1}: {result['action_type']} - {status}")

    summary_message = (
        f"Executed {len(executed_actions_log)} actions, "
        f"{successful_actions_count} successful. "
        f"Details: {'; '.join(summary_parts)}"
    )

    overall_success = successful_actions_count > 0
    return overall_success, summary_message


def _select_and_execute_action(
    user_address: str, private_key: str, config: Dict[str, Any], state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Select and execute a single random action.

    Args:
        user_address: User's Ethereum address
        private_key: Private key for signing transactions
        config: Configuration dictionary
        state: Current on-chain state

    Returns:
        Dictionary containing action result details
    """
    random_config = config["random_activity"]
    max_retries = random_config.get("max_action_selection_retries", 3)

    for retry in range(max_retries):
        try:
            # Select action type
            action_type = _select_action_type(random_config["action_weights"])
            logger.info(f"Selected action type: {action_type}")

            # Generate parameters for the action
            params = _generate_action_parameters(action_type, config, state)

            if not params:
                logger.warning("Failed to generate parameters for %s", action_type)
                continue

            # Check feasibility
            if not _check_action_feasibility(action_type, params, state):
                logger.warning(f"Action {action_type} not feasible, retrying")
                continue

            # Execute the action
            return _execute_single_action(
                action_type, user_address, private_key, params, config
            )

        except Exception as e:
            logger.warning("Action selection/execution failed (retry %d): %s", retry, e)

    # All retries failed
    return {
        "success": False,
        "action_type": "unknown",
        "error": "Failed to select feasible action after retries",
        "tx_hash": None,
    }


def _select_action_type(action_weights: Dict[str, int]) -> str:
    """
    Select action type based on weights.

    Args:
        action_weights: Dictionary of action types to weights

    Returns:
        Selected action type
    """
    actions = list(action_weights.keys())
    weights = list(action_weights.values())
    return random.choices(actions, weights=weights, k=1)[0]


def _generate_action_parameters(
    action_type: str, config: Dict[str, Any], state: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Generate randomized parameters for the selected action.

    Args:
        action_type: Type of action to generate parameters for
        config: Configuration dictionary
        state: Current on-chain state

    Returns:
        Dictionary of parameters or None if generation failed
    """
    try:
        random_config = config["random_activity"]

        if action_type == "bridge_eth":
            return _randomize_bridge_parameters(
                random_config.get("bridge_eth", {}), state
            )
        elif action_type == "swap_tokens":
            return _randomize_swap_parameters(
                random_config.get("swap_tokens", {}), state, config
            )
        elif action_type == "lend_borrow":
            return _randomize_lend_borrow_parameters(
                random_config.get("lend_borrow", {}), state, config
            )
        else:
            logger.error(f"Unknown action type: {action_type}")
            return None

    except Exception as e:
        logger.error(f"Error generating parameters for {action_type}: {e}")
        return None


def _randomize_bridge_parameters(
    bridge_config: Dict[str, Any], state: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate randomized parameters for bridge_eth action."""
    amount_range = bridge_config.get("amount_range_eth", [0.005, 0.01])
    amount_eth = random.uniform(amount_range[0], amount_range[1])

    probability_to_l2 = bridge_config.get("probability_to_l2", 0.6)
    to_l2 = random.random() < probability_to_l2

    return {"amount_eth": Decimal(str(amount_eth)), "to_l2": to_l2}


def _randomize_swap_parameters(
    swap_config: Dict[str, Any], state: Dict[str, Any], config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Generate randomized parameters for swap_tokens action."""
    token_pairs = swap_config.get("token_pairs", [])
    if not token_pairs:
        return None

    # Select random token pair
    token_in_symbol, token_out_symbol = random.choice(token_pairs)

    # Get token addresses
    tokens_config = config.get("tokens", {})
    token_in_config = tokens_config.get(token_in_symbol)
    token_out_config = tokens_config.get(token_out_symbol)

    if not token_in_config or not token_out_config:
        return None

    token_in_address = token_in_config["address"]
    token_out_address = token_out_config["address"]

    # Calculate amount based on balance percentage
    balance = state["l2_balances"].get(token_in_symbol, Decimal("0"))
    if balance <= 0:
        return None

    percentage_range = swap_config.get("amount_in_percentage_range", [0.1, 0.25])
    percentage = random.uniform(percentage_range[0], percentage_range[1])
    amount_ether = Decimal(str(balance)) * Decimal(str(percentage))

    # Convert to wei
    decimals = token_in_config.get("decimals", 18)
    amount_in = int(amount_ether * Decimal(10**decimals))

    # Random slippage
    slippage_range = swap_config.get("slippage_bps_range", [30, 70])
    slippage_bps = random.randint(slippage_range[0], slippage_range[1])

    return {
        "token_in_address": token_in_address,
        "token_out_address": token_out_address,
        "amount_in": amount_in,
        "dex_name": "syncswap",
        "slippage_bps": slippage_bps,
    }


def _randomize_lend_borrow_parameters(
    lend_config: Dict[str, Any], state: Dict[str, Any], config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Generate randomized parameters for lend_borrow action."""
    sub_action_weights = lend_config.get("sub_action_weights", {})
    if not sub_action_weights:
        return None

    # Select sub-action
    action = _select_action_type(sub_action_weights)

    # Select token
    supported_tokens = lend_config.get("supported_tokens", ["ETH"])
    token_symbol = random.choice(supported_tokens)

    tokens_config = config.get("tokens", {})
    token_config = tokens_config.get(token_symbol)
    if not token_config:
        return None

    token_address = token_config["address"]

    # Generate amount based on action type
    amount = 0
    collateral_status = None

    if action == "supply":
        balance = state["l2_balances"].get(token_symbol, Decimal("0"))
        if balance > 0:
            percentage_range = lend_config.get(
                "supply_amount_percentage_range", [0.15, 0.5]
            )
            percentage = random.uniform(percentage_range[0], percentage_range[1])
            amount_ether = balance * Decimal(str(percentage))
            decimals = token_config.get("decimals", 18)
            amount = int(amount_ether * Decimal(10**decimals))

    elif action == "set_collateral":
        enable_probability = lend_config.get("set_collateral_enable_probability", 0.75)
        collateral_status = random.random() < enable_probability
        amount = 0  # Not used for set_collateral

    # For other actions (withdraw, borrow, repay), we'd need more complex logic
    # based on existing positions, but for now we'll use simplified amounts

    return {
        "action": action,
        "token_address": token_address,
        "amount": amount,
        "lending_protocol_name": "eralend",
        "collateral_status": collateral_status,
    }


def _check_action_feasibility(
    action_type: str, params: Dict[str, Any], state: Dict[str, Any]
) -> bool:
    """
    Check if the action with given parameters is feasible.

    Args:
        action_type: Type of action
        params: Action parameters
        state: Current on-chain state

    Returns:
        True if action is feasible, False otherwise
    """
    try:
        if action_type == "bridge_eth":
            # Check if we have enough ETH for the bridge amount
            amount_eth = params["amount_eth"]
            eth_balance = state["l2_balances"].get("ETH", Decimal("0"))

            if params["to_l2"]:
                # L1->L2: would need L1 balance check (simplified)
                return amount_eth > 0
            else:
                # L2->L1: check L2 balance
                return eth_balance >= amount_eth

        elif action_type == "swap_tokens":
            # Check if we have enough input token
            amount_in = params["amount_in"]
            if amount_in <= 0:
                return False
            # Additional checks could be added for liquidity, etc.
            return True

        elif action_type == "lend_borrow":
            # Basic feasibility check
            action = params["action"]
            amount = params["amount"]

            if action in ["supply", "borrow"] and amount <= 0:
                return False

            return True

        return False

    except Exception as e:
        logger.warning(f"Error checking feasibility for {action_type}: {e}")
        return False


def _execute_single_action(
    action_type: str,
    user_address: str,
    private_key: str,
    params: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a single action with the given parameters.

    Args:
        action_type: Type of action to execute
        user_address: User's Ethereum address
        private_key: Private key for signing transactions
        params: Action parameters
        config: Configuration dictionary

    Returns:
        Dictionary containing execution result
    """
    try:
        if action_type == "bridge_eth":
            success, result = bridge_eth(
                user_address, private_key, params["amount_eth"], params["to_l2"], config
            )
        elif action_type == "swap_tokens":
            success, result = swap_tokens(
                user_address,
                private_key,
                params["token_in_address"],
                params["token_out_address"],
                params["amount_in"],
                params["dex_name"],
                params["slippage_bps"],
                config,
            )
        elif action_type == "lend_borrow":
            success, result = lend_borrow(
                user_address,
                private_key,
                params["action"],
                params["token_address"],
                params["amount"],
                params["lending_protocol_name"],
                config,
                params.get("collateral_status"),
            )
        else:
            return {
                "success": False,
                "action_type": action_type,
                "error": f"Unknown action type: {action_type}",
                "tx_hash": None,
            }

        return {
            "success": success,
            "action_type": action_type,
            "error": None if success else result,
            "tx_hash": result if success else None,
            "params": params,
        }

    except Exception as e:
        logger.error(f"Error executing {action_type}: {e}")
        return {
            "success": False,
            "action_type": action_type,
            "error": str(e),
            "tx_hash": None,
        }


def _update_internal_state(
    state: Dict[str, Any], action_result: Dict[str, Any]
) -> None:
    """
    Update internal state based on successful action execution.

    Args:
        state: Current state dictionary to update
        action_result: Result of the executed action
    """
    try:
        action_type = action_result["action_type"]
        params = action_result.get("params", {})

        if action_type == "bridge_eth":
            amount_eth = params.get("amount_eth", Decimal("0"))
            to_l2 = params.get("to_l2", True)

            if to_l2:
                # L1->L2: increase L2 ETH balance
                current_balance = state["l2_balances"].get("ETH", Decimal("0"))
                state["l2_balances"]["ETH"] = current_balance + amount_eth
            else:
                # L2->L1: decrease L2 ETH balance
                current_balance = state["l2_balances"].get("ETH", Decimal("0"))
                state["l2_balances"]["ETH"] = max(
                    Decimal("0"), current_balance - amount_eth
                )

        elif action_type == "swap_tokens":
            # For swaps, we'd need to update both token balances
            # This is simplified - in reality we'd need the actual output
            pass

        elif action_type == "lend_borrow":
            # Update lending positions based on the action
            # This is simplified - in reality we'd need more detailed tracking
            pass

        logger.debug(f"Updated state after {action_type}")

    except Exception as e:
        logger.warning(f"Error updating state after {action_type}: {e}")
