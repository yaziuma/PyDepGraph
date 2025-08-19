# src/pydepgraph/reporting/evolution_reporter.py

from rich.console import Console
from rich.table import Table

from ..incremental.GraphComparator import ComparisonResult
from ..models import Module, Function, Class, ModuleImport, FunctionCall, Inheritance

class EvolutionReporter:
    """
    Generates and prints a report detailing the evolution of dependencies.
    """
    def __init__(self, result: ComparisonResult, ref_from: str = "before", ref_to: str = "after"):
        self.result = result
        self.ref_from = ref_from
        self.ref_to = ref_to

    def print_report(self, console: Console = None):
        """Prints the evolution report to the console."""
        if console is None:
            console = Console()

        console.print(f"Comparing dependency graph from [bold cyan]{self.ref_from}[/] to [bold cyan]{self.ref_to}[/]")
        console.print()

        self._print_summary_table(console)
        console.print()

        self._print_details(console)

    def _print_summary_table(self, console: Console):
        """Prints the summary table of changes."""
        table = Table(title="📊 Evolution Summary")
        table.add_column("Change Type", justify="left", style="cyan")
        table.add_column("Count", justify="right", style="magenta")

        table.add_row("Added Nodes", str(len(self.result.added_nodes)))
        table.add_row("Deleted Nodes", str(len(self.result.deleted_nodes)))
        table.add_row("Added Dependencies", str(len(self.result.added_edges)))
        table.add_row("Deleted Dependencies", str(len(self.result.deleted_edges)))

        console.print(table)

    def _get_node_name(self, node):
        if hasattr(node, 'qualified_name'):
            return node.qualified_name
        return node.name

    def _get_edge_representation(self, edge):
        if isinstance(edge, ModuleImport):
            return f"{edge.source_module} -> {edge.target_module}"
        if isinstance(edge, FunctionCall):
            return f"{edge.source_function} -> {edge.target_function}"
        if isinstance(edge, Inheritance):
            return f"{edge.child_class} -> {edge.parent_class}"
        return "Unknown Edge"

    def _print_details(self, console: Console):
        """Prints the detailed lists of changes."""
        if self.result.added_nodes:
            console.print("[bold green][+] Added Nodes[/]")
            for node in sorted(self.result.added_nodes, key=self._get_node_name):
                console.print(f"- {self._get_node_name(node)}")
            console.print()

        if self.result.deleted_nodes:
            console.print("[bold red][-] Deleted Nodes[/]")
            for node in sorted(self.result.deleted_nodes, key=self._get_node_name):
                console.print(f"- {self._get_node_name(node)}")
            console.print()

        if self.result.added_edges:
            console.print("[bold green][+] Added Dependencies[/]")
            for edge in sorted(self.result.added_edges, key=self._get_edge_representation):
                console.print(f"- {self._get_edge_representation(edge)}")
            console.print()

        if self.result.deleted_edges:
            console.print("[bold red][-] Deleted Dependencies[/]")
            for edge in sorted(self.result.deleted_edges, key=self._get_edge_representation):
                console.print(f"- {self._get_edge_representation(edge)}")
            console.print()
