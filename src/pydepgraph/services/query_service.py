# pydepgraph/services/query_service.py
from typing import Any, Optional, List, Dict
from ..database import GraphDatabase
from ..models import Module, Function, Class, ModuleImport, FunctionCall

class BasicQueryService:
    """Phase1用の基本的なクエリサービス"""

    def __init__(self, database: GraphDatabase):
        self.database = database

    def find_module_by_name(self, module_name: str) -> Optional[Dict[str, Any]]:
        """モジュール名でモジュールを検索"""
        query = """
        MATCH (m:Module {name: $module_name})
        RETURN m.id as id, m.name as name, m.file_path as file_path,
               m.package as package, m.is_external as is_external
        LIMIT 1
        """

        result = self.database.execute_query(query, {'module_name': module_name})
        return result[0] if result else None

    def find_module_dependencies(self, module_id: str) -> List[Dict[str, Any]]:
        """モジュールが依存するモジュール一覧を取得"""
        query = """
        MATCH (source:Module {id: $module_id})-[r:ModuleImports]->(target:Module)
        RETURN target.id as id, target.name as name, target.file_path as file_path,
               r.import_type as import_type
        ORDER BY target.name
        """

        return self.database.execute_query(query, {'module_id': module_id})

    def find_module_dependents(self, module_id: str) -> List[Dict[str, Any]]:
        """モジュールに依存するモジュール一覧を取得"""
        query = """
        MATCH (source:Module)-[r:ModuleImports]->(target:Module {id: $module_id})
        RETURN source.id as id, source.name as name, source.file_path as file_path,
               r.import_type as import_type
        ORDER BY source.name
        """

        return self.database.execute_query(query, {'module_id': module_id})

    def get_all_modules(self, include_external: bool = False) -> List[Dict[str, Any]]:
        """全モジュール一覧を取得"""
        if include_external:
            query = """
            MATCH (m:Module)
            RETURN m.id as id, m.name as name, m.file_path as file_path,
                   m.package as package, m.is_external as is_external
            ORDER BY m.name
            """
        else:
            query = """
            MATCH (m:Module)
            WHERE m.is_external = false
            RETURN m.id as id, m.name as name, m.file_path as file_path,
                   m.package as package, m.is_external as is_external
            ORDER BY m.name
            """

        return self.database.execute_query(query)


class ExtendedQueryService(BasicQueryService):
    """Phase2用の拡張クエリサービス（Function/Class対応）"""

    def find_function_by_name(self, function_name: str) -> Optional[Dict[str, Any]]:
        """関数名で関数を検索"""
        query = """
        MATCH (f:Function {name: $function_name})
        RETURN f.id as id, f.name as name, f.qualified_name as qualified_name,
               f.file_path as file_path, f.cyclomatic_complexity as complexity,
               f.is_method as is_method, f.class_id as class_id
        LIMIT 1
        """
        
        result = self.database.execute_query(query, {'function_name': function_name})
        return result[0] if result else None

    def find_class_by_name(self, class_name: str) -> Optional[Dict[str, Any]]:
        """クラス名でクラスを検索"""
        query = """
        MATCH (c:Class {name: $class_name})
        RETURN c.id as id, c.name as name, c.qualified_name as qualified_name,
               c.file_path as file_path, c.method_count as method_count,
               c.inheritance_depth as inheritance_depth, c.is_abstract as is_abstract
        LIMIT 1
        """
        
        result = self.database.execute_query(query, {'class_name': class_name})
        return result[0] if result else None

    def find_function_calls_from(self, function_id: str) -> List[Dict[str, Any]]:
        """指定関数が呼び出す関数一覧を取得"""
        query = """
        MATCH (source:Function {id: $function_id})-[r:FunctionCalls]->(target:Function)
        RETURN target.id as id, target.name as name, target.qualified_name as qualified_name,
               r.call_type as call_type, r.line_number as line_number
        ORDER BY target.name
        """
        
        return self.database.execute_query(query, {'function_id': function_id})

    def find_function_calls_to(self, function_id: str) -> List[Dict[str, Any]]:
        """指定関数を呼び出す関数一覧を取得"""
        query = """
        MATCH (source:Function)-[r:FunctionCalls]->(target:Function {id: $function_id})
        RETURN source.id as id, source.name as name, source.qualified_name as qualified_name,
               r.call_type as call_type, r.line_number as line_number
        ORDER BY source.name
        """
        
        return self.database.execute_query(query, {'function_id': function_id})

    def find_class_methods(self, class_id: str) -> List[Dict[str, Any]]:
        """クラスに属するメソッド一覧を取得"""
        query = """
        MATCH (c:Class {id: $class_id})-[r:Contains]->(f:Function)
        RETURN f.id as id, f.name as name, f.qualified_name as qualified_name,
               f.cyclomatic_complexity as complexity, f.parameter_count as parameter_count,
               f.is_static as is_static, f.is_class_method as is_class_method
        ORDER BY f.name
        """
        
        return self.database.execute_query(query, {'class_id': class_id})

    def find_class_hierarchy_up(self, class_id: str) -> List[Dict[str, Any]]:
        """クラスの継承階層（親クラス方向）を取得"""
        query = """
        MATCH (child:Class {id: $class_id})-[r:Inheritance]->(parent:Class)
        RETURN parent.id as id, parent.name as name, parent.qualified_name as qualified_name,
               parent.file_path as file_path, parent.is_abstract as is_abstract
        ORDER BY parent.name
        """
        
        return self.database.execute_query(query, {'class_id': class_id})

    def find_class_hierarchy_down(self, class_id: str) -> List[Dict[str, Any]]:
        """クラスの継承階層（子クラス方向）を取得"""
        query = """
        MATCH (parent:Class {id: $class_id})<-[r:Inheritance]-(child:Class)
        RETURN child.id as id, child.name as name, child.qualified_name as qualified_name,
               child.file_path as file_path, child.is_abstract as is_abstract
        ORDER BY child.name
        """
        
        return self.database.execute_query(query, {'class_id': class_id})

    def get_all_functions(self, include_methods: bool = True) -> List[Dict[str, Any]]:
        """全関数一覧を取得"""
        if include_methods:
            query = """
            MATCH (f:Function)
            RETURN f.id as id, f.name as name, f.qualified_name as qualified_name,
                   f.file_path as file_path, f.is_method as is_method,
                   f.cyclomatic_complexity as complexity
            ORDER BY f.name
            """
        else:
            query = """
            MATCH (f:Function)
            WHERE f.is_method = false
            RETURN f.id as id, f.name as name, f.qualified_name as qualified_name,
                   f.file_path as file_path, f.is_method as is_method,
                   f.cyclomatic_complexity as complexity
            ORDER BY f.name
            """
        
        return self.database.execute_query(query)

    def get_all_classes(self) -> List[Dict[str, Any]]:
        """全クラス一覧を取得"""
        query = """
        MATCH (c:Class)
        RETURN c.id as id, c.name as name, c.qualified_name as qualified_name,
               c.file_path as file_path, c.method_count as method_count,
               c.inheritance_depth as inheritance_depth, c.is_abstract as is_abstract
        ORDER BY c.name
        """
        
        return self.database.execute_query(query)

    def search_functions_by_complexity(self, min_complexity: int, max_complexity: int = None) -> List[Dict[str, Any]]:
        """循環複雑度による関数検索"""
        if max_complexity is None:
            query = """
            MATCH (f:Function)
            WHERE f.cyclomatic_complexity >= $min_complexity
            RETURN f.id as id, f.name as name, f.qualified_name as qualified_name,
                   f.file_path as file_path, f.cyclomatic_complexity as complexity
            ORDER BY f.cyclomatic_complexity DESC
            """
            params = {'min_complexity': min_complexity}
        else:
            query = """
            MATCH (f:Function)
            WHERE f.cyclomatic_complexity >= $min_complexity 
            AND f.cyclomatic_complexity <= $max_complexity
            RETURN f.id as id, f.name as name, f.qualified_name as qualified_name,
                   f.file_path as file_path, f.cyclomatic_complexity as complexity
            ORDER BY f.cyclomatic_complexity DESC
            """
            params = {'min_complexity': min_complexity, 'max_complexity': max_complexity}
        
        return self.database.execute_query(query, params)

    def get_all_module_imports(self) -> List[Dict[str, Any]]:
        """全モジュールimport関係一覧を取得"""
        query = """
        MATCH (source:Module)-[r:ModuleImports]->(target:Module)
        RETURN source.name as source_module, target.name as target_module,
               r.import_type as import_type, r.import_alias as import_alias,
               r.line_number as line_number
        ORDER BY source.name, target.name
        """
        
        return self.database.execute_query(query)

    def get_all_function_calls(self) -> List[Dict[str, Any]]:
        """全関数call関係一覧を取得"""
        query = """
        MATCH (source:Function)-[r:FunctionCalls]->(target:Function)
        RETURN source.qualified_name as source_function, target.qualified_name as target_function,
               r.call_type as call_type, r.line_number as line_number
        ORDER BY source.qualified_name, target.qualified_name
        """
        
        return self.database.execute_query(query)

    def get_all_modules(self, include_external: bool = False) -> List[Module]:
        """全モジュール一覧を取得（モデルオブジェクト版）"""
        results = super().get_all_modules(include_external)
        modules = []
        for row in results:
            if isinstance(row, dict):
                modules.append(Module(
                    name=row.get('name', ''),
                    file_path=row.get('file_path', ''),
                    package=row.get('package'),
                    is_external=row.get('is_external', False)
                ))
        return modules

    def get_all_functions(self, include_methods: bool = True) -> List[Function]:
        """全関数一覧を取得（モデルオブジェクト版）"""
        results = super().get_all_functions(include_methods)
        functions = []
        for row in results:
            if isinstance(row, dict):
                functions.append(Function(
                    name=row.get('name', ''),
                    qualified_name=row.get('qualified_name', ''),
                    file_path=row.get('file_path', ''),
                    cyclomatic_complexity=row.get('complexity'),
                    is_method=row.get('is_method', False)
                ))
        return functions

    def get_all_classes(self) -> List[Class]:
        """全クラス一覧を取得（モデルオブジェクト版）"""
        results = super().get_all_classes()
        classes = []
        for row in results:
            if isinstance(row, dict):
                classes.append(Class(
                    name=row.get('name', ''),
                    qualified_name=row.get('qualified_name', ''),
                    file_path=row.get('file_path', ''),
                    method_count=row.get('method_count'),
                    inheritance_depth=row.get('inheritance_depth'),
                    is_abstract=row.get('is_abstract', False)
                ))
        return classes

    def get_all_module_imports(self) -> List[ModuleImport]:
        """全モジュールimport関係一覧を取得（モデルオブジェクト版）"""
        query = """
        MATCH (source:Module)-[r:ModuleImports]->(target:Module)
        RETURN source.name as source_module, target.name as target_module,
               r.import_type as import_type, r.import_alias as import_alias,
               r.line_number as line_number
        ORDER BY source.name, target.name
        """
        
        results = self.database.execute_query(query)
        imports = []
        for row in results:
            if isinstance(row, dict):
                imports.append(ModuleImport(
                    source_module=row.get('source_module', ''),
                    target_module=row.get('target_module', ''),
                    import_type=row.get('import_type', 'standard'),
                    import_alias=row.get('import_alias'),
                    line_number=row.get('line_number')
                ))
        return imports

    def get_all_function_calls(self) -> List[FunctionCall]:
        """全関数call関係一覧を取得（モデルオブジェクト版）"""
        query = """
        MATCH (source:Function)-[r:FunctionCalls]->(target:Function)
        RETURN source.qualified_name as source_function, target.qualified_name as target_function,
               r.call_type as call_type, r.line_number as line_number
        ORDER BY source.qualified_name, target.qualified_name
        """
        
        results = self.database.execute_query(query)
        calls = []
        for row in results:
            if isinstance(row, dict):
                calls.append(FunctionCall(
                    source_function=row.get('source_function', ''),
                    target_function=row.get('target_function', ''),
                    call_type=row.get('call_type', 'direct'),
                    line_number=row.get('line_number')
                ))
        return calls

# class SearchResult:
#     def __init__(self, items, total_count, search_type, query_time):
#         self.items = items
#         self.total_count = total_count
#         self.search_type = search_type
#         self.query_time = query_time
#
#
# class QueryService:
#     """Service for executing queries against the graph database."""
#
#     def __init__(self, database: GraphDatabase):
#         self.database = database
#
#     def search_by_name(
#         self, name: str, search_type: str = "all", fuzzy: bool = False
#     ) -> SearchResult:
#         print(
#             f"QueryService: Searching for '{name}' (type: {search_type}, fuzzy: {fuzzy})"
#         )
#         return SearchResult([], 0, search_type, 0.1)
#
#
# class QueryCache:
#     """A simple in-memory cache for query results."""
#
#     def __init__(self, max_size: int = 1000, ttl: int = 3600):
#         self.cache = {}
#         self.access_times = {}
#         self.max_size = max_size
#         self.ttl = ttl
#
#     def get(self, key: str) -> Optional[Any]:
#         if key in self.cache and (time.time() - self.access_times[key]) < self.ttl:
#             return self.cache[key]
#         return None
#
#     def set(self, key: str, value: Any) -> None:
#         if len(self.cache) >= self.max_size:
#             oldest_key = min(self.access_times, key=self.access_times.get)
#             del self.cache[oldest_key]
#             del self.access_times[oldest_key]
#         self.cache[key] = value
#         self.access_times[key] = time.time()
#
#
# class CachedQueryService(QueryService):
#     """Query service with a caching layer."""
#
#     def __init__(self, database: GraphDatabase):
#         super().__init__(database)
#         self.cache = QueryCache()
#
#     def _get_cache_key(self, method_name: str, *args, **kwargs) -> str:
#         key_data = {"method": method_name, "args": args, "kwargs": kwargs}
#         return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
#
#     def search_by_name(
#         self, name: str, search_type: str = "all", fuzzy: bool = False
#     ) -> SearchResult:
#         cache_key = self._get_cache_key("search_by_name", name, search_type, fuzzy)
#         cached_result = self.cache.get(cache_key)
#         if cached_result:
#             print("CachedQueryService: Cache hit!")
#             return SearchResult(cached_result, len(cached_result), search_type, 0.0)
#
#         print("CachedQueryService: Cache miss.")
#         result = super().search_by_name(name, search_type, fuzzy)
#         self.cache.set(cache_key, result.items)
#         return result
