# tests/reporting/test_evolution_reporter.py
import pytest
from rich.console import Console
from io import StringIO

from pydepgraph.reporting.evolution_reporter import EvolutionReporter
from pydepgraph.incremental.GraphComparator import ComparisonResult
from pydepgraph.models import Module, ModuleImport, Function

@pytest.fixture
def sample_comparison_result():
    """Creates a sample ComparisonResult for testing the reporter."""
    added_nodes = {
        Module(name="module_c", file_path="c.py"),
        Function(name="func_d", qualified_name="b.func_d", file_path="b.py")
    }
    deleted_nodes = {
        Module(name="module_e", file_path="e.py")
    }
    added_edges = {
        ModuleImport(source_module="a", target_module="c")
    }
    deleted_edges = {
        ModuleImport(source_module="a", target_module="e")
    }
    return ComparisonResult(
        added_nodes=added_nodes,
        deleted_nodes=deleted_nodes,
        added_edges=added_edges,
        deleted_edges=deleted_edges
    )

def test_evolution_reporter_output(sample_comparison_result):
    """
    Tests that the EvolutionReporter produces a correctly formatted string
    representation of the comparison result.
    """
    reporter = EvolutionReporter(sample_comparison_result)

    # Use a StringIO to capture the output of the rich console
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True, color_system="truecolor")

    reporter.print_report(console=console)

    output = string_io.getvalue()

    # Check for summary table headers
    assert "Evolution Summary" in output
    assert "Change Type" in output
    assert "Count" in output

    # Check for summary counts
    assert "Added Nodes" in output and "2" in output
    assert "Deleted Nodes" in output and "1" in output
    assert "Added Dependencies" in output and "1" in output
    assert "Deleted Dependencies" in output and "1" in output

    # Check for detailed sections
    assert "Added Nodes" in output
    assert "module_c" in output
    assert "b.func_d" in output

    assert "Deleted Nodes" in output
    assert "module_e" in output

    assert "Added Dependencies" in output
    assert "a -> c" in output

    assert "Deleted Dependencies" in output
    assert "a -> e" in output
