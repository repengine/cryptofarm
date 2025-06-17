"""
Analytics Platform for Airdrop Tracking and Reporting.

This module provides comprehensive analytics capabilities for tracking airdrop events,
calculating ROI, and generating performance reports.
"""

from airdrops.analytics.tracker import AirdropTracker, AirdropEvent
from airdrops.analytics.reporter import AirdropReporter, ReportFormat
from airdrops.analytics.optimizer import (
    ROIOptimizer,
    ROIMetrics,
    OptimizationSuggestion,
    CostData,
    CostModel,
    OptimizationStrategy
)
from airdrops.analytics.predictor import (
    AirdropPredictor,
    PredictionResult,
    PredictionWindow,
    PredictionConfidence,
    DataSourceType,
    MarketDataStub,
    OnChainActivityStub,
    SocialSentimentStub
)
from airdrops.analytics.portfolio import (
    PortfolioPerformanceAnalyzer,
    PortfolioMetrics,
    PortfolioSnapshot,
    BenchmarkComparison,
    BenchmarkType
)

__all__ = [
    "AirdropTracker",
    "AirdropEvent",
    "AirdropReporter",
    "ReportFormat",
    "ROIOptimizer",
    "ROIMetrics",
    "OptimizationSuggestion",
    "CostData",
    "CostModel",
    "OptimizationStrategy",
    "AirdropPredictor",
    "PredictionResult",
    "PredictionWindow",
    "PredictionConfidence",
    "DataSourceType",
    "MarketDataStub",
    "OnChainActivityStub",
    "SocialSentimentStub",
    "PortfolioPerformanceAnalyzer",
    "PortfolioMetrics",
    "PortfolioSnapshot",
    "BenchmarkComparison",
    "BenchmarkType",
]
