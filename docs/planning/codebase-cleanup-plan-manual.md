# Codebase Cleanup Plan: Manual-First Approach

## 1. Objective

This document outlines a manual-first, phased strategy for improving codebase quality using `ruff`, `mypy`, and `pytest`. The core principle is to perform comprehensive reconnaissance before any code modification, ensuring a deliberate, risk-aware, and transparent cleanup process.

## 2. Guiding Principles

*   **Manual-First, Tool-Assisted:** We will not use automated fixing (`--fix`). Tools will be used for discovery and reporting, with all changes being made manually by developers to ensure context is understood.
*   **Two-Phase Execution:** Each tool's application is split into two distinct phases:
    1.  **Reconnaissance:** A no-change scan to identify, categorize, and assess all issues.
    2.  **Targeted Manual Fixes:** A series of focused sprints to address issues, prioritized by risk.
*   **Risk-Based Prioritization:** Fixes will be addressed in order of severity (High, Medium, Low) to maximize impact and minimize destabilization.

---

## 3. Phase 1: Reconnaissance (Week 1)

**Goal:** To gain a complete and detailed understanding of the current state of the codebase without making any changes.

### Sprint 1.1: Ruff Violation Analysis

*   **Objective:** Identify and categorize all linting violations across the project.
*   **Command:**
    ```bash
    ruff check . --output-format=json --statistics > ruff-report.json
    ```
*   **Deliverable:** A `ruff-report.json` file containing all linting issues.
*   **Analysis:** The JSON output will be analyzed to group violations by type and assess their potential risk.

### Sprint 1.2: MyPy Type Error Analysis

*   **Objective:** Identify all static type checking errors.
*   **Command:**
    ```bash
    mypy src --show-error-codes --json-report reports/mypy
    ```
    *(Note: This command generates a directory with JSON files. These will be consolidated for analysis.)*
*   **Deliverable:** A `reports/mypy` directory containing a detailed JSON report of type violations.
*   **Analysis:** The report will be used to identify areas with weak type coverage and critical type mismatches.

### Sprint 1.3: Test Coverage & Failure Analysis

*   **Objective:** Establish a baseline for test coverage and identify any existing test failures.
*   **Command:**
    ```bash
    pytest --cov=src --cov-report=json:coverage.json
    ```
*   **Deliverable:** A `coverage.json` file and a complete log of the test suite execution.
*   **Analysis:** The coverage report will highlight untested code paths. Test logs will be reviewed for failing or flaky tests.

---

## 4. Phase 2: Targeted Manual Fixes (Weeks 2-7)

**Goal:** Systematically address the issues discovered in Phase 1 through a series of prioritized, focused sprints.

### Sprint Structure

*   **Prioritization:** Sprints will be organized based on the risk level of the issues:
    1.  **High-Risk Sprints:** Address critical bugs, security vulnerabilities, and major type errors.
    2.  **Medium-Risk Sprints:** Address code smells, performance issues, and non-critical warnings.
    3.  **Low-Risk Sprints:** Address formatting, style inconsistencies, and minor refactoring opportunities.
*   **Process:**
    1.  A sprint is defined to target a specific category of issues (e.g., "Fix all `F841` unused variable violations").
    2.  A developer creates a dedicated branch for the sprint.
    3.  Fixes are applied manually.
    4.  A small, focused Pull Request is submitted for review.

---

## 5. Phase 3: Final Validation (Week 8)

**Goal:** Verify that the cleanup has been successful and has not introduced regressions.

*   **Actions:**
    1.  Execute all reconnaissance commands from Phase 1 again.
    2.  Compare the new reports against the initial baselines to confirm that issues have been resolved.
    3.  Perform a full regression test of the application.
    4.  Update all relevant documentation to reflect changes.

## 6. Implementation Timeline

*   **Week 1:** Complete Phase 1: Reconnaissance for `ruff`, `mypy`, and `pytest`.
*   **Weeks 2-7:** Execute Phase 2: Targeted Manual Fix Sprints, prioritized by risk.
*   **Week 8:** Complete Phase 3: Final Validation and Documentation Sync.