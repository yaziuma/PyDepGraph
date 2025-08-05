# 詳細設計: 依存関係分析の強化 (v2)

## ⚠️ 重要な注意事項

**このドキュメントの修正履歴**:
- データモデル: `Dependency` → `ModuleImport`に修正済み
- 出力形式: `RawExtractionResult`形式に修正済み
- データベース: Kùzuスキーマに準拠するよう修正済み
- 依存関係: `rich`をpyproject.tomlに追加済み

## 1. 概要

本ドキュメントでは、PyDepGraphの依存関係分析機能を強化するための詳細設計を定義する。主な強化点は以下の2つである。

-   **外部ライブラリ依存関係の抽出**: `requirements.txt`や`pyproject.toml`を解析し、外部ライブラリへの依存関係をグラフに追加する。
-   **ファイル横断的な関数呼び出し解析**: 異なるファイルやモジュールにまたがる関数呼び出しを追跡し、より完全な関数レベルの依存関係グラフを構築する。

## 2. 設計詳細

### 2.1. 外部ライブラリ依存関係の抽出

#### 2.1.1. 担当クラス

-   `pydepgraph.extractors.dependency_file_extractor.DependencyFileExtractor` (新規作成)

#### 2.1.2. データ構造

抽出した依存関係は、`pydepgraph.models.ModuleImport`クラスのインスタンスとして表現する。

-   `source_module`: プロジェクト名 (e.g., `pyprolog`)
-   `target_module`: 外部ライブラリ名 (e.g., `requests`)
-   `import_type`: `EXTERNAL_LIBRARY`
-   `is_external`: `True`

#### 2.1.3. 処理フロー

1.  **Extractorの初期化**: `DependencyFileExtractor`は、プロジェクトのルートパスを引数に初期化される。
2.  **ファイルの探索**: ルートパス配下から`requirements.txt`および`pyproject.toml`を探索する。
3.  **`requirements.txt`の解析**:
    -   ファイルを1行ずつ読み込む。
    -   コメント行 (`#`で始まる) や空行は無視する。
    -   `==`, `>=`, `<=`, `~=`, `[` などのバージョン指定子や追加オプションを区切り文字として、ライブラリ名を抽出する。
    -   例: `requests>=2.25.1` -> `requests`
4.  **`pyproject.toml`の解析**:
    -   Python標準ライブラリの`tomllib`を使用してTOMLファイルをパースする。
    -   `[project.dependencies]` (PEP 621) の配列を読み込む。
    -   `[tool.poetry.dependencies]` (Poetry) の辞書からキー（ライブラリ名）を読み込む。
    -   各ライブラリ名から、`requirements.txt`と同様にバージョン指定子等を除去する。
5.  **結果の返却**: 抽出したライブラリ名のリストを`ModuleImport`オブジェクトのリストに変換して返却する。

#### 2.1.4. 擬似コード

```python
class DependencyFileExtractor(BaseExtractor):
    def __init__(self, project_root):
        self.project_root = project_root
        self.dependencies = set()

    def extract(self) -> RawExtractionResult:
        self._parse_requirements_txt()
        self._parse_pyproject_toml()
        # Return dict format compatible with current DataIntegrator
        return {
            "extractor": "dependency_file",
            "modules": [],
            "functions": [],
            "classes": [],
            "imports": [{"source_module": "project", "target_module": lib, "import_type": "EXTERNAL_LIBRARY", "is_external": True} for lib in self.dependencies],
            "function_calls": [],
            "inheritance": []
        }

    def _parse_requirements_txt(self):
        # Find and read requirements.txt
        # For each line:
        #   line = line.strip()
        #   if line and not line.startswith('#'):
        #       lib_name = re.split(r'[<>=~[]', line)[0].strip()
        #       self.dependencies.add(lib_name)

    def _parse_pyproject_toml(self):
        # Find and read pyproject.toml with tomllib
        # data = toml.load(file)
        # deps1 = data.get('project', {}).get('dependencies', [])
        # deps2 = data.get('tool', {}).get('poetry', {}).get('dependencies', {})
        # Extract library names from deps1 (list) and deps2 (dict keys)
        # Add to self.dependencies
```

### 2.2. ファイル横断的な関数呼び出し解析

この解析は、既存の`code2flow_extractor.py`を大幅に拡張して実装する。2段階のパスで解析を行う。

#### 2.2.1. 第1パス: プロジェクト全体の定義インデックス化

**目的**: プロジェクト内に存在するすべてのクラス、関数、メソッドの情報を収集し、名前解決可能なインデックスを構築する。

**担当クラス**: `pydepgraph.utils.definition_indexer.DefinitionIndexer` (新規作成)

**インデックスのデータ構造**:

```
# key: 完全修飾名 (e.g., 'my_app.services.user_service.create_user')
# value: 定義情報オブジェクト
{
  "my_app.services.user_service.create_user": {
    "file_path": "/path/to/my_app/services/user_service.py",
    "start_line": 50,
    "end_line": 75,
    "node_type": "function" # 'class', 'method'
  },
  ...
}
```

**処理フロー**:

1.  プロジェクトのソースディレクトリ配下の全`.py`ファイルを探索する。
2.  各ファイルをAST（`ast`モジュール）でパースする。
3.  ASTを木構造として走査 (`ast.walk`) し、`ast.FunctionDef`, `ast.AsyncFunctionDef`, `ast.ClassDef` ノードを探索する。
4.  各定義ノードについて、以下の情報を抽出する。
    -   **完全修飾名 (FQN)**: ファイルパスをモジュールパスに変換し、クラス名（もしあれば）と関数名を結合して生成する (e.g., `my_app.utils.helpers.format_string`)。
    -   ファイルパス、開始/終了行番号。
5.  抽出した情報をインデックス（辞書）に格納して返却する。

#### 2.2.2. 第2パス: 呼び出し関係の解析とグラフ構築

**目的**: 第1パスで作成したインデックスを利用して、関数/メソッド呼び出しを名前解決し、依存関係を特定する。

**担当クラス**: `pydepgraph.extractors.code2flow_extractor.Code2FlowExtractor` (拡張)

**処理フロー**:

1.  **初期化**: `DefinitionIndexer`を実行し、プロジェクトの定義インデックスを取得する。
2.  **ファイルごとの解析**: 各ソースファイルを再度ASTでパースする。
3.  **コンテキスト管理**: ファイルを走査する際に、現在のスコープ（モジュールFQN、クラス名）と、そのファイル内で有効なインポート（`import a.b`, `from x.y import z`, `import p.q as r`）を追跡する。
4.  **呼び出しノードの走査**: `ast.walk`で`ast.Call`ノードを探索する。
5.  **呼び出し先の名前解決**:
    -   `ast.Call`ノードの`func`属性から、呼び出されている関数の名前を取得する (e.g., `requests.get`, `self.my_method`, `User.find`)。
    -   ステップ3で追跡しているインポート情報と現在のスコープを基に、呼び出し先候補の完全修飾名（FQN）を複数生成する。
        -   例: `db.query()`という呼び出しがあった場合、`import database as db`なら`database.query`を候補とする。
    -   生成したFQN候補が、第1パスで作成した定義インデックスに存在するかを確認する。
6.  **依存関係の生成**:
    -   インデックスにFQNが存在した場合、呼び出し元（現在の関数/メソッドのFQN）から呼び出し先（解決できたFQN）への依存関係が成立する。
    -   `FunctionCall`オブジェクトを作成し、結果リストに追加する。

## 3. データベーススキーマの変更

-   Kùzuグラフデータベースの`ModuleImports`関係テーブルに、外部ライブラリ依存関係を格納する。
-   `Module`ノードに`is_external`プロパティを追加し、外部ライブラリノードを識別できるようにする。
-   既存の`import_type`フィールドに`EXTERNAL_LIBRARY`値を追加する。

## 4. 期待される効果

-   これまで捉えきれなかった外部ライブラリへの依存が明確になり、SBOM（ソフトウェア部品表）の生成や脆弱性管理が容易になる。
-   ファイルやモジュールをまたいだ実際の処理フローに近い、高精度の関数レベル依存関係グラフが得られる。これにより、影響範囲分析やリファクタリング計画の精度が劇的に向上する。