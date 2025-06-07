"""Configuration constants for EigenLayer protocol operations."""

# LST Token Addresses (Ethereum Mainnet)
STETH_TOKEN_ADDRESS = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
RETH_TOKEN_ADDRESS = "0xae78736Cd615f374D3085123A210448E74Fc6393"

# EigenLayer Strategy Addresses (Ethereum Mainnet)
STETH_STRATEGY_ADDRESS = "0x93c4b944D05dfe6df72a2751b1A0541D03217475"
RETH_STRATEGY_ADDRESS = "0x1BeE69b7dFFfA4E2d53C2A2Df135C34A2B5202c3"

# EigenLayer StrategyManager Address (Ethereum Mainnet)
STRATEGY_MANAGER_ADDRESS = "0x858646372CC42E1A627fcE94aa7A7033e7CF075A"

# Gas settings
DEFAULT_GAS_MULTIPLIER = 1.2
DEFAULT_GAS_LIMIT_APPROVAL = 100000
DEFAULT_GAS_LIMIT_DEPOSIT = 300000

# Mapping for easy lookup
LST_ASSET_DETAILS = {
    "stETH": {
        "token_address": STETH_TOKEN_ADDRESS,
        "strategy_address": STETH_STRATEGY_ADDRESS,
        "token_abi_file": "ERC20.json",
        "strategy_abi_file": "StrategyBaseTVLLimits_stETH.json"
    },
    "rETH": {
        "token_address": RETH_TOKEN_ADDRESS,
        "strategy_address": RETH_STRATEGY_ADDRESS,
        "token_abi_file": "ERC20.json",
        "strategy_abi_file": "StrategyBaseTVLLimits_stETH.json"
    }
}

# Canonical contract mapping for EigenLayer protocol
EIGENLAYER_CONTRACTS = {
    "StrategyManager": STRATEGY_MANAGER_ADDRESS,
    "stETH": STETH_STRATEGY_ADDRESS,
    "rETH": RETH_STRATEGY_ADDRESS,
    "steth_strategy": STETH_STRATEGY_ADDRESS,
    "reth_strategy": RETH_STRATEGY_ADDRESS,
}

# Supported LST tokens
LST_TOKENS = {
    "stETH": STETH_TOKEN_ADDRESS,
    "rETH": RETH_TOKEN_ADDRESS,
}