Testing Strategy
================

This document outlines the comprehensive testing approach for the Airdrops system, ensuring reliability, performance, and maintainability.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

Our testing strategy ensures >85% code coverage through multiple testing levels:

* **Unit Tests** - Test individual functions and classes
* **Integration Tests** - Verify component interactions
* **Property-Based Tests** - Validate system invariants
* **Performance Tests** - Ensure operations meet speed requirements
* **End-to-End Tests** - Simulate real-world scenarios
* **Failure Recovery Tests** - Verify resilience

Test Organization
-----------------

Test Structure
~~~~~~~~~~~~~~

.. code-block:: text

   tests/
   ├── test_*.py                    # Unit tests
   ├── integration/                 # Integration tests
   │   ├── test_scroll_integration.py
   │   ├── test_zksync_integration.py
   │   ├── test_scheduler_protocols.py
   │   ├── test_capital_allocation_integration.py
   │   └── test_monitoring_integration.py
   ├── test_property_based.py       # Property-based tests
   ├── test_performance_benchmarks.py # Performance tests
   ├── test_end_to_end.py          # E2E scenarios
   └── test_failure_recovery.py     # Failure tests

Unit Testing
------------

Unit tests verify individual components in isolation.

**Example:**

.. code-block:: python

   @patch('web3.Web3')
   def test_bridge_eth(mock_web3):
       """Test ETH bridging functionality."""
       # Setup mock
       mock_web3.eth.get_balance.return_value = Web3.to_wei(1, 'ether')
       
       # Execute test
       success, tx_hash = bridge_eth(
           mock_web3, 
           wallet_address,
           amount=Decimal("0.1")
       )
       
       # Verify
       assert success is True
       assert tx_hash.startswith('0x')

Integration Testing
-------------------

Integration tests verify components work together correctly.

**Key Integration Points:**

1. **Protocol + Scheduler**
   
   .. code-block:: python
   
      def test_scheduler_executes_protocol_tasks():
          scheduler = CentralScheduler(config)
          task = create_protocol_task("scroll", "swap")
          result = scheduler.execute_task(task)
          assert result["success"] is True

2. **Capital Allocation + Risk Management**
   
   .. code-block:: python
   
      def test_risk_adjusted_allocation():
          allocator = CapitalAllocator(config)
          risk_manager = RiskManager(config)
          
          portfolio = allocator.optimize_portfolio(protocols)
          risk_check = risk_manager.validate_portfolio(portfolio)
          assert risk_check["approved"] is True

3. **Monitoring + Alerting**
   
   .. code-block:: python
   
      def test_alert_on_high_failure_rate():
          collector = MetricsCollector()
          alerter = Alerter(config)
          
          # Record failures
          for _ in range(10):
              collector.record_failure("scroll", "swap")
          
          # Check alerts triggered
          alerts = alerter.check_alerts()
          assert len(alerts) > 0

Property-Based Testing
----------------------

Using Hypothesis framework to test invariants:

.. code-block:: python

   from hypothesis import given, strategies as st
   
   @given(
       protocols=st.lists(st.sampled_from(["scroll", "zksync"]), min_size=1),
       total_capital=st.decimals(min_value=1000, max_value=1000000)
   )
   def test_allocation_never_exceeds_capital(protocols, total_capital):
       allocations = allocator.allocate(protocols, total_capital)
       assert sum(allocations.values()) <= total_capital

**Key Properties Tested:**

* Allocations sum to total or less
* Rebalancing triggers are consistent
* Task distribution is fair
* Metrics aggregation is correct

Performance Benchmarks
----------------------

Critical operations have performance targets:

.. list-table:: Performance Targets
   :header-rows: 1
   :widths: 40 20 20 20

   * - Operation
     - Target
     - P95
     - Status
   * - Portfolio Optimization
     - <100ms
     - 85ms
     - ✅ Pass
   * - Transaction Building
     - <50ms
     - 42ms
     - ✅ Pass
   * - Metrics Collection
     - >10k/s
     - 12k/s
     - ✅ Pass
   * - Rebalancing Check
     - <10ms
     - 8ms
     - ✅ Pass

End-to-End Testing
------------------

E2E tests simulate complete workflows:

1. **Daily Operation Cycle**
   
   * System initialization
   * Capital allocation
   * Task scheduling
   * Execution and monitoring
   * End-of-day reporting

2. **Multi-Day Portfolio Evolution**
   
   * Performance tracking
   * Rebalancing triggers
   * Risk adjustments
   * Capital preservation

3. **Incident Response**
   
   * Gas price spikes
   * Protocol failures
   * Emergency shutdown

Failure Recovery Testing
------------------------

Tests system resilience:

.. code-block:: python

   def test_network_failover():
       """Test automatic RPC failover."""
       primary_rpc = Mock(is_connected=False)
       backup_rpc = Mock(is_connected=True)
       
       connection = ConnectionManager([primary_rpc, backup_rpc])
       active_rpc = connection.get_connection()
       
       assert active_rpc == backup_rpc

**Scenarios Tested:**

* Network failures with RPC failover
* Transaction retry with gas adjustment
* State recovery after crash
* Data corruption recovery
* Cascading failure prevention

Mocking Strategy
----------------

All external dependencies are mocked:

.. code-block:: python

   # Mock Web3
   mock_web3 = Mock()
   mock_web3.eth.get_balance.return_value = Web3.to_wei(1, "ether")
   mock_web3.eth.gas_price = Web3.to_wei(30, "gwei")
   
   # Mock contracts
   mock_contract = Mock()
   mock_contract.functions.swap.return_value.build_transaction.return_value = {
       "to": "0x123",
       "data": "0xabc",
       "gas": 200000
   }

Continuous Integration
----------------------

**Pre-commit Checks:**

.. code-block:: bash

   poetry run pytest               # Run tests
   poetry run mypy --strict src/   # Type check
   poetry run ruff check src/      # Lint
   poetry run coverage report      # Coverage

**CI Pipeline:**

1. **Fast Tests** (<5 min)
   
   * Unit tests
   * Type checking
   * Linting

2. **Full Suite** (<15 min)
   
   * All tests
   * Coverage report
   * Performance benchmarks

3. **Nightly** 
   
   * Extended E2E tests
   * Load testing
   * Security scanning

Coverage Requirements
---------------------

.. list-table:: Coverage Targets
   :header-rows: 1
   :widths: 50 25 25

   * - Component
     - Target
     - Current
   * - Overall
     - ≥85%
     - 88%
   * - Critical Modules
     - ≥90%
     - 92%
   * - New Code
     - 100%
     - 100%

Testing New Features
--------------------

Follow TDD approach:

1. **Write failing tests** for expected behavior
2. **Implement feature** to make tests pass
3. **Add integration tests** for workflows
4. **Add property tests** for invariants
5. **Add performance tests** if critical path
6. **Document** test rationale

Common Issues
-------------

**Mock Configuration:**

.. code-block:: python

   # ❌ Wrong
   mock.gas_price = 30
   
   # ✅ Correct
   mock.gas_price = 30000000000  # Wei
   
   # ❌ Wrong
   mock.eth.get_balance = 1
   
   # ✅ Correct  
   mock.eth.get_balance.return_value = 1000000000000000000

**Flaky Tests:**

* Use deterministic time mocking
* Clear state between tests
* Add proper waits/retries
* Isolate test dependencies

Running Tests
-------------

.. code-block:: bash

   # All tests
   poetry run pytest
   
   # Specific module
   poetry run pytest tests/test_capital_allocation.py
   
   # With coverage
   poetry run pytest --cov=airdrops --cov-report=html
   
   # Specific test
   poetry run pytest tests/test_scheduler.py::test_task_execution
   
   # Verbose output
   poetry run pytest -v -s

Future Enhancements
-------------------

* **Mutation Testing** - Verify test effectiveness
* **Chaos Engineering** - Random failure injection
* **Load Testing** - High-volume simulation
* **Security Testing** - Automated vulnerability scanning
* **Contract Testing** - Provider/consumer contracts