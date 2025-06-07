# airdrops/src/airdrops/protocols/layerzero/layerzero.py
"""
LayerZero/Stargate Protocol Module.

This module provides functionalities to interact with the LayerZero messaging
protocol and Stargate bridge for cross-chain asset transfers.
"""

from decimal import Decimal
from typing import Tuple, Dict, Any, List, Optional
import logging
import random

from web3 import Web3
from web3.contract import Contract
from web3.types import TxReceipt, Wei
from eth_typing import ChecksumAddress
from eth_typing.encoding import HexStr

# Configure logging for this module
logger = logging.getLogger(__name__)

# Standard ERC20 ABI (minimal required functions)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "remaining", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "success", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

# Stargate Router ABI (minimal required functions)
STARGATE_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint16", "name": "_dstChainId", "type": "uint16"},
            {"internalType": "uint8", "name": "_functionType", "type": "uint8"},
            {"internalType": "bytes", "name": "_toAddress", "type": "bytes"},
            {
                "internalType": "bytes",
                "name": "_transferAndCallPayload",
                "type": "bytes",
            },
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "dstGasForCall",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "dstNativeAmount",
                        "type": "uint256",
                    },
                    {"internalType": "bytes", "name": "dstNativeAddr", "type": "bytes"},
                ],
                "internalType": "struct IStargateRouter.lzTxObj",
                "name": "_lzTxParams",
                "type": "tuple",
            },
        ],
        "name": "quoteLayerZeroFee",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "_dstChainId", "type": "uint16"},
            {"internalType": "uint256", "name": "_srcPoolId", "type": "uint256"},
            {"internalType": "uint256", "name": "_dstPoolId", "type": "uint256"},
            {
                "internalType": "address payable",
                "name": "_refundAddress",
                "type": "address",
            },
            {"internalType": "uint256", "name": "_amountLD", "type": "uint256"},
            {"internalType": "uint256", "name": "_minAmountLD", "type": "uint256"},
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "dstGasForCall",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "dstNativeAmount",
                        "type": "uint256",
                    },
                    {"internalType": "bytes", "name": "dstNativeAddr", "type": "bytes"},
                ],
                "internalType": "struct IStargateRouter.lzTxObj",
                "name": "_lzTxParams",
                "type": "tuple",
            },
            {"internalType": "bytes", "name": "_to", "type": "bytes"},
            {"internalType": "bytes", "name": "_payload", "type": "bytes"},
        ],
        "name": "swap",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
]

__all__ = ["bridge", "perform_random_bridge"]


def _get_web3_provider(rpc_url: str) -> Web3:
    """
    Create a Web3 provider instance.

    Args:
        rpc_url: RPC endpoint URL for the blockchain.

    Returns:
        Configured Web3 instance.

    Raises:
        ValueError: If RPC URL is invalid or connection fails.
    """
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise ValueError(f"Failed to connect to RPC: {rpc_url}")
        return w3
    except Exception as e:
        raise ValueError(f"Error creating Web3 provider: {e}") from e


def _get_contract(  # noqa: E501
    w3: Web3, address: ChecksumAddress, abi: List[Dict[str, Any]]
) -> Contract:
    """
    Get a contract instance.

    Args:
        w3: Web3 instance.
        address: Contract address.
        abi: Contract ABI.

    Returns:
        Contract instance.
    """
    return w3.eth.contract(address=address, abi=abi)


def _check_or_approve_token(
    w3: Web3,
    token_address: ChecksumAddress,
    user_address: ChecksumAddress,
    spender_address: ChecksumAddress,
    amount_wei: int,
    private_key: str,
    gas_settings: Dict[str, Any],
) -> bool:
    """
    Check token allowance and approve if necessary.

    Args:
        w3: Web3 instance.
        token_address: ERC20 token contract address.
        user_address: User's wallet address.
        spender_address: Spender address (Stargate Router).
        amount_wei: Amount in wei to approve.
        private_key: User's private key.
        gas_settings: Gas configuration.

    Returns:
        True if approval successful or not needed, False otherwise.
    """
    try:
        token_contract = _get_contract(w3, token_address, ERC20_ABI)

        # Check current allowance
        current_allowance = token_contract.functions.allowance(
            Web3.to_checksum_address(user_address),  # noqa: E501
            Web3.to_checksum_address(spender_address),
        ).call()

        if current_allowance >= amount_wei:
            logger.info(  # noqa: E501
                f"Sufficient allowance: {current_allowance} >= {amount_wei}"
            )
            return True

        logger.info(f"Approving token spend: {amount_wei}")

        # Build approval transaction
        approve_tx = token_contract.functions.approve(
            Web3.to_checksum_address(spender_address), amount_wei
        ).build_transaction(
            {
                "from": Web3.to_checksum_address(user_address),
                "nonce": w3.eth.get_transaction_count(
                    Web3.to_checksum_address(user_address)  # noqa: E501
                ),
                "gas": gas_settings.get("gas_limit", 100000),
                "gasPrice": w3.to_wei(
                    gas_settings.get("gas_price_gwei", 20), "gwei"  # noqa: E501
                ),
            }
        )

        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(approve_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for receipt
        receipt: TxReceipt = w3.eth.wait_for_transaction_receipt(
            tx_hash, timeout=gas_settings.get("transaction_timeout_seconds", 300)
        )

        if receipt["status"] == 1:
            logger.info(f"Token approval successful: {HexStr(tx_hash.hex())}")
            return True
        else:
            logger.error(f"Token approval failed: {HexStr(tx_hash.hex())}")
            return False

    except Exception as e:
        logger.error(f"Error in token approval: {e}")
        return False


def _estimate_lz_fee(
    router_contract: Contract,
    destination_lz_chain_id: int,
    user_address: ChecksumAddress,
) -> int:
    """
    Estimate LayerZero messaging fee.

    Args:
        router_contract: Stargate Router contract instance.
        destination_lz_chain_id: LayerZero chain ID for destination.
        user_address: User's wallet address.

    Returns:
        Native fee amount in wei.
    """
    try:
        user_address_bytes = Web3.to_bytes(hexstr=HexStr(user_address))
        lz_tx_params = (0, 0, "0x0000000000000000000000000000000000000001")

        native_fee, zro_fee = router_contract.functions.quoteLayerZeroFee(
            destination_lz_chain_id,
            1,  # function type for swap
            user_address_bytes,
            b"",  # empty payload
            lz_tx_params,
        ).call()

        logger.info(f"LayerZero fee estimate: {native_fee} wei")
        return native_fee  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(f"Error estimating LayerZero fee: {e}")
        raise ValueError(f"Failed to estimate LayerZero fee: {e}") from e


def bridge(
    source_chain_id: int,
    destination_chain_id: int,
    source_token_symbol: str,
    amount_in_source_token_units: Decimal,
    user_address: ChecksumAddress,
    slippage_bps: int,
    config: Dict[str, Any],
    private_key: str,
) -> Tuple[bool, str]:
    """
    Bridge assets from source to destination chain via Stargate.

    Args:
        source_chain_id: Network ID of the source chain (e.g., 1 for Ethereum).
        destination_chain_id: Network ID of the destination chain.
        source_token_symbol: Symbol of the token to bridge (e.g., "USDC").
        amount_in_source_token_units: Amount of source token to bridge.
        user_address: EOA initiating the bridge.
        slippage_bps: Maximum acceptable slippage in basis points.
        config: LayerZero module configuration dictionary.
        private_key: Private key for the user_address to sign transactions.

    Returns:
        Tuple containing:
            - bool: True if bridge transaction was successfully submitted.
            - str: Transaction hash if successful, or error message if failed.

    Example:
        >>> config = {
        ...     "layerzero": {
        ...         "chains": {
        ...             1: {"rpc_url": "https://eth.llamarpc.com", ...},
        ...             42161: {"rpc_url": "https://arb1.arbitrum.io/rpc", ...}
        ...         },
        ...         "tokens": {"USDC": {1: {...}, 42161: {...}}}
        ...     }
        ... }
        >>> success, result = bridge(1, 42161, "USDC", Decimal("100"),
        ...                          "0x123...", 50, config, "0xprivkey...")
        >>> print(f"Success: {success}, Result: {result}")
    """
    try:
        logger.info(
            f"Starting bridge: {amount_in_source_token_units} "
            f"{source_token_symbol} "
            f"from chain {source_chain_id} to {destination_chain_id}"
        )

        # Validate configuration
        lz_config = config.get("layerzero", {})
        chains_config = lz_config.get("chains", {})
        tokens_config = lz_config.get("tokens", {})
        gas_settings = lz_config.get("gas_settings", {})

        if source_chain_id not in chains_config:
            return False, f"Source chain {source_chain_id} not configured"

        if destination_chain_id not in chains_config:
            return (False, f"Destination chain {destination_chain_id} not configured")

        if source_token_symbol not in tokens_config:
            return False, f"Token {source_token_symbol} not configured"

        source_chain_config = chains_config[source_chain_id]
        dest_chain_config = chains_config[destination_chain_id]

        if source_chain_id not in tokens_config[source_token_symbol]:
            return (
                False,
                f"Token {source_token_symbol} not configured for " f"source chain",
            )

        if destination_chain_id not in tokens_config[source_token_symbol]:
            return (
                False,
                f"Token {source_token_symbol} not configured for " f"destination chain",
            )

        source_token_config = tokens_config[source_token_symbol][source_chain_id]
        dest_token_config = tokens_config[source_token_symbol][destination_chain_id]

        # Initialize Web3 for source chain
        w3 = _get_web3_provider(source_chain_config["rpc_url"])

        # Convert amount to wei
        token_decimals = source_token_config["decimals"]
        amount_wei = int(amount_in_source_token_units * (10**token_decimals))

        # Calculate minimum amount after slippage
        min_amount_wei = amount_wei * (10000 - slippage_bps) // 10000

        # Get Stargate Router contract
        router_address = source_chain_config["stargate_router_address"]
        router_contract = _get_contract(w3, router_address, STARGATE_ROUTER_ABI)

        # Handle token approval for non-native tokens
        if source_token_config["address"] != "NATIVE":
            approval_success = _check_or_approve_token(
                w3,
                Web3.to_checksum_address(source_token_config["address"]),
                user_address,  # Already ChecksumAddress from signature
                Web3.to_checksum_address(router_address),
                amount_wei,
                private_key,
                gas_settings,  # noqa: E261
            )
            if not approval_success:
                return False, "Token approval failed"

        # Estimate LayerZero fee
        dest_lz_chain_id = dest_chain_config["layerzero_chain_id"]
        native_fee = _estimate_lz_fee(
            router_contract,  # noqa: E501
            dest_lz_chain_id,
            user_address,  # Already ChecksumAddress
        )

        # Build swap transaction
        user_address_bytes = Web3.to_bytes(hexstr=HexStr(user_address))  # noqa: E501
        lz_tx_params = (0, 0, user_address_bytes)

        swap_tx = router_contract.functions.swap(
            dest_lz_chain_id,
            source_token_config["stargate_pool_id"],
            dest_token_config["stargate_pool_id"],
            Web3.to_checksum_address(user_address),
            amount_wei,
            min_amount_wei,
            lz_tx_params,
            user_address_bytes,
            b"",  # empty payload
        ).build_transaction(
            {
                "from": Web3.to_checksum_address(user_address),
                "value": Wei(native_fee),
                "nonce": w3.eth.get_transaction_count(
                    Web3.to_checksum_address(user_address)  # noqa: E501
                ),
                "gas": gas_settings.get("gas_limit", 500000),
                "gasPrice": w3.to_wei(
                    gas_settings.get("gas_price_gwei", 20), "gwei"  # noqa: E501
                ),
            }
        )

        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(swap_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for transaction receipt
        receipt: TxReceipt = w3.eth.wait_for_transaction_receipt(
            tx_hash, timeout=gas_settings.get("transaction_timeout_seconds", 300)
        )

        if receipt["status"] == 1:
            tx_hash_hex = HexStr(tx_hash.hex())
            logger.info(f"Bridge transaction successful: {tx_hash_hex}")
            return True, tx_hash_hex
        else:
            logger.error(f"Bridge transaction failed: {HexStr(tx_hash.hex())}")
            return False, "Transaction failed on source chain"

    except Exception as e:
        error_msg = f"Bridge operation failed: {e}"
        logger.error(error_msg)
        return False, error_msg


def perform_random_bridge(
    user_address: ChecksumAddress, config: Dict[str, Any], private_key: str
) -> Tuple[bool, str]:
    """
    Perform a randomized bridge transaction based on configuration.

    This function selects random parameters (chains, token, amount, slippage)
    based on the provided strategy in the configuration and then calls the
    `bridge` function to execute the transaction.

    Args:
        user_address: User's wallet address.
        config: LayerZero module configuration. Expected to contain
            `layerzero.perform_random_bridge_settings`.
        private_key: Private key for the user_address.

    Returns:
        Tuple containing:
            - bool: True if the bridge attempt was successfully initiated via
                    the underlying `bridge` call.
            - str: Descriptive message including the action taken and
                   transaction hash if successful, or an error message if
                   failed.

    Raises:
        ValueError: If critical configuration for random bridging is missing
                    or invalid.

    Notes:
        - Amount Selection: The current implementation selects a USD amount
          from the configured range (`amount_usd_min`, `amount_usd_max`)
          and converts it to token units assuming a **placeholder price of
          1 USD per token**. For accurate USD-based amounts, a proper price
          oracle integration is required.
        - Balance Checking: This function currently does not perform explicit
          pre-bridge balance checks for the selected token or native gas
          token. It relies on the underlying `bridge` call or RPC node to
          handle insufficient balance errors.
          `min_source_balance_usd_threshold` is evaluated using the
          placeholder $1 price.

    Example:
        >>> mock_config = {
        ...     "layerzero": {
        ...         "chains": {
        ...             1: {"name": "ethereum", "layerzero_chain_id": 101,
        ...                 ...},
        ...             42161: {"name": "arbitrum", "layerzero_chain_id": 110,
        ...                     ...}
        ...         },
        ...         "tokens": {
        ...             "USDC": {
        ...                 1: {"address": "0x...", "decimals": 6, ...},
        ...                 42161: {"address": "0x...", "decimals": 6, ...}
        ...             }
        ...         },
        ...         "perform_random_bridge_settings": {
        ...             "enabled_chains": ["ethereum", "arbitrum"],
        ...             "enabled_tokens": ["USDC"],
        ...             "chain_weights": {"ethereum": 50, "arbitrum": 50},
        ...             "token_weights": {"USDC": 100},
        ...             "amount_usd_min": 10.0,
        ...             "amount_usd_max": 50.0,
        ...             "slippage_bps_min": 10,
        ...             "slippage_bps_max": 50,
        ...             "min_source_balance_usd_threshold": 5.0
        ...         },
        ...         # ... other necessary bridge config ...
        ...     }
        ... }
        >>> # This is a conceptual example; actual call requires mocks for
        >>> # bridge()
        >>> # success, message = perform_random_bridge("0x123...",
        >>> #                                          mock_config, "0xkey")
        >>> # print(f"Result: {message}")
    """
    logger.info(f"Attempting to perform a random bridge for {user_address}.")

    lz_config = config.get("layerzero", {})
    settings = lz_config.get("perform_random_bridge_settings")
    if not settings:
        return False, "perform_random_bridge_settings not found in config"

    chains_config = lz_config.get("chains", {})
    tokens_config = lz_config.get("tokens", {})

    # Validate essential settings
    # Validate essential settings
    required_settings = [
        "enabled_chains",
        "enabled_tokens",
        "chain_weights",
        "token_weights",
        "amount_usd_min",
        "amount_usd_max",
    ]
    for req_setting in required_settings:
        if req_setting not in settings:
            return False, (
                f"Missing '{req_setting}' in " f"perform_random_bridge_settings"
            )
    if not settings["enabled_chains"] or not settings["enabled_tokens"]:
        return False, "enabled_chains or enabled_tokens cannot be empty."

    try:
        # 1. Select Source and Destination Chains
        enabled_chain_names = settings["enabled_chains"]
        chain_weights = [
            settings["chain_weights"].get(name, 0) for name in enabled_chain_names
        ]

        if sum(chain_weights) == 0 and len(enabled_chain_names) > 0:
            # Handle if all weights are zero
            chain_weights = [1] * len(enabled_chain_names)

        if len(enabled_chain_names) < 2:
            return False, ("At least two enabled_chains are required " "for bridging.")

        source_chain_name = random.choices(
            enabled_chain_names, weights=chain_weights, k=1
        )[0]

        # Ensure destination chain is different from source chain
        possible_dest_chains = [
            ch for ch in enabled_chain_names if ch != source_chain_name
        ]
        if not possible_dest_chains:
            return False, (
                "Could not select a destination chain different " "from the source."
            )
        dest_chain_weights = [
            settings["chain_weights"].get(name, 0) for name in possible_dest_chains
        ]
        if sum(dest_chain_weights) == 0 and len(possible_dest_chains) > 0:
            dest_chain_weights = [1] * len(possible_dest_chains)

        destination_chain_name = random.choices(
            possible_dest_chains, weights=dest_chain_weights, k=1
        )[0]

        source_chain_id: Optional[int] = None
        destination_chain_id: Optional[int] = None

        for chain_id_int, chain_data in chains_config.items():
            if chain_data.get("name") == source_chain_name:
                source_chain_id = int(chain_id_int)
            if chain_data.get("name") == destination_chain_name:
                destination_chain_id = int(chain_id_int)

        if source_chain_id is None or destination_chain_id is None:
            return False, "Could not map selected chain names to chain IDs."

        logger.info(
            f"Selected source chain: {source_chain_name} "
            f"(ID: {source_chain_id}), destination chain: "
            f"{destination_chain_name} (ID: {destination_chain_id})"
        )

        # 2. Select Token
        enabled_token_symbols = settings["enabled_tokens"]
        token_weights_list = [
            settings["token_weights"].get(sym, 0) for sym in enabled_token_symbols
        ]
        if sum(token_weights_list) == 0 and len(enabled_token_symbols) > 0:
            token_weights_list = [1] * len(enabled_token_symbols)

        selected_token_symbol: Optional[str] = None
        attempts = 0
        max_attempts = len(enabled_token_symbols) * 2  # Allow some retries

        while attempts < max_attempts:
            attempts += 1
            if not enabled_token_symbols or not any(w > 0 for w in token_weights_list):
                logger.warning(
                    "No enabled tokens with positive weights to select from."
                )
                return False, "No valid token to select for bridging."

            current_token_symbol = random.choices(
                enabled_token_symbols, weights=token_weights_list, k=1
            )[0]

            # Verify token is configured for both chains
            token_cfg = tokens_config.get(current_token_symbol, {})
            if source_chain_id in token_cfg and destination_chain_id in token_cfg:
                selected_token_symbol = current_token_symbol
                break
            else:
                logger.warning(
                    f"Token {current_token_symbol} not configured for both "
                    f"source {source_chain_name} and dest "
                    f"{destination_chain_name}. Retrying selection."
                )

        if selected_token_symbol is None:
            return False, (
                "Could not find a token compatible with selected "
                "source and destination chains."
            )

        logger.info(f"Selected token: {selected_token_symbol}")

        # 3. Select Amount
        # Placeholder: Using USD range and assuming 1 USD = 1 token unit.
        # A proper price oracle is needed for accurate conversion.
        amount_usd_min = float(settings["amount_usd_min"])
        amount_usd_max = float(settings["amount_usd_max"])
        if amount_usd_min <= 0 or amount_usd_max <= amount_usd_min:
            return False, "Invalid amount_usd_min/max settings."

        random_usd_amount = Decimal(str(random.uniform(amount_usd_min, amount_usd_max)))

        # Assuming 1 token = 1 USD for simplification.
        # This needs a price oracle for real-world application.
        token_decimals = tokens_config[selected_token_symbol][source_chain_id][
            "decimals"
        ]
        amount_in_token_units = random_usd_amount  # Assuming 1:1 USD

        logger.warning(
            "Using placeholder 1 USD = 1 token unit for amount calculation. "
            "Price oracle integration needed for accuracy."
        )
        logger.info(
            f"Selected amount: {amount_in_token_units:.{token_decimals}f} "
            f"{selected_token_symbol} "
            f"(target USD value: ${random_usd_amount:.2f})"
        )

        # Check min_source_balance_usd_threshold (simplified)
        min_balance_usd = float(settings.get("min_source_balance_usd_threshold", 0))
        if min_balance_usd > 0:
            # This check is conceptual
            logger.warning(
                "Conceptual check for min_source_balance_usd_threshold: "
                f"${min_balance_usd}. Actual balance check and price "
                "oracle needed."
            )
            # if amount_in_token_units < min_balance_usd:
            #    return False, (
            #        f"Selected amount {amount_in_token_units} is below "
            #        f"min_source_balance_usd_threshold of {min_balance_usd}"
            #    )

        # 4. Select Slippage
        slippage_bps_min = int(settings["slippage_bps_min"])
        slippage_bps_max = int(settings["slippage_bps_max"])
        # Max 100%
        if not (0 <= slippage_bps_min <= slippage_bps_max <= 10000):
            return False, "Invalid slippage_bps_min/max settings."
        selected_slippage_bps = random.randint(slippage_bps_min, slippage_bps_max)
        logger.info(f"Selected slippage: {selected_slippage_bps} bps")

        # 5. Call bridge function
        log_msg = (
            f"Calling bridge: {amount_in_token_units} {selected_token_symbol} "
            f"from {source_chain_name} (ID: {source_chain_id}) to "
            f"{destination_chain_name} (ID: {destination_chain_id}) "
            f"with slippage {selected_slippage_bps} bps."
        )
        logger.info(log_msg)

        amount_quantized = amount_in_token_units.quantize(
            Decimal(f"1e-{token_decimals}")
        )
        success, bridge_result = bridge(
            source_chain_id=source_chain_id,
            destination_chain_id=destination_chain_id,
            source_token_symbol=selected_token_symbol,
            amount_in_source_token_units=amount_quantized,
            user_address=user_address,
            slippage_bps=selected_slippage_bps,
            config=config,
            private_key=private_key,
        )

        if success:
            message = (
                f"Successfully initiated random bridge: "
                f"{amount_in_token_units:.{token_decimals}f} "
                f"{selected_token_symbol} from {source_chain_name} to "
                f"{destination_chain_name}. Tx: {bridge_result}"
            )
            logger.info(message)
            return True, message
        else:
            message = (
                f"Random bridge failed: {bridge_result}. Parameters: "
                f"Token: {selected_token_symbol}, "
                f"Amount: {amount_in_token_units}, Src: {source_chain_name}, "
                f"Dest: {destination_chain_name}, "
                f"Slippage: {selected_slippage_bps}bps."
            )
            logger.error(message)
            return False, message
    except KeyError as e:
        err_msg = f"Configuration key error during random bridge: {e}"
        logger.error(err_msg)
        return False, err_msg
    except ValueError as e:
        err_msg = f"Value error during random bridge: {e}"
        logger.error(err_msg)
        return False, err_msg
    except Exception as e:
        err_msg = f"Unexpected error during random bridge: {e}"
        logger.exception(err_msg)  # Log with stack trace
        return False, err_msg
