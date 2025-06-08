"""EigenLayer protocol module for restaking LSTs."""

import json
import os
from typing import Dict, Optional, Tuple, List, Any # Ensure Any is imported
from web3 import Web3
# from web3.exceptions import TransactionNotFound # Unused import

from airdrops.protocols.eigenlayer.eigenlayer_config import (
    EIGENLAYER_CONTRACTS,
    LST_TOKENS,
)
from .exceptions import (
    DepositCapReachedError,
    EigenLayerRestakeError,
    UnsupportedLSTError,
)
import logging # Changed from airdrops.shared.config

logger = logging.getLogger(__name__)


# Strategy mapping
LST_STRATEGIES = {
    "stETH": EIGENLAYER_CONTRACTS["steth_strategy"],
    "rETH": EIGENLAYER_CONTRACTS["reth_strategy"],
}


def _load_abi(filename: str) -> List[Dict[str, Any]]:
    """Load ABI from JSON file.
    
    Args:
        filename: Name of the ABI file to load
        
    Returns:
        List of ABI definitions
        
    Raises:
        EigenLayerRestakeError: If ABI file cannot be loaded
    """
    try:
        abi_path = os.path.join(os.path.dirname(__file__), "abi", filename)
        with open(abi_path, "r") as f:
            data: List[Dict[str, Any]] = json.load(f)
            return data
    except FileNotFoundError:
        raise EigenLayerRestakeError(f"ABI file not found: {filename}")
    except json.JSONDecodeError:
        raise EigenLayerRestakeError(f"Invalid JSON in ABI file: {filename}")


def _get_eigenlayer_lst_strategy_details(lst_symbol: str) -> Dict[str, str]:
    """Get LST token and strategy contract details.

    Args:
        lst_symbol: Symbol of the LST token ("stETH" or "rETH")

    Returns:
        Dictionary containing token_address, strategy_address, token_abi_file, and strategy_abi_file
        
    Raises:
        UnsupportedLSTError: If LST symbol is not supported
    """
    if lst_symbol not in LST_TOKENS:
        raise UnsupportedLSTError(f"Unsupported LST: {lst_symbol}")
    
    token_address = LST_TOKENS[lst_symbol]
    strategy_address = LST_STRATEGIES[lst_symbol]

    # Determine ABI file names based on LST symbol
    token_abi_file = "ERC20.json"
    if lst_symbol == "stETH":
        strategy_abi_file = "StrategyBaseTVLLimits_stETH.json"
    elif lst_symbol == "rETH":
        strategy_abi_file = "StrategyBaseTVLLimits_rETH.json"
    else:
        # This case should ideally not be reached due to the check above,
        # but as a fallback:
        raise UnsupportedLSTError(f"Unknown LST symbol for ABI determination: {lst_symbol}")

    return {
        "token_address": token_address,
        "strategy_address": strategy_address,
        "token_abi_file": token_abi_file,
        "strategy_abi_file": strategy_abi_file,
    }


def _check_eigenlayer_deposit_cap(
    web3_eth: Web3,
    strategy_address: str,
    deposit_amount: int
) -> bool:
    """Check if deposit would exceed strategy cap.

    Args:
        web3_eth: Web3 instance
        strategy_address: Strategy contract address
        deposit_amount: Amount to deposit in wei

    Returns:
        True if deposit is within cap, False otherwise

    Raises:
        EigenLayerRestakeError: If contract call fails
    """
    try:
        # Assuming stETH ABI for cap check as it's a common base.
        # This might need adjustment if rETH strategy has different cap functions.
        strategy_abi = _load_abi("StrategyBaseTVLLimits_stETH.json")
        
        strategy_contract = web3_eth.eth.contract(
            address=Web3.to_checksum_address(strategy_address),
            abi=strategy_abi
        )
        
        total_shares = strategy_contract.functions.totalShares().call()
        max_total_deposits = strategy_contract.functions.maxTotalDeposits().call()
        
        return bool((total_shares + deposit_amount) <= max_total_deposits)
        
    except Exception as e:
        raise EigenLayerRestakeError(f"Failed to check deposit cap: {str(e)}")


def restake_lst(
    web3_eth: Web3,
    private_key: str,
    lst_symbol: str,
    amount: int
) -> Tuple[bool, Optional[str]]:
    """Restake LST tokens into EigenLayer strategy.

    Args:
        web3_eth: Web3 instance connected to Ethereum mainnet
        private_key: Private key of the user's wallet
        lst_symbol: Symbol of the LST to restake ("stETH" or "rETH")
        amount: Amount to restake in wei

    Returns:
        Tuple of (success, transaction_hash_or_error_message)

    Raises:
        UnsupportedLSTError: If LST symbol is not supported
        EigenLayerRestakeError: If restaking operation fails
    """
    try:
        if amount <= 0:
            raise EigenLayerRestakeError("Amount must be positive")
        
        details = _get_eigenlayer_lst_strategy_details(lst_symbol)
        token_address = details["token_address"]
        strategy_address = details["strategy_address"]
        token_abi_file = details["token_abi_file"]
        strategy_abi_file = details["strategy_abi_file"]
        
        account = web3_eth.eth.account.from_key(private_key)
        user_address = account.address
        
        erc20_abi = _load_abi(token_abi_file)
        strategy_abi = _load_abi(strategy_abi_file)
        
        token_contract = web3_eth.eth.contract(address=Web3.to_checksum_address(token_address), abi=erc20_abi)
        strategy_contract = web3_eth.eth.contract(address=Web3.to_checksum_address(strategy_address), abi=strategy_abi)
        
        user_balance = token_contract.functions.balanceOf(user_address).call()
        if user_balance < amount:
            return False, f"Insufficient balance. Have: {user_balance}, Need: {amount}"
        
        if not _check_eigenlayer_deposit_cap(web3_eth, strategy_address, amount):
            raise DepositCapReachedError("Deposit would exceed strategy cap")
        
        allowance = token_contract.functions.allowance(user_address, strategy_address).call()
        if allowance < amount:
            approve_txn = token_contract.functions.approve(strategy_address, amount).build_transaction({
                'from': user_address,
                'gas': 100000,
                'gasPrice': web3_eth.eth.gas_price,
                'nonce': web3_eth.eth.get_transaction_count(user_address),
            })
            
            signed_approve = web3_eth.eth.account.sign_transaction(approve_txn, private_key)
            approve_hash = web3_eth.eth.send_raw_transaction(signed_approve.rawTransaction)
            approve_receipt = web3_eth.eth.wait_for_transaction_receipt(approve_hash)
            if approve_receipt['status'] != 1:
                 return False, "Approval transaction failed"

        deposit_txn = strategy_contract.functions.deposit(token_address, amount).build_transaction({
            'from': user_address,
            'gas': 200000,
            'gasPrice': web3_eth.eth.gas_price,
            'nonce': web3_eth.eth.get_transaction_count(user_address),
        })
        
        signed_deposit = web3_eth.eth.account.sign_transaction(deposit_txn, private_key)
        deposit_hash = web3_eth.eth.send_raw_transaction(signed_deposit.rawTransaction)
        
        receipt = web3_eth.eth.wait_for_transaction_receipt(deposit_hash)
        
        if receipt['status'] == 1:
            return True, deposit_hash.hex()
        else:
            return False, "Transaction failed"
            
    except UnsupportedLSTError:
        raise
    except DepositCapReachedError:
        raise
    except Exception as e:
        logger.error(f"Restaking failed: {str(e)}")
        raise EigenLayerRestakeError(f"Restaking operation failed: {str(e)}")


__all__ = [
    "restake_lst",
    "UnsupportedLSTError",
    "EigenLayerRestakeError",
    "DepositCapReachedError",
]