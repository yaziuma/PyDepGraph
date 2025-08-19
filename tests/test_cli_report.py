# tests/test_cli_report.py
import pytest
import argparse
from unittest.mock import patch, MagicMock

from pydepgraph.cli import cmd_report
from pydepgraph.config import Config

@patch('pydepgraph.cli.GraphDatabase')
@patch('pydepgraph.cli.GraphAnalyticsService')
def test_cli_report_with_metrics(MockAnalyticsService, MockDatabase, capsys):
    """
    Tests the `report` command with the `--metrics` flag.
    """
    # Setup mock service to return some metric data
    mock_service_instance = MockAnalyticsService.return_value
    mock_service_instance.get_all_metrics.return_value = [
        {'node': 'module_a', 'fan_in': 1, 'fan_out': 2, 'betweenness': 0.5, 'closeness': 0.8},
        {'node': 'module_b', 'fan_in': 2, 'fan_out': 0, 'betweenness': 0.0, 'closeness': 0.6},
    ]
    # Mock other service calls made by cmd_report
    mock_service_instance.get_graph_statistics.return_value = {
        'node_counts': {'total':2}, 'edge_counts': {'total':1}, 'graph_metrics': {'density':1,'total_lines_of_code':100,'average_complexity':1}
    }
    mock_service_instance.detect_circular_dependencies.return_value = []
    mock_service_instance.calculate_importance_scores.return_value = {}


    # Setup args for the command
    args = argparse.Namespace(
        metrics=True,
        sort_by='fan_in',
        # other args for cmd_report
        output_file=None,
        format='table' # a new format option i will add
    )
    config = Config.get_default_config()

    # Run the command
    return_code = cmd_report(args, config)

    assert return_code == 0

    # Check the output
    captured = capsys.readouterr()
    output = captured.out

    assert "Module Metrics & Centrality" in output
    assert "module_a" in output
    assert "module_b" in output
    assert "fan_in" in output.lower()
    assert "betweenness" in output.lower()
