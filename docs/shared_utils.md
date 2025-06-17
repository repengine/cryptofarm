# Shared Utilities Module Documentation

## Overview

The `airdrops.shared.utils` module provides essential utility functions for the airdrop automation system. This module contains core functionality for currency formatting, unique ID generation, decimal conversion, configuration management, and blockchain interaction utilities.

## Module Structure

```
airdrops/src/airdrops/shared/
├── __init__.py          # Module exports
└── utils.py             # Core utility functions
```

## Core Functions

### Currency Formatting

#### `format_currency(amount, symbol="$", precision=2)`
Formats numeric values as currency strings with proper decimal precision.

**Features:**
- Uses Python's `Decimal` type for precise financial calculations
- Handles negative values with proper formatting
- Customizable currency symbol and decimal precision
- Comprehensive input validation and type checking

**Usage Example:**
```python
from airdrops.shared.utils import format_currency
from decimal import Decimal

# Basic usage
print(format_currency(1234.56))  # "$1234.56"
print(format_currency(Decimal("1234.567"), precision=3))  # "$1234.567"

# Custom symbol
print(format_currency(100, symbol="€"))  # "€100.00"

# Negative values
print(format_currency(-50.25))  # "-$50.25"
```

### Unique ID Generation

#### `generate_unique_id()`
Generates UUID-based unique identifiers for system components.

**Features:**
- Uses `uuid.uuid4()` for cryptographically secure random UUIDs
- Returns string representation for easy storage and transmission
- Guaranteed uniqueness across distributed systems

**Usage Example:**
```python
from airdrops.shared.utils import generate_unique_id

# Generate unique transaction ID
tx_id = generate_unique_id()
print(tx_id)  # "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### Decimal Conversion

#### `convert_to_decimal(value)`
Safely converts various numeric types to Python's `Decimal` type.

**Features:**
- Handles `int`, `float`, `str`, and existing `Decimal` inputs
- Comprehensive type validation with descriptive error messages
- Identity optimization for existing `Decimal` objects
- Robust error handling for invalid inputs

**Usage Example:**
```python
from airdrops.shared.utils import convert_to_decimal
from decimal import Decimal

# Convert various types
print(convert_to_decimal(42))        # Decimal('42')
print(convert_to_decimal("123.45"))  # Decimal('123.45')
print(convert_to_decimal(3.14159))   # Decimal('3.14159')

# Identity check for existing Decimals
existing = Decimal("100.00")
result = convert_to_decimal(existing)
assert result is existing  # Same object reference
```

### Configuration Management

#### `load_config(file_path)`
Loads JSON configuration files with comprehensive error handling.

**Features:**
- JSON file parsing with proper error handling
- Custom `ConfigError` exceptions for configuration issues
- File existence validation
- Malformed JSON detection and reporting

**Usage Example:**
```python
from airdrops.shared.utils import load_config, ConfigError

try:
    config = load_config("config/settings.json")
    print(f"Loaded config: {config}")
except ConfigError as e:
    print(f"Configuration error: {e}")
```

#### `save_config(config, file_path)`
Saves configuration dictionaries to JSON files.

**Features:**
- Automatic directory creation for nested paths
- Pretty-printed JSON output with proper indentation
- Comprehensive error handling for write operations
- Type validation for configuration data

**Usage Example:**
```python
from airdrops.shared.utils import save_config, ConfigError

config = {
    "api_endpoint": "https://api.example.com",
    "timeout": 30,
    "retry_attempts": 3
}

try:
    save_config(config, "config/app_settings.json")
    print("Configuration saved successfully")
except ConfigError as e:
    print(f"Failed to save config: {e}")
```

### Exception Classes

#### `ConfigError`
Custom exception class for configuration-related errors.

**Features:**
- Inherits from built-in `Exception` class
- Used by configuration management functions
- Provides clear error context for debugging

## Blockchain Integration

### Web3 Transaction Support

The module includes type annotations and utilities for Web3 transaction handling:

- `TxReceipt` type alias for Web3 transaction receipts
- Support for blockchain transaction processing
- Integration with Web3.py ecosystem

## Type Safety

### Full mypy Compliance

All functions include comprehensive type annotations:
- Input parameter types
- Return value types
- Exception specifications
- Generic type support where applicable

### Supported Types

- `Union` types for flexible input handling
- `Optional` types for nullable parameters
- `Dict[str, Any]` for configuration data
- `Decimal` for precise numeric calculations

## Testing Coverage

### Comprehensive Test Suite

Located in `tests/shared/test_utils.py`:

- **Positive test cases**: Normal operation scenarios
- **Edge case testing**: Boundary conditions and special values
- **Error handling**: Exception scenarios and error recovery
- **Type validation**: Input type checking and conversion
- **Integration testing**: Cross-function compatibility

### Test Categories

1. **Currency Formatting Tests**
   - Various numeric input types
   - Custom symbols and precision
   - Negative value handling
   - Edge cases (zero, very large numbers)

2. **UUID Generation Tests**
   - Uniqueness validation
   - Format verification
   - Performance testing

3. **Decimal Conversion Tests**
   - Type conversion accuracy
   - Error handling for invalid inputs
   - Identity preservation for existing Decimals

4. **Configuration Management Tests**
   - File loading and saving
   - Error handling for missing/corrupted files
   - Directory creation for nested paths

## Quality Assurance

### Code Quality Standards

- **flake8**: Zero style violations
- **mypy --strict**: Full type checking compliance
- **pytest**: 100% test coverage
- **Google-style docstrings**: Complete documentation

### Performance Characteristics

- **Currency formatting**: O(1) complexity
- **UUID generation**: O(1) complexity  
- **Decimal conversion**: O(1) complexity
- **Configuration I/O**: O(n) where n is config size

## Dependencies

### Standard Library
- `decimal`: Precise decimal arithmetic
- `json`: Configuration file handling
- `pathlib`: File system operations
- `uuid`: Unique identifier generation
- `typing`: Type annotations

### External Dependencies
- `web3`: Blockchain interaction support (type annotations only)

## Integration Points

### System Integration

The shared utilities module integrates with:

- **Risk Management System**: Currency formatting for financial calculations
- **Capital Allocation Engine**: Decimal precision for portfolio calculations  
- **Monitoring Infrastructure**: Unique ID generation for tracking
- **Analytics Platform**: Configuration management for settings
- **Protocol Modules**: Transaction receipt handling

### Import Structure

```python
# Direct function imports
from airdrops.shared.utils import (
    format_currency,
    generate_unique_id,
    convert_to_decimal,
    load_config,
    save_config,
    ConfigError
)

# Module-level import
from airdrops.shared import utils
```

## Future Enhancements

### Planned Features

1. **Enhanced Currency Support**
   - Multi-currency formatting
   - Locale-aware number formatting
   - Currency conversion utilities

2. **Advanced Configuration**
   - YAML configuration support
   - Environment variable integration
   - Configuration validation schemas

3. **Extended Utilities**
   - Date/time formatting utilities
   - Logging configuration helpers
   - Network utility functions

### Backward Compatibility

All future enhancements will maintain backward compatibility with existing function signatures and behavior.