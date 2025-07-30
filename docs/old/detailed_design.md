# PyDepGraph 詳細設計書

## 📋 概要

本書は、TachとCode2Flowの出力サンプルを基に、PyDepGraphの詳細な実装設計を定義します。

## 📊 入力データ形式分析

### Tach出力形式（モジュール依存関係）

**ファイル**: `module_dependencies.json`

```json
{
  "module_path": [
    "imported_module1",
    "imported_module2"
  ]
}
```

**データ構造**:
- **形式**: JSONオブジェクト（key-value）
- **キー**: インポート元モジュールパス（文字列）
- **値**: インポート先モジュールパスの配列

**例**:
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

### Code2Flow出力形式（関数依存関係）

**ファイル**: `function_dependencies.json`, `prolog_mcp_functions.json`

```json
{
  "graph": {
    "directed": true,
    "nodes": {
      "node_id": {
        "uid": "node_id",
        "label": "line_number: function_name()",
        "name": "module::class.method_name"
      }
    },
    "edges": {
      "edge_id": {
        "uid": "edge_id", 
        "source": "source_node_id",
        "target": "target_node_id"
      }
    }
  }
}
```

**ノード属性**:
- `uid`: ノードの一意識別子
- `label`: 表示用ラベル（行番号 + 関数名）
- `name`: 完全修飾名（module::class.method形式）

**エッジ属性**:
- `uid`: エッジの一意識別子
- `source`: 呼び出し元ノードID
- `target`: 呼び出し先ノードID

## 🔧 データ変換設計

### 1. ExtractorBase実装

#### TachExtractor
```python
from typing import Dict, List, Any
import json
from pathlib import Path

class TachExtractor(ExtractorBase):
    def extract(self, project_path: str) -> ExtractionResult:
        """Tachコマンドを実行してモジュール依存関係を抽出"""
        
        # Tachコマンド実行
        result = subprocess.run(
            ["tach", "report", "dependencies", "--format", "json"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise PrologExecutionError(f"Tach execution failed: {result.stderr}")
        
        # JSON解析
        dependencies = json.loads(result.stdout)
        
        # PyDepGraph形式に変換
        modules = []
        relationships = []
        
        for source_module, imported_modules in dependencies.items():
            # モジュール情報の構築
            module_info = self._extract_module_info(source_module)
            modules.append(module_info)
            
            # 依存関係の構築
            for target_module in imported_modules:
                relationship = {
                    'relationship_type': 'ModuleImports',
                    'source_module': source_module,
                    'target_module': target_module,
                    'import_type': 'direct',  # Tachからは詳細不明のためdefault
                }
                relationships.append(relationship)
        
        return ExtractionResult(
            modules=modules,
            functions=[],  # Tachは関数レベルの情報なし
            classes=[],    # Tachは関数レベルの情報なし
            relationships=relationships,
            metadata={'extractor': 'tach', 'total_modules': len(modules)}
        )
    
    def _extract_module_info(self, module_path: str) -> Dict[str, Any]:
        """モジュールパスから基本情報を抽出"""
        path = Path(module_path)
        
        return {
            'name': path.stem,
            'file_path': module_path,
            'package': str(path.parent).replace('/', '.'),
            'is_external': not module_path.startswith('.'),  # 相対パス以外は外部
            'is_test': 'test' in module_path.lower(),
        }
```

#### Code2FlowExtractor
```python
class Code2FlowExtractor(ExtractorBase):
    def extract(self, project_path: str) -> ExtractionResult:
        """Code2Flowコマンドを実行して関数依存関係を抽出"""
        
        # Code2Flowコマンド実行
        result = subprocess.run(
            ["code2flow", project_path, "--language", "py", "--format", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise PrologExecutionError(f"Code2Flow execution failed: {result.stderr}")
        
        # JSON解析
        graph_data = json.loads(result.stdout)
        
        # PyDepGraph形式に変換
        functions = []
        classes = []
        relationships = []
        
        # ノード処理（関数・クラス情報）
        for node_id, node_data in graph_data['graph']['nodes'].items():
            parsed_function = self._parse_function_info(node_data)
            
            if parsed_function['is_method']:
                # クラスメソッドの場合はクラス情報も抽出
                class_info = self._extract_class_info(parsed_function)
                if class_info not in classes:
                    classes.append(class_info)
            
            functions.append(parsed_function)
        
        # エッジ処理（関数呼び出し関係）
        for edge_id, edge_data in graph_data['graph']['edges'].items():
            relationship = {
                'relationship_type': 'FunctionCalls',
                'source_function_id': edge_data['source'],
                'target_function_id': edge_data['target'],
                'call_type': 'direct',  # Code2Flowからは詳細不明のためdefault
            }
            relationships.append(relationship)
        
        return ExtractionResult(
            modules=[],  # Code2Flowからはモジュール情報の直接取得は困難
            functions=functions,
            classes=classes,
            relationships=relationships,
            metadata={'extractor': 'code2flow', 'total_functions': len(functions)}
        )
    
    def _parse_function_info(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Code2Flowノードから関数情報を解析"""
        name = node_data['name']
        label = node_data['label']
        
        # ラベルから行番号を抽出（"155: __init__()" 形式）
        line_match = re.match(r'(\d+):\s*(.+)', label)
        line_number = int(line_match.group(1)) if line_match else 0
        function_name = line_match.group(2) if line_match else label
        
        # nameから完全修飾名を解析（"module::class.method" 形式）
        parts = name.split('::')
        module_name = parts[0] if len(parts) > 1 else 'unknown'
        
        if len(parts) > 1:
            func_parts = parts[1].split('.')
            class_name = func_parts[0] if len(func_parts) > 1 else None
            method_name = func_parts[-1]
        else:
            class_name = None
            method_name = parts[0]
        
        return {
            'uid': node_data['uid'],
            'name': method_name,
            'qualified_name': name,
            'module_name': module_name,
            'class_name': class_name,
            'line_number': line_number,
            'is_method': class_name is not None,
            'is_async': 'async' in function_name.lower(),
            'is_private': method_name.startswith('_'),
        }
    
    def _extract_class_info(self, function_info: Dict[str, Any]) -> Dict[str, Any]:
        """関数情報からクラス情報を抽出"""
        if not function_info['class_name']:
            return None
        
        return {
            'name': function_info['class_name'],
            'qualified_name': f"{function_info['module_name']}::{function_info['class_name']}",
            'module_name': function_info['module_name'],
        }
```

### 2. DataNormalizer実装

```python
class DataNormalizer:
    def normalize_extraction_results(
        self, 
        results: List[ExtractionResult]
    ) -> ExtractionResult:
        """複数の抽出結果を統合・正規化"""
        
        all_modules = []
        all_functions = []
        all_classes = []
        all_relationships = []
        
        # 各抽出結果を統合
        for result in results:
            all_modules.extend(result.modules)
            all_functions.extend(result.functions)
            all_classes.extend(result.classes)
            all_relationships.extend(result.relationships)
        
        # 重複排除
        unique_modules = self._deduplicate_modules(all_modules)
        unique_functions = self._deduplicate_functions(all_functions)
        unique_classes = self._deduplicate_classes(all_classes)
        unique_relationships = self._deduplicate_relationships(all_relationships)
        
        # ID付与
        self._assign_ids(unique_modules, unique_functions, unique_classes)
        
        return ExtractionResult(
            modules=unique_modules,
            functions=unique_functions,
            classes=unique_classes,
            relationships=unique_relationships,
            metadata={'normalized': True}
        )
    
    def _deduplicate_modules(self, modules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """モジュールの重複排除（file_pathをキーとして使用）"""
        seen = set()
        unique_modules = []
        
        for module in modules:
            key = module['file_path']
            if key not in seen:
                seen.add(key)
                unique_modules.append(module)
        
        return unique_modules
    
    def _deduplicate_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """関数の重複排除（qualified_nameをキーとして使用）"""
        seen = set()
        unique_functions = []
        
        for function in functions:
            key = function['qualified_name']
            if key not in seen:
                seen.add(key)
                unique_functions.append(function)
        
        return unique_functions
    
    def _assign_ids(
        self, 
        modules: List[Dict[str, Any]], 
        functions: List[Dict[str, Any]], 
        classes: List[Dict[str, Any]]
    ) -> None:
        """統一されたIDを付与"""
        for i, module in enumerate(modules):
            module['id'] = f"module_{i:06d}"
        
        for i, function in enumerate(functions):
            function['id'] = f"function_{i:06d}"
        
        for i, class_obj in enumerate(classes):
            class_obj['id'] = f"class_{i:06d}"
```

## 🗄️ データベーススキーマ実装

### Kùzuスキーマ定義

```python
class GraphDatabase:
    def initialize_schema(self) -> None:
        """グラフデータベースのスキーマを初期化"""
        
        # ノードテーブル作成
        self._create_module_table()
        self._create_function_table()
        self._create_class_table()
        
        # エッジテーブル作成
        self._create_module_imports_table()
        self._create_function_calls_table()
        self._create_inheritance_table()
        self._create_contains_table()
    
    def _create_module_table(self) -> None:
        """Moduleノードテーブル作成"""
        query = """
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
        """
        self.connection.execute(query)
    
    def _create_function_table(self) -> None:
        """Functionノードテーブル作成"""
        query = """
        CREATE NODE TABLE Function (
            id SERIAL,
            name STRING,
            qualified_name STRING,
            module_name STRING,
            class_name STRING,
            line_number INT32,
            is_method BOOLEAN,
            is_async BOOLEAN,
            is_private BOOLEAN,
            PRIMARY KEY (id)
        );
        """
        self.connection.execute(query)
    
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
    
    def _create_function_calls_table(self) -> None:
        """FunctionCallsエッジテーブル作成"""
        query = """
        CREATE REL TABLE FunctionCalls (
            FROM Function TO Function,
            call_type STRING,
            line_number INT32,
            call_context STRING
        );
        """
        self.connection.execute(query)
```

### データ挿入処理

```python
def bulk_insert_extraction_result(self, result: ExtractionResult) -> None:
    """抽出結果をデータベースに一括挿入"""
    
    # ノード挿入
    self._insert_modules(result.modules)
    self._insert_functions(result.functions)
    self._insert_classes(result.classes)
    
    # エッジ挿入
    self._insert_relationships(result.relationships)

def _insert_modules(self, modules: List[Dict[str, Any]]) -> None:
    """モジュールを一括挿入"""
    if not modules:
        return
    
    values = []
    for module in modules:
        values.append({
            'name': module['name'],
            'file_path': module['file_path'],
            'package': module.get('package', ''),
            'is_external': module.get('is_external', False),
            'is_test': module.get('is_test', False),
            'lines_of_code': module.get('lines_of_code', 0),
            'complexity_score': module.get('complexity_score', 0.0),
        })
    
    # Kùzuバルクインサート
    for value in values:
        query = """
        CREATE (m:Module {
            name: $name,
            file_path: $file_path,
            package: $package,
            is_external: $is_external,
            is_test: $is_test,
            lines_of_code: $lines_of_code,
            complexity_score: $complexity_score
        })
        """
        self.connection.execute(query, value)
```

## 🔍 クエリサービス実装

### 基本検索クエリ

```python
class QueryService:
    def find_function_dependencies(
        self, 
        function_name: str, 
        direction: str = "outgoing"
    ) -> List[str]:
        """関数の依存関係検索"""
        
        if direction == "outgoing":
            # 呼び出し先を検索
            query = """
            MATCH (f1:Function {name: $function_name})-[c:FunctionCalls]->(f2:Function)
            RETURN f2.qualified_name as dependency
            ORDER BY f2.qualified_name
            """
        else:
            # 呼び出し元を検索
            query = """
            MATCH (f1:Function)-[c:FunctionCalls]->(f2:Function {name: $function_name})
            RETURN f1.qualified_name as dependency
            ORDER BY f1.qualified_name
            """
        
        result = self.database.execute_query(query, {'function_name': function_name})
        return [row['dependency'] for row in result]
    
    def find_module_dependencies(
        self, 
        module_path: str, 
        depth: int = 1
    ) -> List[Dict[str, Any]]:
        """モジュールの依存関係検索（指定深度まで）"""
        
        if depth == 1:
            query = """
            MATCH (m1:Module {file_path: $module_path})-[i:ModuleImports]->(m2:Module)
            RETURN m2.file_path as dependency, i.import_type as import_type
            ORDER BY m2.file_path
            """
        else:
            # 再帰的検索（深度指定）
            query = f"""
            MATCH path = (m1:Module {{file_path: $module_path}})-[i:ModuleImports*1..{depth}]->(m2:Module)
            RETURN m2.file_path as dependency, length(path) as depth
            ORDER BY depth, m2.file_path
            """
        
        result = self.database.execute_query(query, {'module_path': module_path})
        return result
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """循環依存検出"""
        query = """
        MATCH path = (m:Module)-[i:ModuleImports*2..10]->(m)
        WHERE m.is_external = false
        RETURN [n in nodes(path) | n.file_path] as cycle
        ORDER BY length(path)
        """
        
        result = self.database.execute_query(query)
        return [row['cycle'] for row in result]
```

## 🎯 CLI実装

### コマンド構造

```python
import click
from pathlib import Path
import json

@click.group()
def cli():
    """PyDepGraph - Python依存関係分析ツール"""
    pass

@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Choice(['json', 'yaml']), help='出力形式')
@click.option('--include-external', is_flag=True, help='外部依存関係も含める')
def analyze(project_path: str, output: str, include_external: bool):
    """プロジェクトを分析してグラフデータベースを構築"""
    
    project_path = Path(project_path)
    
    # 分析実行
    service = AnalyzerService()
    service.analyze_project(project_path)
    
    click.echo(f"✅ プロジェクト '{project_path}' の分析が完了しました")
    
    if output:
        # 結果出力
        query_service = QueryService()
        results = query_service.export_analysis_results(include_external)
        
        output_file = project_path / f"analysis_results.{output}"
        
        if output == 'json':
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        elif output == 'yaml':
            import yaml
            with open(output_file, 'w') as f:
                yaml.dump(results, f, default_flow_style=False, allow_unicode=True)
        
        click.echo(f"📄 分析結果を {output_file} に出力しました")

@cli.command()
@click.argument('function_name')
@click.option('--direction', type=click.Choice(['outgoing', 'incoming']), 
              default='outgoing', help='検索方向')
@click.option('--depth', type=int, default=1, help='検索深度')
def deps(function_name: str, direction: str, depth: int):
    """関数の依存関係を検索"""
    
    query_service = QueryService()
    dependencies = query_service.find_function_dependencies(
        function_name, direction, depth
    )
    
    if dependencies:
        click.echo(f"📋 {function_name} の{direction}依存関係:")
        for dep in dependencies:
            click.echo(f"  → {dep}")
    else:
        click.echo(f"❌ {function_name} の依存関係が見つかりませんでした")

@cli.command()
@click.argument('source')
@click.argument('target')
def path(source: str, target: str):
    """2つの要素間の依存パスを検索"""
    
    query_service = QueryService()
    dependency_path = query_service.find_shortest_path(source, target)
    
    if dependency_path:
        click.echo(f"🛤️  {source} → {target} への最短パス:")
        for i, step in enumerate(dependency_path.path):
            if i < len(dependency_path.path) - 1:
                click.echo(f"  {step} →")
            else:
                click.echo(f"  {step}")
        click.echo(f"深度: {dependency_path.depth}")
    else:
        click.echo(f"❌ {source} から {target} への依存パスが見つかりませんでした")

@cli.command()
def cycles():
    """循環依存を検出"""
    
    query_service = QueryService()
    circular_deps = query_service.find_circular_dependencies()
    
    if circular_deps:
        click.echo("🔄 検出された循環依存:")
        for i, cycle in enumerate(circular_deps, 1):
            click.echo(f"\n{i}. {' → '.join(cycle)}")
    else:
        click.echo("✅ 循環依存は検出されませんでした")

if __name__ == '__main__':
    cli()
```

## ⚙️ エラー処理とロバスト性

### エラーハンドリング戦略

```python
class AnalyzerService:
    def analyze_project(self, project_path: Path) -> None:
        """プロジェクト分析（エラー処理含む）"""
        failed_extractors = []
        successful_results = []
        
        for extractor in self.extractors:
            try:
                result = extractor.extract(str(project_path))
                successful_results.append(result)
                logger.info(f"✅ {extractor.__class__.__name__} の分析が完了")
                
            except Exception as e:
                failed_extractors.append((extractor.__class__.__name__, str(e)))
                logger.warning(f"⚠️  {extractor.__class__.__name__} の分析に失敗: {e}")
        
        if not successful_results:
            raise PrologExecutionError("すべての抽出器が失敗しました")
        
        # 成功した結果のみを統合
        normalized_result = self.normalizer.normalize_extraction_results(successful_results)
        
        # データベースに挿入
        try:
            self.database.bulk_insert_extraction_result(normalized_result)
            logger.info("✅ データベースへの挿入が完了")
            
        except Exception as e:
            logger.error(f"❌ データベース挿入に失敗: {e}")
            raise
        
        # 失敗した抽出器がある場合は警告を出力
        if failed_extractors:
            logger.warning("以下の抽出器が失敗しました:")
            for name, error in failed_extractors:
                logger.warning(f"  - {name}: {error}")
```

この詳細設計書は、TachとCode2Flowの実際の出力形式に基づいて、具体的な実装方法を定義しています。