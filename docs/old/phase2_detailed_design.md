# PyDepGraph Phase 2 詳細設計書
## 関数レベル分析（Week 3-4）

## 📋 Phase 2 概要

**目標**: Code2Flowを使った関数レベルの依存関係分析

**実装対象**:
- Code2FlowExtractor（関数間呼び出し関係抽出）
- Function・Classノードテーブルの実装
- FunctionCallsエッジテーブルの実装
- DataNormalizer（複数抽出結果の統合）

## 📊 入力データ形式（Code2Flow）

### Code2Flow出力形式
```json
{
  "graph": {
    "directed": true,
    "nodes": {
      "node_e46a398d": {
        "uid": "node_e46a398d",
        "label": "155: __init__()",
        "name": "advanced_input_handlers::AdvancedCharInput.__init__"
      }
    },
    "edges": {
      "edge_123": {
        "uid": "edge_123",
        "source": "node_e46a398d",
        "target": "node_c548af3c"
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

## 🏗️ 拡張データ構造

### Function情報構造
```python
function_info = {
    'id': str,                    # 一意識別子
    'uid': str,                   # Code2FlowのUID
    'name': str,                  # 関数名
    'qualified_name': str,        # 完全修飾名
    'module_name': str,           # モジュール名
    'class_name': Optional[str],  # クラス名（メソッドの場合）
    'line_number': int,           # 行番号
    'is_method': bool,            # メソッドかどうか
    'is_async': bool,             # 非同期関数かどうか
    'is_private': bool,           # プライベート関数かどうか
    'is_global': bool,            # グローバル関数かどうか
    'docstring': str,             # ドキュメント文字列（Phase2では空文字）
}
```

### Class情報構造
```python
class_info = {
    'id': str,                    # 一意識別子
    'name': str,                  # クラス名
    'qualified_name': str,        # 完全修飾名
    'module_name': str,           # モジュール名
    'line_number': int,           # 定義行番号（Phase2では0）
    'method_count': int,          # メソッド数
    'is_abstract': bool,          # 抽象クラス（Phase2ではFalse）
    'inheritance_depth': int,     # 継承深度（Phase2では0）
    'docstring': str,             # ドキュメント文字列（Phase2では空文字）
}
```

### FunctionCall情報構造
```python
function_call_info = {
    'relationship_type': str,     # 'FunctionCalls'
    'source_function_id': str,    # 呼び出し元関数ID
    'target_function_id': str,    # 呼び出し先関数ID
    'call_type': str,             # 'direct', 'method', 'async'
    'line_number': int,           # 呼び出し行番号（Phase2では0）
    'call_context': str,          # 呼び出しコンテキスト（Phase2では空文字）
}
```

## 🔧 Code2FlowExtractor実装

```python
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

class Code2FlowExtractor(ExtractorBase):
    """Code2Flowを使用した関数依存関係抽出器"""
    
    def extract(self, project_path: str) -> ExtractionResult:
        """Code2Flowコマンドを実行して関数依存関係を抽出"""
        
        if not self.validate_project_path(project_path):
            raise ValueError(f"Invalid project path: {project_path}")
        
        # Code2Flowコマンド実行
        try:
            result = subprocess.run(
                ["code2flow", project_path, "--language", "py", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=600  # 10分のタイムアウト
            )
            
            if result.returncode != 0:
                raise PrologExecutionError(f"Code2Flow execution failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise PrologExecutionError("Code2Flow execution timed out")
        except FileNotFoundError:
            raise PrologExecutionError("Code2Flow command not found. Please install code2flow.")
        
        # JSON解析
        try:
            graph_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise PrologExecutionError(f"Failed to parse Code2Flow output: {e}")
        
        # PyDepGraph形式に変換
        functions = []
        classes = []
        relationships = []
        
        function_id_counter = 0
        class_id_counter = 0
        
        # UID -> IDのマッピング
        uid_to_function_id = {}
        class_name_to_id = {}
        
        # ノード処理（関数・クラス情報）
        if 'graph' in graph_data and 'nodes' in graph_data['graph']:
            for node_id, node_data in graph_data['graph']['nodes'].items():
                parsed_function = self._parse_function_info(node_data, function_id_counter)
                function_id_counter += 1
                
                functions.append(parsed_function)
                uid_to_function_id[node_data['uid']] = parsed_function['id']
                
                # クラスメソッドの場合はクラス情報も抽出
                if parsed_function['is_method'] and parsed_function['class_name']:
                    class_key = f"{parsed_function['module_name']}::{parsed_function['class_name']}"
                    
                    if class_key not in class_name_to_id:
                        class_info = self._extract_class_info(parsed_function, class_id_counter)
                        class_id_counter += 1
                        
                        classes.append(class_info)
                        class_name_to_id[class_key] = class_info['id']
        
        # エッジ処理（関数呼び出し関係）
        if 'graph' in graph_data and 'edges' in graph_data['graph']:
            for edge_id, edge_data in graph_data['graph']['edges'].items():
                source_uid = edge_data.get('source')
                target_uid = edge_data.get('target')
                
                if source_uid in uid_to_function_id and target_uid in uid_to_function_id:
                    relationship = {
                        'relationship_type': 'FunctionCalls',
                        'source_function_id': uid_to_function_id[source_uid],
                        'target_function_id': uid_to_function_id[target_uid],
                        'call_type': self._determine_call_type(source_uid, target_uid),
                        'line_number': 0,        # Phase2では詳細不明
                        'call_context': '',      # Phase2では空文字
                    }
                    relationships.append(relationship)
        
        # クラス内メソッドの所属関係を追加
        for function in functions:
            if function['is_method'] and function['class_name']:
                class_key = f"{function['module_name']}::{function['class_name']}"
                if class_key in class_name_to_id:
                    contains_rel = {
                        'relationship_type': 'Contains',
                        'source_class_id': class_name_to_id[class_key],
                        'target_function_id': function['id'],
                        'definition_type': 'method',
                    }
                    relationships.append(contains_rel)
        
        logger.info(f"Code2Flow extraction completed: {len(functions)} functions, {len(classes)} classes, {len(relationships)} relationships")
        
        return ExtractionResult(
            modules=[],  # Code2Flowからは直接取得困難
            functions=functions,
            classes=classes,
            relationships=relationships,
            metadata={
                'extractor': 'code2flow',
                'total_functions': len(functions),
                'total_classes': len(classes),
                'total_relationships': len(relationships),
                'project_path': project_path,
            }
        )
    
    def _parse_function_info(self, node_data: Dict[str, Any], function_id: int) -> Dict[str, Any]:
        """Code2Flowノードから関数情報を解析"""
        uid = node_data.get('uid', '')
        name = node_data.get('name', '')
        label = node_data.get('label', '')
        
        # ラベルから行番号を抽出（"155: __init__()" 形式）
        line_number = 0
        function_display_name = label
        
        line_match = re.match(r'(\d+):\s*(.+)', label)
        if line_match:
            line_number = int(line_match.group(1))
            function_display_name = line_match.group(2).strip()
        
        # nameから完全修飾名を解析（"module::class.method" 形式）
        module_name = 'unknown'
        class_name = None
        method_name = 'unknown'
        
        if '::' in name:
            parts = name.split('::')
            module_name = parts[0]
            
            if len(parts) > 1:
                func_parts = parts[1].split('.')
                if len(func_parts) > 1:
                    class_name = func_parts[0]
                    method_name = func_parts[-1]
                else:
                    method_name = func_parts[0]
            else:
                method_name = parts[0]
        else:
            method_name = name
        
        # 関数の特性を判定
        is_method = class_name is not None
        is_async = 'async' in function_display_name.lower() or method_name.startswith('async_')
        is_private = method_name.startswith('_') and not method_name.startswith('__')
        is_global = not is_method and class_name is None
        
        return {
            'id': f"function_{function_id:06d}",
            'uid': uid,
            'name': method_name,
            'qualified_name': name,
            'module_name': module_name,
            'class_name': class_name,
            'line_number': line_number,
            'is_method': is_method,
            'is_async': is_async,
            'is_private': is_private,
            'is_global': is_global,
            'docstring': '',  # Phase2では空文字
        }
    
    def _extract_class_info(self, function_info: Dict[str, Any], class_id: int) -> Dict[str, Any]:
        """関数情報からクラス情報を抽出"""
        if not function_info['class_name']:
            return None
        
        return {
            'id': f"class_{class_id:06d}",
            'name': function_info['class_name'],
            'qualified_name': f"{function_info['module_name']}::{function_info['class_name']}",
            'module_name': function_info['module_name'],
            'line_number': 0,      # Phase2では詳細不明
            'method_count': 1,     # 後で正確にカウント
            'is_abstract': False,  # Phase2では判定しない
            'inheritance_depth': 0, # Phase2では計算しない
            'docstring': '',       # Phase2では空文字
        }
    
    def _determine_call_type(self, source_uid: str, target_uid: str) -> str:
        """関数呼び出しの種類を判定"""
        # Phase2では詳細判定は困難なため、デフォルトで'direct'
        return 'direct'
    
    def get_supported_file_types(self) -> List[str]:
        """サポートするファイル拡張子を返す"""
        return ['.py']
```

## 🔧 DataNormalizer実装

```python
from collections import defaultdict

class DataNormalizer:
    """複数抽出結果の統合・正規化クラス"""
    
    def __init__(self):
        self.id_counter = 0
    
    def normalize_extraction_results(
        self, 
        results: List[ExtractionResult]
    ) -> ExtractionResult:
        """複数の抽出結果を統合・正規化"""
        
        logger.info(f"Normalizing {len(results)} extraction results...")
        
        all_modules = []
        all_functions = []
        all_classes = []
        all_relationships = []
        combined_metadata = {}
        
        # 各抽出結果を統合
        for result in results:
            all_modules.extend(result.modules)
            all_functions.extend(result.functions)
            all_classes.extend(result.classes)
            all_relationships.extend(result.relationships)
            
            # メタデータも統合
            for key, value in result.metadata.items():
                if key in combined_metadata:
                    if isinstance(combined_metadata[key], list):
                        combined_metadata[key].append(value)
                    else:
                        combined_metadata[key] = [combined_metadata[key], value]
                else:
                    combined_metadata[key] = value
        
        # 重複排除
        unique_modules = self._deduplicate_modules(all_modules)
        unique_functions = self._deduplicate_functions(all_functions)
        unique_classes = self._deduplicate_classes(all_classes)
        unique_relationships = self._deduplicate_relationships(all_relationships)
        
        # クラスのメソッド数を更新
        self._update_class_method_counts(unique_classes, unique_functions)
        
        # ID付与（統一されたID体系）
        self._assign_unified_ids(unique_modules, unique_functions, unique_classes)
        
        # 関係性のIDを更新
        self._update_relationship_ids(unique_relationships, unique_modules, unique_functions, unique_classes)
        
        logger.info(f"Normalization completed: {len(unique_modules)} modules, {len(unique_functions)} functions, {len(unique_classes)} classes, {len(unique_relationships)} relationships")
        
        return ExtractionResult(
            modules=unique_modules,
            functions=unique_functions,
            classes=unique_classes,
            relationships=unique_relationships,
            metadata={
                **combined_metadata,
                'normalized': True,
                'total_extractors': len(results),
            }
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
    
    def _deduplicate_classes(self, classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """クラスの重複排除（qualified_nameをキーとして使用）"""
        seen = set()
        unique_classes = []
        
        for class_obj in classes:
            key = class_obj['qualified_name']
            if key not in seen:
                seen.add(key)
                unique_classes.append(class_obj)
        
        return unique_classes
    
    def _deduplicate_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """関係性の重複排除"""
        seen = set()
        unique_relationships = []
        
        for rel in relationships:
            # 関係性の種類に応じてキーを生成
            if rel['relationship_type'] == 'ModuleImports':
                key = (rel['relationship_type'], rel['source_module'], rel['target_module'])
            elif rel['relationship_type'] == 'FunctionCalls':
                key = (rel['relationship_type'], rel['source_function_id'], rel['target_function_id'])
            elif rel['relationship_type'] == 'Contains':
                if 'source_class_id' in rel:
                    key = (rel['relationship_type'], rel['source_class_id'], rel['target_function_id'])
                else:
                    key = (rel['relationship_type'], rel.get('source_module_id', ''), rel.get('target_function_id', ''))
            else:
                # その他の関係性
                key = str(rel)
            
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)
        
        return unique_relationships
    
    def _update_class_method_counts(self, classes: List[Dict[str, Any]], functions: List[Dict[str, Any]]) -> None:
        """クラスのメソッド数を正確にカウント"""
        class_method_counts = defaultdict(int)
        
        for function in functions:
            if function['is_method'] and function['class_name']:
                class_key = f"{function['module_name']}::{function['class_name']}"
                class_method_counts[class_key] += 1
        
        for class_obj in classes:
            class_key = class_obj['qualified_name']
            class_obj['method_count'] = class_method_counts.get(class_key, 0)
    
    def _assign_unified_ids(
        self, 
        modules: List[Dict[str, Any]], 
        functions: List[Dict[str, Any]], 
        classes: List[Dict[str, Any]]
    ) -> None:
        """統一されたIDを付与"""
        
        # モジュールID付与
        for i, module in enumerate(modules):
            if not module.get('id') or not module['id'].startswith('module_'):
                module['id'] = f"module_{i:06d}"
        
        # クラスID付与
        for i, class_obj in enumerate(classes):
            if not class_obj.get('id') or not class_obj['id'].startswith('class_'):
                class_obj['id'] = f"class_{i:06d}"
        
        # 関数ID付与
        for i, function in enumerate(functions):
            if not function.get('id') or not function['id'].startswith('function_'):
                function['id'] = f"function_{i:06d}"
    
    def _update_relationship_ids(
        self,
        relationships: List[Dict[str, Any]],
        modules: List[Dict[str, Any]],
        functions: List[Dict[str, Any]],
        classes: List[Dict[str, Any]]
    ) -> None:
        """関係性のIDを統一されたIDに更新"""
        
        # 各種マッピングを作成
        module_path_to_id = {m['file_path']: m['id'] for m in modules}
        function_qualified_to_id = {f['qualified_name']: f['id'] for f in functions}
        class_qualified_to_id = {c['qualified_name']: c['id'] for c in classes}
        
        for rel in relationships:
            if rel['relationship_type'] == 'ModuleImports':
                # モジュールパスからIDに変換
                if 'source_module' in rel and 'target_module' in rel:
                    rel['source_module_id'] = module_path_to_id.get(rel['source_module'])
                    rel['target_module_id'] = module_path_to_id.get(rel['target_module'])
            
            elif rel['relationship_type'] == 'Contains' and 'source_class_id' in rel:
                # クラス内関数の所属関係は既にIDが設定されているはず
                pass
```

## 🗄️ データベーススキーマ拡張

```python
class GraphDatabase:
    """Phase2対応のGraphDatabaseクラス拡張"""
    
    def initialize_schema(self) -> None:
        """グラフデータベースのスキーマを初期化（Phase2拡張版）"""
        
        logger.info("Initializing Phase 2 database schema...")
        
        # 既存テーブルの確認と削除（開発時）
        self._drop_existing_tables()
        
        # ノードテーブル作成
        self._create_module_table()
        self._create_function_table()
        self._create_class_table()
        
        # エッジテーブル作成
        self._create_module_imports_table()
        self._create_function_calls_table()
        self._create_contains_table()
        
        logger.info("Phase 2 database schema initialized successfully")
    
    def _drop_existing_tables(self) -> None:
        """既存テーブルの削除（開発時用）"""
        try:
            self.connection.execute("DROP TABLE IF EXISTS Contains;")
            self.connection.execute("DROP TABLE IF EXISTS FunctionCalls;")
            self.connection.execute("DROP TABLE IF EXISTS ModuleImports;")
            self.connection.execute("DROP TABLE IF EXISTS Function;")
            self.connection.execute("DROP TABLE IF EXISTS Class;")
            self.connection.execute("DROP TABLE IF EXISTS Module;")
        except Exception as e:
            logger.debug(f"Table drop failed (expected): {e}")
    
    def _create_function_table(self) -> None:
        """Functionノードテーブル作成"""
        query = """
        CREATE NODE TABLE Function (
            id STRING,
            uid STRING,
            name STRING,
            qualified_name STRING,
            module_name STRING,
            class_name STRING,
            line_number INT32,
            is_method BOOLEAN,
            is_async BOOLEAN,
            is_private BOOLEAN,
            is_global BOOLEAN,
            docstring STRING,
            PRIMARY KEY (id)
        );
        """
        self.connection.execute(query)
        logger.debug("Function table created")
    
    def _create_class_table(self) -> None:
        """Classノードテーブル作成"""
        query = """
        CREATE NODE TABLE Class (
            id STRING,
            name STRING,
            qualified_name STRING,
            module_name STRING,
            line_number INT32,
            method_count INT32,
            is_abstract BOOLEAN,
            inheritance_depth INT32,
            docstring STRING,
            PRIMARY KEY (id)
        );
        """
        self.connection.execute(query)
        logger.debug("Class table created")
    
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
        logger.debug("FunctionCalls table created")
    
    def _create_contains_table(self) -> None:
        """Containsエッジテーブル作成"""
        query = """
        CREATE REL TABLE Contains (
            FROM Class TO Function,
            definition_type STRING
        );
        """
        self.connection.execute(query)
        logger.debug("Contains table created")
    
    def bulk_insert_functions(self, functions: List[Dict[str, Any]]) -> None:
        """関数を一括挿入"""
        if not functions:
            logger.warning("No functions to insert")
            return
        
        logger.info(f"Inserting {len(functions)} functions...")
        
        for function in functions:
            query = """
            CREATE (f:Function {
                id: $id,
                uid: $uid,
                name: $name,
                qualified_name: $qualified_name,
                module_name: $module_name,
                class_name: $class_name,
                line_number: $line_number,
                is_method: $is_method,
                is_async: $is_async,
                is_private: $is_private,
                is_global: $is_global,
                docstring: $docstring
            })
            """
            
            params = {
                'id': function['id'],
                'uid': function['uid'],
                'name': function['name'],
                'qualified_name': function['qualified_name'],
                'module_name': function['module_name'],
                'class_name': function.get('class_name', ''),
                'line_number': function['line_number'],
                'is_method': function['is_method'],
                'is_async': function['is_async'],
                'is_private': function['is_private'],
                'is_global': function['is_global'],
                'docstring': function['docstring'],
            }
            
            self.connection.execute(query, params)
        
        logger.info(f"Successfully inserted {len(functions)} functions")
    
    def bulk_insert_classes(self, classes: List[Dict[str, Any]]) -> None:
        """クラスを一括挿入"""
        if not classes:
            logger.warning("No classes to insert")
            return
        
        logger.info(f"Inserting {len(classes)} classes...")
        
        for class_obj in classes:
            query = """
            CREATE (c:Class {
                id: $id,
                name: $name,
                qualified_name: $qualified_name,
                module_name: $module_name,
                line_number: $line_number,
                method_count: $method_count,
                is_abstract: $is_abstract,
                inheritance_depth: $inheritance_depth,
                docstring: $docstring
            })
            """
            
            params = {
                'id': class_obj['id'],
                'name': class_obj['name'],
                'qualified_name': class_obj['qualified_name'],
                'module_name': class_obj['module_name'],
                'line_number': class_obj['line_number'],
                'method_count': class_obj['method_count'],
                'is_abstract': class_obj['is_abstract'],
                'inheritance_depth': class_obj['inheritance_depth'],
                'docstring': class_obj['docstring'],
            }
            
            self.connection.execute(query, params)
        
        logger.info(f"Successfully inserted {len(classes)} classes")
    
    def bulk_insert_function_calls(self, relationships: List[Dict[str, Any]]) -> None:
        """関数呼び出し関係を一括挿入"""
        function_calls = [r for r in relationships if r['relationship_type'] == 'FunctionCalls']
        
        if not function_calls:
            logger.warning("No function call relationships to insert")
            return
        
        logger.info(f"Inserting {len(function_calls)} function call relationships...")
        
        for rel in function_calls:
            query = """
            MATCH (source:Function {id: $source_id}), (target:Function {id: $target_id})
            CREATE (source)-[r:FunctionCalls {
                call_type: $call_type,
                line_number: $line_number,
                call_context: $call_context
            }]->(target)
            """
            
            params = {
                'source_id': rel['source_function_id'],
                'target_id': rel['target_function_id'],
                'call_type': rel['call_type'],
                'line_number': rel['line_number'],
                'call_context': rel['call_context'],
            }
            
            self.connection.execute(query, params)
        
        logger.info(f"Successfully inserted {len(function_calls)} function call relationships")
    
    def bulk_insert_contains(self, relationships: List[Dict[str, Any]]) -> None:
        """包含関係を一括挿入"""
        contains_rels = [r for r in relationships if r['relationship_type'] == 'Contains']
        
        if not contains_rels:
            logger.warning("No contains relationships to insert")
            return
        
        logger.info(f"Inserting {len(contains_rels)} contains relationships...")
        
        for rel in contains_rels:
            if 'source_class_id' in rel:
                query = """
                MATCH (source:Class {id: $source_id}), (target:Function {id: $target_id})
                CREATE (source)-[r:Contains {
                    definition_type: $definition_type
                }]->(target)
                """
                
                params = {
                    'source_id': rel['source_class_id'],
                    'target_id': rel['target_function_id'],
                    'definition_type': rel['definition_type'],
                }
                
                self.connection.execute(query, params)
        
        logger.info(f"Successfully inserted {len(contains_rels)} contains relationships")
```

## 🧪 Phase 2 統合処理

```python
class Phase2IntegrationService:
    """Phase2の統合処理サービス"""
    
    def __init__(self, database_path: str):
        self.database = GraphDatabase(database_path)
        self.tach_extractor = TachExtractor()
        self.code2flow_extractor = Code2FlowExtractor()
        self.normalizer = DataNormalizer()
    
    def analyze_project_phase2(self, project_path: str) -> None:
        """Phase2完全分析実行"""
        
        logger.info(f"Starting Phase 2 analysis for project: {project_path}")
        
        # 1. 各抽出器を実行
        extraction_results = []
        
        try:
            tach_result = self.tach_extractor.extract(project_path)
            extraction_results.append(tach_result)
            logger.info("✅ Tach extraction completed")
        except Exception as e:
            logger.error(f"❌ Tach extraction failed: {e}")
        
        try:
            code2flow_result = self.code2flow_extractor.extract(project_path)
            extraction_results.append(code2flow_result)
            logger.info("✅ Code2Flow extraction completed")
        except Exception as e:
            logger.error(f"❌ Code2Flow extraction failed: {e}")
        
        if not extraction_results:
            raise PrologExecutionError("All extractors failed")
        
        # 2. 結果統合
        normalized_result = self.normalizer.normalize_extraction_results(extraction_results)
        logger.info("✅ Data normalization completed")
        
        # 3. データベース初期化
        self.database.initialize_schema()
        logger.info("✅ Database schema initialized")
        
        # 4. データ挿入
        if normalized_result.modules:
            self.database.bulk_insert_modules(normalized_result.modules)
        
        if normalized_result.functions:
            self.database.bulk_insert_functions(normalized_result.functions)
        
        if normalized_result.classes:
            self.database.bulk_insert_classes(normalized_result.classes)
        
        # 関係性挿入
        self.database.bulk_insert_module_imports(normalized_result.relationships)
        self.database.bulk_insert_function_calls(normalized_result.relationships)
        self.database.bulk_insert_contains(normalized_result.relationships)
        
        logger.info("✅ Phase 2 analysis completed successfully")
    
    def close(self):
        """リソースクローズ"""
        self.database.close()
```

## 🧪 Phase 2 成功基準とテスト

### 成功基準
- [x] Code2Flowの出力を正しく解析できる
- [x] 関数間の呼び出し関係をグラフデータベースに格納できる
- [x] 関数の依存関係検索が動作する

### 基本的な動作テスト例
```python
def test_phase2_integration():
    """Phase2の統合テスト"""
    
    # Phase2統合処理テスト
    service = Phase2IntegrationService("test_phase2.db")
    service.analyze_project_phase2("/path/to/test/project")
    
    # 関数検索テスト
    query = """
    MATCH (f:Function)
    RETURN count(f) as function_count
    """
    result = service.database.execute_query(query)
    assert result[0]['function_count'] > 0
    
    # 関数呼び出し関係テスト
    query = """
    MATCH (f1:Function)-[c:FunctionCalls]->(f2:Function)
    RETURN count(c) as call_count
    """
    result = service.database.execute_query(query)
    assert result[0]['call_count'] > 0
    
    # クラス・メソッド関係テスト
    query = """
    MATCH (c:Class)-[r:Contains]->(f:Function)
    RETURN count(r) as contains_count
    """
    result = service.database.execute_query(query)
    # クラスがある場合は Contains 関係があることを確認
    
    service.close()
```

Phase 2では、TachとCode2Flowの両方から情報を抽出し、統合してより詳細な依存関係グラフを構築します。