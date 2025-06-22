# Changelog

## [Unreleased]

### Added
- feat(test): Capital allocation engine unit tests - Comprehensive test suite for CapitalAllocator initialization with 26 test cases covering default configuration, custom configuration validation, environment variable handling, error handling, and dependency injection scenarios
- feat(code): Portfolio optimization algorithm tests - Added comprehensive unit tests for portfolio optimization algorithms in CapitalAllocator with 56 test cases covering equal weight, risk parity, mean variance strategies, constraint handling, and edge cases with full mypy strict compliance

### Fixed
- fix(debug): Capital allocation interface signature mismatch - Updated ICapitalAllocator protocol interface to match CapitalAllocator implementation signatures for optimize_portfolio and rebalance_portfolio methods, resolving mypy strict type checking errors while maintaining all 56 passing tests
- fix(debug): Mypy import path error - Resolved "Source file found twice under different module names" error by standardizing import statements in tests/capital_allocation/test_engine.py from `src.airdrops.*` to `airdrops.*` pattern, consistent with project conventions
- fix(debug): Type conversion errors - Corrected all incompatible type conversions (int to Decimal, float to Wei) across the codebase for mypy compliance
- fix(debug): Addressed verification failures. Added `apscheduler` dependency, fixed all `ruff` linting errors, and resolved all `mypy` strict type-checking issues in `scroll.py` and its corresponding integration tests.
- fix(debug): Mock object attribute errors - Fixed mypy error in tests/test_scenarios.py where MagicMock record_transaction method was not recognized as having assert_called_once_with attribute. Updated mock fixture to use proper MagicMock with spec and added type ignore comment for assertion.
- fix(debug): Import integrity failure in Scroll protocol - Fixed inconsistent import patterns by converting absolute imports to relative imports in scroll.py and shared/__init__.py for proper module resolution
- fix(debug): Mypy errors in test_scenarios.py - Resolved all remaining mypy errors by fixing MetricsCollector.record_transaction method calls with missing required parameters (action, wallet, gas_used, tx_hash), corrected mock fixture type annotations, and added proper null checks for mock objects to achieve 100% mypy compliance