# Codebase Refactoring Plan

## Overview
This document outlines the phased approach to refactoring the cryptofarm codebase for better organization, maintainability, and clarity.

## Phase 1: Directory Structure Cleanup ✅ COMPLETED

### Objective
Clean up the directory structure by relocating Grafana dashboard files to a more appropriate location.

### Actions Completed
- ✅ Created new directory: `docs/dashboards`
- ✅ Moved all JSON dashboard files from `airdrops/monitoring/dashboards` to `docs/dashboards`:
  - `alerting-system.json`
  - `capital-allocation.json`
  - `risk-management.json`
  - `scheduler-performance.json`
  - `system-overview.json`
- ✅ Moved `README.md` from `airdrops/monitoring/dashboards` to `docs/dashboards`
- ✅ Removed empty `airdrops/monitoring/dashboards` directory

### Rationale
- Dashboard files are documentation artifacts and belong in the `docs/` hierarchy
- Consolidates all documentation in a single location
- Reduces clutter in the application-specific `airdrops/` directory

### Status: COMPLETED ✅
**Completion Date:** 2025-06-16

---

## Phase 2: Cross-Chain Unification

### Objective
To refactor the cross-chain interaction logic by introducing a unified `BridgeAdapter` interface. This will decouple the `CrossChainManager` from specific bridge protocol implementations, making the system more modular and extensible.

### Detailed Plan

#### 1. `BridgeAdapter` Abstract Base Class

An abstract base class, `BridgeAdapter`, will be created in a new file at `airdrops/src/airdrops/cross_chain/bridge_adapter.py`. This class will define the common interface for all bridge adapters.

**Interface Definition:**
```python
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List

class BridgeAdapter(ABC):
    """Abstract base class for all bridge protocol adapters."""

    @abstractmethod
    def get_supported_chains(self) -> List[str]:
        """Returns a list of chain names supported by the bridge."""
        pass

    @abstractmethod
    def get_supported_assets(self, chain: str) -> List[str]:
        """Returns a list of asset symbols supported on a given chain."""
        pass

    @abstractmethod
    def estimate_bridge_fee(self, source_chain: str, destination_chain: str, asset: str, amount: Decimal) -> Decimal:
        """Estimates the fee for a bridge transaction."""
        pass

    @abstractmethod
    def bridge_assets(self, source_chain: str, destination_chain: str, asset: str, amount: Decimal, recipient_address: str) -> str:
        """
        Initiates a bridge transaction.
        
        Returns:
            A transaction hash or a unique job ID for tracking.
        """
        pass
```

#### 2. Concrete Adapter Implementations

Concrete adapters will be created for each supported bridging protocol. Each adapter will implement the `BridgeAdapter` interface, wrapping the existing protocol-specific functions.

*   **`LayerZeroBridgeAdapter`** ✅ IMPLEMENTED:
    *   Wraps the LayerZero protocol's `send_message` function in `airdrops/src/airdrops/protocols/layerzero/layerzero.py`.
    *   Located at `airdrops/src/airdrops/cross_chain/adapters/layerzero_adapter.py`.
    *   Comprehensive test suite at `airdrops/tests/cross_chain/adapters/test_layerzero_adapter.py`.
*   **`ZkSyncBridgeAdapter`** ✅ IMPLEMENTED:
    *   Wraps the `bridge_assets` function in `airdrops/src/airdrops/protocols/zksync/zksync.py`.
    *   Located at `airdrops/src/airdrops/cross_chain/adapters/zksync_adapter.py`.
    *   Comprehensive test suite at `airdrops/tests/cross_chain/adapters/test_zksync_adapter.py`.
*   **`ScrollBridgeAdapter`** ✅ IMPLEMENTED:
    *   Wraps the `bridge_assets` function in `airdrops/src/airdrops/protocols/scroll/scroll.py`.
    *   Located at `airdrops/src/airdrops/cross_chain/adapters/scroll_adapter.py`.
    *   Comprehensive test suite at `airdrops/tests/cross_chain/adapters/test_scroll_adapter.py`.

#### 3. `CrossChainManager` Integration ✅ IMPLEMENTED

The `CrossChainManager` has been refactored to use the `BridgeAdapter` interface.

*   **Adapter Registration** ✅ IMPLEMENTED: The manager now accepts a list of bridge adapters in its constructor and stores them in `self._bridge_adapters`.
*   **Dynamic Adapter Selection** ✅ IMPLEMENTED: The `_get_adapter_for_job` method dynamically selects the appropriate adapter based on the source and destination chains of the rebalancing job.
*   **Execution** ✅ IMPLEMENTED: The `initiate_rebalancing` method uses the selected adapter's `bridge_assets` method to execute the cross-chain transfer.

#### 4. Comprehensive Test Suite ✅ IMPLEMENTED

*   **Manager Integration Tests**: Complete test suite for `CrossChainManager` with BridgeAdapter integration
*   **Adapter Selection Tests**: Tests for correct adapter selection based on job requirements
*   **Error Handling Tests**: Tests for scenarios where no suitable adapter is found
*   **Mock Adapter Tests**: Tests using mock adapters for all supported protocols

### Status: COMPLETED ✅
**Completion Date:** 2025-06-16

---

## Phase 3: System Integration ✅ COMPLETED

### Objective
Integrate the `CrossChainManager` with the `AirdropSchedulerBot` to enable automated, periodic liquidity checks and rebalancing operations.

### Actions Completed
- ✅ Modified `AirdropSchedulerBot.__init__()` to accept optional `CrossChainManager` instance
- ✅ Added `schedule_rebalancing_checks()` method to `AirdropSchedulerBot` class
- ✅ Implemented automated scheduling of `CrossChainManager.check_liquidity_thresholds()` using APScheduler interval triggers
- ✅ Added comprehensive test suite covering:
  - Integration initialization and configuration
  - Successful scheduling with various time intervals
  - Error handling for missing dependencies
  - Job replacement and update scenarios
  - Edge cases and validation
- ✅ Updated documentation in `airdrops/docs/scheduler.md` and `airdrops/docs/cross_chain_management.md`
- ✅ Added usage examples and configuration patterns

### Technical Implementation
- **Integration Pattern**: Optional dependency injection through constructor parameter
- **Scheduling Method**: `schedule_rebalancing_checks(interval_hours: float)` with APScheduler IntervalTrigger
- **Error Handling**: Comprehensive validation and graceful failure handling
- **Job Management**: Automatic replacement of existing jobs when rescheduling
- **Priority**: High priority scheduling for rebalancing checks
- **Retry Logic**: Reduced retry attempts (2) for monitoring tasks

### Status: COMPLETED ✅
**Completion Date:** 2025-06-16

---

## Notes
- All changes maintain backward compatibility
- No functional code was modified during Phase 1
- Dashboard files remain accessible at their new location: `docs/dashboards/`
- Phase 3 integration enables automated cross-chain capital management