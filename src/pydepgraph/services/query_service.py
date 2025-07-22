# pydepgraph/services/query_service.py
from typing import Any, Optional
from ..database import GraphDatabase
import time
import hashlib
import json


class SearchResult:
    def __init__(self, items, total_count, search_type, query_time):
        self.items = items
        self.total_count = total_count
        self.search_type = search_type
        self.query_time = query_time


class QueryService:
    """Service for executing queries against the graph database."""

    def __init__(self, database: GraphDatabase):
        self.database = database

    def search_by_name(
        self, name: str, search_type: str = "all", fuzzy: bool = False
    ) -> SearchResult:
        print(
            f"QueryService: Searching for '{name}' (type: {search_type}, fuzzy: {fuzzy})"
        )
        return SearchResult([], 0, search_type, 0.1)


class QueryCache:
    """A simple in-memory cache for query results."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache and (time.time() - self.access_times[key]) < self.ttl:
            return self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        self.cache[key] = value
        self.access_times[key] = time.time()


class CachedQueryService(QueryService):
    """Query service with a caching layer."""

    def __init__(self, database: GraphDatabase):
        super().__init__(database)
        self.cache = QueryCache()

    def _get_cache_key(self, method_name: str, *args, **kwargs) -> str:
        key_data = {"method": method_name, "args": args, "kwargs": kwargs}
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

    def search_by_name(
        self, name: str, search_type: str = "all", fuzzy: bool = False
    ) -> SearchResult:
        cache_key = self._get_cache_key("search_by_name", name, search_type, fuzzy)
        cached_result = self.cache.get(cache_key)
        if cached_result:
            print("CachedQueryService: Cache hit!")
            return SearchResult(cached_result, len(cached_result), search_type, 0.0)

        print("CachedQueryService: Cache miss.")
        result = super().search_by_name(name, search_type, fuzzy)
        self.cache.set(cache_key, result.items)
        return result
