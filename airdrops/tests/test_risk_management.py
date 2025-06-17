"""
Tests for the airdrops.risk_management.core module.
"""

import pytest
from decimal import Decimal

from airdrops.risk_management.core import (  # type: ignore
    RiskManager,
    RiskLevel,
    RiskEvent,
    RiskAssessment,
)
from airdrops.shared.utils import get_current_timestamp  # type: ignore


@pytest.fixture
def risk_manager():
    """Fixture for a RiskManager instance."""
    config = {
        "risk_management": {
            "volatility_thresholds": {
                "low": Decimal("0.01"),
                "medium": Decimal("0.05"),
                "high": Decimal("0.10"),
                "extreme": Decimal("0.20"),
            },
            "gas_price_threshold_gwei": Decimal("100"),
            "max_consecutive_failures": 3,
            "circuit_breaker_threshold": Decimal("0.8"),  # 80% failure rate
        }
    }
    return RiskManager(config)


def test_initial_state(risk_manager):
    """Test the initial state of the RiskManager."""
    assert risk_manager.current_risk_level == RiskLevel.LOW
    assert risk_manager.protocol_failure_counts == {}
    assert risk_manager.circuit_breaker_active is False


def test_assess_volatility_low(risk_manager):
    """Test volatility assessment for low volatility."""
    metrics = {"price_volatility": Decimal("0.005")}
    risk_level = risk_manager.assess_volatility(metrics)
    assert risk_level == RiskLevel.LOW


def test_assess_volatility_medium(risk_manager):
    """Test volatility assessment for medium volatility."""
    metrics = {"price_volatility": Decimal("0.03")}
    risk_level = risk_manager.assess_volatility(metrics)
    assert risk_level == RiskLevel.MEDIUM


def test_assess_volatility_high(risk_manager):
    """Test volatility assessment for high volatility."""
    metrics = {"price_volatility": Decimal("0.08")}
    risk_level = risk_manager.assess_volatility(metrics)
    assert risk_level == RiskLevel.HIGH


def test_assess_volatility_extreme(risk_manager):
    """Test volatility assessment for extreme volatility."""
    metrics = {"price_volatility": Decimal("0.15")}
    risk_level = risk_manager.assess_volatility(metrics)
    assert risk_level == RiskLevel.EXTREME


def test_assess_gas_price_normal(risk_manager):
    """Test gas price assessment for normal gas prices."""
    metrics = {"gas_price_gwei": Decimal("50")}
    risk_event = risk_manager.assess_gas_price(metrics)
    assert risk_event is None


def test_assess_gas_price_high(risk_manager):
    """Test gas price assessment for high gas prices."""
    metrics = {"gas_price_gwei": Decimal("120")}
    risk_event = risk_manager.assess_gas_price(metrics)
    assert risk_event is not None
    assert risk_event.event_type == "high_gas_price"
    assert risk_event.severity == "high"
    assert risk_event.details == "Current gas price (120.00 Gwei) exceeds threshold (100.00 Gwei)."


def test_assess_transaction_failures_single_protocol(risk_manager):
    """Test transaction failure assessment for a single protocol."""
    # Simulate 1 failure
    risk_manager.record_transaction_outcome("scroll", False)
    assert risk_manager.protocol_failure_counts["scroll"] == 1
    assert risk_manager.assess_transaction_failures("scroll") is None

    # Simulate 2 more failures (total 3)
    risk_manager.record_transaction_outcome("scroll", False)
    risk_manager.record_transaction_outcome("scroll", False)
    risk_event = risk_manager.assess_transaction_failures("scroll")
    assert risk_event is not None
    assert risk_event.event_type == "consecutive_failures"
    assert risk_event.severity == "critical"
    assert risk_event.affected_protocol == "scroll"
    assert "3 consecutive failures" in risk_event.details

    # Simulate a success, should reset count
    risk_manager.record_transaction_outcome("scroll", True)
    assert risk_manager.protocol_failure_counts["scroll"] == 0
    assert risk_manager.assess_transaction_failures("scroll") is None


def test_assess_transaction_failures_multiple_protocols(risk_manager):
    """Test transaction failure assessment for multiple protocols."""
    risk_manager.record_transaction_outcome("zksync", False)
    risk_manager.record_transaction_outcome("eigenlayer", False)
    risk_manager.record_transaction_outcome("zksync", False)
    risk_manager.record_transaction_outcome("eigenlayer", False)
    risk_manager.record_transaction_outcome("zksync", False)  # ZkSync hits 3 failures

    zksync_event = risk_manager.assess_transaction_failures("zksync")
    assert zksync_event is not None
    assert zksync_event.affected_protocol == "zksync"

    eigenlayer_event = risk_manager.assess_transaction_failures("eigenlayer")
    assert eigenlayer_event is None  # Only 2 failures for EigenLayer


def test_check_circuit_breaker_active(risk_manager):
    """Test circuit breaker activation based on overall failure rate."""
    # Simulate metrics that trigger circuit breaker (e.g., 90% failure rate)
    mock_metrics = {
        "total_transactions": 100,
        "successful_transactions": 10,
        "failed_transactions": 90,
        "failure_rate": Decimal("0.9"),
    }
    risk_manager.check_circuit_breaker(mock_metrics)
    assert risk_manager.circuit_breaker_active is True

    # Simulate metrics that deactivate circuit breaker (e.g., 10% failure rate)
    mock_metrics_recovery = {
        "total_transactions": 100,
        "successful_transactions": 90,
        "failed_transactions": 10,
        "failure_rate": Decimal("0.1"),
    }
    risk_manager.check_circuit_breaker(mock_metrics_recovery)
    assert risk_manager.circuit_breaker_active is False


def test_get_overall_risk_assessment(risk_manager):
    """Test getting overall risk assessment."""
    # Simulate some conditions
    risk_manager.current_risk_level = RiskLevel.HIGH
    risk_manager.circuit_breaker_active = True
    risk_manager.protocol_failure_counts["scroll"] = 5

    assessment = risk_manager.get_overall_risk_assessment()
    assert isinstance(assessment, RiskAssessment)
    assert assessment.overall_risk_level == RiskLevel.HIGH
    assert assessment.circuit_breaker_active is True
    assert "scroll" in assessment.unhealthy_protocols
    assert assessment.unhealthy_protocols["scroll"] == 5


def test_update_risk_parameters(risk_manager):
    """Test updating risk parameters dynamically."""
    new_config = {
        "risk_management": {
            "volatility_thresholds": {
                "low": Decimal("0.02"),
                "medium": Decimal("0.06"),
            },
            "gas_price_threshold_gwei": Decimal("150"),
        }
    }
    risk_manager.update_risk_parameters(new_config)

    assert risk_manager.config["risk_management"]["volatility_thresholds"]["low"] == Decimal("0.02")
    assert risk_manager.config["risk_management"]["gas_price_threshold_gwei"] == Decimal("150")


def test_handle_external_risk_event(risk_manager):
    """Test handling an external risk event."""
    external_event = RiskEvent(
        event_type="external_market_crash",
        severity="critical",
        details="Major crypto market downturn.",
        affected_protocol=None,
        timestamp=get_current_timestamp(),
    )
    risk_manager.handle_external_risk_event(external_event)
    assert risk_manager.current_risk_level == RiskLevel.EXTREME
    assert risk_manager.circuit_breaker_active is True  # Critical event should activate it


def test_risk_level_transition(risk_manager):
    """Test how risk level transitions based on multiple factors."""
    # Start low
    risk_manager.current_risk_level = RiskLevel.LOW

    # High volatility should push to HIGH
    risk_manager.assess_volatility({"price_volatility": Decimal("0.12")})
    assert risk_manager.current_risk_level == RiskLevel.HIGH

    # High gas price should also contribute
    risk_manager.assess_gas_price({"gas_price_gwei": Decimal("110")})
    # Still HIGH, as it's not EXTREME yet

    # Consecutive failures should push to CRITICAL/EXTREME
    risk_manager.record_transaction_outcome("protocol_x", False)
    risk_manager.record_transaction_outcome("protocol_x", False)
    risk_manager.record_transaction_outcome("protocol_x", False)
    risk_manager.assess_transaction_failures("protocol_x")
    assert risk_manager.current_risk_level == RiskLevel.EXTREME
    assert risk_manager.circuit_breaker_active is True


def test_risk_level_degradation_and_recovery(risk_manager):
    """Test risk level degradation and recovery."""
    risk_manager.current_risk_level = RiskLevel.EXTREME
    risk_manager.circuit_breaker_active = True
    risk_manager.protocol_failure_counts["protocol_y"] = 5

    # Simulate recovery
    risk_manager.assess_volatility({"price_volatility": Decimal("0.001")})  # Low volatility
    risk_manager.assess_gas_price({"gas_price_gwei": Decimal("30")})  # Low gas
    risk_manager.record_transaction_outcome("protocol_y", True)  # Success
    risk_manager.check_circuit_breaker({
        "total_transactions": 100,
        "successful_transactions": 99,
        "failed_transactions": 1,
        "failure_rate": Decimal("0.01"),
    })

    # Risk level should gradually decrease
    # (Actual implementation might have a decay mechanism)
    # For this test, we'll check if it's no longer EXTREME
    assert risk_manager.current_risk_level != RiskLevel.EXTREME
    assert risk_manager.circuit_breaker_active is False
    assert risk_manager.protocol_failure_counts["protocol_y"] == 0
