# src/pydepgraph/incremental/GraphComparator.py

from dataclasses import dataclass, field
from typing import Set, Union

from ..models import ExtractionResult, Module, Function, Class, ModuleImport, FunctionCall, Inheritance

# A generic type for any node or edge model
Node = Union[Module, Function, Class]
Edge = Union[ModuleImport, FunctionCall, Inheritance]

@dataclass
class ComparisonResult:
    """Holds the result of a comparison between two dependency graphs."""
    added_nodes: Set[Node] = field(default_factory=set)
    deleted_nodes: Set[Node] = field(default_factory=set)
    added_edges: Set[Edge] = field(default_factory=set)
    deleted_edges: Set[Edge] = field(default_factory=set)

class GraphComparator:
    """Compares two ExtractionResult objects to find differences."""

    def compare(self, before: ExtractionResult, after: ExtractionResult) -> ComparisonResult:
        """
        Compares two extraction results and returns a ComparisonResult.
        This version relies on the data models being hashable.
        """
        # --- Node Comparison ---
        nodes_before = set(before.all_nodes())
        nodes_after = set(after.all_nodes())

        added_nodes = nodes_after - nodes_before
        deleted_nodes = nodes_before - nodes_after

        # --- Edge Comparison ---
        edges_before = set(before.all_edges())
        edges_after = set(after.all_edges())

        added_edges = edges_after - edges_before
        deleted_edges = edges_before - edges_after

        return ComparisonResult(
            added_nodes=added_nodes,
            deleted_nodes=deleted_nodes,
            added_edges=added_edges,
            deleted_edges=deleted_edges
        )
