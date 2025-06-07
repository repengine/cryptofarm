# EigenLayer Protocol Module

## Overview

The EigenLayer protocol module provides functionality for interacting with EigenLayer's restaking protocol on Ethereum mainnet. This module enables users to deposit Liquid Staking Tokens (LSTs) into EigenLayer Strategy contracts to earn additional rewards through restaking.

## Supported Operations

### LST Restaking
- **stETH Restaking**: Deposit Lido staked ETH (stETH) into EigenLayer's stETH Strategy
- **rETH Restaking**: Deposit Rocket Pool ETH (rETH) into EigenLayer's rETH Strategy

## Configuration

The module uses the following contract addresses on Ethereum mainnet:

### LST Token Addresses
- **stETH**: `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84`
- **rETH**: `0xae78736Cd615f374D3085123A210448E74Fc6393`

### EigenLayer Strategy Addresses
- **stETH Strategy**: `0x93c4b944D05dfe6df72a2751b1A0541D03217475`
- **rETH Strategy**: `0x1BeE69b7dFFfA4E2d53C2A2Df135C34A2B5202c3`

### StrategyManager
- **StrategyManager**: `0x858646372CC42E1A627fcE94aa7A7033e7CF075A`

## Functions

### `restake_lst(web3_eth, private_key, lst_symbol, amount)`

Deposits the specified LST into its corresponding EigenLayer Strategy contract.

**Parameters:**
- `web3_eth` (Web3): Web3 instance connected to Ethereum Mainnet
- `private_key` (str): The private key of the user's wallet
- `lst_symbol` (str): The symbol of the LST to deposit ("stETH" or "rETH")
- `amount` (int): The amount of LST to deposit, in its smallest unit (wei)

**Returns:**
- `Tuple[bool, Optional[str]]`: Success status and transaction hash or error message

**Process:**
1. Validates input parameters and LST symbol
2. Checks user's LST balance
3. Verifies deposit won't exceed strategy cap
4. Approves strategy contract to spend LST tokens
5. Deposits LST tokens into the strategy contract

**Example:**
```python
from web3 import Web3
from airdrops.protocols.eigenlayer import restake_lst

# Initialize Web3 connection
w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_KEY"))

# Restake 1 stETH
success, result = restake_lst(
    web3_eth=w3,
    private_key="0x...",
    lst_symbol="stETH",
    amount=1000000000000000000  # 1 stETH in wei
)

if success:
    print(f"Restaking successful! Transaction hash: {result}")
else:
    print(f"Restaking failed: {result}")
```

## Error Handling

The module defines custom exceptions for different error scenarios:

- **`UnsupportedLSTError`**: Raised when an unsupported LST symbol is provided
- **`EigenLayerRestakeError`**: Base exception for restaking operation failures
- **`DepositCapReachedError`**: Raised when deposit would exceed strategy cap

## Security Considerations

- Private keys are never logged or stored
- All contract addresses are validated using checksums
- Transaction parameters are validated before execution
- Gas estimation is performed to prevent failed transactions
- Deposit caps are checked to prevent failed deposits

## Gas Optimization

- Default gas limits are configured for approval and deposit operations
- Gas estimation is performed with a safety multiplier
- Failed gas estimation triggers appropriate error handling

## Dependencies

- `web3.py`: Ethereum blockchain interaction
- `typing`: Type hints for better code clarity
- Standard library modules for JSON handling and logging

## Testing

Comprehensive unit tests cover:
- Successful restaking scenarios for both stETH and rETH
- Error handling for various failure modes
- Input validation and edge cases
- Contract interaction mocking
- Gas estimation and transaction building

Run tests with:
```bash
pytest airdrops/tests/protocols/test_eigenlayer.py -v