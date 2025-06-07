# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **LayerBank Scroll Protocol Critical Issues** - 2025-01-31
  - Fixed invalid ABI files: Replaced placeholder ABIs with correct Compound V2-based interfaces for LayerBankComptroller and LayerBankLbToken contracts
  - Implemented missing repay logic: Added debt balance validation in `_handle_repay_action_scroll` with proper `RepayAmountExceedsDebtError` handling
  - Fixed USDC test mocks: Corrected `mock_layerbank_lbtoken_contract` fixture to use dynamic contract addresses instead of hardcoded lbETH addresses
  - Fixed function name mismatch: Updated test mocks to use `borrowBalanceStored` instead of `borrowBalanceCurrent`
  - LayerBank lending/borrowing functionality now fully operational for Scroll protocol automation

### Added
- Implemented `provide_liquidity_scroll` in `airdrops.protocols.scroll.scroll` for adding/removing liquidity on SyncSwap DEX on Scroll L2, including all required helpers and error handling.
- Added unit tests for `provide_liquidity_scroll` covering add/remove, min amounts, LP approval, deadlines, and error handling.
- Implemented `perform_random_activity_scroll` in `airdrops.protocols.scroll.scroll` for orchestrated random activity execution across all Scroll protocols (bridging, swapping, liquidity provision, lending/borrowing).
- Added comprehensive unit tests for `perform_random_activity_scroll` covering orchestration logic, action selection weights, parameter generation, stop_on_failure behavior, and error handling scenarios.
- Updated protocol documentation, pulse inventory, and configuration for SyncSwap Classic Pool Factory.
- Implemented `swap_tokens` function in `airdrops.protocols.scroll.scroll` for swapping tokens on SyncSwap DEX on Scroll L2. Supports ETH-to-Token, Token-to-ETH, and Token-to-Token swaps.
- Added helper functions for SyncSwap interactions: pool/factory contract loading, pool address discovery, quote fetching (`get_expected_amount_out`), `amountOutMin` calculation, and swap path construction (`_construct_syncswap_paths_scroll`).
- Added ABIs: `SyncSwapRouter.json`, `SyncSwapClassicPoolFactory.json`, `SyncSwapClassicPool.json` to `airdrops/src/airdrops/protocols/scroll/abi/`.
- Added new configuration constants for SyncSwap Router and Classic Pool Factory addresses in `airdrops/src/airdrops/shared/config.py`.
- Added new swap-specific exceptions: `ScrollSwapError`, `InsufficientLiquidityError`, `TokenNotSupportedError` (already existed but now used by swap).
- Implemented comprehensive unit tests for `swap_tokens` and its new helper functions in `airdrops.tests.protocols.test_scroll`, covering various swap scenarios and error conditions.
- Implemented `lend_borrow_layerbank_scroll` function in `airdrops.protocols.scroll.scroll` for LayerBank V2 lending protocol integration on Scroll L2. Supports lend, borrow, repay, and withdraw actions for ETH and USDC.
- Added LayerBank-specific helper functions: `_get_layerbank_lbtoken_address_scroll`, `_check_and_enter_layerbank_market_scroll`, `_get_layerbank_account_liquidity_scroll`, and action handlers for each operation.
- Added LayerBank ABIs: `LayerBankComptroller.json` and `LayerBankLbToken.json` to `airdrops/src/airdrops/protocols/scroll/abi/`.
- Added LayerBank configuration constants: comptroller and lbToken addresses in `airdrops/src/airdrops/shared/config.py`.
- Added lending-specific exceptions: `ScrollLendingError`, `InsufficientCollateralError`, `MarketNotEnteredError`, `RepayAmountExceedsDebtError`, `LayerBankComptrollerRejectionError`.
- Implemented comprehensive unit tests for LayerBank lending functionality covering all actions, error conditions, and helper functions.

### Changed
- Updated `_get_l2_token_address_scroll` to correctly resolve ETH to WETH address for internal operations.
- Enhanced `_build_and_send_tx_scroll` with more detailed logging for gas estimation failures and nonce management during retries.
- Updated `_approve_erc20_scroll` to check current allowance before attempting approval.
- Refined `bridge_assets` in `airdrops.protocols.scroll.scroll` to correctly use L1 execution gas limit for withdrawal transactions and added missing ERC20 approval for L2 withdrawals.

### Fixed
- Corrected `bridge_assets` L1 deposit function calls (`depositETH`, `depositERC20`) to align with ABI by not passing `fee` as a direct argument (it's part of `msg.value`).
- Ensured `to` address is correctly passed in `TxParams` for `_build_and_send_tx_scroll` when building transactions for `bridge_assets`.

### Previous Unreleased (Kept for reference during release)

#### Added (from previous work)
- Custom exceptions for `airdrops.protocols.scroll` module to provide more specific error handling for Scroll bridge operations (`ScrollBridgeError`, `InsufficientBalanceError`, `TransactionRevertedError`, `ApprovalError`, `GasEstimationError`, `MaxRetriesExceededError`, `TransactionBuildError`, `TransactionSendError`).
- Retry logic with nonce management to `_build_and_send_tx_scroll` in `airdrops.protocols.scroll.scroll` to handle transient RPC/network errors.
- Comprehensive unit tests for new custom exceptions and retry logic in `airdrops.tests.protocols.test_scroll`.

### Changed
- Updated `bridge_assets` function docstring in `airdrops.protocols.scroll.scroll` to NumPy style.
- Refactored `_approve_erc20_scroll` in `airdrops.protocols.scroll.scroll` to correctly handle and re-raise `ApprovalError` with the underlying transaction receipt.
- Improved granularity of assertions in existing `airdrops.tests.protocols.test_scroll` unit tests.