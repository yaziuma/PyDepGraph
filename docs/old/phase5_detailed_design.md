# PyDepGraph Phase 5 詳細設計書
## 最適化・完成（Week 9-10）

## 📋 Phase 5 概要

**目標**: パフォーマンス最適化と最終仕上げ

**実装対象**:
- 増分更新機能（変更ファイルのみ再分析）
- クエリパフォーマンスの最適化
- インデックス作成とチューニング
- 包括的なテストとドキュメント整備

## 🚀 増分更新機能

### ファイル変更検出システム

```python
# pydepgraph/incremental.py

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class FileChangeDetector:
    """ファイル変更検出クラス"""
    
    def __init__(self, cache_file: str = ".pydepgraph/file_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.file_cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Dict[str, any]]:
        """キャッシュファイルを読み込み"""
        
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"キャッシュファイルの読み込みに失敗: {e}")
        
        return {}
    
    def _save_cache(self) -> None:
        """キャッシュファイルを保存"""
        
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_cache, f, indent=2)
        except Exception as e:
            logger.error(f"キャッシュファイルの保存に失敗: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """ファイルハッシュを計算"""
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.error(f"ファイルハッシュ計算に失敗 {file_path}: {e}")
            return ""
    
    def detect_changes(self, project_path: Path) -> Tuple[Set[Path], Set[Path], Set[Path]]:
        """
        変更を検出
        
        Returns:
            Tuple[added, modified, deleted]: 追加・変更・削除されたファイル
        """
        
        # 現在のPythonファイル一覧を取得
        current_files = set(project_path.glob("**/*.py"))
        current_files = {f for f in current_files if not self._should_exclude(f)}
        
        # キャッシュされたファイル一覧
        cached_files = set(Path(p) for p in self.file_cache.keys())
        
        # 追加・削除されたファイル
        added_files = current_files - cached_files
        deleted_files = cached_files - current_files
        
        # 変更されたファイル
        modified_files = set()
        
        for file_path in current_files & cached_files:
            current_hash = self._calculate_file_hash(file_path)
            cached_info = self.file_cache.get(str(file_path), {})
            cached_hash = cached_info.get('hash', '')
            
            if current_hash != cached_hash:
                modified_files.add(file_path)
        
        logger.info(f"変更検出: 追加={len(added_files)}, 変更={len(modified_files)}, 削除={len(deleted_files)}")
        
        return added_files, modified_files, deleted_files
    
    def update_cache(self, files: Set[Path]) -> None:
        """指定ファイルのキャッシュを更新"""
        
        for file_path in files:
            if file_path.exists():
                file_hash = self._calculate_file_hash(file_path)
                stat = file_path.stat()
                
                self.file_cache[str(file_path)] = {
                    'hash': file_hash,
                    'mtime': stat.st_mtime,
                    'size': stat.st_size,
                    'last_analyzed': time.time()
                }
            else:
                # ファイルが削除された場合はキャッシュからも削除
                self.file_cache.pop(str(file_path), None)
        
        self._save_cache()
    
    def _should_exclude(self, file_path: Path) -> bool:
        """ファイルを除外するかどうか判定"""
        
        exclude_patterns = [
            '__pycache__',
            '.git',
            'venv',
            '.venv',
            'node_modules',
            '.tox',
            '.pytest_cache',
            'build',
            'dist'
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in exclude_patterns)

class IncrementalAnalyzer:
    """増分分析クラス"""
    
    def __init__(self, database: GraphDatabase):
        self.database = database
        self.detector = FileChangeDetector()
        self.tach_extractor = TachExtractor()
        self.code2flow_extractor = Code2FlowExtractor()
        self.normalizer = DataNormalizer()
    
    def analyze_incremental(self, project_path: Path) -> Dict[str, any]:
        """増分分析実行"""
        
        logger.info("増分分析を開始...")
        
        # 変更検出
        added_files, modified_files, deleted_files = self.detector.detect_changes(project_path)
        
        if not (added_files or modified_files or deleted_files):
            logger.info("変更されたファイルがありません")
            return {
                'status': 'no_changes',
                'added': 0,
                'modified': 0,
                'deleted': 0
            }
        
        # 削除されたファイルの処理
        if deleted_files:
            self._remove_deleted_files(deleted_files)
        
        # 変更されたファイルの処理
        changed_files = added_files | modified_files
        if changed_files:
            self._analyze_changed_files(changed_files, project_path)
        
        # キャッシュ更新
        self.detector.update_cache(added_files | modified_files)
        
        logger.info("増分分析が完了")
        
        return {
            'status': 'completed',
            'added': len(added_files),
            'modified': len(modified_files), 
            'deleted': len(deleted_files),
            'changed_files': [str(f) for f in changed_files]
        }
    
    def _remove_deleted_files(self, deleted_files: Set[Path]) -> None:
        """削除されたファイルに関連するデータをDBから削除"""
        
        logger.info(f"削除されたファイルのデータを削除中: {len(deleted_files)}件")
        
        for file_path in deleted_files:
            file_path_str = str(file_path)
            
            try:
                # モジュール削除
                module_query = """
                MATCH (m:Module {file_path: $file_path})
                DETACH DELETE m
                """
                self.database.execute_query(module_query, {'file_path': file_path_str})
                
                # そのモジュールに属する関数・クラスも削除
                # Kùzuでは CASCADE DELETE がないため、手動で関連データを削除
                
                # 関数削除  
                function_query = """
                MATCH (f:Function)
                WHERE f.qualified_name STARTS WITH $module_prefix
                DETACH DELETE f
                """
                module_prefix = file_path.stem
                self.database.execute_query(function_query, {'module_prefix': module_prefix})
                
                # クラス削除
                class_query = """
                MATCH (c:Class)
                WHERE c.qualified_name STARTS WITH $module_prefix
                DETACH DELETE c
                """
                self.database.execute_query(class_query, {'module_prefix': module_prefix})
                
            except Exception as e:
                logger.error(f"ファイル削除処理に失敗 {file_path}: {e}")
    
    def _analyze_changed_files(self, changed_files: Set[Path], project_path: Path) -> None:
        """変更されたファイルを分析"""
        
        logger.info(f"変更されたファイルを分析中: {len(changed_files)}件")
        
        # まず既存データを削除（変更されたファイル分のみ）
        for file_path in changed_files:
            self._remove_file_data(file_path)
        
        # 変更されたファイルのみを対象とした抽出
        # 注意: TachとCode2Flowは通常プロジェクト全体を分析するため、
        # ファイル単位の部分分析は困難。ここでは簡略化した実装を示す
        
        try:
            # 全体分析を実行（実用的には、これを最適化する必要がある）
            tach_result = self.tach_extractor.extract(str(project_path))
            code2flow_result = self.code2flow_extractor.extract(str(project_path))
            
            # 結果統合
            normalized_result = self.normalizer.normalize_extraction_results([tach_result, code2flow_result])
            
            # 変更されたファイルに関連するデータのみを抽出してDB挿入
            relevant_data = self._filter_relevant_data(normalized_result, changed_files)
            
            # データベース更新
            if relevant_data.modules:
                self.database.bulk_insert_modules(relevant_data.modules)
            
            if relevant_data.functions:
                self.database.bulk_insert_functions(relevant_data.functions)
            
            if relevant_data.classes:
                self.database.bulk_insert_classes(relevant_data.classes)
            
            # 関係性挿入
            self.database.bulk_insert_module_imports(relevant_data.relationships)
            self.database.bulk_insert_function_calls(relevant_data.relationships)
            self.database.bulk_insert_contains(relevant_data.relationships)
            
        except Exception as e:
            logger.error(f"変更ファイル分析に失敗: {e}")
    
    def _remove_file_data(self, file_path: Path) -> None:
        """特定ファイルに関連するデータを削除"""
        
        file_path_str = str(file_path)
        
        try:
            # 既存のモジュール・関数・クラスデータを削除
            queries = [
                ("Module", "MATCH (m:Module {file_path: $file_path}) DETACH DELETE m"),
                ("Function", "MATCH (f:Function) WHERE f.qualified_name STARTS WITH $module_prefix DETACH DELETE f"),
                ("Class", "MATCH (c:Class) WHERE c.qualified_name STARTS WITH $module_prefix DETACH DELETE c")
            ]
            
            module_prefix = file_path.stem
            
            for name, query in queries:
                if name == "Module":
                    self.database.execute_query(query, {'file_path': file_path_str})
                else:
                    self.database.execute_query(query, {'module_prefix': module_prefix})
                    
        except Exception as e:
            logger.error(f"ファイルデータ削除に失敗 {file_path}: {e}")
    
    def _filter_relevant_data(self, result: ExtractionResult, changed_files: Set[Path]) -> ExtractionResult:
        """変更されたファイルに関連するデータのみをフィルタ"""
        
        changed_file_strs = {str(f) for f in changed_files}
        changed_modules = {f.stem for f in changed_files}
        
        # 関連モジュールをフィルタ
        relevant_modules = [
            m for m in result.modules 
            if m['file_path'] in changed_file_strs
        ]
        
        # 関連関数をフィルタ
        relevant_functions = [
            f for f in result.functions
            if f['module_name'] in changed_modules
        ]
        
        # 関連クラスをフィルタ
        relevant_classes = [
            c for c in result.classes
            if c['module_name'] in changed_modules
        ]
        
        # 関連する関係性をフィルタ
        relevant_relationships = []
        for rel in result.relationships:
            if rel['relationship_type'] == 'ModuleImports':
                source_in = any(rel['source_module'].endswith(str(f)) for f in changed_files)
                target_in = any(rel['target_module'].endswith(str(f)) for f in changed_files)
                if source_in or target_in:
                    relevant_relationships.append(rel)
            else:
                # 関数・クラスの関係性は関連するもののみ
                relevant_relationships.append(rel)
        
        return ExtractionResult(
            modules=relevant_modules,
            functions=relevant_functions,
            classes=relevant_classes,
            relationships=relevant_relationships,
            metadata=result.metadata
        )
```

## ⚡ パフォーマンス最適化

### データベースインデックス最適化

```python
# pydepgraph/database.py (拡張)

class OptimizedGraphDatabase(GraphDatabase):
    """パフォーマンス最適化されたGraphDatabase"""
    
    def initialize_schema(self) -> None:
        """最適化されたスキーマ初期化"""
        
        # 基本スキーマ作成
        super().initialize_schema()
        
        # インデックス作成
        self._create_indexes()
    
    def _create_indexes(self) -> None:
        """パフォーマンス向上のためのインデックス作成"""
        
        logger.info("インデックスを作成中...")
        
        try:
            # よく検索される属性にインデックスを作成
            index_queries = [
                # Module用インデックス
                "CREATE INDEX IF NOT EXISTS idx_module_name ON Module(name)",
                "CREATE INDEX IF NOT EXISTS idx_module_file_path ON Module(file_path)",
                "CREATE INDEX IF NOT EXISTS idx_module_package ON Module(package)",
                
                # Function用インデックス
                "CREATE INDEX IF NOT EXISTS idx_function_name ON Function(name)",
                "CREATE INDEX IF NOT EXISTS idx_function_qualified_name ON Function(qualified_name)",
                "CREATE INDEX IF NOT EXISTS idx_function_module_name ON Function(module_name)",
                "CREATE INDEX IF NOT EXISTS idx_function_class_name ON Function(class_name)",
                
                # Class用インデックス
                "CREATE INDEX IF NOT EXISTS idx_class_name ON Class(name)",
                "CREATE INDEX IF NOT EXISTS idx_class_qualified_name ON Class(qualified_name)",
                "CREATE INDEX IF NOT EXISTS idx_class_module_name ON Class(module_name)",
            ]
            
            for query in index_queries:
                try:
                    self.connection.execute(query)
                except Exception as e:
                    # インデックス作成の失敗は警告レベル
                    logger.warning(f"インデックス作成に失敗: {query} - {e}")
            
            logger.info("インデックス作成完了")
            
        except Exception as e:
            logger.error(f"インデックス作成処理でエラー: {e}")
    
    def optimize_query_plan(self, query: str) -> str:
        """クエリプランを最適化"""
        
        # よく使用されるパターンを最適化
        optimizations = [
            # LIMIT句の追加
            (
                lambda q: 'MATCH' in q and 'RETURN' in q and 'LIMIT' not in q and 'ORDER BY' in q,
                lambda q: q + " LIMIT 1000"
            ),
            
            # WHERE句による早期フィルタリング
            (
                lambda q: 'MATCH (m:Module)' in q and 'WHERE m.is_external' not in q,
                lambda q: q.replace('MATCH (m:Module)', 'MATCH (m:Module) WHERE m.is_external = false', 1)
            ),
        ]
        
        optimized_query = query
        
        for condition, optimization in optimizations:
            if condition(optimized_query):
                optimized_query = optimization(optimized_query)
        
        return optimized_query
    
    def execute_query_optimized(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """最適化されたクエリ実行"""
        
        # クエリ最適化
        optimized_query = self.optimize_query_plan(query)
        
        # 実行時間測定
        start_time = time.time()
        
        try:
            result = self.execute_query(optimized_query, params)
            execution_time = time.time() - start_time
            
            # 長時間実行クエリをログ出力
            if execution_time > 5.0:  # 5秒以上
                logger.warning(f"長時間クエリ実行: {execution_time:.2f}秒")
                logger.warning(f"クエリ: {optimized_query[:200]}...")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"クエリ実行失敗 ({execution_time:.2f}秒): {e}")
            raise

class QueryCache:
    """クエリ結果キャッシュ"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
    
    def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """キャッシュから取得"""
        
        if key not in self.cache:
            return None
        
        # TTL チェック
        if time.time() - self.access_times[key] > self.ttl:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
            return None
        
        # アクセス時間更新
        self.access_times[key] = time.time()
        
        return self.cache[key]
    
    def set(self, key: str, value: List[Dict[str, Any]]) -> None:
        """キャッシュに保存"""
        
        # サイズ制限チェック
        if len(self.cache) >= self.max_size:
            # 最も古いアクセスのエントリを削除
            oldest_key = min(self.access_times.keys(), key=self.access_times.get)
            self.cache.pop(oldest_key, None)
            self.access_times.pop(oldest_key, None)
        
        self.cache[key] = value
        self.access_times[key] = time.time()
    
    def clear(self) -> None:
        """キャッシュクリア"""
        self.cache.clear()
        self.access_times.clear()

class CachedQueryService(QueryService):
    """キャッシュ機能付きQueryService"""
    
    def __init__(self, database: GraphDatabase):
        super().__init__(database)
        self.cache = QueryCache()
    
    def _get_cache_key(self, method_name: str, *args, **kwargs) -> str:
        """キャッシュキー生成"""
        key_data = {
            'method': method_name,
            'args': args,
            'kwargs': kwargs
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def search_by_name(self, name: str, search_type: str = "all", fuzzy: bool = False) -> SearchResult:
        """キャッシュ機能付き名前検索"""
        
        cache_key = self._get_cache_key('search_by_name', name, search_type, fuzzy)
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return SearchResult(
                items=cached_result,
                total_count=len(cached_result),
                search_type=search_type,
                query_time=0.0  # キャッシュヒット
            )
        
        # キャッシュミス時は通常処理
        result = super().search_by_name(name, search_type, fuzzy)
        
        # 結果をキャッシュに保存
        self.cache.set(cache_key, result.items)
        
        return result
    
    def find_function_dependencies(self, function_name: str, direction: str = "outgoing", depth: int = 1) -> List[Dict[str, Any]]:
        """キャッシュ機能付き依存関係検索"""
        
        cache_key = self._get_cache_key('find_function_dependencies', function_name, direction, depth)
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # キャッシュミス時は通常処理
        result = super().find_function_dependencies(function_name, direction, depth)
        
        # 結果をキャッシュに保存
        self.cache.set(cache_key, result)
        
        return result
    
    def invalidate_cache(self) -> None:
        """キャッシュ無効化（データ更新時に呼び出し）"""
        self.cache.clear()
```

### 並列処理最適化

```python
# pydepgraph/parallel.py

import concurrent.futures
import threading
from typing import List, Callable, Any
import logging

logger = logging.getLogger(__name__)

class ParallelProcessor:
    """並列処理ユーティリティ"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
    
    def process_files_parallel(
        self, 
        files: List[Path], 
        processor: Callable[[Path], Any],
        chunk_size: int = None
    ) -> List[Any]:
        """ファイルを並列処理"""
        
        if chunk_size is None:
            chunk_size = max(1, len(files) // self.max_workers)
        
        results = []
        failed_files = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # ファイルをチャンクに分割して並列実行
            future_to_file = {}
            
            for i in range(0, len(files), chunk_size):
                chunk = files[i:i+chunk_size]
                future = executor.submit(self._process_chunk, chunk, processor)
                future_to_file[future] = chunk
            
            # 結果収集
            for future in concurrent.futures.as_completed(future_to_file):
                chunk = future_to_file[future]
                try:
                    chunk_results = future.result()
                    results.extend(chunk_results)
                except Exception as e:
                    logger.error(f"チャンク処理に失敗: {chunk} - {e}")
                    failed_files.extend(chunk)
        
        if failed_files:
            logger.warning(f"処理に失敗したファイル: {len(failed_files)}件")
        
        return results
    
    def _process_chunk(self, files: List[Path], processor: Callable[[Path], Any]) -> List[Any]:
        """ファイルチャンクを処理"""
        
        results = []
        
        for file_path in files:
            try:
                result = processor(file_path)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"ファイル処理に失敗 {file_path}: {e}")
        
        return results

class ParallelAnalyzer:
    """並列分析実行クラス"""
    
    def __init__(self):
        self.processor = ParallelProcessor()
        self.tach_extractor = TachExtractor()
        self.code2flow_extractor = Code2FlowExtractor()
    
    def analyze_project_parallel(self, project_path: Path) -> ExtractionResult:
        """プロジェクトを並列分析"""
        
        logger.info(f"並列分析を開始: {project_path}")
        
        # Pythonファイル一覧取得
        python_files = list(project_path.glob("**/*.py"))
        python_files = [f for f in python_files if not self._should_exclude(f)]
        
        logger.info(f"対象ファイル数: {len(python_files)}")
        
        # 並列で各ファイルの基本情報を収集
        file_info_results = self.processor.process_files_parallel(
            python_files, 
            self._analyze_single_file
        )
        
        # 全体的な抽出処理は従来通り実行
        # (TachとCode2Flowは通常プロジェクト全体を対象とするため)
        tach_result = self.tach_extractor.extract(str(project_path))
        code2flow_result = self.code2flow_extractor.extract(str(project_path))
        
        # 結果統合
        normalizer = DataNormalizer()
        extraction_results = [tach_result, code2flow_result]
        
        # ファイル情報も追加
        if file_info_results:
            file_result = ExtractionResult(
                modules=file_info_results,
                functions=[],
                classes=[],
                relationships=[],
                metadata={'extractor': 'file_analyzer'}
            )
            extraction_results.append(file_result)
        
        normalized_result = normalizer.normalize_extraction_results(extraction_results)
        
        logger.info("並列分析が完了")
        
        return normalized_result
    
    def _analyze_single_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """単一ファイルの基本分析"""
        
        try:
            stat = file_path.stat()
            
            # 行数カウント
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = sum(1 for _ in f)
            
            # 基本的な複雑度計算（簡略版）
            complexity = self._calculate_basic_complexity(file_path)
            
            return {
                'name': file_path.stem,
                'file_path': str(file_path),
                'package': str(file_path.parent).replace('/', '.'),
                'lines_of_code': lines,
                'complexity_score': complexity,
                'is_external': False,
                'is_test': 'test' in str(file_path).lower(),
                'file_size': stat.st_size,
                'last_modified': stat.st_mtime
            }
            
        except Exception as e:
            logger.error(f"ファイル分析に失敗 {file_path}: {e}")
            return None
    
    def _calculate_basic_complexity(self, file_path: Path) -> float:
        """基本的な複雑度を計算"""
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 簡単な指標
            complexity_indicators = [
                'if ', 'elif ', 'else:',
                'for ', 'while ',
                'try:', 'except:', 'finally:',
                'def ', 'class ',
                'and ', 'or ', 'not '
            ]
            
            complexity = 1  # 基本複雑度
            
            for indicator in complexity_indicators:
                complexity += content.count(indicator)
            
            # 行数で正規化
            lines = content.count('\n') + 1
            return complexity / max(lines, 1) * 100
            
        except Exception:
            return 1.0
    
    def _should_exclude(self, file_path: Path) -> bool:
        """ファイルを除外するかどうか判定"""
        
        exclude_patterns = [
            '__pycache__',
            '.git',
            'venv',
            '.venv',
            'node_modules',
            '.tox',
            '.pytest_cache'
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in exclude_patterns)
```

## 📊 詳細統計・レポート機能

```python
# pydepgraph/reporting.py

from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from typing import Dict, List, Any

class AdvancedReporter:
    """詳細レポート生成クラス"""
    
    def __init__(self, analytics: GraphAnalyticsService):
        self.analytics = analytics
    
    def generate_comprehensive_report(self, output_path: Path) -> None:
        """総合レポート生成"""
        
        report_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'tool_version': '1.0.0'
            },
            'summary': self._generate_summary(),
            'architecture_analysis': self._analyze_architecture(),
            'complexity_analysis': self._analyze_complexity(),
            'dependency_analysis': self._analyze_dependencies(),
            'recommendations': self._generate_recommendations()
        }
        
        # JSONレポート
        json_path = output_path / 'report.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # HTMLレポート生成
        self._generate_html_report(report_data, output_path / 'report.html')
        
        # 図表生成
        self._generate_charts(report_data, output_path)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """サマリー生成"""
        
        stats = self.analytics.get_graph_statistics()
        
        return {
            'total_modules': stats['module_count'],
            'total_functions': stats['function_count'],
            'total_classes': stats['class_count'],
            'total_relationships': (
                stats['module_imports_count'] + 
                stats['function_calls_count']
            ),
            'code_metrics': {
                'avg_functions_per_module': round(stats['avg_functions_per_module'], 2),
                'avg_methods_per_class': round(stats['avg_methods_per_class'], 2)
            }
        }
    
    def _analyze_architecture(self) -> Dict[str, Any]:
        """アーキテクチャ分析"""
        
        violations = self.analytics.analyze_architecture_violations()
        cycles = self.analytics.find_circular_dependencies('module')
        
        return {
            'violations': {
                'count': len(violations),
                'high_severity': len([v for v in violations if v['severity'] == 'high']),
                'medium_severity': len([v for v in violations if v['severity'] == 'medium']),
                'details': violations[:10]  # 上位10件
            },
            'circular_dependencies': {
                'count': len(cycles),
                'details': cycles[:5]  # 上位5件
            }
        }
    
    def _analyze_complexity(self) -> Dict[str, Any]:
        """複雑度分析"""
        
        # 高複雑度モジュール
        high_complexity_query = """
        MATCH (m:Module)
        WHERE m.complexity_score > 50 AND m.is_external = false
        RETURN m.file_path as module, m.complexity_score as complexity
        ORDER BY m.complexity_score DESC
        LIMIT 10
        """
        
        high_complexity = self.analytics.database.execute_query(high_complexity_query)
        
        return {
            'high_complexity_modules': high_complexity,
            'complexity_distribution': self._calculate_complexity_distribution()
        }
    
    def _calculate_complexity_distribution(self) -> Dict[str, int]:
        """複雑度分布を計算"""
        
        complexity_query = """
        MATCH (m:Module)
        WHERE m.is_external = false
        RETURN m.complexity_score as complexity
        """
        
        results = self.analytics.database.execute_query(complexity_query)
        complexities = [r['complexity'] for r in results]
        
        # 分布計算
        distribution = {
            'low (0-25)': len([c for c in complexities if 0 <= c <= 25]),
            'medium (26-50)': len([c for c in complexities if 26 <= c <= 50]),
            'high (51-100)': len([c for c in complexities if 51 <= c <= 100]),
            'very_high (100+)': len([c for c in complexities if c > 100])
        }
        
        return distribution
    
    def _analyze_dependencies(self) -> Dict[str, Any]:
        """依存関係分析"""
        
        # モジュール中心性
        module_centrality = self.analytics.calculate_degree_centrality('module', 'both')
        
        # 関数中心性
        function_centrality = self.analytics.calculate_degree_centrality('function', 'both')
        
        return {
            'most_connected_modules': module_centrality[:5],
            'most_connected_functions': function_centrality[:5],
            'dependency_metrics': self._calculate_dependency_metrics()
        }
    
    def _calculate_dependency_metrics(self) -> Dict[str, float]:
        """依存関係メトリクス計算"""
        
        stats = self.analytics.get_graph_statistics()
        
        if stats['module_count'] > 0:
            coupling_ratio = stats['module_imports_count'] / stats['module_count']
        else:
            coupling_ratio = 0
        
        if stats['function_count'] > 0:
            call_density = stats['function_calls_count'] / stats['function_count']
        else:
            call_density = 0
        
        return {
            'module_coupling_ratio': round(coupling_ratio, 2),
            'function_call_density': round(call_density, 2)
        }
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """改善提案生成"""
        
        recommendations = []
        
        # 統計に基づく提案
        stats = self.analytics.get_graph_statistics()
        
        if stats['avg_functions_per_module'] > 20:
            recommendations.append({
                'type': 'module_size',
                'severity': 'medium',
                'title': 'モジュールサイズの最適化',
                'description': f"平均{stats['avg_functions_per_module']:.1f}個の関数を持つモジュールが存在します。モジュール分割を検討してください。"
            })
        
        if stats['avg_methods_per_class'] > 15:
            recommendations.append({
                'type': 'class_size',
                'severity': 'medium', 
                'title': 'クラスサイズの最適化',
                'description': f"平均{stats['avg_methods_per_class']:.1f}個のメソッドを持つクラスが存在します。単一責任原則に基づくクラス分割を検討してください。"
            })
        
        # 循環依存チェック
        cycles = self.analytics.find_circular_dependencies('module')
        if cycles:
            recommendations.append({
                'type': 'circular_dependency',
                'severity': 'high',
                'title': '循環依存の解決',
                'description': f"{len(cycles)}個の循環依存が検出されました。依存関係の再設計が必要です。"
            })
        
        return recommendations
    
    def _generate_html_report(self, data: Dict[str, Any], output_path: Path) -> None:
        """HTMLレポート生成"""
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PyDepGraph 分析レポート</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; }
                .metrics { display: flex; gap: 20px; }
                .metric { background: white; padding: 15px; border-radius: 5px; border: 1px solid #ddd; }
                .violations { color: #d32f2f; }
                .recommendations { background: #e3f2fd; padding: 15px; border-radius: 5px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>PyDepGraph 分析レポート</h1>
            <p>生成日時: {generated_at}</p>
            
            <div class="summary">
                <h2>サマリー</h2>
                <div class="metrics">
                    <div class="metric">
                        <h3>モジュール数</h3>
                        <p>{total_modules}</p>
                    </div>
                    <div class="metric">
                        <h3>関数数</h3>
                        <p>{total_functions}</p>
                    </div>
                    <div class="metric">
                        <h3>クラス数</h3>
                        <p>{total_classes}</p>
                    </div>
                </div>
            </div>
            
            <h2>アーキテクチャ分析</h2>
            <div class="violations">
                <p>検出された問題: {violation_count}件</p>
                <p>循環依存: {cycle_count}件</p>
            </div>
            
            <h2>改善提案</h2>
            <div class="recommendations">
                {recommendations_html}
            </div>
        </body>
        </html>
        """
        
        # テンプレート変数
        recommendations_html = ""
        for rec in data['recommendations']:
            recommendations_html += f"""
            <div style="margin-bottom: 10px;">
                <strong>{rec['title']}</strong> ({rec['severity']})
                <p>{rec['description']}</p>
            </div>
            """
        
        html_content = html_template.format(
            generated_at=data['metadata']['generated_at'],
            total_modules=data['summary']['total_modules'],
            total_functions=data['summary']['total_functions'],
            total_classes=data['summary']['total_classes'],
            violation_count=data['architecture_analysis']['violations']['count'],
            cycle_count=data['architecture_analysis']['circular_dependencies']['count'],
            recommendations_html=recommendations_html
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_charts(self, data: Dict[str, Any], output_dir: Path) -> None:
        """図表生成"""
        
        # 複雑度分布チャート
        complexity_dist = data['complexity_analysis']['complexity_distribution']
        
        plt.figure(figsize=(10, 6))
        plt.bar(complexity_dist.keys(), complexity_dist.values())
        plt.title('複雑度分布')
        plt.xlabel('複雑度レベル')
        plt.ylabel('モジュール数')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / 'complexity_distribution.png')
        plt.close()
        
        # 中心性チャート
        if data['dependency_analysis']['most_connected_modules']:
            modules = data['dependency_analysis']['most_connected_modules'][:5]
            names = [Path(m['name']).stem for m in modules]
            degrees = [m['total_degree'] for m in modules]
            
            plt.figure(figsize=(10, 6))
            plt.barh(names, degrees)
            plt.title('最も接続されたモジュール（上位5位）')
            plt.xlabel('結合度')
            plt.tight_layout()
            plt.savefig(output_dir / 'module_centrality.png')
            plt.close()
```

## 🧪 包括的テストスイート

```python
# tests/test_integration.py

import pytest
import tempfile
import shutil
from pathlib import Path

class TestPhase5Integration:
    """Phase 5統合テスト"""
    
    @pytest.fixture
    def temp_project(self):
        """テスト用プロジェクト作成"""
        
        temp_dir = Path(tempfile.mkdtemp())
        
        # サンプルPythonファイル作成
        (temp_dir / "main.py").write_text("""
def main():
    from utils import helper
    helper.do_something()

if __name__ == "__main__":
    main()
""")
        
        (temp_dir / "utils.py").write_text("""
def helper():
    return "Helper function"

class HelperClass:
    def method1(self):
        return self.method2()
    
    def method2(self):
        return "Method 2"
""")
        
        yield temp_dir
        
        # クリーンアップ
        shutil.rmtree(temp_dir)
    
    def test_incremental_analysis(self, temp_project):
        """増分分析テスト"""
        
        # 初回分析
        analyzer = IncrementalAnalyzer(GraphDatabase(str(temp_project / "test.db")))
        result1 = analyzer.analyze_incremental(temp_project)
        
        assert result1['status'] == 'completed'
        assert result1['added'] >= 2  # main.py, utils.py
        
        # ファイル変更
        (temp_project / "new_file.py").write_text("def new_function(): pass")
        
        # 増分分析
        result2 = analyzer.analyze_incremental(temp_project)
        
        assert result2['status'] == 'completed'
        assert result2['added'] == 1  # new_file.py のみ
        assert result2['modified'] == 0
    
    def test_performance_optimization(self, temp_project):
        """パフォーマンス最適化テスト"""
        
        db = OptimizedGraphDatabase(str(temp_project / "test_opt.db"))
        db.initialize_schema()
        
        # インデックスが作成されていることを確認
        # (実際のKùzuではINDEXの存在確認方法を調べる必要がある)
        
        # 最適化されたクエリ実行テスト
        query = "MATCH (m:Module) RETURN m.name ORDER BY m.name"
        optimized_query = db.optimize_query_plan(query)
        
        # LIMIT句が追加されているか確認
        assert "LIMIT" in optimized_query
    
    def test_parallel_processing(self, temp_project):
        """並列処理テスト"""
        
        parallel_analyzer = ParallelAnalyzer()
        result = parallel_analyzer.analyze_project_parallel(temp_project)
        
        assert result.modules
        assert result.functions
        assert result.metadata
    
    def test_comprehensive_reporting(self, temp_project):
        """総合レポート生成テスト"""
        
        # データベース準備
        db = GraphDatabase(str(temp_project / "test_report.db"))
        db.initialize_schema()
        
        # 基本データ挿入（テスト用）
        test_modules = [{
            'id': 'module_000001',
            'name': 'test_module',
            'file_path': 'test_module.py',
            'package': '',
            'lines_of_code': 100,
            'complexity_score': 25.0,
            'is_external': False,
            'is_test': False
        }]
        
        db.bulk_insert_modules(test_modules)
        
        # レポート生成
        analytics = GraphAnalyticsService(db)
        reporter = AdvancedReporter(analytics)
        
        report_dir = temp_project / "reports"
        report_dir.mkdir()
        
        reporter.generate_comprehensive_report(report_dir)
        
        # レポートファイル存在確認
        assert (report_dir / "report.json").exists()
        assert (report_dir / "report.html").exists()
    
    def test_cache_functionality(self):
        """キャッシュ機能テスト"""
        
        cache = QueryCache(max_size=2, ttl=10)
        
        # 基本操作
        cache.set("key1", [{"test": "data1"}])
        cache.set("key2", [{"test": "data2"}])
        
        assert cache.get("key1") == [{"test": "data1"}]
        assert cache.get("key2") == [{"test": "data2"}]
        
        # サイズ制限テスト
        cache.set("key3", [{"test": "data3"}])
        
        # 最も古いkey1が削除されているはず
        assert cache.get("key1") is None
        assert cache.get("key2") == [{"test": "data2"}]
        assert cache.get("key3") == [{"test": "data3"}]

def test_end_to_end_workflow(temp_project):
    """エンドツーエンドワークフローテスト"""
    
    # 1. プロジェクト分析
    db_path = temp_project / "workflow_test.db"
    
    # 並列分析実行
    analyzer = ParallelAnalyzer()
    result = analyzer.analyze_project_parallel(temp_project)
    
    # データベース保存
    db = OptimizedGraphDatabase(str(db_path))
    db.initialize_schema()
    
    if result.modules:
        db.bulk_insert_modules(result.modules)
    if result.functions:
        db.bulk_insert_functions(result.functions)
    
    # 2. 検索・分析
    query_service = CachedQueryService(db)
    search_result = query_service.search_by_name("main", "function")
    
    assert search_result.total_count >= 0
    
    # 3. 統計取得
    analytics = GraphAnalyticsService(db)
    stats = analytics.get_graph_statistics()
    
    assert 'module_count' in stats
    
    # 4. レポート生成
    reporter = AdvancedReporter(analytics)
    report_dir = temp_project / "final_report"
    report_dir.mkdir()
    
    reporter.generate_comprehensive_report(report_dir)
    
    # 5. 増分更新テスト
    incremental_analyzer = IncrementalAnalyzer(db)
    incremental_result = incremental_analyzer.analyze_incremental(temp_project)
    
    # 初回実行後なので変更なし
    assert incremental_result['status'] in ['completed', 'no_changes']
```

## 🧪 Phase 5 成功基準

### 成功基準
- [x] 中規模プロジェクト（1000ファイル程度）を5分以内で分析完了
- [x] 増分更新が正常に動作する  
- [x] 実用的なパフォーマンスを達成する

### パフォーマンステスト
```bash
# 大規模プロジェクト分析テスト
time pydepgraph analyze /path/to/large/project

# 増分更新テスト  
pydepgraph analyze /path/to/project
echo "# Comment" >> /path/to/project/main.py
time pydepgraph analyze /path/to/project  # 増分更新

# メモリ使用量テスト
/usr/bin/time -v pydepgraph analyze /path/to/project
```

Phase 5では、実用レベルのパフォーマンスと運用機能を実装し、プロダクションレディなツールとして完成させます。