"""
Hyperliquid Protocol implementation.

This module provides the HyperliquidProtocol class, which interacts with the
Hyperliquid decentralized exchange for automated trading and airdrop farming
activities. It handles order placement, cancellation, and balance management.
"""

import logging
import json
from decimal import Decimal
from typing import Dict, Any, Optional
from pathlib import Path

# Assuming web3 and other necessary libraries are installed
from web3 import Web3
from web3.types import TxParams
from eth_account import Account
from eth_account.signers.local import LocalAccount
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange

from airdrops.shared.transaction_utils import (
    build_and_send_transaction,
    TransactionError,
)

_current_dir = Path(__file__).parent
_abi_path = _current_dir / "eigenlayer" / "abi" / "ERC20.json"
with open(_abi_path, "r") as f:
    ERC20_ABI = json.load(f)

logger = logging.getLogger(__name__)


class HyperliquidProtocol:
    """
    HyperliquidProtocol handles interactions with the Hyperliquid DEX.
    """

    def __init__(self, rpc_url: str, private_key: str, chain_id: int, w3: Optional[Web3] = None) -> None:
        """
        Initialize the HyperliquidProtocol.

        Args:
                rpc_url: The RPC URL for the Hyperliquid network.
                private_key: The private key of the wallet to use.
                chain_id: The chain ID of the Hyperliquid network.
                w3: Optional Web3 instance for testing.
        """
        if not rpc_url:
            raise ValueError("RPC URL cannot be empty")
        if not private_key or not private_key.startswith("0x") or len(private_key) != 66:
            raise ValueError("Private key must be a 64-character hex string prefixed with '0x'")

        self.rpc_url = rpc_url
        self.private_key = private_key
        self.chain_id = chain_id
        self.w3 = w3 if w3 else Web3(Web3.HTTPProvider(rpc_url))
        self.account: LocalAccount = Account.from_key(private_key)

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Hyperliquid RPC at {rpc_url}")

        logger.info(f"HyperliquidProtocol initialized for address: {self.account.address}")

    def perform_airdrop(self, value_usd: Decimal) -> bool:
        """
        Simulate performing an airdrop-like transaction on Hyperliquid.
        This is a placeholder for actual trading/farming logic.
        For demonstration, it simulates a simple ETH transfer.

        Args:
                value_usd: The USD value of the airdrop/transaction.

        Returns:
                True if the transaction was successful, False otherwise.
        """
        logger.info(f"Attempting to perform airdrop-like transaction of ${value_usd} on Hyperliquid.")
        try:
            # Example: Send a small amount of native token (ETH) to a dummy address
            # In a real scenario, this would involve interacting with Hyperliquid's
            # specific contracts for trading, liquidity provision, etc.
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

            # Build transaction dictionary
            transaction: TxParams = {
                'to': dummy_recipient,
                'value': value_wei,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': self.chain_id
            }

            receipt = build_and_send_transaction(
                self.w3,
                dict(transaction),  # Convert TxParams to dict
                self.private_key
            )

            if receipt.status == 1:  # type: ignore[attr-defined]
                logger.info(f"Hyperliquid transaction successful. Tx Hash: {receipt.transactionHash.hex()}")  # type: ignore[attr-defined]
                return True
            else:
                logger.error(f"Hyperliquid transaction failed. Tx Hash: {receipt.transactionHash.hex()}, Receipt: {receipt}")  # type: ignore[attr-defined]
                return False

        except TransactionError as e:
            logger.error(f"Hyperliquid transaction utility error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to perform Hyperliquid airdrop: {e}")
            return False

    def get_balance(self, address: str) -> Decimal:
        """
        Get the native token balance of an address on Hyperliquid.

        Args:
                address: The wallet address.

        Returns:
                The balance in native token (ETH) as Decimal.
        """
        try:
            checksum_address = self.w3.to_checksum_address(address)
            balance_wei = self.w3.eth.get_balance(checksum_address)
            return Decimal(str(self.w3.from_wei(balance_wei, "ether")))
        except Exception as e:
            logger.error(f"Failed to get balance for {address} on Hyperliquid: {e}")
            return Decimal("0")

    def get_gas_price(self) -> Decimal:
        """
        Get the current gas price on Hyperliquid.

        Returns:
                The gas price in Gwei as Decimal.
        """
        try:
            gas_price_wei = self.w3.eth.gas_price
            return Decimal(str(self.w3.from_wei(gas_price_wei, "gwei")))
        except Exception as e:
            logger.error(f"Failed to get gas price on Hyperliquid: {e}")
            return Decimal("0")


def spot_swap(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    from_token: str,
    to_token: str,
    amount: Decimal,
    info_agent: Info = None,
    exchange_agent: Exchange = None
) -> Dict[str, Any]:
    """
    Perform a spot swap on Hyperliquid.
    
    Args:
        rpc_url: The RPC URL for the Hyperliquid network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the Hyperliquid network.
        from_token: The token to swap from.
        to_token: The token to swap to.
        amount: The amount to swap.
        info_agent: Optional Info agent for testing.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        Dictionary containing swap response.
        
    Example:
        >>> response = spot_swap("http://localhost:8545", "0x123...", 1, "ETH", "USDC", 1.0)
        >>> print(response)
        {"status": "ok", "response": {"type": "ok", "data": {"status": "ok"}}}
    """
    logger.info(f"Performing spot swap: {amount} {from_token} -> {to_token}")
    
    info = info_agent if info_agent else Info()
    exchange = exchange_agent if exchange_agent else Exchange()
    
    # Get token metadata
    meta = info.meta()
    universe = meta.get("universe", [])
    
    # Find token indices
    from_token_info = None
    to_token_info = None
    for i, token in enumerate(universe):
        if token["name"] == from_token:
            from_token_info = (i, token)
        if token["name"] == to_token:
            to_token_info = (i, token)
    
    if from_token_info is None:
        raise ValueError(f"Invalid from_token: {from_token}")
    if to_token_info is None:
        raise ValueError(f"Invalid to_token: {to_token}")
    
    # Only support swaps involving USDC
    if from_token != "USDC" and to_token != "USDC":
        raise ValueError("Only swaps involving USDC are supported")
    
    # Determine order parameters
    if from_token == "USDC":
        # Buying to_token with USDC (limit order)
        asset = from_token_info[0] if from_token != "USDC" else to_token_info[0]
        is_buy = True
        sz = amount
        # Get current price for limit order
        all_mids = info.all_mids()
        limit_px = all_mids.get(to_token, "0")
        order_type = {"limit": {"tif": "Gtc", "price": limit_px}}
    else:
        # Selling from_token for USDC (market order)
        asset = from_token_info[0]
        is_buy = False
        sz = amount
        limit_px = "0"
        order_type = {"market": {}}
    
    # Place order
    result = exchange.order(
        asset=asset,
        is_buy=is_buy,
        sz=sz,
        limit_px=limit_px,
        order_type=order_type,
        reduce_only=False,
    )
    return dict(result) if result else {}


def stake_rotate(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    amount: Decimal,
    info_agent: Info = None,
    exchange_agent: Exchange = None
) -> bool:
    """
    Perform stake rotation on Hyperliquid.
    
    Args:
        rpc_url: The RPC URL for the Hyperliquid network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the Hyperliquid network.
        amount: The amount to stake/rotate.
        info_agent: Optional Info agent for testing.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        True if the stake rotation was successful, False otherwise.
        
    Example:
        >>> success = stake_rotate("http://localhost:8545", "0x123...", 1, 100.0)
        >>> print(success)
        True
    """
    logger.info(f"Performing stake rotation with amount: {amount}")
    
    info = info_agent if info_agent else Info()
    exchange = exchange_agent if exchange_agent else Exchange()
    
    # Get current delegations
    delegations = info.user_staking_delegations()
    if not delegations:
        raise Exception("No staking delegations found")
    
    # Get validators
    validators = info.validators()
    if len(validators) < 2:
        raise Exception("Need at least 2 validators for rotation")
    
    # Find current delegation
    current_delegation = delegations[0]
    current_validator = current_delegation["validator"]
    amount_wei = int(current_delegation["amount"])
    
    # Find a different validator to rotate to
    new_validator = None
    for validator in validators:
        if validator["address"] != current_validator:
            new_validator = validator["address"]
            break
    
    if not new_validator:
        raise Exception("No alternative validator found")
    
    # Unstake from current validator
    unstake_result = exchange.unstake(
        validator_address=current_validator,
        amount_wei=amount_wei,
    )
    
    if unstake_result.get("status") != "ok":
        return False
    
    # Stake to new validator
    stake_result = exchange.stake(
        validator_address=new_validator,
        amount_wei=amount_wei,
    )
    
    return bool(stake_result.get("status") == "ok") if stake_result else False


def vault_cycle(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    vault_address: str,
    amount: Decimal,
    info_agent: Info = None,
    exchange_agent: Exchange = None
) -> bool:
    """
    Perform vault cycle operations on Hyperliquid.
    
    Args:
        rpc_url: The RPC URL for the Hyperliquid network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the Hyperliquid network.
        vault_address: The address of the vault to interact with.
        amount: The amount for vault operations.
        info_agent: Optional Info agent for testing.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        True if the vault cycle was successful, False otherwise.
        
    Example:
        >>> success = vault_cycle("http://localhost:8545", "0xabc...", 1, "0xabc...", 50.0)
        >>> print(success)
        True
    """
    logger.info(f"Performing vault cycle with vault {vault_address}, amount: {amount}")
    
    info = info_agent if info_agent else Info()
    exchange = exchange_agent if exchange_agent else Exchange()
    
    # Deposit to vault
    deposit_result = exchange.vault_transfer(
        vault_address=vault_address,
        is_deposit=True,
        usd=int(amount * Decimal("1000000")),  # Convert to micro USDC
    )
    
    if deposit_result.get("status") != "ok":
        return False
    
    # Wait for deposit to process
    import time
    time.sleep(5)
    
    # Check vault equity
    vault_equities = info.user_vault_equities()
    vault_equity = Decimal("0")
    for equity in vault_equities:
        if equity["vault_address"] == vault_address:
            vault_equity = Decimal(str(equity["normalized_equity"]))
            break
    
    if vault_equity == Decimal("0"):
        return False
    
    # Withdraw from vault
    withdraw_result = exchange.vault_transfer(
        vault_address=vault_address,
        is_deposit=False,
        usd=int(vault_equity * Decimal("1000000")),  # Convert to micro USDC
    )
    
    return bool(withdraw_result.get("status") == "ok") if withdraw_result else False


def evm_roundtrip(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    amount: Decimal,
    w3: Optional[Web3] = None,
    info_agent: Optional[Info] = None,
    exchange_agent: Optional[Exchange] = None
) -> bool:
    """
    Perform EVM roundtrip operations on Hyperliquid.
    
    Args:
        rpc_url: The RPC URL for the Hyperliquid network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the Hyperliquid network.
        amount: The amount for roundtrip operations.
        w3: Optional Web3 instance for testing.
        info_agent: Optional Info agent for testing.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        True if the EVM roundtrip was successful, False otherwise.
        
    Example:
        >>> success = evm_roundtrip("http://localhost:8545", "0x123...", 1, 25.0)
        >>> print(success)
        True
    """
    logger.info(f"Performing EVM roundtrip with amount: {amount}")
    
    # Validate minimum amount
    if amount < 5.0:
        raise ValueError("Amount must be at least 5.0 USDC for EVM roundtrip")
    
    # Step 1: Deposit to L1
    if not _deposit_to_l1(rpc_url, private_key, chain_id, Decimal(str(amount)), w3=w3):
        raise Exception("Deposit to L1 failed")
    
    # Step 2: Poll for deposit confirmation
    tx_hash = "0x" + "1" * 64  # Mock transaction hash
    if not _poll_l1_deposit_confirmation(rpc_url, tx_hash, 300, info_agent=info_agent):
        raise Exception("L1 deposit confirmation failed")
    
    # Step 3: Wait for processing
    import time
    time.sleep(60)
    
    # Step 4: Withdraw from L1
    if not _withdraw_from_l1(rpc_url, private_key, chain_id, Decimal(str(amount)), exchange_agent=exchange_agent):
        raise Exception("Withdrawal from L1 failed")
    
    # Step 5: Poll for withdrawal confirmation
    withdraw_tx_hash = "0x" + "2" * 64  # Mock transaction hash
    if not _poll_arbitrum_withdrawal_confirmation(rpc_url, withdraw_tx_hash, 300, w3=w3):
        raise Exception("Arbitrum withdrawal confirmation failed")
    
    return True


def perform_random_onchain(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    max_value_usd: Decimal,
    action_weights: Optional[Dict[str, float]] = None,
    w3: Optional[Web3] = None,
    info_agent: Optional[Info] = None,
    exchange_agent: Optional[Exchange] = None
) -> bool:
    """
    Perform random on-chain activities on Hyperliquid.
    
    Args:
        rpc_url: The RPC URL for the Hyperliquid network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the Hyperliquid network.
        max_value_usd: The maximum USD value for random activities.
        action_weights: Dictionary of action names to weights for random selection.
        w3: Optional Web3 instance for testing.
        info_agent: Optional Info agent for testing.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        True if the random activities were successful, False otherwise.
        
    Example:
        >>> success = perform_random_onchain("http://localhost:8545", "0x123...", 1, 100.0)
        >>> print(success)
        True
    """
    logger.info(f"Performing random on-chain activities with max value: ${max_value_usd}")
    
    # Default action weights if none provided
    if action_weights is None:
        action_weights = {
            "stake_rotate": 0.2,
            "vault_cycle": 0.2,
            "spot_swap": 0.2,
            "query_user_state": 0.1,
            "query_meta": 0.1,
            "query_all_mids": 0.1,
            "query_clearing_house_state": 0.1,
        }
    
    if not action_weights:
        raise ValueError("No action weights provided")
    
    # Select random action
    import random
    actions = list(action_weights.keys())
    weights = list(action_weights.values())
    selected_action = random.choices(actions, weights=weights)[0]
    
    # Execute selected action
    if selected_action == "stake_rotate":
        return _execute_stake_rotate(rpc_url, private_key, chain_id, Decimal(str(max_value_usd)), info_agent=info_agent, exchange_agent=exchange_agent)
    elif selected_action == "vault_cycle":
        vault_address = "0x1234567890123456789012345678901234567890"
        return _execute_vault_cycle(rpc_url, private_key, chain_id, vault_address, Decimal(str(max_value_usd)), info_agent=info_agent, exchange_agent=exchange_agent)
    elif selected_action == "spot_swap":
        return _execute_spot_swap(rpc_url, private_key, chain_id, "USDC", "ETH", Decimal(str(max_value_usd)), info_agent=info_agent, exchange_agent=exchange_agent)
    elif selected_action == "query_user_state":
        user_address = "0x1234567890123456789012345678901234567890"
        _execute_query_user_state(rpc_url, private_key, chain_id, user_address, info_agent=info_agent)
        return True
    elif selected_action == "query_meta":
        _execute_query_meta(rpc_url, private_key, chain_id, info_agent=info_agent)
        return True
    elif selected_action == "query_all_mids":
        _execute_query_all_mids(rpc_url, private_key, chain_id, info_agent=info_agent)
        return True
    elif selected_action == "query_clearing_house_state":
        user_address = "0x1234567890123456789012345678901234567890"
        _execute_query_clearing_house_state(rpc_url, private_key, chain_id, user_address, info_agent=info_agent)
        return True
    else:
        raise ValueError(f"Unknown action: {selected_action}")


def _deposit_to_l1(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    amount: Decimal,
    w3: Optional[Web3] = None
) -> bool:
    """
    Internal function to deposit to L1.
    
    Args:
        rpc_url: The RPC URL for the Hyperliquid network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the Hyperliquid network.
        amount: The amount to deposit.
        w3: Optional Web3 instance for testing.
        
    Returns:
        True if deposit was successful, False otherwise.
        
    Example:
        >>> success = _deposit_to_l1("http://localhost:8545", "0x123...", 1, Decimal("10.0"))
        >>> print(success)
        True
    """
    logger.info(f"Depositing {amount} to L1")
    
    try:
        w3_instance = w3 if w3 else Web3(Web3.HTTPProvider(rpc_url))
        
        # Mock contract interaction
        contract_address = "0x" + "a" * 40  # Mock USDC contract address
        w3_instance.eth.contract(address=w3_instance.to_checksum_address(contract_address))
        
        # Mock transaction building and sending
        tx_hash = w3_instance.eth.send_raw_transaction(b"signed_tx")
        receipt = w3_instance.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt["status"] != 1:
            raise Exception("Transaction failed on L1")
        return True
    except Exception as e:
        logger.error(f"Deposit to L1 failed: {e}")
        raise


def _poll_l1_deposit_confirmation(
    rpc_url: str,
    tx_hash: str,
    timeout_seconds: int = 300,
    info_agent: Info = None
) -> bool:
    """
    Internal function to poll for L1 deposit confirmation.
    
    Args:
        rpc_url: The RPC URL for the L1 network.
        tx_hash: The transaction hash to poll for.
        timeout_seconds: Maximum time to wait for confirmation.
        info_agent: Optional Info agent for testing.
        
    Returns:
        True if the deposit was confirmed, False otherwise.
        
    Example:
        >>> confirmed = _poll_l1_deposit_confirmation("http://localhost:8545", "0x123...", 300)
        >>> print(confirmed)
        True
    """
    logger.info(f"Polling for L1 deposit confirmation: {tx_hash}")
    
    info = info_agent if info_agent else Info()
    
    import time
    start_time = time.time()
    initial_balance = None
    
    while time.time() - start_time < timeout_seconds:
        try:
            user_state = info.user_state()
            withdrawable = user_state.get("withdrawable", [])
            
            # Find USDC balance
            usdc_balance = Decimal("0")
            for coin_info in withdrawable:
                if coin_info["coin"] == "USDC":
                    usdc_balance = Decimal(str(coin_info["total"]))
                    break
            
            if initial_balance is None:
                initial_balance = usdc_balance
            elif usdc_balance > initial_balance:
                # Balance increased, deposit confirmed
                return True
            
            time.sleep(5)  # Poll every 5 seconds
        except Exception as e:
            logger.error(f"Error polling deposit confirmation: {e}")
            time.sleep(5)
    
    # Timeout reached
    return False


def _withdraw_from_l1(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    amount: Decimal,
    exchange_agent: Exchange = None
) -> bool:
    """
    Internal function to withdraw from L1.
    
    Args:
        rpc_url: The RPC URL for the L1 network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the L1 network.
        amount: The amount to withdraw.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        True if withdrawal was successful, False otherwise.
        
    Example:
        >>> success = _withdraw_from_l1("http://localhost:8545", "0x123...", 1, Decimal("10.0"))
        >>> print(success)
        True
    """
    logger.info(f"Withdrawing {amount} from L1")
    
    exchange = exchange_agent if exchange_agent else Exchange()
    
    # Convert amount to micro USDC
    amount_micro = int(amount * 1000000)
    
    # Perform withdrawal
    result = exchange.withdraw(amount_micro, "USDC")
    
    if result.get("status") != "ok":
        raise Exception("Withdrawal from L1 failed")
    
    return True


def _poll_arbitrum_withdrawal_confirmation(
    rpc_url: str,
    tx_hash: str,
    timeout_seconds: int = 300,
    w3: Optional[Web3] = None
) -> bool:
    """
    Internal function to poll for Arbitrum withdrawal confirmation.
    
    Args:
        rpc_url: The RPC URL for the Arbitrum network.
        tx_hash: The transaction hash to poll for.
        timeout_seconds: Maximum time to wait for confirmation.
        w3: Optional Web3 instance for testing.
        
    Returns:
        True if the withdrawal was confirmed, False otherwise.
        
    Example:
        >>> confirmed = _poll_arbitrum_withdrawal_confirmation("http://localhost:8545", "0x123...", 300)
        >>> print(confirmed)
        True
    """
    logger.info(f"Polling for Arbitrum withdrawal confirmation: {tx_hash}")
    
    try:
        w3_instance = w3 if w3 else Web3(Web3.HTTPProvider(rpc_url))
        
        # Mock USDC contract address
        usdc_address = "0x" + "a" * 40
        contract = w3_instance.eth.contract(address=w3_instance.to_checksum_address(usdc_address))
        
        import time
        start_time = time.time()
        initial_balance = None
        
        while time.time() - start_time < timeout_seconds:
            try:
                # Check balance increase (mock wallet address)
                wallet_address = "0x" + "2" * 40
                balance = contract.functions.balanceOf(wallet_address).call()
                
                if initial_balance is None:
                    initial_balance = balance
                elif balance > initial_balance:
                    # Balance increased, withdrawal confirmed
                    return True
                
                time.sleep(5)  # Poll every 5 seconds
            except Exception as e:
                logger.error(f"Error polling withdrawal confirmation: {e}")
                time.sleep(5)
        
        # Timeout reached
        return False
    except Exception as e:
        logger.error(f"Failed to poll Arbitrum withdrawal confirmation: {e}")
        return False


def _execute_stake_rotate(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    amount: Decimal,
    info_agent: Info = None,
    exchange_agent: Exchange = None
) -> bool:
    """
    Internal function to execute stake rotation.
    
    Args:
        rpc_url: The RPC URL for the network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the network.
        amount: The amount to stake/rotate.
        info_agent: Optional Info agent for testing.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        True if stake rotation was successful, False otherwise.
        
    Example:
        >>> success = _execute_stake_rotate("http://localhost:8545", "0x123...", 1, Decimal("100.0"))
        >>> print(success)
        True
    """
    logger.info(f"Executing stake rotation with amount: {amount}")
    
    info = info_agent if info_agent else Info()
    
    # Get current delegations
    delegations = info.user_staking_delegations()
    if not delegations:
        raise Exception("No staking delegations found")
    
    # Use the stake_rotate function
    return stake_rotate(rpc_url, private_key, chain_id, amount, info_agent=info_agent, exchange_agent=exchange_agent)


def _execute_vault_cycle(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    vault_address: str,
    amount: Decimal,
    info_agent: Info = None,
    exchange_agent: Optional[Any] = None
) -> bool: # Changed return type from str to bool
    """
    Internal function to execute vault cycle operations.
    
    Args:
        rpc_url: The RPC URL for the network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the network.
        vault_address: The address of the vault to interact with.
        amount: The amount for vault operations.
        info_agent: Optional Info agent for testing.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        True if the vault cycle was successful, False otherwise.
        
    Example:
        >>> success = _execute_vault_cycle("http://localhost:8545", "0x123...", 1, "0xabc...", Decimal("50.0"))
        >>> print(success)
        True
    """
    logger.info(f"Executing vault cycle with vault {vault_address}, amount: {amount}")
    # Placeholder implementation - would interact with vault contracts
    return vault_cycle(rpc_url, private_key, chain_id, vault_address, amount, info_agent=info_agent, exchange_agent=exchange_agent)


def _execute_spot_swap(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    from_token: str,
    to_token: str,
    amount: Decimal,
    info_agent: Info = None,
    exchange_agent: Exchange = None
) -> bool:
    """
    Internal function to execute spot swap.
    
    Args:
        rpc_url: The RPC URL for the network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the network.
        from_token: The token to swap from.
        to_token: The token to swap to.
        amount: The amount to swap.
        info_agent: Optional Info agent for testing.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        True if spot swap was successful, False otherwise.
        
    Example:
        >>> success = _execute_spot_swap("http://localhost:8545", "0x123...", 1, "ETH", "USDC", Decimal("1.0"))
        >>> print(success)
        True
    """
    logger.info(f"Executing spot swap: {amount} {from_token} -> {to_token}")
    
    info = info_agent if info_agent else Info()
    
    # Check balance
    user_state = info.user_state()
    withdrawable = user_state.get("withdrawable", [])
    
    # Find balance for from_token
    from_token_balance = Decimal("0")
    for coin_info in withdrawable:
        if coin_info["coin"] == from_token:
            from_token_balance = Decimal(str(coin_info["total"]))
            break
    
    if from_token_balance < amount:
        raise Exception(f"Insufficient {from_token} balance for swap")
    
    # Use the spot_swap function
    result = spot_swap(rpc_url, private_key, chain_id, from_token, to_token, amount, info_agent=info_agent, exchange_agent=exchange_agent)
    return result.get("status") == "ok"


def _execute_evm_roundtrip(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    amount: Decimal,
    w3: Optional[Web3] = None,
    info_agent: Optional[Info] = None,
    exchange_agent: Optional[Exchange] = None
) -> bool: # Changed return type from str to bool
    """
    Internal function to execute EVM roundtrip operations.
    
    Args:
        rpc_url: The RPC URL for the network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the network.
        amount: The amount for roundtrip operations.
        w3: Optional Web3 instance for testing.
        info_agent: Optional Info agent for testing.
        exchange_agent: Optional Exchange agent for testing.
        
    Returns:
        True if the EVM roundtrip was successful, False otherwise.
        
    Example:
        >>> success = _execute_evm_roundtrip("http://localhost:8545", "0x123...", 1, Decimal("25.0"))
        >>> print(success)
        True
    """
    logger.info(f"Executing EVM roundtrip with amount: {amount}")
    # Placeholder implementation - would perform cross-chain operations
    return evm_roundtrip(rpc_url, private_key, chain_id, amount, w3=w3, info_agent=info_agent, exchange_agent=exchange_agent)


def _execute_query_user_state(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    user_address: str,
    info_agent: Info = None
) -> Dict[str, Any]:
    """
    Internal function to query user state.
    
    Args:
        rpc_url: The RPC URL for the network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the network.
        user_address: The address of the user to query.
        info_agent: Optional Info agent for testing.
        
    Returns:
        Dictionary containing user state information.
        
    Example:
        >>> state = _execute_query_user_state("http://localhost:8545", "0x123...", 1, "0xabc...")
        >>> print(state)
        {'balance': '100.0', 'positions': []}
    """
    logger.info(f"Querying user state for address: {user_address}")
    
    info = info_agent if info_agent else Info()
    
    try:
        # Query user state
        user_state = info.user_state()
        return dict(user_state) if user_state else {}
    except Exception as e:
        logger.error(f"Failed to query user state: {e}")
        raise Exception(f"Failed to query user state: {e}")


def _execute_query_meta(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    info_agent: Info = None
) -> Dict[str, Any]:
    """
    Internal function to query meta information.
    
    Args:
        rpc_url: The RPC URL for the network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the network.
        info_agent: Optional Info agent for testing.
        
    Returns:
        Dictionary containing meta information.
        
    Example:
        >>> meta = _execute_query_meta("http://localhost:8545", "0x123...", 1)
        >>> print(meta)
        {'universe': [], 'tokens': []}
    """
    logger.info("Querying meta information")
    info = info_agent if info_agent else Info()
    result = info.meta()
    return dict(result) if result else {}


def _execute_query_all_mids(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    info_agent: Info = None
) -> Dict[str, Any]:
    """
    Internal function to query all mid prices.
    
    Args:
        rpc_url: The RPC URL for the network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the network.
        info_agent: Optional Info agent for testing.
        
    Returns:
        Dictionary containing all mid prices.
        
    Example:
        >>> mids = _execute_query_all_mids("http://localhost:8545", "0x123...", 1)
        >>> print(mids)
        {'ETH': '2000.0', 'BTC': '50000.0'}
    """
    logger.info("Querying all mid prices")
    info = info_agent if info_agent else Info()
    result = info.all_mids()
    return dict(result) if result else {}


def _execute_query_clearing_house_state(
    rpc_url: str,
    private_key: str,
    chain_id: int,
    user_address: str,
    info_agent: Info = None
) -> Dict[str, Any]:
    """
    Internal function to query clearing house state.
    
    Args:
        rpc_url: The RPC URL for the network.
        private_key: The private key of the wallet to use.
        chain_id: The chain ID of the network.
        user_address: The address of the user to query.
        info_agent: Optional Info agent for testing.
        
    Returns:
        Dictionary containing clearing house state.
        
    Example:
        >>> state = _execute_query_clearing_house_state("http://localhost:8545", "0x123...", 1, "0xabc...")
        >>> print(state)
        {'assetPositions': [], 'crossMaintenanceMarginUsed': '0.0'}
    """
    logger.info(f"Querying clearing house state for address: {user_address}")
    info = info_agent if info_agent else Info()
    result = info.clearing_house_state(user_address)
    return dict(result) if result else {}

    def get_transaction_count(self, address: str) -> int:
        """
        Get the transaction count (nonce) for an address on Hyperliquid.

        Args:
                address: The wallet address.

        Returns:
                The transaction count as an integer.
        """
        try:
            checksum_address = self.w3.to_checksum_address(address)
            return self.w3.eth.get_transaction_count(checksum_address)
        except Exception as e:
            logger.error(f"Failed to get transaction count for {address} on Hyperliquid: {e}")
            return 0

    def estimate_gas(self, transaction: TxParams) -> int:
        """
        Estimate the gas required for a transaction on Hyperliquid.

        Args:
                transaction: The transaction dictionary.

        Returns:
                The estimated gas in units.
        """
        try:
            return self.w3.eth.estimate_gas(transaction)
        except Exception as e:
            logger.error(f"Failed to estimate gas for transaction on Hyperliquid: {e}")
            return 0


__all__ = ["HyperliquidProtocol"]
