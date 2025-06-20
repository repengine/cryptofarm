"""
Global pytest configuration for the cryptofarm project.

This file ensures that all test modules can properly import from the tests.mocks package
regardless of their location in the directory structure.
"""
import logging
import pytest

# Configure logging for tests to show INFO and DEBUG messages
logging.basicConfig(level=logging.INFO)

@pytest.fixture(autouse=True)
def setup_logging():
    """Fixture to ensure logging is configured for tests."""
    # This fixture ensures logging is set up before each test
    # The basicConfig call above already sets the root logger level
    pass

@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """
    Fixture to automatically clear the Prometheus registry before each test.
    
    This prevents "Duplicated timeseries in CollectorRegistry" errors when multiple
    tests create MetricsCollector instances that register the same metrics.
    
    This fixture is automatically applied to all tests (autouse=True) to ensure
    consistent test isolation for Prometheus metrics.
    
    Example:
        >>> def test_example():
        ...     from airdrops.monitoring.collector import MetricsCollector
        ...     collector = MetricsCollector()
        ...     assert collector is not None
    """
    import prometheus_client
    
    # Clear the global Prometheus registry before the test
    prometheus_client.REGISTRY._collector_to_names.clear()
    prometheus_client.REGISTRY._names_to_collectors.clear()

@pytest.fixture
def airdrop_tracker_cleanup():
    """
    Fixture to clean up AirdropTracker resources after tests.
    Ensures that the SQLAlchemy engine is properly disposed for in-memory databases.
    """
    from airdrops.analytics.tracker import AirdropTracker
    
    # Yield control to the test
    yield
    
    # After the test, dispose of the engine if it was created
    # This is important for in-memory databases to prevent resource leaks
    tracker_instance = AirdropTracker() # Re-instantiate to access the engine
    tracker_instance.close_engine()

# @pytest.fixture(autouse=True)
# def aggressive_cleanup():
#     """
#     Aggressively cleans up global state between tests to prevent memory leaks.
#     This includes clearing sys.modules and resetting logging handlers.
#     """
#     # Store initial state of sys.modules
#     initial_sys_modules = set(sys.modules.keys())

#     # Store initial logging handlers
#     root_logger = logging.getLogger()
#     initial_handlers = list(root_logger.handlers)

#     yield

#     # --- Teardown after test execution ---

#     # 1. Clean up sys.modules to force re-import of modules
#     # This helps clear module-level global state that might persist
#     current_sys_modules = set(sys.modules.keys())
#     for module_name in current_sys_modules - initial_sys_modules:
#         if module_name.startswith("airdrops.") or module_name.startswith("tests."):
#             if module_name in sys.modules:
#                 del sys.modules[module_name]

#     # 2. Reset logging handlers
#     for handler in root_logger.handlers:
#         if handler not in initial_handlers:
#             root_logger.removeHandler(handler)
#     for handler in initial_handlers:
#         if handler not in root_logger.handlers:
#             root_logger.addHandler(handler)

#     # Optional: Force garbage collection
#     import gc
#     gc.collect()
