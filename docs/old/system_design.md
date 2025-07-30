# PyDepGraph システム設計書

## 📋 システム概要

### プロジェクト名
**PyDepGraph** - Python プロジェクト依存関係分析・検索ライブラリ

### アーキテクチャ方針
- **モジュラー設計**: 各機能を独立したコンポーネントとして実装
- **プラグイン機構**: 新しい分析ツールの追加が容易な拡張可能設計
- **データドリブン**: グラフデータベースを中心とした高速検索対応
- **型安全性**: 完全な型ヒント対応による堅牢な実装

## 🏗️ システムアーキテクチャ

### レイヤー構成

```
┌─────────────────────────────────────────────────┐
│                 UI Layer                        │
│  ┌─────────────┐                                 │
│  │     CLI     │                                 │
│  └─────────────┘                                 │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│              Service Layer                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │  Analyzer   │ │   Query     │ │   Graph     │ │
│  │  Service    │ │  Service    │ │ Algorithm   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│             Data Layer                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │ Extractors  │ │ Normalizer  │ │ Kùzu Graph  │ │
│  │ (Tach,      │ │             │ │  Database   │ │
│  │ Code2Flow)  │ │             │ │             │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────┘
```

## 📊 データスキーマ設計

### グラフデータベーススキーマ（Kùzu）

#### ノードテーブル

##### 1. Module ノード
```cypher
CREATE NODE TABLE Module (
    id SERIAL,
    name STRING,
    file_path STRING,
    package STRING,
    lines_of_code INT32,
    complexity_score DOUBLE,
    is_external BOOLEAN,
    is_test BOOLEAN,
    PRIMARY KEY (id)
);
```

##### 2. Function ノード
```cypher
CREATE NODE TABLE Function (
    id SERIAL,
    name STRING,
    qualified_name STRING,
    module_id INT64,
    class_name STRING,
    line_number INT32,
    lines_of_code INT32,
    cyclomatic_complexity INT32,
    is_method BOOLEAN,
    is_async BOOLEAN,
    is_private BOOLEAN,
    docstring STRING,
    PRIMARY KEY (id)
);
```

##### 3. Class ノード
```cypher
CREATE NODE TABLE Class (
    id SERIAL,
    name STRING,
    qualified_name STRING,
    module_id INT64,
    line_number INT32,
    method_count INT32,
    is_abstract BOOLEAN,
    inheritance_depth INT32,
    docstring STRING,
    PRIMARY KEY (id)
);
```

#### エッジテーブル

##### 1. ModuleImports エッジ
```cypher
CREATE REL TABLE ModuleImports (
    FROM Module TO Module,
    import_type STRING, -- 'direct', 'from_import', 'star_import'
    import_alias STRING,
    line_number INT32,
    is_conditional BOOLEAN
);
```

##### 2. FunctionCalls エッジ
```cypher
CREATE REL TABLE FunctionCalls (
    FROM Function TO Function,
    call_type STRING, -- 'direct', 'method', 'async'
    line_number INT32,
    call_context STRING -- 'try', 'except', 'finally', 'if', 'loop'
);
```

##### 3. Inheritance エッジ
```cypher
CREATE REL TABLE Inheritance (
    FROM Class TO Class,
    inheritance_type STRING -- 'extends', 'implements', 'mixin'
);
```

##### 4. Contains エッジ
```cypher
CREATE REL TABLE Contains (
    FROM Module TO Function,
    definition_type STRING -- 'function', 'method', 'property'
);

CREATE REL TABLE Contains (
    FROM Module TO Class,
    definition_type STRING -- 'class'
);

CREATE REL TABLE Contains (
    FROM Class TO Function,
    definition_type STRING -- 'method', 'property', 'staticmethod', 'classmethod'
);
```

## 🔧 コンポーネント設計

### 1. Data Extraction Layer

#### ExtractorBase (抽象基底クラス)
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ExtractionResult:
    modules: List[Dict[str, Any]]
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class ExtractorBase(ABC):
    @abstractmethod
    def extract(self, project_path: str) -> ExtractionResult:
        pass
    
    @abstractmethod
    def get_supported_file_types(self) -> List[str]:
        pass
```

#### TachExtractor (モジュールレベル依存関係)
```python
class TachExtractor(ExtractorBase):
    def extract(self, project_path: str) -> ExtractionResult:
        # Tachを使用してモジュール間依存関係を抽出
        pass
    
    def get_supported_file_types(self) -> List[str]:
        return ['.py']
```

#### Code2FlowExtractor (関数レベル依存関係)
```python
class Code2FlowExtractor(ExtractorBase):
    def extract(self, project_path: str) -> ExtractionResult:
        # Code2Flowを使用して関数間呼び出し関係を抽出
        pass
    
    def get_supported_file_types(self) -> List[str]:
        return ['.py']
```

### 2. Data Processing Layer

#### DataNormalizer
```python
from typing import List, Dict, Any

class DataNormalizer:
    def __init__(self):
        self.id_counter = 0
    
    def normalize_extraction_results(
        self, 
        results: List[ExtractionResult]
    ) -> ExtractionResult:
        # 複数の抽出結果を統合・正規化
        pass
    
    def resolve_duplicates(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 重複データの解決
        pass
    
    def generate_qualified_names(self, data: Dict[str, Any]) -> str:
        # 完全修飾名の生成
        pass
```

### 3. Database Layer

#### GraphDatabase
```python
import kuzu
from typing import List, Dict, Any, Optional

class GraphDatabase:
    def __init__(self, db_path: str):
        self.database = kuzu.Database(db_path)
        self.connection = kuzu.Connection(self.database)
    
    def initialize_schema(self) -> None:
        # スキーマ初期化
        pass
    
    def bulk_insert_nodes(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        # ノードの一括挿入
        pass
    
    def bulk_insert_edges(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        # エッジの一括挿入
        pass
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        # Cypherクエリの実行
        pass
```

### 4. Service Layer

#### AnalyzerService
```python
from typing import List, Optional
from pathlib import Path

class AnalyzerService:
    def __init__(self, database: GraphDatabase):
        self.database = database
        self.extractors = [
            TachExtractor(),
            Code2FlowExtractor()
        ]
        self.normalizer = DataNormalizer()
    
    def analyze_project(self, project_path: Path) -> None:
        # プロジェクトの全体分析
        pass
    
    def update_analysis(self, changed_files: List[Path]) -> None:
        # 増分更新
        pass
```

#### QueryService
```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class DependencyPath:
    source: str
    target: str
    path: List[str]
    path_type: str  # 'function_call', 'import', 'inheritance'
    depth: int

class QueryService:
    def __init__(self, database: GraphDatabase):
        self.database = database
    
    def find_function_dependencies(
        self, 
        function_name: str, 
        direction: str = "outgoing"
    ) -> List[str]:
        # 関数の依存関係検索
        pass
    
    def find_shortest_path(
        self, 
        source: str, 
        target: str
    ) -> Optional[DependencyPath]:
        # 最短依存パス検索
        pass
    
    def find_circular_dependencies(self) -> List[List[str]]:
        # 循環依存検出
        pass
```

#### GraphAnalyticsService
```python
from typing import Dict, List, Tuple

class GraphAnalyticsService:
    def __init__(self, database: GraphDatabase):
        self.database = database
    
    def calculate_centrality(self) -> Dict[str, float]:
        # 中心性分析
        pass
    
    def detect_communities(self) -> List[List[str]]:
        # コミュニティ検出
        pass
    
    def analyze_architecture_violations(self) -> List[Dict[str, Any]]:
        # アーキテクチャ違反検出
        pass
```

### 5. CLI Layer
```python
import click
from pathlib import Path

@click.group()
def cli():
    """PyDepGraph - Python依存関係分析ツール"""
    pass

@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--output', '-o', help='出力形式 (json/yaml)')
def analyze(project_path: str, output: str):
    """プロジェクトを分析"""
    graph = PyDepGraph(Path(project_path))
    graph.analyze()
    
    if output:
        # 結果を指定形式で出力
        pass

@cli.command()
@click.argument('function_name')
@click.option('--direction', default='outgoing', help='検索方向 (outgoing/incoming)')
def dependencies(function_name: str, direction: str):
    """関数の依存関係を検索"""
    graph = PyDepGraph()
    deps = graph.find_dependencies(function_name, direction)
    for dep in deps:
        click.echo(dep)
```

## 🔧 設定管理

### Configuration Schema
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ExtractorConfig(BaseModel):
    enabled: bool = True
    options: Dict[str, Any] = Field(default_factory=dict)

class DatabaseConfig(BaseModel):
    path: Optional[str] = None
    connection_pool_size: int = 5
    query_timeout: int = 30

class AnalysisConfig(BaseModel):
    include_tests: bool = True
    exclude_patterns: List[str] = Field(default_factory=list)
    max_depth: int = 100

class PyDepGraphConfig(BaseModel):
    extractors: Dict[str, ExtractorConfig] = Field(default_factory=dict)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
```

### デフォルト設定ファイル (`pydepgraph.toml`)
```toml
[extractors.tach]
enabled = true

[extractors.code2flow]
enabled = true
[extractors.code2flow.options]
max_depth = 10

[database]
connection_pool_size = 5
query_timeout = 30

[analysis]
include_tests = true
exclude_patterns = [
    "__pycache__/*",
    "*.pyc",
    ".git/*",
    "venv/*",
    ".venv/*"
]
max_depth = 100
```

## 🔧 エラー処理

### エラー処理方針
- **部分的な分析失敗時の継続処理**: 一部ファイルの分析に失敗しても他のファイルは継続
- **エラー内容の詳細な報告**: 失敗したファイルとその理由をユーザーに報告

### データ整合性
- **分析結果の一貫性保証**: グラフデータベースのトランザクション機能を活用
- **増分更新時の整合性維持**: 変更ファイル検出による差分更新

## 🚀 開発フェーズ

### Phase 1: 基盤実装（Week 1-2）
**目標**: 基本的なデータ抽出とデータベース操作の実装

**実装対象**:
- ExtractorBase抽象クラス
- TachExtractor（基本的なモジュール依存関係抽出）
- GraphDatabase（Kùzuデータベース基本操作）
- 基本的なデータ構造とスキーマ定義

**成功基準**:
- Tachコマンドを実行してJSONを取得できる
- 取得したデータをKùzuデータベースに格納できる
- 基本的なモジュール検索クエリが動作する

### Phase 2: 関数レベル分析（Week 3-4）
**目標**: Code2Flowを使った関数レベルの依存関係分析

**実装対象**:
- Code2FlowExtractor（関数間呼び出し関係抽出）
- Function・Classノードテーブルの実装
- FunctionCallsエッジテーブルの実装
- DataNormalizer（複数抽出結果の統合）

**成功基準**:
- Code2Flowの出力を正しく解析できる
- 関数間の呼び出し関係をグラフデータベースに格納できる
- 関数の依存関係検索が動作する

### Phase 3: 検索・分析機能（Week 5-6）
**目標**: 高度な検索・分析機能の実装

**実装対象**:
- QueryService（依存関係検索、パス検索）
- GraphAnalyticsService（循環依存検出）
- 複雑なCypherクエリの実装
- エラーハンドリングの強化

**成功基準**:
- 最短依存パスを検索できる
- 循環依存を検出できる
- 部分的な分析失敗時も継続処理できる

### Phase 4: CLI実装（Week 7-8）
**目標**: コマンドラインインターフェースの完成

**実装対象**:
- Click-based CLI（analyze, deps, path, cycles）
- 結果出力（JSON/YAML形式）
- 設定管理（TOML設定ファイル）
- ログ出力とユーザビリティ向上

**成功基準**:
- 全CLIコマンドが期待通りに動作する
- 設定ファイルによるカスタマイズが可能
- エラー時に分かりやすいメッセージを表示する

### Phase 5: 最適化・完成（Week 9-10）
**目標**: パフォーマンス最適化と最終仕上げ

**実装対象**:
- 増分更新機能（変更ファイルのみ再分析）
- クエリパフォーマンスの最適化
- インデックス作成とチューニング
- 包括的なテストとドキュメント整備

**成功基準**:
- 中規模プロジェクト（1000ファイル程度）を5分以内で分析完了
- 増分更新が正常に動作する
- 実用的なパフォーマンスを達成する

## 📋 各フェーズの成果物

- **Phase 1**: 基本的なTach連携とデータベース操作
- **Phase 2**: 完全な依存関係抽出機能
- **Phase 3**: 高度な検索・分析機能
- **Phase 4**: 使いやすいCLIツール
- **Phase 5**: 本格運用可能なライブラリ

この設計書は、要求仕様書に基づいた個人利用向けの実装可能な技術仕様を提供します。