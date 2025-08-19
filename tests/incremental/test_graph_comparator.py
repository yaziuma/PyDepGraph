# tests/incremental/test_graph_comparator.py
import pytest

from pydepgraph.models import ExtractionResult, Module, ModuleImport, FunctionCall, Class, Inheritance
# The classes to be tested
# from pydepgraph.incremental import GraphComparator, ComparisonResult

@pytest.fixture
def comparison_test_data():
    """Provides two ExtractionResult objects for comparison."""

    # Common elements
    module_common = Module(name="common.py", file_path="common.py")
    module_a = Module(name="a.py", file_path="a.py")
    edge_common = ModuleImport(source_module="a.py", target_module="common.py")

    # Elements only in 'before'
    module_deleted = Module(name="deleted.py", file_path="deleted.py")
    edge_deleted = ModuleImport(source_module="a.py", target_module="deleted.py")

    # Elements only in 'after'
    module_added = Module(name="added.py", file_path="added.py")
    edge_added = ModuleImport(source_module="a.py", target_module="added.py")

    result_before = ExtractionResult(
        modules=[module_common, module_a, module_deleted],
        module_imports=[edge_common, edge_deleted],
        functions=[], classes=[], function_calls=[], inheritance=[], contains=[], metadata={}
    )

    result_after = ExtractionResult(
        modules=[module_common, module_a, module_added],
        module_imports=[edge_common, edge_added],
        functions=[], classes=[], function_calls=[], inheritance=[], contains=[], metadata={}
    )

    return result_before, result_after, {
        "deleted_module": module_deleted,
        "added_module": module_added,
        "deleted_edge": edge_deleted,
        "added_edge": edge_added
    }

def test_graph_comparator(comparison_test_data):
    """Tests the comparison logic of GraphComparator."""
    from pydepgraph.incremental import GraphComparator

    result_before, result_after, expected_diffs = comparison_test_data

    comparator = GraphComparator()
    comparison_result = comparator.compare(result_before, result_after)

    # Check added nodes
    assert len(comparison_result.added_nodes) == 1
    # We need to convert set to list to access element
    added_node = list(comparison_result.added_nodes)[0]
    assert added_node.name == expected_diffs["added_module"].name

    # Check deleted nodes
    assert len(comparison_result.deleted_nodes) == 1
    deleted_node = list(comparison_result.deleted_nodes)[0]
    assert deleted_node.name == expected_diffs["deleted_module"].name

    # Check added edges
    assert len(comparison_result.added_edges) == 1
    added_edge = list(comparison_result.added_edges)[0]
    assert added_edge.target_module == expected_diffs["added_edge"].target_module

    # Check deleted edges
    assert len(comparison_result.deleted_edges) == 1
    deleted_edge = list(comparison_result.deleted_edges)[0]
    assert deleted_edge.target_module == expected_diffs["deleted_edge"].target_module

def test_graph_comparator_with_no_changes(comparison_test_data):
    """Tests the comparator when there are no changes."""
    from pydepgraph.incremental import GraphComparator

    result_before, _, _ = comparison_test_data

    comparator = GraphComparator()
    # Compare the same object to itself
    comparison_result = comparator.compare(result_before, result_before)

    assert len(comparison_result.added_nodes) == 0
    assert len(comparison_result.deleted_nodes) == 0
    assert len(comparison_result.added_edges) == 0
    assert len(comparison_result.deleted_edges) == 0
