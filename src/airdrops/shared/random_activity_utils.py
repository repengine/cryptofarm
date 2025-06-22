"""
Random activity utility functions for airdrop protocol implementations.

This module provides shared utilities for selecting activities, generating random amounts,
and selecting random tokens based on weighted configurations.
"""

from typing import List, Dict, Any, Tuple
from decimal import Decimal
import random


def select_activity_by_weight(
    activities: List[Dict[str, Any]]
) -> str:
    """
    Selects an activity from a list based on assigned weights.

    Each activity in the list is a dictionary that must contain 'name' and
    'weight' keys.

    Args:
        activities (List[Dict[str, Any]]): A list of activity dictionaries.
            Example: [{'name': 'swap', 'weight': 50}, {'name': 'lend', 'weight': 30}]

    Returns:
        str: The name of the selected activity.

    Raises:
        ValueError: If the activities list is empty or weights are invalid.

    Example:
        >>> activities = [
        ...     {'name': 'swap', 'weight': 50},
        ...     {'name': 'lend', 'weight': 30},
        ...     {'name': 'bridge', 'weight': 20}
        ... ]
        >>> activity = select_activity_by_weight(activities)
        >>> isinstance(activity, str)
        True
        >>> activity in ['swap', 'lend', 'bridge']
        True
    """
    if not activities:
        raise ValueError("Activities list cannot be empty")
    
    # Validate that all activities have required keys
    for activity in activities:
        if not isinstance(activity, dict):
            raise ValueError("Each activity must be a dictionary")
        if 'name' not in activity:
            raise ValueError("Each activity must have a 'name' key")
        if 'weight' not in activity:
            raise ValueError("Each activity must have a 'weight' key")
        if not isinstance(activity['weight'], (int, float)) or activity['weight'] <= 0:
            raise ValueError("Activity weights must be positive numbers")
    
    # Extract names and weights
    names = [activity['name'] for activity in activities]
    weights = [activity['weight'] for activity in activities]
    
    # Use random.choices for weighted selection
    selected = random.choices(names, weights=weights, k=1)
    return str(selected[0])


def generate_random_amount(
    min_amount: Decimal,
    max_amount: Decimal,
    decimals: int
) -> Decimal:
    """
    Generates a random Decimal amount within a specified range and precision.

    Args:
        min_amount (Decimal): The minimum possible amount.
        max_amount (Decimal): The maximum possible amount.
        decimals (int): The number of decimal places for the generated amount.

    Returns:
        Decimal: A randomly generated amount.

    Raises:
        ValueError: If min_amount > max_amount.

    Example:
        >>> from decimal import Decimal
        >>> min_amt = Decimal('0.01')
        >>> max_amt = Decimal('1.00')
        >>> amount = generate_random_amount(min_amt, max_amt, 2)
        >>> isinstance(amount, Decimal)
        True
        >>> min_amt <= amount <= max_amt
        True
    """
    if min_amount > max_amount:
        raise ValueError("min_amount cannot be greater than max_amount")
    
    if decimals < 0:
        raise ValueError("decimals must be non-negative")
    
    # Convert to float for random.uniform, then back to Decimal
    min_float = float(min_amount)
    max_float = float(max_amount)
    
    # Generate random float amount
    random_float = random.uniform(min_float, max_float)
    
    # Convert to Decimal and round to specified decimals
    random_decimal = Decimal(str(random_float))
    
    # Create quantizer for rounding
    quantizer = Decimal('0.1') ** decimals
    
    return random_decimal.quantize(quantizer)


def select_random_tokens(
    token_config: Dict[str, Any],
    num_tokens: int = 2
) -> Tuple[str, ...]:
    """
    Selects a random pair of tokens from the configuration.

    Args:
        token_config (Dict[str, Any]): A dictionary where keys are token symbols.
        num_tokens (int): The number of unique tokens to select.

    Returns:
        Tuple[str, ...]: A tuple containing the selected token symbols (e.g., ("ETH", "USDC")).

    Raises:
        ValueError: If token_config is empty or num_tokens is invalid.

    Example:
        >>> token_config = {
        ...     'ETH': {'address': '0x123'},
        ...     'USDC': {'address': '0x456'},
        ...     'DAI': {'address': '0x789'}
        ... }
        >>> tokens = select_random_tokens(token_config, 2)
        >>> isinstance(tokens, tuple)
        True
        >>> len(tokens) == 2
        True
        >>> all(token in token_config for token in tokens)
        True
    """
    if not token_config:
        raise ValueError("token_config cannot be empty")
    
    if num_tokens <= 0:
        raise ValueError("num_tokens must be positive")
    
    available_tokens = list(token_config.keys())
    
    if num_tokens > len(available_tokens):
        raise ValueError(f"Cannot select {num_tokens} tokens from {len(available_tokens)} available tokens")
    
    # Use random.sample to select unique tokens
    selected_tokens = random.sample(available_tokens, num_tokens)
    
    return tuple(selected_tokens)


__all__ = [
    "select_activity_by_weight",
    "generate_random_amount", 
    "select_random_tokens",
]