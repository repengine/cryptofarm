# Random Activity Utils

## Overview

The `random_activity_utils` module provides shared utility functions for implementing random activity selection in airdrop protocol implementations. This module is part of the `perform_random_activity` feature architecture and provides weighted selection, random amount generation, and token selection capabilities.

## Functions

### `select_activity_by_weight(activities: List[Dict[str, Any]]) -> str`

Selects an activity from a list based on assigned weights using Python's `random.choices()` function.

**Parameters:**
- `activities`: List of activity dictionaries, each containing 'name' and 'weight' keys

**Returns:**
- `str`: The name of the selected activity

**Raises:**
- `ValueError`: If activities list is empty, missing required keys, or weights are invalid

**Example:**
```python
activities = [
    {'name': 'swap', 'weight': 50},
    {'name': 'lend', 'weight': 30},
    {'name': 'bridge', 'weight': 20}
]
selected = select_activity_by_weight(activities)
# Returns one of: 'swap', 'lend', 'bridge' (weighted probability)
```

### `generate_random_amount(min_amount: Decimal, max_amount: Decimal, decimals: int) -> Decimal`

Generates a random Decimal amount within a specified range and precision.

**Parameters:**
- `min_amount`: The minimum possible amount
- `max_amount`: The maximum possible amount  
- `decimals`: The number of decimal places for the generated amount

**Returns:**
- `Decimal`: A randomly generated amount

**Raises:**
- `ValueError`: If min_amount > max_amount or decimals < 0

**Example:**
```python
from decimal import Decimal

min_amt = Decimal('0.01')
max_amt = Decimal('1.00')
amount = generate_random_amount(min_amt, max_amt, 2)
# Returns a Decimal between 0.01 and 1.00 with 2 decimal places
```

### `select_random_tokens(token_config: Dict[str, Any], num_tokens: int = 2) -> Tuple[str, ...]`

Selects random unique tokens from the configuration using `random.sample()`.

**Parameters:**
- `token_config`: Dictionary where keys are token symbols
- `num_tokens`: Number of unique tokens to select (default: 2)

**Returns:**
- `Tuple[str, ...]`: Tuple containing the selected token symbols

**Raises:**
- `ValueError`: If token_config is empty, num_tokens is invalid, or requesting more tokens than available

**Example:**
```python
token_config = {
    'ETH': {'address': '0x123'},
    'USDC': {'address': '0x456'},
    'DAI': {'address': '0x789'}
}
tokens = select_random_tokens(token_config, 2)
# Returns tuple like ('ETH', 'USDC') with unique tokens
```

## Usage in Protocol Implementations

These utilities are designed to be used by protocol-specific `perform_random_activity` implementations:

```python
from airdrops.shared.random_activity_utils import (
    select_activity_by_weight,
    generate_random_amount,
    select_random_tokens,
)

# In a protocol's perform_random_activity function:
def perform_random_activity(config: Dict[str, Any]) -> Dict[str, Any]:
    # Select activity type
    activities = config['random_activity']['action_weights']
    activity_list = [
        {'name': name, 'weight': weight} 
        for name, weight in activities.items()
    ]
    selected_activity = select_activity_by_weight(activity_list)
    
    # Generate random amount
    min_amt = Decimal(str(config['min_amount']))
    max_amt = Decimal(str(config['max_amount']))
    amount = generate_random_amount(min_amt, max_amt, 6)
    
    # Select random tokens
    tokens = select_random_tokens(config['tokens'], 2)
    
    # Execute the selected activity...
```

## Design Principles

- **Stateless**: All functions are pure and thread-safe
- **Type Safety**: Full type annotations with mypy compliance
- **Error Handling**: Comprehensive validation with descriptive error messages
- **Testability**: Deterministic behavior when mocked, comprehensive test coverage
- **Performance**: O(n) complexity for all operations

## Dependencies

- `typing`: For type annotations
- `decimal`: For precise financial calculations
- `random`: For weighted selection and sampling

## Testing

Comprehensive test suite located in `tests/shared/test_random_activity_utils.py` covering:
- Positive test cases for all functions
- Edge cases (empty inputs, boundary values)
- Error conditions with proper exception handling
- Randomness validation and distribution testing
- Mock-based deterministic testing

## Integration

This module integrates with:
- Protocol implementations (ZkSync, Scroll, LayerZero, etc.)
- Scheduler bot for activity execution
- Risk management for amount validation
- Configuration management for activity weights