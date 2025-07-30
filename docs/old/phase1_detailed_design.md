# PyDepGraph Phase 1 詳細設計書
## 基盤実装（Week 1-2）

## 📋 Phase 1 概要

**目標**: 基本的なデータ抽出とデータベース操作の実装

**実装対象**:
- ExtractorBase抽象クラス
- TachExtractor（基本的なモジュール依存関係抽出）
- GraphDatabase（Kùzuデータベース基本操作）
- 基本的なデータ構造とスキーマ定義

## 📊 入力データ形式（Tach）

### Tach出力形式
```json
{
  "prolog_mcp/prolog_wrapper.py": [
    "prolog_mcp/streamable_http_manager.py",
    "prolog_mcp/logger.py",
    "prolog_mcp/exceptions.py",
    "prolog_mcp/config.py"
  ]
}
```

**データ構造**:
- **形式**: JSONオブジェクト（key-value）
- **キー**: インポート元モジュールパス（文字列）
- **値**: インポート先モジュールパスの配列

## 🏗️ 基本データ構造

### ExtractionResult
```python
from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class ExtractionResult:
    modules: List[Dict[str, Any]]
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    metadata: Dict[str, Any]
```

### Module情報構造
```python
module_info = {
    'id': str,                    # 一意識別子
    'name': str,                  # モジュール名
    'file_path': str,             # ファイルパス
    'package': str,               # パッケージ名
    'lines_of_code': int,         # 行数（Phase1では0）
    'complexity_score': float,    # 複雑度（Phase1では0.0）
    'is_external': bool,          # 外部ライブラリフラグ
    'is_test': bool,             # テストファイルフラグ
}
```

### Relationship情報構造
```python
relationship_info = {
    'relationship_type': str,     # 'ModuleImports'
    'source_module': str,         # インポート元モジュールパス
    'target_module': str,         # インポート先モジュールパス
    'import_type': str,           # 'direct'（Phase1では固定）
    'import_alias': str,          # エイリアス（Phase1では空文字）
    'line_number': int,           # 行番号（Phase1では0）
    'is_conditional': bool,       # 条件付きインポート（Phase1ではFalse）
}
```

## 🔧 ExtractorBase抽象クラス

```python
from abc import ABC, abstractmethod
from typing import List
import logging

logger = logging.getLogger(__name__)

class ExtractorBase(ABC):
    """依存関係抽出器の抽象基底クラス"""
    
    @abstractmethod
    def extract(self, project_path: str) -> ExtractionResult:
        """
        プロジェクトから依存関係を抽出
        
        Args:
            project_path: プロジェクトのルートパス
            
        Returns:
            ExtractionResult: 抽出結果
            
        Raises:
            PrologExecutionError: 抽出に失敗した場合
        """
        pass
    
    @abstractmethod
    def get_supported_file_types(self) -> List[str]:
        """
        サポートするファイル拡張子を返す
        
        Returns:
            List[str]: サポートする拡張子のリスト
        """
        pass
    
    def validate_project_path(self, project_path: str) -> bool:
        """
        プロジェクトパスの有効性を検証
        
        Args:
            project_path: 検証するパス
            
        Returns:
            bool: 有効な場合True
        """
        path = Path(project_path)
        return path.exists() and path.is_dir()
```

## 🔧 TachExtractor実装

```python
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any

class TachExtractor(ExtractorBase):
    """Tachを使用したモジュール依存関係抽出器"""
    
    def extract(self, project_path: str) -> ExtractionResult:
        """Tachコマンドを実行してモジュール依存関係を抽出"""
        
        if not self.validate_project_path(project_path):
            raise ValueError(f"Invalid project path: {project_path}")
        
        # Tachコマンド実行
        try:
            result = subprocess.run(
                ["tach", "report", "dependencies", "--format", "json"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5分のタイムアウト
            )
            
            if result.returncode != 0:
                raise PrologExecutionError(f"Tach execution failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise PrologExecutionError("Tach execution timed out")
        except FileNotFoundError:
            raise PrologExecutionError("Tach command not found. Please install tach.")
        
        # JSON解析
        try:
            dependencies = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise PrologExecutionError(f"Failed to parse Tach output: {e}")
        
        # PyDepGraph形式に変換
        modules = []
        relationships = []
        module_id_counter = 0
        
        # 全モジュールの集合を作成
        all_modules = set()
        for source_module, imported_modules in dependencies.items():
            all_modules.add(source_module)
            all_modules.extend(imported_modules)
        
        # モジュール情報の構築
        module_id_map = {}
        for module_path in all_modules:
            module_id = f"module_{module_id_counter:06d}"
            module_id_counter += 1
            
            module_info = self._extract_module_info(module_path, module_id)
            modules.append(module_info)
            module_id_map[module_path] = module_id
        
        # 依存関係の構築
        for source_module, imported_modules in dependencies.items():
            for target_module in imported_modules:
                relationship = {
                    'relationship_type': 'ModuleImports',
                    'source_module': source_module,
                    'target_module': target_module,
                    'source_module_id': module_id_map[source_module],
                    'target_module_id': module_id_map[target_module],
                    'import_type': 'direct',  # Phase1では詳細不明のためdefault
                    'import_alias': '',       # Phase1では空文字
                    'line_number': 0,         # Phase1では0
                    'is_conditional': False,  # Phase1ではFalse
                }
                relationships.append(relationship)
        
        logger.info(f"Tach extraction completed: {len(modules)} modules, {len(relationships)} relationships")
        
        return ExtractionResult(
            modules=modules,
            functions=[],  # Phase1では空
            classes=[],    # Phase1では空
            relationships=relationships,
            metadata={
                'extractor': 'tach',
                'total_modules': len(modules),
                'total_relationships': len(relationships),
                'project_path': project_path,
            }
        )
    
    def _extract_module_info(self, module_path: str, module_id: str) -> Dict[str, Any]:
        """モジュールパスから基本情報を抽出"""
        path = Path(module_path)
        
        return {
            'id': module_id,
            'name': path.stem,
            'file_path': module_path,
            'package': str(path.parent).replace('/', '.') if path.parent != Path('.') else '',
            'lines_of_code': 0,      # Phase1では計算しない
            'complexity_score': 0.0,  # Phase1では計算しない
            'is_external': self._is_external_module(module_path),
            'is_test': self._is_test_module(module_path),
        }
    
    def _is_external_module(self, module_path: str) -> bool:
        """外部モジュールかどうかを判定"""
        # 相対パス以外は外部、またはsite-packagesを含む場合は外部
        return not module_path.startswith('.') and 'site-packages' in module_path
    
    def _is_test_module(self, module_path: str) -> bool:
        """テストモジュールかどうかを判定"""
        lower_path = module_path.lower()
        return ('test' in lower_path or 
                'tests' in lower_path or 
                lower_path.endswith('_test.py') or
                lower_path.endswith('test_.py'))
    
    def get_supported_file_types(self) -> List[str]:
        """サポートするファイル拡張子を返す"""
        return ['.py']
```

## 🗄️ GraphDatabase基本実装

```python
import kuzu
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class GraphDatabase:
    """Kùzuグラフデータベース操作クラス"""
    
    def __init__(self, db_path: str):
        """
        データベース初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.database = kuzu.Database(str(self.db_path))
        self.connection = kuzu.Connection(self.database)
        
        logger.info(f"Graph database initialized at: {self.db_path}")
    
    def initialize_schema(self) -> None:
        """グラフデータベースのスキーマを初期化"""
        
        logger.info("Initializing database schema...")
        
        # 既存テーブルの確認と削除（開発時）
        self._drop_existing_tables()
        
        # ノードテーブル作成
        self._create_module_table()
        
        # エッジテーブル作成
        self._create_module_imports_table()
        
        logger.info("Database schema initialized successfully")
    
    def _drop_existing_tables(self) -> None:
        """既存テーブルの削除（開発時用）"""
        try:
            self.connection.execute("DROP TABLE IF EXISTS ModuleImports;")
            self.connection.execute("DROP TABLE IF EXISTS Module;")
        except Exception as e:
            logger.debug(f"Table drop failed (expected): {e}")
    
    def _create_module_table(self) -> None:
        """Moduleノードテーブル作成"""
        query = """
        CREATE NODE TABLE Module (
            id STRING,
            name STRING,
            file_path STRING,
            package STRING,
            lines_of_code INT32,
            complexity_score DOUBLE,
            is_external BOOLEAN,
            is_test BOOLEAN,
            PRIMARY KEY (id)
        );
        """
        self.connection.execute(query)
        logger.debug("Module table created")
    
    def _create_module_imports_table(self) -> None:
        """ModuleImportsエッジテーブル作成"""
        query = """
        CREATE REL TABLE ModuleImports (
            FROM Module TO Module,
            import_type STRING,
            import_alias STRING,
            line_number INT32,
            is_conditional BOOLEAN
        );
        """
        self.connection.execute(query)
        logger.debug("ModuleImports table created")
    
    def bulk_insert_modules(self, modules: List[Dict[str, Any]]) -> None:
        """モジュールを一括挿入"""
        if not modules:
            logger.warning("No modules to insert")
            return
        
        logger.info(f"Inserting {len(modules)} modules...")
        
        for module in modules:
            query = """
            CREATE (m:Module {
                id: $id,
                name: $name,
                file_path: $file_path,
                package: $package,
                lines_of_code: $lines_of_code,
                complexity_score: $complexity_score,
                is_external: $is_external,
                is_test: $is_test
            })
            """
            
            params = {
                'id': module['id'],
                'name': module['name'],
                'file_path': module['file_path'],
                'package': module['package'],
                'lines_of_code': module['lines_of_code'],
                'complexity_score': module['complexity_score'],
                'is_external': module['is_external'],
                'is_test': module['is_test'],
            }
            
            self.connection.execute(query, params)
        
        logger.info(f"Successfully inserted {len(modules)} modules")
    
    def bulk_insert_module_imports(self, relationships: List[Dict[str, Any]]) -> None:
        """モジュール依存関係を一括挿入"""
        if not relationships:
            logger.warning("No relationships to insert")
            return
        
        logger.info(f"Inserting {len(relationships)} module import relationships...")
        
        for rel in relationships:
            query = """
            MATCH (source:Module {id: $source_id}), (target:Module {id: $target_id})
            CREATE (source)-[r:ModuleImports {
                import_type: $import_type,
                import_alias: $import_alias,
                line_number: $line_number,
                is_conditional: $is_conditional
            }]->(target)
            """
            
            params = {
                'source_id': rel['source_module_id'],
                'target_id': rel['target_module_id'],
                'import_type': rel['import_type'],
                'import_alias': rel['import_alias'],
                'line_number': rel['line_number'],
                'is_conditional': rel['is_conditional'],
            }
            
            self.connection.execute(query, params)
        
        logger.info(f"Successfully inserted {len(relationships)} relationships")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Cypherクエリを実行"""
        try:
            if params:
                result = self.connection.execute(query, params)
            else:
                result = self.connection.execute(query)
            
            # 結果を辞書のリストに変換
            return [dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            raise
    
    def close(self) -> None:
        """データベース接続を閉じる"""
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()
        logger.info("Database connection closed")
```

## 🔍 基本クエリ実装

```python
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
```

## 🧪 Phase 1 成功基準とテスト

### 成功基準
- [x] Tachコマンドを実行してJSONを取得できる
- [x] 取得したデータをKùzuデータベースに格納できる
- [x] 基本的なモジュール検索クエリが動作する

### 基本的な動作テスト例
```python
def test_phase1_integration():
    """Phase1の統合テスト"""
    
    # 1. TachExtractor動作確認
    extractor = TachExtractor()
    result = extractor.extract("/path/to/test/project")
    
    assert len(result.modules) > 0
    assert len(result.relationships) > 0
    assert result.metadata['extractor'] == 'tach'
    
    # 2. GraphDatabase動作確認
    db = GraphDatabase("test.db")
    db.initialize_schema()
    db.bulk_insert_modules(result.modules)
    db.bulk_insert_module_imports(result.relationships)
    
    # 3. 基本クエリ動作確認
    query_service = BasicQueryService(db)
    all_modules = query_service.get_all_modules()
    
    assert len(all_modules) == len(result.modules)
    
    # 4. 依存関係検索確認
    if all_modules:
        first_module = all_modules[0]
        dependencies = query_service.find_module_dependencies(first_module['id'])
        # 依存関係があることを確認（プロジェクトによる）
    
    db.close()
```

Phase 1では、TachによるモジュールレベルのDependency抽出とKùzuデータベースへの基本的な格納・検索機能を実装します。