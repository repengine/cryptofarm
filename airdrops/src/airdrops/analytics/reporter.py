"""
Airdrop Reporting Module.

This module provides functionality to generate reports and analytics from tracked
airdrop data, including ROI calculations and performance summaries.
"""

import csv
import json
import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from airdrops.analytics.tracker import AirdropEvent, AirdropTracker
from airdrops.analytics.optimizer import ROIOptimizer, ROIMetrics, OptimizationSuggestion
from airdrops.analytics.portfolio import PortfolioPerformanceAnalyzer, PortfolioMetrics

# Configure logging
logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Supported report output formats."""
    JSON = "json"
    CSV = "csv"
    CONSOLE = "console"


class ProtocolSummary(BaseModel):
    """Summary statistics for a protocol."""
    protocol_name: str
    total_events: int
    total_tokens_received: Decimal
    total_estimated_value_usd: Optional[Decimal]
    unique_tokens: List[str]
    first_airdrop_date: Optional[datetime]
    last_airdrop_date: Optional[datetime]


class AirdropReport(BaseModel):
    """Complete airdrop analytics report."""
    report_generated_at: datetime
    total_airdrops: int
    total_protocols: int
    total_estimated_value_usd: Optional[Decimal]
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    protocol_summaries: List[ProtocolSummary]
    top_protocols_by_value: List[Dict[str, Union[str, Decimal, int]]]
    monthly_breakdown: List[Dict[str, Union[str, int, Decimal]]]
    roi_metrics: Optional[List[ROIMetrics]] = None
    optimization_suggestions: Optional[List[OptimizationSuggestion]] = None
    portfolio_metrics: Optional[PortfolioMetrics] = None


class AirdropReporter:
    """
    Airdrop analytics and reporting system.

    Generates comprehensive reports from tracked airdrop data including
    protocol summaries, ROI calculations, and performance analytics.

    Example:
        >>> tracker = AirdropTracker()
        >>> reporter = AirdropReporter(tracker)
        >>> report = reporter.generate_comprehensive_report()
        >>> reporter.export_report(report, "report.json", ReportFormat.JSON)
    """
    def __init__(self, tracker: AirdropTracker) -> None:
        """
        Initialize the airdrop reporter.

        Args:
            tracker: AirdropTracker instance for data access
        """
        self.tracker = tracker
        self.roi_optimizer: Optional[ROIOptimizer] = None
        self.portfolio_analyzer: Optional[PortfolioPerformanceAnalyzer] = None
        logger.info("AirdropReporter initialized")

    def enable_roi_analysis(self, roi_optimizer: ROIOptimizer) -> None:
        """
        Enable ROI analysis in reports.

        Args:
            roi_optimizer: ROIOptimizer instance for ROI calculations

        Example:
            >>> optimizer = ROIOptimizer(tracker)
            >>> reporter.enable_roi_analysis(optimizer)
        """
        self.roi_optimizer = roi_optimizer
        logger.info("ROI analysis enabled for reports")

    def enable_portfolio_analytics(
        self, portfolio_analyzer: PortfolioPerformanceAnalyzer
    ) -> None:
        """
        Enable portfolio performance analytics in reports.

        Args:
            portfolio_analyzer: PortfolioPerformanceAnalyzer instance

        Example:
            >>> analyzer = PortfolioPerformanceAnalyzer(tracker)
            >>> reporter.enable_portfolio_analytics(analyzer)
        """
        self.portfolio_analyzer = portfolio_analyzer
        logger.info("Portfolio performance analytics enabled for reports")

    def generate_comprehensive_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_roi: bool = True,
        include_portfolio: bool = True
    ) -> AirdropReport:
        """
        Generate a comprehensive airdrop analytics report.

        Args:
            start_date: Start date for report (optional)
            end_date: End date for report (optional)
            include_roi: Whether to include ROI analysis (requires roi_optimizer)
            include_portfolio: Whether to include portfolio analytics (requires portfolio_analyzer)

        Returns:
            AirdropReport instance with complete analytics

        Example:
            >>> reporter = AirdropReporter(tracker)
            >>> report = reporter.generate_comprehensive_report()
        """
        try:
            # Get all events in date range
            if start_date and end_date:
                events = self.tracker.get_airdrops_by_date_range(start_date, end_date)
            else:
                # Get all events by querying a very wide date range
                start_date = datetime(2020, 1, 1)
                end_date = datetime.now()
                events = self.tracker.get_airdrops_by_date_range(start_date, end_date)

            if not events:
                logger.warning("No airdrop events found for report generation")
                return self._create_empty_report(start_date, end_date)

            # Calculate basic statistics
            total_airdrops = len(events)
            protocols = set(event.protocol_name for event in events)
            total_protocols = len(protocols)

            total_estimated_value = sum(
                event.estimated_value_usd or Decimal('0') for event in events
            )

            # Generate protocol summaries
            protocol_summaries = self._generate_protocol_summaries(events)

            # Generate top protocols by value
            top_protocols = self._generate_top_protocols_by_value(protocol_summaries)

            # Generate monthly breakdown
            monthly_breakdown = self._generate_monthly_breakdown(events)

            # Generate ROI analysis if enabled
            roi_metrics = None
            optimization_suggestions = None
            if include_roi and self.roi_optimizer:
                try:
                    roi_metrics = self.roi_optimizer.calculate_portfolio_roi(
                        start_date, end_date
                    )
                    optimization_suggestions = self.roi_optimizer.generate_optimization_suggestions()
                    logger.info("ROI analysis included in comprehensive report")
                except Exception as e:
                    logger.warning(f"Failed to generate ROI analysis: {e}")

            # Generate portfolio performance analytics if enabled
            portfolio_metrics = None
            if include_portfolio and self.portfolio_analyzer:
                try:
                    portfolio_metrics = self.portfolio_analyzer.calculate_portfolio_metrics(
                        end_date
                    )
                    logger.info("Portfolio performance analytics included in comprehensive report")
                except Exception as e:
                    logger.warning(f"Failed to generate portfolio analytics: {e}")

            report = AirdropReport(
                report_generated_at=datetime.now(),
                total_airdrops=total_airdrops,
                total_protocols=total_protocols,
                total_estimated_value_usd=Decimal(str(total_estimated_value))
                if total_estimated_value is not None and total_estimated_value > 0
                else None,
                date_range_start=start_date,
                date_range_end=end_date,
                protocol_summaries=protocol_summaries,
                top_protocols_by_value=top_protocols,
                monthly_breakdown=monthly_breakdown,
                roi_metrics=roi_metrics,
                optimization_suggestions=optimization_suggestions,
                portfolio_metrics=portfolio_metrics
            )

            logger.info(f"Generated comprehensive report with {total_airdrops} events")
            return report

        except Exception as e:
            logger.error(f"Failed to generate comprehensive report: {e}")
            raise RuntimeError(f"Report generation failed: {e}") from e

    def generate_protocol_report(self, protocol_name: str) -> ProtocolSummary:
        """
        Generate a detailed report for a specific protocol.

        Args:
            protocol_name: Name of the protocol to analyze

        Returns:
            ProtocolSummary with detailed statistics
        """
        try:
            events = self.tracker.get_airdrops_by_protocol(protocol_name)

            if not events:
                logger.warning(f"No events found for protocol: {protocol_name}")
                return ProtocolSummary(
                    protocol_name=protocol_name,
                    total_events=0,
                    total_tokens_received=Decimal('0'),
                    total_estimated_value_usd=None,
                    unique_tokens=[],
                    first_airdrop_date=None,
                    last_airdrop_date=None
                )

            return self._create_protocol_summary(protocol_name, events)

        except Exception as e:
            logger.error(f"Failed to generate protocol report for {protocol_name}: {e}")
            raise RuntimeError(f"Protocol report generation failed: {e}") from e

    def export_report(
        self,
        report: AirdropReport,
        output_path: str,
        format_type: ReportFormat
    ) -> None:
        """
        Export report to file in specified format.

        Args:
            report: AirdropReport to export
            output_path: Path where to save the report
            format_type: Output format (JSON, CSV, or CONSOLE)
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if format_type == ReportFormat.JSON:
                self._export_json(report, output_file)
            elif format_type == ReportFormat.CSV:
                self._export_csv(report, output_file)
            elif format_type == ReportFormat.CONSOLE:
                self._export_console(report)
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            logger.info(
                f"Report exported to {output_path} in {format_type.value} format"
            )

        except (IOError, OSError) as e:  # Catch specific I/O errors for export failures
            logger.error(f"Failed to export report: {e}")
            raise RuntimeError(f"Report export failed: {e}") from e
        except Exception as e:  # Catch other unexpected errors, but not ValueError
            if isinstance(e, ValueError):  # Re-raise ValueError directly
                raise e
            logger.error(f"An unexpected error occurred during report export: {e}")
            raise RuntimeError(
                f"Report export failed due to unexpected error: {e}"
            ) from e

    def _generate_protocol_summaries(
        self, events: List[AirdropEvent]
    ) -> List[ProtocolSummary]:
        """Generate summaries for all protocols in the events."""
        protocol_events: Dict[str, List[AirdropEvent]] = {}
        for event in events:
            if event.protocol_name not in protocol_events:
                protocol_events[event.protocol_name] = []
            protocol_events[event.protocol_name].append(event)

        summaries = []
        for protocol_name, protocol_event_list in protocol_events.items():
            summary = self._create_protocol_summary(
                protocol_name, protocol_event_list
            )
            summaries.append(summary)

        return sorted(
            summaries,
            key=lambda x: x.total_estimated_value_usd or Decimal('0'),
            reverse=True
        )

    def _create_protocol_summary(
        self, protocol_name: str, events: List[AirdropEvent]
    ) -> ProtocolSummary:
        """Create a protocol summary from events."""
        total_tokens = Decimal(str(sum(event.amount_received for event in events)))
        total_value = Decimal(
            str(sum(event.estimated_value_usd or Decimal('0') for event in events))
        )
        unique_tokens = list(set(event.token_symbol for event in events))

        event_dates = [event.event_date for event in events]
        first_date = min(event_dates) if event_dates else None
        last_date = max(event_dates) if event_dates else None

        return ProtocolSummary(
            protocol_name=protocol_name,
            total_events=len(events),
            total_tokens_received=total_tokens if total_tokens > 0 else Decimal('0'),
            total_estimated_value_usd=total_value if total_value > 0 else None,
            unique_tokens=unique_tokens,
            first_airdrop_date=first_date,
            last_airdrop_date=last_date
        )

    def _generate_top_protocols_by_value(
        self, summaries: List[ProtocolSummary]
    ) -> List[Dict[str, Union[str, Decimal, int]]]:
        """Generate top protocols ranked by estimated value."""
        protocols_with_value = [
            s for s in summaries
            if s.total_estimated_value_usd and s.total_estimated_value_usd > 0
        ]

        return [
            {
                "protocol_name": summary.protocol_name,
                "total_value_usd": Decimal(str(summary.total_estimated_value_usd)),
                "total_events": summary.total_events,
            }
            for summary in protocols_with_value[:10]  # Top 10
        ]

    def _generate_monthly_breakdown(
        self, events: List[AirdropEvent]
    ) -> List[Dict[str, Union[str, int, Decimal]]]:
        """Generate monthly breakdown of airdrop activity."""
        monthly_data: Dict[str, Dict[str, Union[str, int, Decimal]]] = {}

        for event in events:
            month_key = event.event_date.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "event_count": 0,
                    "total_value_usd": Decimal('0')
                }

            monthly_data[month_key]["event_count"] = (
                int(monthly_data[month_key]["event_count"]) + 1
            )
            if event.estimated_value_usd:
                monthly_data[month_key]["total_value_usd"] = (
                    Decimal(str(monthly_data[month_key]["total_value_usd"]))
                    + event.estimated_value_usd
                )

        # Convert to list and sort by month
        breakdown: List[Dict[str, Union[str, int, Decimal]]] = list(
            monthly_data.values()
        )
        breakdown.sort(key=lambda x: str(x["month"]))

        return breakdown

    def _create_empty_report(
        self, start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> AirdropReport:
        """Create an empty report when no events are found."""
        return AirdropReport(
            report_generated_at=datetime.now(),
            total_airdrops=0,
            total_protocols=0,
            total_estimated_value_usd=None,
            date_range_start=start_date,
            date_range_end=end_date,
            protocol_summaries=[],
            top_protocols_by_value=[],
            monthly_breakdown=[]
        )

    def _export_json(self, report: AirdropReport, output_file: Path) -> None:
        """Export report as JSON."""
        report_dict = report.model_dump()

        # Convert Decimal and datetime objects for JSON serialization
        def convert_for_json(obj: Any) -> Union[str, Any]:
            if isinstance(obj, Decimal):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        def recursive_convert(data: Any) -> Any:
            if isinstance(data, dict):
                return {k: recursive_convert(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [recursive_convert(item) for item in data]
            else:
                return convert_for_json(data)

        converted_report = recursive_convert(report_dict)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(converted_report, f, indent=2, ensure_ascii=False)

    def _export_csv(self, report: AirdropReport, output_file: Path) -> None:
        """Export protocol summaries as CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                'Protocol Name',
                'Total Events',
                'Total Tokens Received',
                'Total Estimated Value USD',
                'Unique Tokens',
                'First Airdrop Date',
                'Last Airdrop Date'
            ])

            # Write protocol summaries
            for summary in report.protocol_summaries:
                writer.writerow([
                    summary.protocol_name,
                    summary.total_events,
                    str(summary.total_tokens_received),
                    str(summary.total_estimated_value_usd)
                    if summary.total_estimated_value_usd else '',
                    ', '.join(summary.unique_tokens),
                    summary.first_airdrop_date.isoformat()
                    if summary.first_airdrop_date else '',
                    summary.last_airdrop_date.isoformat()
                    if summary.last_airdrop_date else ''
                ])

    def _export_console(self, report: AirdropReport) -> None:
        """Print report to console."""
        print("\n" + "="*60)
        print("AIRDROP ANALYTICS REPORT")
        print("="*60)
        print(f"Generated: {report.report_generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Airdrops: {report.total_airdrops}")
        print(f"Total Protocols: {report.total_protocols}")
        if report.total_estimated_value_usd:
            print(f"Total Estimated Value: ${report.total_estimated_value_usd:,.2f}")

        if report.date_range_start and report.date_range_end:
            print(
                f"Date Range: {report.date_range_start.strftime('%Y-%m-%d')} to "
                f"{report.date_range_end.strftime('%Y-%m-%d')}"
            )
        print("\nTOP PROTOCOLS BY VALUE:")
        print("-" * 40)
        for i, protocol in enumerate(report.top_protocols_by_value[:5], 1):
            print(
                f"{i}. {protocol['protocol_name']}: ${protocol['total_value_usd']:,.2f} "
                f"({protocol['total_events']} events)"
            )

        # ROI Analysis Section
        if report.roi_metrics:
            print("\nROI ANALYSIS:")
            print("-" * 40)
            for roi in report.roi_metrics[:5]:  # Show top 5
                print(f"\n{roi.protocol_name}:")
                print(f"  ROI: {roi.roi_percentage:.1f}%")
                print(f"  Revenue: ${roi.total_revenue_usd:,.2f}")
                print(f"  Cost: ${roi.total_cost_usd:,.2f}")
                print(f"  Profit: ${roi.profit_usd:,.2f}")

        # Optimization Suggestions Section
        if report.optimization_suggestions:
            print("\nOPTIMIZATION SUGGESTIONS:")
            print("-" * 40)
            for suggestion in report.optimization_suggestions[:3]:  # Show top 3
                print(f"\n{suggestion.priority.upper()} PRIORITY:")
                print(f"  Protocol: {suggestion.protocol_name}")
                print(f"  Suggestion: {suggestion.description}")
                print(f"  Expected Impact: {suggestion.expected_impact}")

        # Portfolio Performance Section
        if report.portfolio_metrics:
            print("\nPORTFOLIO PERFORMANCE:")
            print("-" * 40)
            pm = report.portfolio_metrics
            print(f"Total Portfolio Value: ${pm.total_portfolio_value_usd:,.2f}")
            print(f"Total Profit/Loss: ${pm.total_profit_loss_usd:,.2f}")
            print(f"Portfolio ROI: {pm.portfolio_roi_percentage:.1f}%")
            print(f"Protocols: {pm.protocol_count}")
            print(f"Tokens: {pm.token_count}")
            print(f"Diversification Index: {pm.diversification_index:.3f}")
            print(f"Largest Position: {pm.largest_position_percentage:.1f}%")
            if pm.value_at_risk_usd:
                print(f"Value at Risk: ${pm.value_at_risk_usd:,.2f}")

        print("\nPROTOCOL SUMMARIES:")
        print("-" * 40)
        for summary in report.protocol_summaries[:10]:  # Show top 10
            print(f"\n{summary.protocol_name}:")
            print(f"  Events: {summary.total_events}")
            print(f"  Tokens: {summary.total_tokens_received}")
            if summary.total_estimated_value_usd:
                print(f"  Value: ${summary.total_estimated_value_usd:,.2f}")
            print(f"  Token Types: {', '.join(summary.unique_tokens)}")
        print("\n" + "="*60)
