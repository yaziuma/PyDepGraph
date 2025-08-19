# pydepgraph/services/analytics_service.py
from typing import Dict, Any, List, Optional, Set, Tuple
from ..database import GraphDatabase
import networkx as nx
from collections import defaultdict


class GraphAnalyticsService:
    """Service for performing graph analytics."""

    def __init__(self, database: GraphDatabase):
        self.database = database
        self._graph_cache: Optional[nx.DiGraph] = None

    def _build_graph(self, force_refresh: bool = False) -> nx.DiGraph:
        """Build NetworkX graph from database for analysis"""
        if self._graph_cache is not None and not force_refresh:
            return self._graph_cache
        
        graph = nx.DiGraph()
        
        # Add module nodes
        modules_result = self.database.execute_query("MATCH (m:Module) RETURN m.name, m.file_path, m.lines_of_code, m.complexity_score")
        for row in modules_result:
            # row is a dict, extract values
            if isinstance(row, dict):
                name = row.get('m.name')
                file_path = row.get('m.file_path')
                lines_of_code = row.get('m.lines_of_code')
                complexity_score = row.get('m.complexity_score')
                
                if name:
                    graph.add_node(f"module:{name}", 
                                 type="module", 
                                 file_path=file_path,
                                 lines_of_code=lines_of_code or 0,
                                 complexity_score=complexity_score or 0)
        
        # Add function nodes
        functions_result = self.database.execute_query("MATCH (f:Function) RETURN f.qualified_name, f.cyclomatic_complexity")
        for row in functions_result:
            if isinstance(row, dict):
                qualified_name = row.get('f.qualified_name')
                complexity = row.get('f.cyclomatic_complexity')
                
                if qualified_name:
                    graph.add_node(f"function:{qualified_name}", 
                                 type="function",
                                 complexity=complexity or 1)
        
        # Add class nodes
        classes_result = self.database.execute_query("MATCH (c:Class) RETURN c.qualified_name, c.method_count")
        for row in classes_result:
            if isinstance(row, dict):
                qualified_name = row.get('c.qualified_name')
                method_count = row.get('c.method_count')
                
                if qualified_name:
                    graph.add_node(f"class:{qualified_name}", 
                                 type="class",
                                 method_count=method_count or 0)
        
        # Add module import edges
        imports_result = self.database.execute_query(
            "MATCH (m1:Module)-[r:ModuleImports]->(m2:Module) RETURN m1.name, m2.name, r.import_type"
        )
        for row in imports_result:
            if isinstance(row, dict):
                source_name = row.get('m1.name')
                target_name = row.get('m2.name')
                import_type = row.get('r.import_type')
                
                if source_name and target_name:
                    graph.add_edge(f"module:{source_name}", f"module:{target_name}", 
                                 type="import", import_type=import_type)
        
        # Add function call edges
        calls_result = self.database.execute_query(
            "MATCH (f1:Function)-[r:FunctionCalls]->(f2:Function) RETURN f1.qualified_name, f2.qualified_name"
        )
        for row in calls_result:
            if isinstance(row, dict):
                source_name = row.get('f1.qualified_name')
                target_name = row.get('f2.qualified_name')
                
                if source_name and target_name:
                    graph.add_edge(f"function:{source_name}", f"function:{target_name}", type="call")
        
        # Add inheritance edges
        inheritance_result = self.database.execute_query(
            "MATCH (c1:Class)-[r:Inheritance]->(c2:Class) RETURN c1.qualified_name, c2.qualified_name"
        )
        for row in inheritance_result:
            if isinstance(row, dict):
                child_name = row.get('c1.qualified_name')
                parent_name = row.get('c2.qualified_name')
                
                if child_name and parent_name:
                    graph.add_edge(f"class:{child_name}", f"class:{parent_name}", type="inheritance")
        
        self._graph_cache = graph
        return graph

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics"""
        graph = self._build_graph()
        
        # Count nodes by type
        module_nodes = [n for n in graph.nodes() if n.startswith("module:")]
        function_nodes = [n for n in graph.nodes() if n.startswith("function:")]
        class_nodes = [n for n in graph.nodes() if n.startswith("class:")]
        
        # Count edges by type
        import_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("type") == "import"]
        call_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("type") == "call"]
        inheritance_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("type") == "inheritance"]
        
        # Calculate graph density
        total_possible_edges = len(graph.nodes()) * (len(graph.nodes()) - 1)
        density = len(graph.edges()) / total_possible_edges if total_possible_edges > 0 else 0
        
        # Calculate complexity metrics
        total_lines = sum(graph.nodes[n].get("lines_of_code", 0) for n in module_nodes)
        avg_complexity = sum(graph.nodes[n].get("complexity_score", 0) for n in module_nodes) / len(module_nodes) if module_nodes else 0
        
        return {
            "node_counts": {
                "modules": len(module_nodes),
                "functions": len(function_nodes),
                "classes": len(class_nodes),
                "total": len(graph.nodes())
            },
            "edge_counts": {
                "imports": len(import_edges),
                "function_calls": len(call_edges),
                "inheritance": len(inheritance_edges),
                "total": len(graph.edges())
            },
            "graph_metrics": {
                "density": round(density, 4),
                "total_lines_of_code": total_lines,
                "average_complexity": round(avg_complexity, 2)
            }
        }

    def detect_circular_dependencies(self, node_type: str = "module") -> List[List[str]]:
        """Detect circular dependencies in the graph"""
        graph = self._build_graph()
        
        # Filter graph by node type
        if node_type == "module":
            nodes = [n for n in graph.nodes() if n.startswith("module:")]
        elif node_type == "function":
            nodes = [n for n in graph.nodes() if n.startswith("function:")]
        elif node_type == "class":
            nodes = [n for n in graph.nodes() if n.startswith("class:")]
        else:
            nodes = list(graph.nodes())
        
        subgraph = graph.subgraph(nodes)
        
        # Find strongly connected components
        cycles = []
        try:
            sccs = list(nx.strongly_connected_components(subgraph))
            for scc in sccs:
                if len(scc) > 1:  # Cycles must have more than one node
                    cycle_nodes = list(scc)
                    # Remove type prefix for cleaner output
                    clean_nodes = [node.split(":", 1)[1] for node in cycle_nodes]
                    cycles.append(clean_nodes)
        except nx.NetworkXError:
            pass
        
        return cycles

    def find_shortest_path(self, source: str, target: str, node_type: str = "module") -> Optional[List[str]]:
        """Find shortest path between two nodes"""
        graph = self._build_graph()
        
        source_node = f"{node_type}:{source}"
        target_node = f"{node_type}:{target}"
        
        if source_node not in graph or target_node not in graph:
            return None
        
        try:
            path = nx.shortest_path(graph, source_node, target_node)
            # Remove type prefix for cleaner output
            return [node.split(":", 1)[1] for node in path]
        except nx.NetworkXNoPath:
            return None

    def find_all_paths(self, source: str, target: str, node_type: str = "module", max_length: int = 10) -> List[List[str]]:
        """Find all paths between two nodes (limited by max_length)"""
        graph = self._build_graph()
        
        source_node = f"{node_type}:{source}"
        target_node = f"{node_type}:{target}"
        
        if source_node not in graph or target_node not in graph:
            return []
        
        try:
            paths = list(nx.all_simple_paths(graph, source_node, target_node, cutoff=max_length))
            # Remove type prefix for cleaner output
            return [[node.split(":", 1)[1] for node in path] for path in paths]
        except nx.NetworkXNoPath:
            return []

    def calculate_importance_scores(self, node_type: str = "module") -> Dict[str, float]:
        """Calculate importance scores for nodes using PageRank algorithm"""
        graph = self._build_graph()
        
        # Filter graph by node type
        if node_type == "module":
            nodes = [n for n in graph.nodes() if n.startswith("module:")]
        elif node_type == "function":
            nodes = [n for n in graph.nodes() if n.startswith("function:")]
        elif node_type == "class":
            nodes = [n for n in graph.nodes() if n.startswith("class:")]
        else:
            nodes = list(graph.nodes())
        
        subgraph = graph.subgraph(nodes)
        
        if len(subgraph.nodes()) == 0:
            return {}
        
        try:
            pagerank_scores = nx.pagerank(subgraph)
            # Remove type prefix for cleaner output
            return {node.split(":", 1)[1]: score for node, score in pagerank_scores.items()}
        except (nx.NetworkXError, nx.PowerIterationFailedConvergence):
            # Fallback to simple degree centrality
            centrality_scores = nx.degree_centrality(subgraph)
            return {node.split(":", 1)[1]: score for node, score in centrality_scores.items()}

    def analyze_dependency_depth(self, root_node: str, node_type: str = "module") -> Dict[str, Any]:
        """Analyze dependency depth from a root node"""
        graph = self._build_graph()
        
        root = f"{node_type}:{root_node}"
        if root not in graph:
            return {"error": f"Node {root_node} not found"}
        
        # Calculate shortest path lengths from root to all other nodes
        try:
            lengths = nx.single_source_shortest_path_length(graph, root)
            depth_distribution = defaultdict(int)
            
            for target, length in lengths.items():
                if target != root:  # Exclude self
                    depth_distribution[length] += 1
            
            max_depth = max(lengths.values()) if lengths else 0
            avg_depth = sum(lengths.values()) / len(lengths) if lengths else 0
            
            return {
                "root_node": root_node,
                "max_depth": max_depth,
                "average_depth": round(avg_depth, 2),
                "depth_distribution": dict(depth_distribution),
                "reachable_nodes": len(lengths) - 1  # Exclude root itself
            }
        except nx.NetworkXError:
            return {"error": "Failed to analyze dependency depth"}

    def calculate_fan_in_out(self) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Calculate fan-in and fan-out for all nodes in the graph."""
        graph = self._build_graph()

        def clean_node_name(node_name: str) -> str:
            if ":" in node_name:
                return node_name.split(":", 1)[1]
            return node_name

        fan_in = {clean_node_name(node): degree for node, degree in graph.in_degree()}
        fan_out = {clean_node_name(node): degree for node, degree in graph.out_degree()}

        return fan_in, fan_out

    def calculate_betweenness_centrality(self, node_type: Optional[str] = None) -> Dict[str, float]:
        """Calculate betweenness centrality for nodes."""
        graph = self._build_graph()
        centrality = nx.betweenness_centrality(graph)

        def clean_node_name(node_name: str) -> str:
            if ":" in node_name:
                return node_name.split(":", 1)[1]
            return node_name

        return {clean_node_name(node): score for node, score in centrality.items()}

    def calculate_closeness_centrality(self, node_type: Optional[str] = None) -> Dict[str, float]:
        """Calculate closeness centrality for nodes."""
        graph = self._build_graph()
        centrality = nx.closeness_centrality(graph)

        def clean_node_name(node_name: str) -> str:
            if ":" in node_name:
                return node_name.split(":", 1)[1]
            return node_name

        return {clean_node_name(node): score for node, score in centrality.items()}

    def get_all_metrics(self, node_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Calculates and returns all metrics for each node in the graph.
        """
        graph = self._build_graph()
        if not graph.nodes:
            return []

        fan_in, fan_out = self.calculate_fan_in_out()
        betweenness = self.calculate_betweenness_centrality()
        closeness = self.calculate_closeness_centrality()

        all_metrics = []
        for node in graph.nodes:
            clean_name = node.split(":", 1)[1] if ":" in node else node
            metrics = {
                "node": clean_name,
                "fan_in": fan_in.get(clean_name, 0),
                "fan_out": fan_out.get(clean_name, 0),
                "betweenness": betweenness.get(clean_name, 0.0),
                "closeness": closeness.get(clean_name, 0.0),
            }
            all_metrics.append(metrics)

        return all_metrics

    def invalidate_cache(self):
        """Invalidate the graph cache"""
        self._graph_cache = None
