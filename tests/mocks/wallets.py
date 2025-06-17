"""Mock wallet implementations for testing blockchain interactions.

This module provides mock wallet classes that simulate various wallet behaviors
and failure scenarios without requiring actual blockchain connections.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import hashlib
import time
from web3.types import Wei, TxParams
from eth_account import Account

# Type aliases for better readability
Address = str
HexStr = str


class MockWallet(ABC):
    """Abstract base class for mock wallet implementations.

    Provides the interface that all mock wallets must implement,
    ensuring consistent behavior across different wallet types.

    Example:
    >>> wallet = MockHotWallet()
    >>> balance = wallet.get_balance()
    >>> tx_hash = wallet.send_transaction({
    ...     'to': '0x742d35Cc6634C0532925a3b8D4C9db96',
    ...     'value': Wei(1000000000000000000),
    ...     'gas': 21000,
    ...     'gasPrice': Wei(20000000000)
    ... }
    """

    def __init__(self) -> None:
        """Initialize the mock wallet with a generated private key."""
        self.account = Account.create()
        self.private_key = self.account.key.hex()
        self.address = Address(self.account.address)
        self.nonce = 0
        self.transaction_history: List[Dict[str, Any]] = []

    @abstractmethod
    def get_balance(self) -> Wei:
        """Get the current balance of the wallet.

        Returns:
            Wei: The wallet balance in Wei units.
        """
        pass

    @abstractmethod
    def send_transaction(self, tx_params: TxParams) -> HexStr:
        """Send a transaction from this wallet.

        Args:
            tx_params: Transaction parameters including to, value, gas, etc.

        Returns:
            HexStr: The transaction hash.

        Raises:
            Various exceptions depending on wallet type and conditions.
        """
        pass

    def get_address(self) -> Address:
        """Get the wallet's address.

        Returns:
            Address: The wallet's Ethereum address.

        Example:
            >>> wallet = MockHotWallet()
            >>> addr = wallet.get_address()
            >>> isinstance(addr, str)
            True
        """
        return self.address

    def get_nonce(self) -> int:
        """Get the current nonce for this wallet.

        Returns:
            int: The current transaction nonce.

        Example:
            >>> wallet = MockHotWallet()
            >>> nonce = wallet.get_nonce()
            >>> isinstance(nonce, int)
            True
        """
        return self.nonce

    def get_transaction_history(self) -> List[Dict[str, Any]]:
        """Get the transaction history for this wallet.

        Returns:
            List[Dict[str, Any]]: List of transaction records.

        Example:
            >>> wallet = MockHotWallet()
            >>> history = wallet.get_transaction_history()
            >>> isinstance(history, list)
            True
        """
        return self.transaction_history.copy()


class MockHotWallet(MockWallet):
    """Mock implementation of a hot wallet with normal functionality.

    This wallet simulates a standard hot wallet that can successfully
    send transactions and maintain balance.

    Example:
    >>> wallet = MockHotWallet()
    >>> balance = wallet.get_balance()
    >>> balance > 0
    True
    """

    def __init__(self, initial_balance: Wei = Wei(1000000000000000000)) -> None:
        """Initialize hot wallet with specified balance.

        Args:
            initial_balance: Starting balance in Wei (default: 1 ETH).
        """
        super().__init__()
        self.balance = initial_balance

    def get_balance(self) -> Wei:
        """Get the current balance.

        Returns:
            Wei: Current wallet balance.
        """
        return self.balance

    def send_transaction(self, tx_params: TxParams) -> HexStr:
        """Send a transaction, deducting gas and value from balance.

        Args:
            tx_params: Transaction parameters.

        Returns:
            HexStr: Deterministic transaction hash.

        Raises:
            ValueError: If insufficient balance for transaction.
        """
        # Calculate total cost (value + gas)
        value = Wei(tx_params.get('value', 0))
        gas = tx_params.get('gas', 21000)
        gas_price = Wei(tx_params.get('gasPrice', 20000000000))
        total_cost = value + Wei(gas * gas_price)

        if self.balance < total_cost:
            raise ValueError(f"Insufficient balance: {self.balance} < {total_cost}")

        # Deduct cost from balance
        self.balance = Wei(self.balance - total_cost)

        # Generate deterministic transaction hash
        tx_data = (f"{str(self.address)}{str(tx_params.get('to', ''))}"
                   f"{str(value)}{str(self.nonce)}{str(int(time.time()))}")
        tx_hash = HexStr('0x' + hashlib.sha256(tx_data.encode()).hexdigest())

        # Record transaction
        tx_record: Dict[str, Any] = {
            'hash': tx_hash,
            'from': self.address,
            'to': tx_params.get('to'),
            'value': value,
            'gas': gas,
            'gasPrice': gas_price,
            'nonce': self.nonce,
            'timestamp': int(time.time())
        }
        self.transaction_history.append(tx_record)

        # Increment nonce
        self.nonce += 1

        return tx_hash


class MockLowBalanceWallet(MockWallet):
    """Mock wallet with insufficient balance for most transactions.

    This wallet simulates a wallet that has very low balance,
    useful for testing insufficient funds scenarios.

    Example:
    >>> wallet = MockLowBalanceWallet()
    >>> balance = wallet.get_balance()
    >>> balance < Wei(1000000000000000000)  # Less than 1 ETH
    True
    """

    def __init__(self, balance: Wei = Wei(100000000000000)) -> None:
        """Initialize with very low balance.

        Args:
            balance: Starting balance in Wei (default: 0.0001 ETH).
        """
        super().__init__()
        self.balance = balance

    def get_balance(self) -> Wei:
        """Get the current low balance.

        Returns:
            Wei: Current wallet balance (very low).
        """
        return self.balance

    def send_transaction(self, tx_params: TxParams) -> HexStr:
        """Attempt to send transaction, likely failing due to low balance.

        Args:
            tx_params: Transaction parameters.

        Returns:
            HexStr: Transaction hash if successful.

        Raises:
            ValueError: When insufficient balance (most cases).
        """
        # Calculate total cost
        value = Wei(tx_params.get('value', 0))
        gas = tx_params.get('gas', 21000)
        gas_price = Wei(tx_params.get('gasPrice', 20000000000))
        total_cost = value + Wei(gas * gas_price)

        if self.balance < total_cost:
            raise ValueError(f"Insufficient balance: {self.balance} < {total_cost}")

        # If somehow we have enough, proceed like normal wallet
        self.balance = Wei(self.balance - total_cost)
        tx_data = (f"{str(self.address)}{str(tx_params.get('to', ''))}"
                   f"{str(value)}{str(self.nonce)}{str(int(time.time()))}")
        tx_hash = HexStr('0x' + hashlib.sha256(tx_data.encode()).hexdigest())

        tx_record: Dict[str, Any] = {
            'hash': tx_hash,
            'from': self.address,
            'to': tx_params.get('to'),
            'value': value,
            'gas': gas,
            'gasPrice': gas_price,
            'nonce': self.nonce,
            'timestamp': int(time.time())
        }
        self.transaction_history.append(tx_record)
        self.nonce += 1

        return tx_hash


class MockCompromisedWallet(MockWallet):
    """Mock wallet that simulates a compromised/hacked wallet.

    This wallet throws security-related exceptions to simulate
    various security breach scenarios.

    Example:
    >>> wallet = MockCompromisedWallet()
    >>> try:
    ...     wallet.send_transaction({'to': '0x123', 'value': 1000})
    ... except Exception as e:
    ...     'security' in str(e).lower()
    True
    """

    def __init__(self, balance: Wei = Wei(500000000000000000)) -> None:
        """Initialize compromised wallet.

        Args:
            balance: Starting balance in Wei (default: 0.5 ETH).
        """
        super().__init__()
        self.balance = balance
        self.is_compromised = True

    def get_balance(self) -> Wei:
        """Get balance, but wallet is compromised.

        Returns:
            Wei: Current balance.
        """
        return self.balance

    def send_transaction(self, tx_params: TxParams) -> HexStr:
        """Attempt transaction but fail due to security breach.

        Args:
            tx_params: Transaction parameters.

        Returns:
            HexStr: Never returns successfully.

        Raises:
            RuntimeError: Always raises security-related error.
        """
        raise RuntimeError("Wallet security breach detected: private key compromised")


class MockNetworkFailureWallet(MockWallet):
    """Mock wallet that simulates network connectivity issues.

    This wallet throws network-related exceptions to simulate
    various network failure scenarios.

    Example:
    >>> wallet = MockNetworkFailureWallet()
    >>> try:
    ...     wallet.send_transaction({'to': '0x123', 'value': 1000})
    ... except Exception as e:
    ...     'network' in str(e).lower()
    True
    """

    def __init__(self, balance: Wei = Wei(2000000000000000000)) -> None:
        """Initialize wallet with network issues.

        Args:
            balance: Starting balance in Wei (default: 2 ETH).
        """
        super().__init__()
        self.balance = balance

    def get_balance(self) -> Wei:
        """Get balance despite network issues.

        Returns:
            Wei: Current balance.

        Note:
            Balance queries might work even with network issues.
        """
        return self.balance

    def send_transaction(self, tx_params: TxParams) -> HexStr:
        """Attempt transaction but fail due to network issues.

        Args:
            tx_params: Transaction parameters.

        Returns:
            HexStr: Never returns successfully.

        Raises:
            ConnectionError: Always raises network-related error.
        """
        raise ConnectionError("Network timeout: unable to broadcast transaction")


# Export all wallet classes
__all__ = [
    'MockWallet',
    'MockHotWallet',
    'MockLowBalanceWallet',
    'MockCompromisedWallet',
    'MockNetworkFailureWallet'
]

