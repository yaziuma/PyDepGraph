# pydepgraph/services/query_service.py
from typing import Any, Optional, List, Dict
from ..database import GraphDatabase
import time
import hashlib
import json

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
