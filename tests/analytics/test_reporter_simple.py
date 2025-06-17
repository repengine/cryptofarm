"""Comprehensive tests for analytics reporter to improve coverage."""

import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from airdrops.analytics.reporter import (
    AirdropReporter, 
    ReportFormat, 
    AirdropReport, 
    ProtocolSummary
)
from airdrops.analytics.tracker import AirdropEvent
from airdrops.analytics.optimizer import ROIMetrics, OptimizationSuggestion
from airdrops.analytics.portfolio import PortfolioMetrics


class TestAirdropReporter:
    """Comprehensive test cases for AirdropReporter to improve coverage."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_tracker = Mock()
        self.reporter = AirdropReporter(self.mock_tracker)

    def test_init(self) -> None:
        """Test AirdropReporter initialization."""
        assert self.reporter.tracker == self.mock_tracker
        assert self.reporter.roi_optimizer is None
        assert self.reporter.portfolio_analyzer is None

    def test_enable_roi_analysis(self) -> None:
        """Test enabling ROI analysis."""
        mock_optimizer = Mock()
        self.reporter.enable_roi_analysis(mock_optimizer)
        assert self.reporter.roi_optimizer == mock_optimizer

    def test_enable_portfolio_analytics(self) -> None:
        """Test enabling portfolio analytics."""
        mock_analyzer = Mock()
        self.reporter.enable_portfolio_analytics(mock_analyzer)
        assert self.reporter.portfolio_analyzer == mock_analyzer

    def test_generate_comprehensive_report_no_events(self) -> None:
        """Test comprehensive report generation with no events."""
        self.mock_tracker.get_airdrops_by_date_range.return_value = []
        
        report = self.reporter.generate_comprehensive_report()
        
        assert report.total_airdrops == 0
        assert report.total_protocols == 0
        assert report.total_estimated_value_usd is None
        assert report.protocol_summaries == []
        assert report.top_protocols_by_value == []
        assert report.monthly_breakdown == []

    def test_generate_comprehensive_report_with_events(self) -> None:
        """Test comprehensive report generation with events."""
        # Create mock events
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            ),
            AirdropEvent(
                protocol_name="Compound",
                token_symbol="COMP",
                amount_received=Decimal("50"),
                estimated_value_usd=Decimal("300"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 2, 10, tzinfo=timezone.utc)
            )
        ]
        
        self.mock_tracker.get_airdrops_by_date_range.return_value = events
        
        report = self.reporter.generate_comprehensive_report()
        
        assert report.total_airdrops == 2
        assert report.total_protocols == 2
        assert report.total_estimated_value_usd == Decimal("800")
        assert len(report.protocol_summaries) == 2
        assert len(report.top_protocols_by_value) == 2
        assert len(report.monthly_breakdown) == 2

    def test_generate_comprehensive_report_with_roi_analysis(self) -> None:
        """Test comprehensive report with ROI analysis enabled."""
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            )
        ]
        
        mock_roi_metrics = [
            ROIMetrics(
                total_roi=Decimal("150"),
                average_roi_per_airdrop=Decimal("150"),
                success_rate=Decimal("100"),
                total_capital_deployed=Decimal("100"),
                total_profit=Decimal("150"),
                protocol_rois={"Uniswap": Decimal("150")},
                protocol_name="Uniswap",
                roi_percentage=Decimal("150"),
                total_revenue_usd=Decimal("500"),
                total_cost_usd=Decimal("100"),
                profit_usd=Decimal("400")
            )
        ]
        
        mock_suggestions = [
            OptimizationSuggestion(
                strategy="increase_allocation",
                protocol="Uniswap",
                suggested_allocation_change=Decimal("50"),
                reason="High ROI protocol",
                expected_impact="Increase returns by 25%",
                priority="high",
                protocol_name="Uniswap",
                description="Increase allocation to high-performing protocol"
            )
        ]
        
        mock_optimizer = Mock()
        mock_optimizer.calculate_portfolio_roi.return_value = mock_roi_metrics
        mock_optimizer.generate_optimization_suggestions.return_value = mock_suggestions
        
        self.mock_tracker.get_airdrops_by_date_range.return_value = events
        self.reporter.enable_roi_analysis(mock_optimizer)
        
        report = self.reporter.generate_comprehensive_report(include_roi=True)
        
        assert report.roi_metrics == mock_roi_metrics
        assert report.optimization_suggestions == mock_suggestions

    def test_generate_comprehensive_report_with_portfolio_analytics(self) -> None:
        """Test comprehensive report with portfolio analytics enabled."""
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            )
        ]
        
        mock_portfolio_metrics = PortfolioMetrics(
            calculation_date=datetime.now(timezone.utc),
            total_portfolio_value_usd=Decimal("1000"),
            total_profit_loss_usd=Decimal("200"),
            total_cost_usd=Decimal("800"),
            portfolio_roi_percentage=Decimal("25"),
            protocol_count=1,
            token_count=1,
            diversification_index=Decimal("0.5"),
            largest_position_percentage=Decimal("100"),
            value_at_risk_usd=Decimal("50")
        )
        
        mock_analyzer = Mock()
        mock_analyzer.calculate_portfolio_metrics.return_value = mock_portfolio_metrics
        
        self.mock_tracker.get_airdrops_by_date_range.return_value = events
        self.reporter.enable_portfolio_analytics(mock_analyzer)
        
        report = self.reporter.generate_comprehensive_report(include_portfolio=True)
        
        assert report.portfolio_metrics == mock_portfolio_metrics

    def test_generate_comprehensive_report_roi_failure(self) -> None:
        """Test comprehensive report when ROI analysis fails."""
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            )
        ]
        
        mock_optimizer = Mock()
        mock_optimizer.calculate_portfolio_roi.side_effect = Exception("ROI calculation failed")
        
        self.mock_tracker.get_airdrops_by_date_range.return_value = events
        self.reporter.enable_roi_analysis(mock_optimizer)
        
        report = self.reporter.generate_comprehensive_report(include_roi=True)
        
        assert report.roi_metrics is None
        assert report.optimization_suggestions is None

    def test_generate_comprehensive_report_portfolio_failure(self) -> None:
        """Test comprehensive report when portfolio analysis fails."""
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            )
        ]
        
        mock_analyzer = Mock()
        mock_analyzer.calculate_portfolio_metrics.side_effect = Exception("Portfolio calculation failed")
        
        self.mock_tracker.get_airdrops_by_date_range.return_value = events
        self.reporter.enable_portfolio_analytics(mock_analyzer)
        
        report = self.reporter.generate_comprehensive_report(include_portfolio=True)
        
        assert report.portfolio_metrics is None

    def test_generate_comprehensive_report_exception(self) -> None:
        """Test comprehensive report generation with exception."""
        self.mock_tracker.get_airdrops_by_date_range.side_effect = Exception("Database error")
        
        with pytest.raises(RuntimeError, match="Report generation failed"):
            self.reporter.generate_comprehensive_report()

    def test_generate_protocol_report_with_events(self) -> None:
        """Test protocol report generation with events."""
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            ),
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("50"),
                estimated_value_usd=Decimal("250"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 2, 10, tzinfo=timezone.utc)
            )
        ]
        
        self.mock_tracker.get_airdrops_by_protocol.return_value = events
        
        summary = self.reporter.generate_protocol_report("Uniswap")
        
        assert summary.protocol_name == "Uniswap"
        assert summary.total_events == 2
        assert summary.total_tokens_received == Decimal("150")
        assert summary.total_estimated_value_usd == Decimal("750")
        assert summary.unique_tokens == ["UNI"]

    def test_generate_protocol_report_no_events(self) -> None:
        """Test protocol report generation with no events."""
        self.mock_tracker.get_airdrops_by_protocol.return_value = []
        
        summary = self.reporter.generate_protocol_report("NonExistent")
        
        assert summary.protocol_name == "NonExistent"
        assert summary.total_events == 0
        assert summary.total_tokens_received == Decimal("0")
        assert summary.total_estimated_value_usd is None
        assert summary.unique_tokens == []
        assert summary.first_airdrop_date is None
        assert summary.last_airdrop_date is None

    def test_generate_protocol_report_exception(self) -> None:
        """Test protocol report generation with exception."""
        self.mock_tracker.get_airdrops_by_protocol.side_effect = Exception("Database error")
        
        with pytest.raises(RuntimeError, match="Protocol report generation failed"):
            self.reporter.generate_protocol_report("Uniswap")

    def test_export_report_unsupported_format(self) -> None:
        """Test export report with unsupported format."""
        mock_report = Mock()
        
        with pytest.raises(ValueError, match="Unsupported format"):
            self.reporter.export_report(mock_report, "test.txt", "INVALID")

    def test_export_report_io_error(self) -> None:
        """Test export report with IO error."""
        mock_report = Mock()
        
        with patch('pathlib.Path.mkdir', side_effect=OSError("Permission denied")):
            with pytest.raises(RuntimeError, match="Report export failed"):
                self.reporter.export_report(mock_report, "/invalid/path/test.json", ReportFormat.JSON)

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_export_json(self, mock_json_dump, mock_file) -> None:
        """Test JSON export functionality."""
        mock_report = AirdropReport(
            report_generated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            total_airdrops=1,
            total_protocols=1,
            total_estimated_value_usd=Decimal("500"),
            date_range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            date_range_end=datetime(2024, 1, 31, tzinfo=timezone.utc),
            protocol_summaries=[],
            top_protocols_by_value=[],
            monthly_breakdown=[]
        )
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            self.reporter.export_report(mock_report, str(tmp_path), ReportFormat.JSON)
            mock_json_dump.assert_called_once()
        finally:
            tmp_path.unlink(missing_ok=True)

    @patch('builtins.open', new_callable=mock_open)
    @patch('csv.writer')
    def test_export_csv(self, mock_csv_writer, mock_file) -> None:
        """Test CSV export functionality."""
        mock_writer = Mock()
        mock_csv_writer.return_value = mock_writer
        
        protocol_summary = ProtocolSummary(
            protocol_name="Uniswap",
            total_events=1,
            total_tokens_received=Decimal("100"),
            total_estimated_value_usd=Decimal("500"),
            unique_tokens=["UNI"],
            first_airdrop_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            last_airdrop_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
        )
        
        mock_report = AirdropReport(
            report_generated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            total_airdrops=1,
            total_protocols=1,
            total_estimated_value_usd=Decimal("500"),
            date_range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            date_range_end=datetime(2024, 1, 31, tzinfo=timezone.utc),
            protocol_summaries=[protocol_summary],
            top_protocols_by_value=[],
            monthly_breakdown=[]
        )
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            self.reporter.export_report(mock_report, str(tmp_path), ReportFormat.CSV)
            # Verify header and data rows were written
            assert mock_writer.writerow.call_count == 2  # Header + 1 data row
        finally:
            tmp_path.unlink(missing_ok=True)

    @patch('builtins.print')
    def test_export_console(self, mock_print) -> None:
        """Test console export functionality."""
        protocol_summary = ProtocolSummary(
            protocol_name="Uniswap",
            total_events=1,
            total_tokens_received=Decimal("100"),
            total_estimated_value_usd=Decimal("500"),
            unique_tokens=["UNI"],
            first_airdrop_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            last_airdrop_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
        )
        
        roi_metrics = ROIMetrics(
            total_roi=Decimal("150"),
            average_roi_per_airdrop=Decimal("150"),
            success_rate=Decimal("100"),
            total_capital_deployed=Decimal("100"),
            total_profit=Decimal("150"),
            protocol_rois={"Uniswap": Decimal("150")},
            protocol_name="Uniswap",
            roi_percentage=Decimal("150"),
            total_revenue_usd=Decimal("500"),
            total_cost_usd=Decimal("100"),
            profit_usd=Decimal("400")
        )
        
        optimization_suggestion = OptimizationSuggestion(
            strategy="increase_allocation",
            protocol="Uniswap",
            suggested_allocation_change=Decimal("50"),
            reason="High ROI protocol",
            expected_impact="Increase returns by 25%",
            priority="high",
            protocol_name="Uniswap",
            description="Increase allocation to high-performing protocol"
        )
        
        portfolio_metrics = PortfolioMetrics(
            calculation_date=datetime.now(timezone.utc),
            total_portfolio_value_usd=Decimal("1000"),
            total_profit_loss_usd=Decimal("200"),
            total_cost_usd=Decimal("800"),
            portfolio_roi_percentage=Decimal("25"),
            protocol_count=1,
            token_count=1,
            diversification_index=Decimal("0.5"),
            largest_position_percentage=Decimal("100"),
            value_at_risk_usd=Decimal("50")
        )
        
        mock_report = AirdropReport(
            report_generated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            total_airdrops=1,
            total_protocols=1,
            total_estimated_value_usd=Decimal("500"),
            date_range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            date_range_end=datetime(2024, 1, 31, tzinfo=timezone.utc),
            protocol_summaries=[protocol_summary],
            top_protocols_by_value=[{
                "protocol_name": "Uniswap",
                "total_value_usd": Decimal("500"),
                "total_events": 1
            }],
            monthly_breakdown=[{
                "month": "2024-01",
                "event_count": 1,
                "total_value_usd": Decimal("500")
            }],
            roi_metrics=[roi_metrics],
            optimization_suggestions=[optimization_suggestion],
            portfolio_metrics=portfolio_metrics
        )
        
        self.reporter.export_report(mock_report, "console", ReportFormat.CONSOLE)
        
        # Verify print was called multiple times for different sections
        assert mock_print.call_count > 10

    def test_create_protocol_summary(self) -> None:
        """Test _create_protocol_summary method."""
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            ),
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="USDC",
                amount_received=Decimal("200"),
                estimated_value_usd=Decimal("200"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 2, 10, tzinfo=timezone.utc)
            )
        ]
        
        summary = self.reporter._create_protocol_summary("Uniswap", events)
        
        assert summary.protocol_name == "Uniswap"
        assert summary.total_events == 2
        assert summary.total_tokens_received == Decimal("300")
        assert summary.total_estimated_value_usd == Decimal("700")
        assert set(summary.unique_tokens) == {"UNI", "USDC"}
        assert summary.first_airdrop_date == datetime(2024, 1, 15, tzinfo=timezone.utc)
        assert summary.last_airdrop_date == datetime(2024, 2, 10, tzinfo=timezone.utc)

    def test_generate_top_protocols_by_value(self) -> None:
        """Test _generate_top_protocols_by_value method."""
        summaries = [
            ProtocolSummary(
                protocol_name="Uniswap",
                total_events=2,
                total_tokens_received=Decimal("100"),
                total_estimated_value_usd=Decimal("500"),
                unique_tokens=["UNI"],
                first_airdrop_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
                last_airdrop_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            ),
            ProtocolSummary(
                protocol_name="Compound",
                total_events=1,
                total_tokens_received=Decimal("50"),
                total_estimated_value_usd=Decimal("300"),
                unique_tokens=["COMP"],
                first_airdrop_date=datetime(2024, 2, 10, tzinfo=timezone.utc),
                last_airdrop_date=datetime(2024, 2, 10, tzinfo=timezone.utc)
            ),
            ProtocolSummary(
                protocol_name="NoValue",
                total_events=1,
                total_tokens_received=Decimal("10"),
                total_estimated_value_usd=None,
                unique_tokens=["NV"],
                first_airdrop_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
                last_airdrop_date=datetime(2024, 3, 1, tzinfo=timezone.utc)
            )
        ]
        
        top_protocols = self.reporter._generate_top_protocols_by_value(summaries)
        
        assert len(top_protocols) == 2  # Only protocols with value
        assert top_protocols[0]["protocol_name"] == "Uniswap"
        assert top_protocols[0]["total_value_usd"] == Decimal("500")
        assert top_protocols[1]["protocol_name"] == "Compound"
        assert top_protocols[1]["total_value_usd"] == Decimal("300")

    def test_generate_monthly_breakdown(self) -> None:
        """Test _generate_monthly_breakdown method."""
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            ),
            AirdropEvent(
                protocol_name="Compound",
                token_symbol="COMP",
                amount_received=Decimal("50"),
                estimated_value_usd=Decimal("300"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 25, tzinfo=timezone.utc)
            ),
            AirdropEvent(
                protocol_name="Aave",
                token_symbol="AAVE",
                amount_received=Decimal("25"),
                estimated_value_usd=Decimal("200"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 2, 10, tzinfo=timezone.utc)
            )
        ]
        
        breakdown = self.reporter._generate_monthly_breakdown(events)
        
        assert len(breakdown) == 2
        assert breakdown[0]["month"] == "2024-01"
        assert breakdown[0]["event_count"] == 2
        assert breakdown[0]["total_value_usd"] == Decimal("800")
        assert breakdown[1]["month"] == "2024-02"
        assert breakdown[1]["event_count"] == 1
        assert breakdown[1]["total_value_usd"] == Decimal("200")

    def test_get_current_protocol_allocations(self) -> None:
        """Test _get_current_protocol_allocations method."""
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            ),
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("50"),
                estimated_value_usd=Decimal("250"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 25, tzinfo=timezone.utc)
            ),
            AirdropEvent(
                protocol_name="Compound",
                token_symbol="COMP",
                amount_received=Decimal("25"),
                estimated_value_usd=Decimal("200"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 2, 10, tzinfo=timezone.utc)
            )
        ]
        
        allocations = self.reporter._get_current_protocol_allocations(events)
        
        assert allocations["Uniswap"] == Decimal("750")
        assert allocations["Compound"] == Decimal("200")

    def test_create_empty_report(self) -> None:
        """Test _create_empty_report method."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        report = self.reporter._create_empty_report(start_date, end_date)
        
        assert report.total_airdrops == 0
        assert report.total_protocols == 0
        assert report.total_estimated_value_usd is None
        assert report.date_range_start == start_date
        assert report.date_range_end == end_date
        assert report.protocol_summaries == []
        assert report.top_protocols_by_value == []
        assert report.monthly_breakdown == []

    def test_generate_protocol_summaries(self) -> None:
        """Test _generate_protocol_summaries method."""
        events = [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            ),
            AirdropEvent(
                protocol_name="Compound",
                token_symbol="COMP",
                amount_received=Decimal("50"),
                estimated_value_usd=Decimal("300"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime(2024, 2, 10, tzinfo=timezone.utc)
            )
        ]
        
        summaries = self.reporter._generate_protocol_summaries(events)
        
        assert len(summaries) == 2
        # Should be sorted by value (Uniswap first with higher value)
        assert summaries[0].protocol_name == "Uniswap"
        assert summaries[0].total_estimated_value_usd == Decimal("500")
        assert summaries[1].protocol_name == "Compound"
        assert summaries[1].total_estimated_value_usd == Decimal("300")

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_export_json_conversion(self, mock_json_dump, mock_file) -> None:
        """Test JSON export with Decimal and datetime conversion."""
        mock_report = AirdropReport(
            report_generated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            total_airdrops=1,
            total_protocols=1,
            total_estimated_value_usd=Decimal("500.50"),
            date_range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            date_range_end=datetime(2024, 1, 31, tzinfo=timezone.utc),
            protocol_summaries=[],
            top_protocols_by_value=[],
            monthly_breakdown=[]
        )
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            self.reporter.export_report(mock_report, str(tmp_path), ReportFormat.JSON)
            
            # Verify the conversion was called with proper data
            mock_json_dump.assert_called_once()
            call_args = mock_json_dump.call_args[0][0]  # First positional argument
            
            # Check that Decimal values were converted to strings
            assert isinstance(call_args['total_estimated_value_usd'], str)
            assert call_args['total_estimated_value_usd'] == "500.50"
            
            # Check that datetime values were converted to ISO format
            assert isinstance(call_args['report_generated_at'], str)
            assert call_args['report_generated_at'] == "2024-01-01T12:00:00+00:00"
            
        finally:
            tmp_path.unlink(missing_ok=True)