# Edge Case Reports

This file documents edge cases and critical fixes applied to the system.

---

## 2025-06-19: Circular Dependency in Test Suite

**Timestamp:** 2025-06-19 23:14:00 EST
**Test:** `tests/test_failure_recovery.py`
**Issue:** ModuleNotFoundError: No module named 'manager' caused by dynamic sys.modules injection

**Root Cause:**
The test file was dynamically injecting mock modules into `sys.modules` at the bottom of the file, which created a fragile import environment when tests ran globally. The imports inside test methods were trying to import non-existent modules before the mocks were registered.

**Fix Applied:**
Moved the `MockComponents` class and `sys.modules` injection to the top of the file, before the test class definition. This ensures the mocks are registered before any test method tries to import the non-existent modules.

**Verification:**
- ✅ pytest tests/test_failure_recovery.py passes
- ✅ Full test suite runs (776 passed, 1 unrelated failure) 
- ✅ ruff check passes
- ✅ mypy errors are pre-existing (not related to this fix)

**CI Link:** N/A (local fix)

---