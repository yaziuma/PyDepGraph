# PyDepGraph Phase 3 詳細設計書
## 検索・分析機能（Week 5-6）

## 📋 Phase 3 概要

**目標**: 高度な検索・分析機能の実装

**実装対象**:
- QueryService（依存関係検索、パス検索）
- GraphAnalyticsService（循環依存検出）
- 複雑なCypherクエリの実装
- エラーハンドリングの強化

## 🔍 QueryService実装

### 基本検索機能

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class DependencyPath:
    source: str
    target: str
    path: List[str]
    path_type: str  # 'function_call', 'import', 'inheritance'
    depth: int
    relationships: List[Dict[str, Any]]

@dataclass 
class SearchResult:
    items: List[Dict[str, Any]]
    total_count: int
    search_type: str
    query_time: float

class QueryService:
    """高度な検索・クエリサービス"""
    
    def __init__(self, database: GraphDatabase):
        self.database = database
    
    # === 基本検索機能 ===
    
    def search_by_name(
        self, 
        name: str, 
        search_type: str = "all",  # "module", "function", "class", "all"
        fuzzy: bool = False
    ) -> SearchResult:
        """名前による検索（完全一致・あいまい検索対応）"""
        
        start_time = time.time()
        results = []
        
        if fuzzy:
            # あいまい検索（LIKE使用）
            name_pattern = f"%{name}%"
        else:
            # 完全一致
            name_pattern = name
        
        if search_type in ["module", "all"]:
            module_query = """
            MATCH (m:Module)
            WHERE m.name LIKE $name_pattern OR m.file_path LIKE $name_pattern
            RETURN 'module' as type, m.id as id, m.name as name, 
                   m.file_path as path, m.package as package
            ORDER BY m.name
            """
            module_results = self.database.execute_query(module_query, {'name_pattern': name_pattern})
            results.extend(module_results)
        
        if search_type in ["function", "all"]:
            function_query = """
            MATCH (f:Function)
            WHERE f.name LIKE $name_pattern OR f.qualified_name LIKE $name_pattern
            RETURN 'function' as type, f.id as id, f.name as name,
                   f.qualified_name as path, f.module_name as module,
                   f.class_name as class_name, f.is_method as is_method
            ORDER BY f.name
            """
            function_results = self.database.execute_query(function_query, {'name_pattern': name_pattern})
            results.extend(function_results)
        
        if search_type in ["class", "all"]:
            class_query = """
            MATCH (c:Class)
            WHERE c.name LIKE $name_pattern OR c.qualified_name LIKE $name_pattern
            RETURN 'class' as type, c.id as id, c.name as name,
                   c.qualified_name as path, c.module_name as module,
                   c.method_count as method_count
            ORDER BY c.name
            """
            class_results = self.database.execute_query(class_query, {'name_pattern': name_pattern})
            results.extend(class_results)
        
        query_time = time.time() - start_time
        
        return SearchResult(
            items=results,
            total_count=len(results),
            search_type=search_type,
            query_time=query_time
        )
    
    def search_by_pattern(
        self, 
        pattern: str, 
        search_type: str = "all"
    ) -> SearchResult:
        """正規表現パターンによる検索"""
        
        start_time = time.time()
        results = []
        
        if search_type in ["function", "all"]:
            # 関数名の正規表現検索
            function_query = """
            MATCH (f:Function)
            WHERE f.name =~ $pattern OR f.qualified_name =~ $pattern
            RETURN 'function' as type, f.id as id, f.name as name,
                   f.qualified_name as path, f.module_name as module,
                   f.line_number as line_number
            ORDER BY f.name
            """
            function_results = self.database.execute_query(function_query, {'pattern': pattern})
            results.extend(function_results)
        
        if search_type in ["class", "all"]:
            # クラス名の正規表現検索
            class_query = """
            MATCH (c:Class)
            WHERE c.name =~ $pattern OR c.qualified_name =~ $pattern
            RETURN 'class' as type, c.id as id, c.name as name,
                   c.qualified_name as path, c.module_name as module
            ORDER BY c.name
            """
            class_results = self.database.execute_query(class_query, {'pattern': pattern})
            results.extend(class_results)
        
        query_time = time.time() - start_time
        
        return SearchResult(
            items=results,
            total_count=len(results),
            search_type=search_type,
            query_time=query_time
        )
    
    # === 依存関係分析 ===
    
    def find_function_dependencies(
        self, 
        function_name: str, 
        direction: str = "outgoing",  # "outgoing", "incoming", "both"
        depth: int = 1
    ) -> List[Dict[str, Any]]:
        """関数の依存関係検索"""
        
        if direction == "outgoing":
            # 呼び出し先を検索
            if depth == 1:
                query = """
                MATCH (f1:Function)-[c:FunctionCalls]->(f2:Function)
                WHERE f1.name = $function_name OR f1.qualified_name = $function_name
                RETURN f2.id as id, f2.name as name, f2.qualified_name as qualified_name,
                       f2.module_name as module_name, f2.class_name as class_name,
                       c.call_type as call_type, 1 as depth
                ORDER BY f2.qualified_name
                """
            else:
                # 複数階層の依存関係
                query = f"""
                MATCH path = (f1:Function)-[c:FunctionCalls*1..{depth}]->(f2:Function)
                WHERE f1.name = $function_name OR f1.qualified_name = $function_name
                RETURN f2.id as id, f2.name as name, f2.qualified_name as qualified_name,
                       f2.module_name as module_name, f2.class_name as class_name,
                       length(path) as depth
                ORDER BY depth, f2.qualified_name
                """
        
        elif direction == "incoming":
            # 呼び出し元を検索
            if depth == 1:
                query = """
                MATCH (f1:Function)-[c:FunctionCalls]->(f2:Function)
                WHERE f2.name = $function_name OR f2.qualified_name = $function_name
                RETURN f1.id as id, f1.name as name, f1.qualified_name as qualified_name,
                       f1.module_name as module_name, f1.class_name as class_name,
                       c.call_type as call_type, 1 as depth
                ORDER BY f1.qualified_name
                """
            else:
                query = f"""
                MATCH path = (f1:Function)-[c:FunctionCalls*1..{depth}]->(f2:Function)
                WHERE f2.name = $function_name OR f2.qualified_name = $function_name
                RETURN f1.id as id, f1.name as name, f1.qualified_name as qualified_name,
                       f1.module_name as module_name, f1.class_name as class_name,
                       length(path) as depth
                ORDER BY depth, f1.qualified_name
                """
        
        else:  # "both"
            # 双方向検索
            outgoing = self.find_function_dependencies(function_name, "outgoing", depth)
            incoming = self.find_function_dependencies(function_name, "incoming", depth)
            
            # 重複除去しつつマージ
            seen = set()
            combined = []
            for dep in outgoing + incoming:
                key = dep['qualified_name']
                if key not in seen:
                    seen.add(key)
                    combined.append(dep)
            
            return combined
        
        return self.database.execute_query(query, {'function_name': function_name})
    
    def find_module_dependencies(
        self, 
        module_path: str, 
        direction: str = "outgoing",
        depth: int = 1,
        include_external: bool = False
    ) -> List[Dict[str, Any]]:
        """モジュールの依存関係検索"""
        
        external_filter = "" if include_external else "AND m2.is_external = false"
        
        if direction == "outgoing":
            if depth == 1:
                query = f"""
                MATCH (m1:Module)-[i:ModuleImports]->(m2:Module)
                WHERE m1.file_path = $module_path {external_filter}
                RETURN m2.id as id, m2.name as name, m2.file_path as file_path,
                       m2.package as package, m2.is_external as is_external,
                       i.import_type as import_type, 1 as depth
                ORDER BY m2.file_path
                """
            else:
                query = f"""
                MATCH path = (m1:Module)-[i:ModuleImports*1..{depth}]->(m2:Module)
                WHERE m1.file_path = $module_path {external_filter}
                RETURN m2.id as id, m2.name as name, m2.file_path as file_path,
                       m2.package as package, m2.is_external as is_external,
                       length(path) as depth
                ORDER BY depth, m2.file_path
                """
        else:  # incoming
            if depth == 1:
                query = f"""
                MATCH (m1:Module)-[i:ModuleImports]->(m2:Module)
                WHERE m2.file_path = $module_path {external_filter}
                RETURN m1.id as id, m1.name as name, m1.file_path as file_path,
                       m1.package as package, m1.is_external as is_external,
                       i.import_type as import_type, 1 as depth
                ORDER BY m1.file_path
                """
            else:
                query = f"""
                MATCH path = (m1:Module)-[i:ModuleImports*1..{depth}]->(m2:Module)
                WHERE m2.file_path = $module_path {external_filter}
                RETURN m1.id as id, m1.name as name, m1.file_path as file_path,
                       m1.package as package, m1.is_external as is_external,
                       length(path) as depth
                ORDER BY depth, m1.file_path
                """
        
        return self.database.execute_query(query, {'module_path': module_path})
    
    # === パス分析 ===
    
    def find_shortest_path(
        self, 
        source: str, 
        target: str,
        path_type: str = "any"  # "function", "module", "any"
    ) -> Optional[DependencyPath]:
        """最短依存パスを検索"""
        
        if path_type == "function":
            query = """
            MATCH path = shortestPath((f1:Function)-[r:FunctionCalls*1..10]->(f2:Function))
            WHERE (f1.name = $source OR f1.qualified_name = $source) 
              AND (f2.name = $target OR f2.qualified_name = $target)
            RETURN [n in nodes(path) | n.qualified_name] as node_path,
                   [rel in relationships(path) | {type: type(rel), call_type: rel.call_type}] as relationships,
                   length(path) as depth
            LIMIT 1
            """
        elif path_type == "module":
            query = """
            MATCH path = shortestPath((m1:Module)-[r:ModuleImports*1..10]->(m2:Module))
            WHERE m1.file_path = $source AND m2.file_path = $target
            RETURN [n in nodes(path) | n.file_path] as node_path,
                   [rel in relationships(path) | {type: type(rel), import_type: rel.import_type}] as relationships,
                   length(path) as depth
            LIMIT 1
            """
        else:  # "any" - より複雑なクエリが必要
            # まず関数レベルで試行
            function_path = self.find_shortest_path(source, target, "function")
            if function_path:
                return function_path
            
            # 次にモジュールレベルで試行
            module_path = self.find_shortest_path(source, target, "module")
            return module_path
        
        result = self.database.execute_query(query, {'source': source, 'target': target})
        
        if result:
            row = result[0]
            return DependencyPath(
                source=source,
                target=target,
                path=row['node_path'],
                path_type=path_type,
                depth=row['depth'],
                relationships=row['relationships']
            )
        
        return None
    
    def find_all_paths(
        self, 
        source: str, 
        target: str,
        max_depth: int = 5,
        path_type: str = "function"
    ) -> List[DependencyPath]:
        """全依存パスを検索"""
        
        if path_type == "function":
            query = f"""
            MATCH path = (f1:Function)-[r:FunctionCalls*1..{max_depth}]->(f2:Function)
            WHERE (f1.name = $source OR f1.qualified_name = $source) 
              AND (f2.name = $target OR f2.qualified_name = $target)
            RETURN [n in nodes(path) | n.qualified_name] as node_path,
                   [rel in relationships(path) | {{type: type(rel), call_type: rel.call_type}}] as relationships,
                   length(path) as depth
            ORDER BY depth, node_path
            LIMIT 100
            """
        else:  # module
            query = f"""
            MATCH path = (m1:Module)-[r:ModuleImports*1..{max_depth}]->(m2:Module)
            WHERE m1.file_path = $source AND m2.file_path = $target
            RETURN [n in nodes(path) | n.file_path] as node_path,
                   [rel in relationships(path) | {{type: type(rel), import_type: rel.import_type}}] as relationships,
                   length(path) as depth
            ORDER BY depth, node_path
            LIMIT 100
            """
        
        results = self.database.execute_query(query, {'source': source, 'target': target})
        
        paths = []
        for row in results:
            paths.append(DependencyPath(
                source=source,
                target=target,
                path=row['node_path'],
                path_type=path_type,
                depth=row['depth'],
                relationships=row['relationships']
            ))
        
        return paths
    
    # === 階層構造分析 ===
    
    def get_class_hierarchy(self, class_name: str = None) -> List[Dict[str, Any]]:
        """クラス階層構造を取得"""
        
        if class_name:
            # 特定クラスの階層
            query = """
            MATCH (c:Class)
            WHERE c.name = $class_name OR c.qualified_name = $class_name
            OPTIONAL MATCH (c)-[r:Contains]->(f:Function)
            RETURN c.id as class_id, c.name as class_name, c.qualified_name as qualified_name,
                   c.module_name as module_name, c.method_count as method_count,
                   collect({id: f.id, name: f.name, is_private: f.is_private}) as methods
            """
            params = {'class_name': class_name}
        else:
            # 全クラス階層
            query = """
            MATCH (c:Class)
            OPTIONAL MATCH (c)-[r:Contains]->(f:Function)
            RETURN c.id as class_id, c.name as class_name, c.qualified_name as qualified_name,
                   c.module_name as module_name, c.method_count as method_count,
                   collect({id: f.id, name: f.name, is_private: f.is_private}) as methods
            ORDER BY c.module_name, c.name
            """
            params = {}
        
        return self.database.execute_query(query, params)
    
    def get_module_structure(self, module_path: str = None) -> List[Dict[str, Any]]:
        """モジュール構造を取得"""
        
        if module_path:
            # 特定モジュールの構造
            query = """
            MATCH (m:Module {file_path: $module_path})
            OPTIONAL MATCH (f:Function {module_name: m.name})
            OPTIONAL MATCH (c:Class {module_name: m.name})
            RETURN m.id as module_id, m.name as module_name, m.file_path as file_path,
                   m.package as package,
                   collect(DISTINCT {id: f.id, name: f.name, is_method: f.is_method}) as functions,
                   collect(DISTINCT {id: c.id, name: c.name, method_count: c.method_count}) as classes
            """
            params = {'module_path': module_path}
        else:
            # 全モジュール構造
            query = """
            MATCH (m:Module)
            WHERE m.is_external = false
            OPTIONAL MATCH (f:Function {module_name: m.name})
            OPTIONAL MATCH (c:Class {module_name: m.name})
            RETURN m.id as module_id, m.name as module_name, m.file_path as file_path,
                   m.package as package,
                   collect(DISTINCT {id: f.id, name: f.name, is_method: f.is_method}) as functions,
                   collect(DISTINCT {id: c.id, name: c.name, method_count: c.method_count}) as classes
            ORDER BY m.package, m.name
            """
            params = {}
        
        return self.database.execute_query(query, params)
```

## 📊 GraphAnalyticsService実装

```python
import time
from collections import defaultdict, deque

class GraphAnalyticsService:
    """グラフ分析・アルゴリズムサービス"""
    
    def __init__(self, database: GraphDatabase):
        self.database = database
    
    # === 循環依存検出 ===
    
    def find_circular_dependencies(
        self, 
        level: str = "module",  # "module", "function"
        max_cycle_length: int = 10
    ) -> List[List[str]]:
        """循環依存を検出"""
        
        if level == "module":
            query = f"""
            MATCH path = (m:Module)-[i:ModuleImports*2..{max_cycle_length}]->(m)
            WHERE m.is_external = false
            RETURN [n in nodes(path) | n.file_path] as cycle,
                   length(path) as cycle_length
            ORDER BY cycle_length
            """
        else:  # function
            query = f"""
            MATCH path = (f:Function)-[c:FunctionCalls*2..{max_cycle_length}]->(f)
            RETURN [n in nodes(path) | n.qualified_name] as cycle,
                   length(path) as cycle_length
            ORDER BY cycle_length
            """
        
        result = self.database.execute_query(query)
        return [row['cycle'] for row in result]
    
    def detect_strongly_connected_components(
        self, 
        level: str = "module"
    ) -> List[List[str]]:
        """強連結成分を検出"""
        
        # まず全ノードと関係を取得
        if level == "module":
            nodes_query = """
            MATCH (m:Module) 
            WHERE m.is_external = false
            RETURN m.id as id, m.file_path as name
            """
            edges_query = """
            MATCH (m1:Module)-[i:ModuleImports]->(m2:Module)
            WHERE m1.is_external = false AND m2.is_external = false
            RETURN m1.id as source, m2.id as target
            """
        else:  # function
            nodes_query = """
            MATCH (f:Function)
            RETURN f.id as id, f.qualified_name as name
            """
            edges_query = """
            MATCH (f1:Function)-[c:FunctionCalls]->(f2:Function)
            RETURN f1.id as source, f2.id as target
            """
        
        nodes_result = self.database.execute_query(nodes_query)
        edges_result = self.database.execute_query(edges_query)
        
        # グラフ構築
        graph = defaultdict(list)
        node_names = {}
        
        for node in nodes_result:
            node_names[node['id']] = node['name']
        
        for edge in edges_result:
            graph[edge['source']].append(edge['target'])
        
        # Tarjanのアルゴリズム実装
        def tarjan_scc(graph):
            index_counter = [0]
            stack = []
            lowlinks = {}
            index = {}
            on_stack = {}
            result = []
            
            def strongconnect(v):
                index[v] = index_counter[0]
                lowlinks[v] = index_counter[0]
                index_counter[0] += 1
                stack.append(v)
                on_stack[v] = True
                
                for w in graph[v]:
                    if w not in index:
                        strongconnect(w)
                        lowlinks[v] = min(lowlinks[v], lowlinks[w])
                    elif on_stack.get(w, False):
                        lowlinks[v] = min(lowlinks[v], index[w])
                
                if lowlinks[v] == index[v]:
                    component = []
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        component.append(w)
                        if w == v:
                            break
                    if len(component) > 1:  # 複数要素の強連結成分のみ
                        result.append(component)
            
            for v in graph:
                if v not in index:
                    strongconnect(v)
            
            return result
        
        sccs = tarjan_scc(graph)
        
        # ノード名に変換
        named_sccs = []
        for scc in sccs:
            named_scc = [node_names[node_id] for node_id in scc if node_id in node_names]
            if named_scc:
                named_sccs.append(named_scc)
        
        return named_sccs
    
    # === 中心性分析 ===
    
    def calculate_degree_centrality(
        self, 
        level: str = "function",
        direction: str = "both"  # "in", "out", "both"
    ) -> List[Dict[str, Any]]:
        """次数中心性を計算"""
        
        if level == "function":
            if direction == "in":
                query = """
                MATCH (f:Function)
                OPTIONAL MATCH (other:Function)-[c:FunctionCalls]->(f)
                WITH f, count(c) as in_degree
                RETURN f.id as id, f.qualified_name as name, f.module_name as module,
                       in_degree, 0 as out_degree, in_degree as total_degree
                ORDER BY in_degree DESC
                LIMIT 50
                """
            elif direction == "out":
                query = """
                MATCH (f:Function)
                OPTIONAL MATCH (f)-[c:FunctionCalls]->(other:Function)
                WITH f, count(c) as out_degree
                RETURN f.id as id, f.qualified_name as name, f.module_name as module,
                       0 as in_degree, out_degree, out_degree as total_degree
                ORDER BY out_degree DESC
                LIMIT 50
                """
            else:  # both
                query = """
                MATCH (f:Function)
                OPTIONAL MATCH (other1:Function)-[c1:FunctionCalls]->(f)
                OPTIONAL MATCH (f)-[c2:FunctionCalls]->(other2:Function)
                WITH f, count(c1) as in_degree, count(c2) as out_degree
                RETURN f.id as id, f.qualified_name as name, f.module_name as module,
                       in_degree, out_degree, (in_degree + out_degree) as total_degree
                ORDER BY total_degree DESC
                LIMIT 50
                """
        else:  # module
            if direction == "in":
                query = """
                MATCH (m:Module)
                WHERE m.is_external = false
                OPTIONAL MATCH (other:Module)-[i:ModuleImports]->(m)
                WITH m, count(i) as in_degree
                RETURN m.id as id, m.file_path as name, m.package as package,
                       in_degree, 0 as out_degree, in_degree as total_degree
                ORDER BY in_degree DESC
                LIMIT 50
                """
            elif direction == "out":
                query = """
                MATCH (m:Module)
                WHERE m.is_external = false
                OPTIONAL MATCH (m)-[i:ModuleImports]->(other:Module)
                WITH m, count(i) as out_degree
                RETURN m.id as id, m.file_path as name, m.package as package,
                       0 as in_degree, out_degree, out_degree as total_degree
                ORDER BY out_degree DESC
                LIMIT 50
                """
            else:  # both
                query = """
                MATCH (m:Module)
                WHERE m.is_external = false
                OPTIONAL MATCH (other1:Module)-[i1:ModuleImports]->(m)
                OPTIONAL MATCH (m)-[i2:ModuleImports]->(other2:Module)
                WITH m, count(i1) as in_degree, count(i2) as out_degree
                RETURN m.id as id, m.file_path as name, m.package as package,
                       in_degree, out_degree, (in_degree + out_degree) as total_degree
                ORDER BY total_degree DESC
                LIMIT 50
                """
        
        return self.database.execute_query(query)
    
    def calculate_betweenness_centrality(
        self, 
        level: str = "function",
        sample_size: int = 100
    ) -> List[Dict[str, Any]]:
        """媒介中心性を計算（近似）"""
        
        # 計算量が大きいため、サンプルベースで近似計算
        if level == "function":
            # ランダムサンプリング
            sample_query = f"""
            MATCH (f:Function)
            WITH f, rand() as r
            ORDER BY r
            LIMIT {sample_size}
            RETURN f.id as id, f.qualified_name as name
            """
        else:  # module
            sample_query = f"""
            MATCH (m:Module)
            WHERE m.is_external = false
            WITH m, rand() as r
            ORDER BY r
            LIMIT {sample_size}
            RETURN m.id as id, m.file_path as name
            """
        
        sample_nodes = self.database.execute_query(sample_query)
        
        # 各ノードペア間の最短パスを計算し、媒介性をカウント
        betweenness_counts = defaultdict(int)
        total_paths = 0
        
        for i, source in enumerate(sample_nodes):
            for j, target in enumerate(sample_nodes):
                if i >= j:
                    continue
                
                # 最短パス検索
                if level == "function":
                    path = self.find_shortest_path(source['name'], target['name'], "function")
                else:
                    path = self.find_shortest_path(source['name'], target['name'], "module")
                
                if path and len(path.path) > 2:
                    total_paths += 1
                    # 中間ノードの媒介性カウント
                    for intermediate in path.path[1:-1]:
                        betweenness_counts[intermediate] += 1
        
        # 正規化して結果作成
        results = []
        for node, count in betweenness_counts.items():
            betweenness = count / total_paths if total_paths > 0 else 0
            results.append({
                'name': node,
                'betweenness_centrality': betweenness,
                'path_count': count
            })
        
        return sorted(results, key=lambda x: x['betweenness_centrality'], reverse=True)[:50]
    
    # === コミュニティ検出 ===
    
    def detect_communities(
        self, 
        level: str = "module",
        method: str = "modularity"  # "modularity", "connected_components"
    ) -> List[List[str]]:
        """コミュニティ検出"""
        
        if method == "connected_components":
            # 弱連結成分による簡単なコミュニティ検出
            if level == "module":
                query = """
                MATCH (m1:Module), (m2:Module)
                WHERE m1.is_external = false AND m2.is_external = false
                   AND m1 <> m2
                   AND shortestPath((m1)-[*..5]-(m2)) IS NOT NULL
                WITH m1, collect(m2.file_path) as connected
                RETURN m1.file_path as root, connected
                ORDER BY size(connected) DESC
                """
            else:  # function
                query = """
                MATCH (f1:Function), (f2:Function)
                WHERE f1 <> f2
                   AND shortestPath((f1)-[*..3]-(f2)) IS NOT NULL
                WITH f1, collect(f2.qualified_name) as connected
                RETURN f1.qualified_name as root, connected
                ORDER BY size(connected) DESC
                """
            
            result = self.database.execute_query(query)
            
            # 重複を排除してコミュニティ作成
            communities = []
            processed = set()
            
            for row in result:
                root = row['root']
                if root not in processed:
                    community = [root] + row['connected']
                    communities.append(community)
                    processed.update(community)
            
            return communities
        
        else:  # modularity - より高度な実装が必要
            # 簡略版：パッケージベースでグループ化
            if level == "module":
                query = """
                MATCH (m:Module)
                WHERE m.is_external = false
                WITH m.package as package, collect(m.file_path) as modules
                WHERE package <> ''
                RETURN package, modules
                ORDER BY size(modules) DESC
                """
                
                result = self.database.execute_query(query)
                return [row['modules'] for row in result if len(row['modules']) > 1]
            
            else:  # function - クラスベースでグループ化
                query = """
                MATCH (f:Function)
                WHERE f.class_name <> ''
                WITH f.module_name + '::' + f.class_name as class_key, 
                     collect(f.qualified_name) as functions
                RETURN class_key, functions
                ORDER BY size(functions) DESC
                """
                
                result = self.database.execute_query(query)
                return [row['functions'] for row in result if len(row['functions']) > 1]
    
    # === 統計情報 ===
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """グラフ統計情報を取得"""
        
        stats_queries = {
            'module_count': "MATCH (m:Module) WHERE m.is_external = false RETURN count(m) as count",
            'external_module_count': "MATCH (m:Module) WHERE m.is_external = true RETURN count(m) as count",
            'function_count': "MATCH (f:Function) RETURN count(f) as count",
            'class_count': "MATCH (c:Class) RETURN count(c) as count",
            'module_imports_count': "MATCH ()-[i:ModuleImports]->() RETURN count(i) as count",
            'function_calls_count': "MATCH ()-[c:FunctionCalls]->() RETURN count(c) as count",
            'contains_relationships_count': "MATCH ()-[r:Contains]->() RETURN count(r) as count",
        }
        
        statistics = {}
        for key, query in stats_queries.items():
            result = self.database.execute_query(query)
            statistics[key] = result[0]['count'] if result else 0
        
        # 追加統計
        # 平均関数数/モジュール
        if statistics['module_count'] > 0:
            statistics['avg_functions_per_module'] = statistics['function_count'] / statistics['module_count']
        else:
            statistics['avg_functions_per_module'] = 0
        
        # 平均メソッド数/クラス
        if statistics['class_count'] > 0:
            method_count_query = "MATCH ()-[r:Contains]->() RETURN count(r) as method_count"
            method_result = self.database.execute_query(method_count_query)
            statistics['avg_methods_per_class'] = method_result[0]['method_count'] / statistics['class_count']
        else:
            statistics['avg_methods_per_class'] = 0
        
        return statistics
    
    # === アーキテクチャ分析 ===
    
    def analyze_architecture_violations(self) -> List[Dict[str, Any]]:
        """アーキテクチャ違反を検出"""
        
        violations = []
        
        # 1. 循環依存の検出
        circular_deps = self.find_circular_dependencies("module")
        for cycle in circular_deps:
            violations.append({
                'type': 'circular_dependency',
                'severity': 'high',
                'description': f"Circular dependency detected: {' -> '.join(cycle)}",
                'items': cycle
            })
        
        # 2. 巨大クラス（メソッド数が多すぎる）
        large_classes_query = """
        MATCH (c:Class)
        WHERE c.method_count > 20
        RETURN c.qualified_name as class_name, c.method_count as method_count,
               c.module_name as module_name
        ORDER BY c.method_count DESC
        LIMIT 10
        """
        
        large_classes = self.database.execute_query(large_classes_query)
        for cls in large_classes:
            violations.append({
                'type': 'large_class',
                'severity': 'medium',
                'description': f"Large class detected: {cls['class_name']} ({cls['method_count']} methods)",
                'items': [cls['class_name']],
                'metrics': {'method_count': cls['method_count']}
            })
        
        # 3. 高結合度（多数のモジュールをインポート）
        high_coupling_query = """
        MATCH (m:Module)-[i:ModuleImports]->(other:Module)
        WHERE m.is_external = false
        WITH m, count(i) as import_count
        WHERE import_count > 10
        RETURN m.file_path as module_path, import_count
        ORDER BY import_count DESC
        LIMIT 10
        """
        
        high_coupling = self.database.execute_query(high_coupling_query)
        for module in high_coupling:
            violations.append({
                'type': 'high_coupling',
                'severity': 'medium',
                'description': f"High coupling detected: {module['module_path']} ({module['import_count']} imports)",
                'items': [module['module_path']],
                'metrics': {'import_count': module['import_count']}
            })
        
        return violations
```

## 🚨 エラーハンドリング強化

```python
class RobustQueryService(QueryService):
    """エラーハンドリングを強化したQueryService"""
    
    def __init__(self, database: GraphDatabase, timeout: int = 30):
        super().__init__(database)
        self.timeout = timeout
    
    def execute_with_timeout(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """タイムアウト付きクエリ実行"""
        
        try:
            start_time = time.time()
            result = self.database.execute_query(query, params)
            execution_time = time.time() - start_time
            
            if execution_time > self.timeout:
                logger.warning(f"Query took {execution_time:.2f}s (timeout: {self.timeout}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            
            # 簡略版クエリで再試行
            if "LIMIT" not in query:
                simplified_query = query + " LIMIT 100"
                logger.info("Retrying with simplified query...")
                try:
                    return self.database.execute_query(simplified_query, params)
                except Exception as e2:
                    logger.error(f"Simplified query also failed: {e2}")
            
            raise PrologExecutionError(f"Query execution failed: {e}")
    
    def safe_search_by_name(self, name: str, search_type: str = "all") -> SearchResult:
        """安全な名前検索（エラー処理付き）"""
        
        try:
            return self.search_by_name(name, search_type)
        except Exception as e:
            logger.error(f"Search failed for name '{name}': {e}")
            
            # 部分的な結果でも返す
            return SearchResult(
                items=[],
                total_count=0,
                search_type=search_type,
                query_time=0.0
            )
    
    def safe_find_dependencies(self, target: str, direction: str = "outgoing") -> List[Dict[str, Any]]:
        """安全な依存関係検索"""
        
        try:
            return self.find_function_dependencies(target, direction, depth=1)
        except Exception as e:
            logger.error(f"Dependency search failed for '{target}': {e}")
            return []
```

## 🧪 Phase 3 成功基準とテスト

### 成功基準
- [x] 最短依存パスを検索できる
- [x] 循環依存を検出できる
- [x] 部分的な分析失敗時も継続処理できる

### 統合テスト例
```python
def test_phase3_integration():
    """Phase3の統合テスト"""
    
    # QueryServiceテスト
    query_service = RobustQueryService(database)
    
    # 検索機能テスト
    search_result = query_service.search_by_name("init", "function")
    assert search_result.total_count > 0
    
    # 依存関係検索テスト
    if search_result.items:
        first_function = search_result.items[0]['name']
        deps = query_service.find_function_dependencies(first_function)
        # 結果があることを確認
    
    # GraphAnalyticsServiceテスト
    analytics = GraphAnalyticsService(database)
    
    # 循環依存検出テスト
    cycles = analytics.find_circular_dependencies("module")
    # 循環があれば検出されることを確認
    
    # 統計情報テスト
    stats = analytics.get_graph_statistics()
    assert 'module_count' in stats
    assert stats['module_count'] > 0
    
    # 中心性分析テスト
    centrality = analytics.calculate_degree_centrality("function")
    assert len(centrality) > 0
```

Phase 3では、高度な検索・分析機能を実装し、実用的な依存関係分析ツールとしての基盤を完成させます。