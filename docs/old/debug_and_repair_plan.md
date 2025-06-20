# Cryptofarm Debug and Repair Plan

## Overview
This plan addresses the broken imports and test failures following the structural refactoring that eliminated the nested `airdrops` directory structure.

## Current State Analysis
- **Before**: `airdrops/src/airdrops/module/file.py`
- **After**: `src/airdrops/module/file.py`
- **Impact**: All import statements need updating throughout codebase

## Phase 1: Initial Triage &amp; Import Fixes (Days 1-3)

### Sprint 1.1: Error Discovery &amp; Cataloging
**Goal**: Run pytest/mypy to catalog all import errors
**Tasks**:
1. Run `pytest --tb=short` to get concise error list
2. Run `mypy src/ tests/` to find type/import issues
3. Create error inventory spreadsheet with:
   - File path
   - Error type (ImportError, ModuleNotFoundError, etc.)
   - Old import statement
   - Required new import
4. Identify common patterns for bulk fixes

### Sprint 1.2: Configuration Updates
**Goal**: Update tool configurations for new structure
**Tasks**:
1. Update `pyproject.toml`:
   - Fix package paths
   - Update tool.pytest paths
   - Verify mypy paths
2. Update `conftest.py` for correct imports
3. Ensure PYTHONPATH includes project root
4. Update `.pre-commit-config.yaml` if needed

### Sprint 1.3: Core Import Fixes
**Goal**: Fix all import statements in src/
**Priority Order**:
1. `src/airdrops/shared/` - foundation modules
2. `src/airdrops/protocols/` - protocol implementations  
3. `src/airdrops/cross_chain/` - adapter modules
4. `src/airdrops/analytics/` - analytics modules
5. `src/airdrops/monitoring/` - monitoring modules
6. `src/airdrops/scheduler/` - scheduler bot
7. `src/airdrops/capital_allocation/` - allocation engine
8. `src/airdrops/risk_management/` - risk modules

### Sprint 1.4: Test Import Fixes
**Goal**: Fix all import statements in tests/
**Tasks**:
1. Update imports in test files to match new structure
2. Fix relative imports in test modules
3. Update mock imports and patches
4. Verify conftest.py fixtures work

## Phase 2: Module-by-Module Repair (Days 4-7)

### Sprint 2.1: Shared &amp; Utils Modules
**Goal**: Ensure foundation modules pass all checks
**Tasks**:
1. Run `ruff check src/airdrops/shared/`
2. Run `mypy src/airdrops/shared/`
3. Run `pytest tests/shared/`
4. Fix any issues found
5. Update `/docs/shared_utils.md`

### Sprint 2.2: Protocol Modules
**Goal**: Fix each protocol implementation
**Priority**:
1. **Scroll** - most complex with multiple components
2. **zkSync** - similar complexity to Scroll
3. **LayerZero** - cross-chain messaging
4. **EigenLayer** - staking protocol
5. **Hyperliquid** - perpetuals trading
6. **Solana** - different blockchain

**For each protocol**:
- Run ruff/mypy on protocol module
- Run protocol-specific tests
- Update protocol documentation in `/docs/protocols/`

### Sprint 2.3: Cross-Chain &amp; Analytics
**Goal**: Fix bridge adapters and analytics
**Tasks**:
1. Fix cross-chain manager and adapters
2. Fix analytics modules (tracker, reporter, optimizer)
3. Run respective test suites
4. Update module documentation

### Sprint 2.4: Monitoring &amp; Scheduler
**Goal**: Fix monitoring and bot scheduler
**Tasks**:
1. Fix monitoring components
2. Fix scheduler bot imports
3. Verify configuration loading works
4. Test health checks and alerts

## Phase 3: Integration &amp; E2E Testing (Days 8-10)

### Sprint 3.1: Integration Tests
**Goal**: Ensure components work together
**Tasks**:
1. Run `pytest tests/integration/`
2. Fix any integration issues
3. Verify cross-module imports work
4. Test configuration loading

### Sprint 3.2: End-to-End Tests
**Goal**: Validate complete workflows
**Tasks**:
1. Run `pytest tests/test_end_to_end.py`
2. Run `pytest tests/test_e2e_farming_cycles.py`
3. Fix any workflow issues
4. Verify scheduler can load protocols

### Sprint 3.3: Final Validation
**Goal**: Ensure all quality checks pass
**Tasks**:
1. Run full test suite: `pytest`
2. Run full linting: `ruff check .`
3. Run full type checking: `mypy .`
4. Generate coverage report
5. Update main documentation

## Success Criteria
- [ ] All pytest tests pass (100%)
- [ ] Ruff reports no issues
- [ ] Mypy reports no type errors
- [ ] Coverage remains above 80%
- [ ] All module docs updated
- [ ] CI/CD pipeline green

## Risk Mitigation
1. **Circular Imports**: Use TYPE_CHECKING imports where needed
2. **Dynamic Imports**: Search for importlib usage and update
3. **Configuration Paths**: Verify all file paths in configs
4. **Mock Patches**: Update all @patch decorators with new paths

## Rollback Plan
If critical issues arise:
1. Git tag current broken state
2. Create fix branches for each phase
3. Ability to revert individual modules
4. Keep detailed changelog of fixes