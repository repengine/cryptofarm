"""Simple tests for analytics reporter to improve coverage."""

from unittest.mock import Mock, patch
from airdrops.analytics.reporter import AirdropReporter, ReportFormat
from pathlib import Path


class TestAirdropReporterSimple:
    """Simple test cases for AirdropReporter to improve coverage."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_tracker = Mock()
        self.reporter = AirdropReporter(self.mock_tracker)

    @patch('airdrops.analytics.reporter.AirdropReporter._export_json')
    @patch('airdrops.analytics.reporter.AirdropReporter._export_csv')
    @patch('airdrops.analytics.reporter.AirdropReporter._export_console')
    def test_export_report_formats(self, mock_console, mock_csv, mock_json) -> None:
        """Test export_report calls correct internal export method based on format."""
        mock_report = Mock()
        
        # Test JSON format
        output_path = "test_report.json"
        self.reporter.export_report(mock_report, output_path, ReportFormat.JSON)
        mock_json.assert_called_once_with(mock_report, Path(output_path))
        mock_csv.assert_not_called()
        mock_console.assert_not_called()

        mock_json.reset_mock()
        mock_csv.reset_mock()
        mock_console.reset_mock()

        # Test CSV format
        output_path = "test_report.csv"
        self.reporter.export_report(mock_report, output_path, ReportFormat.CSV)
        mock_csv.assert_called_once_with(mock_report, Path(output_path))
        mock_json.assert_not_called()
        mock_console.assert_not_called()

        mock_json.reset_mock()
        mock_csv.reset_mock()
        mock_console.reset_mock()

        # Test CONSOLE format
        self.reporter.export_report(mock_report, "console", ReportFormat.CONSOLE)
        mock_console.assert_called_once_with(mock_report)
        mock_json.assert_not_called()
        mock_csv.assert_not_called()
