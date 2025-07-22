# pydepgraph/data_integrator.py

from typing import List, Dict, Any, Set
import logging
from .extractors.base import ExtractionResult

logger = logging.getLogger(__name__)


class DataIntegrator:
    """複数のExtractorの結果を統合するクラス"""

    def __init__(self):
        self.module_id_map = {}
        self.function_id_map = {}
        self.class_id_map = {}

    def integrate(self, results: List[ExtractionResult]) -> ExtractionResult:
        """複数の抽出結果を統合"""
        logger.info(f"Integrating {len(results)} extraction results")

        integrated_modules = []
        integrated_functions = []
        integrated_classes = []
        integrated_relationships = []
        integrated_metadata = {}

        # 各結果を順番に統合
        for result in results:
            self._merge_modules(result.modules, integrated_modules)
            self._merge_functions(result.functions, integrated_functions)
            self._merge_classes(result.classes, integrated_classes)
            self._merge_relationships(result.relationships, integrated_relationships)
            # メタデータをマージ（extractorキーは配列にして保持）
            if 'extractor' in result.metadata:
                if 'extractors' not in integrated_metadata:
                    integrated_metadata['extractors'] = []
                integrated_metadata['extractors'].append(result.metadata['extractor'])
            
            # その他のメタデータをマージ
            for key, value in result.metadata.items():
                if key != 'extractor':
                    integrated_metadata[key] = value

        # 関係性のIDを解決
        self._resolve_relationship_ids(integrated_relationships)

        # 統計情報を追加
        integrated_metadata.update({
            'integrated': True,
            'total_modules': len(integrated_modules),
            'total_functions': len(integrated_functions),
            'total_classes': len(integrated_classes),
            'total_relationships': len(integrated_relationships),
        })

        logger.info(f"Integration completed: {len(integrated_modules)} modules, "
                   f"{len(integrated_functions)} functions, {len(integrated_classes)} classes, "
                   f"{len(integrated_relationships)} relationships")

        return ExtractionResult(
            modules=integrated_modules,
            functions=integrated_functions,
            classes=integrated_classes,
            relationships=integrated_relationships,
            metadata=integrated_metadata
        )

    def _merge_modules(self, new_modules: List[Dict[str, Any]], integrated_modules: List[Dict[str, Any]]) -> None:
        """モジュールのマージ"""
        existing_paths = {m['file_path'] for m in integrated_modules}
        
        for module in new_modules:
            if module['file_path'] not in existing_paths:
                integrated_modules.append(module)
                self.module_id_map[module['file_path']] = module['id']
            else:
                # 既存モジュールの情報を更新（より詳細な情報がある場合）
                existing_module = next(m for m in integrated_modules if m['file_path'] == module['file_path'])
                self._merge_module_info(existing_module, module)

    def _merge_functions(self, new_functions: List[Dict[str, Any]], integrated_functions: List[Dict[str, Any]]) -> None:
        """関数のマージ"""
        existing_qualified_names = {f['qualified_name'] for f in integrated_functions}
        
        for function in new_functions:
            if function['qualified_name'] not in existing_qualified_names:
                integrated_functions.append(function)
                self.function_id_map[function['qualified_name']] = function['id']
            else:
                # 既存関数の情報を更新
                existing_function = next(f for f in integrated_functions if f['qualified_name'] == function['qualified_name'])
                self._merge_function_info(existing_function, function)

    def _merge_classes(self, new_classes: List[Dict[str, Any]], integrated_classes: List[Dict[str, Any]]) -> None:
        """クラスのマージ"""
        existing_qualified_names = {c['qualified_name'] for c in integrated_classes}
        
        for class_data in new_classes:
            if class_data['qualified_name'] not in existing_qualified_names:
                integrated_classes.append(class_data)
                self.class_id_map[class_data['qualified_name']] = class_data['id']
            else:
                # 既存クラスの情報を更新
                existing_class = next(c for c in integrated_classes if c['qualified_name'] == class_data['qualified_name'])
                self._merge_class_info(existing_class, class_data)

    def _merge_relationships(self, new_relationships: List[Dict[str, Any]], integrated_relationships: List[Dict[str, Any]]) -> None:
        """関係性のマージ"""
        # 重複する関係性をチェック
        existing_relationships = set()
        for rel in integrated_relationships:
            key = self._get_relationship_key(rel)
            existing_relationships.add(key)

        for relationship in new_relationships:
            key = self._get_relationship_key(relationship)
            if key not in existing_relationships:
                integrated_relationships.append(relationship)
                existing_relationships.add(key)

    def _merge_module_info(self, existing: Dict[str, Any], new: Dict[str, Any]) -> None:
        """既存モジュール情報の更新"""
        # より詳細な情報がある場合は更新
        if new.get('lines_of_code', 0) > existing.get('lines_of_code', 0):
            existing['lines_of_code'] = new['lines_of_code']
        
        if new.get('complexity_score', 0.0) > existing.get('complexity_score', 0.0):
            existing['complexity_score'] = new['complexity_score']

    def _merge_function_info(self, existing: Dict[str, Any], new: Dict[str, Any]) -> None:
        """既存関数情報の更新"""
        # より詳細な情報がある場合は更新
        if new.get('cyclomatic_complexity', 0) > 0 and existing.get('cyclomatic_complexity', 0) == 0:
            existing['cyclomatic_complexity'] = new['cyclomatic_complexity']

    def _merge_class_info(self, existing: Dict[str, Any], new: Dict[str, Any]) -> None:
        """既存クラス情報の更新"""
        # より詳細な情報がある場合は更新
        if new.get('method_count', 0) > existing.get('method_count', 0):
            existing['method_count'] = new['method_count']

    def _get_relationship_key(self, relationship: Dict[str, Any]) -> str:
        """関係性の一意キーを生成"""
        rel_type = relationship['relationship_type']
        
        if rel_type == 'ModuleImports':
            return f"ModuleImports:{relationship['source_module']}:{relationship['target_module']}"
        elif rel_type == 'FunctionCalls':
            return f"FunctionCalls:{relationship['source_function']}:{relationship['target_function']}"
        elif rel_type == 'Inheritance':
            return f"Inheritance:{relationship['source_class']}:{relationship['target_class']}"
        elif rel_type == 'Contains':
            return f"Contains:{relationship['source_class']}:{relationship['target_function']}"
        else:
            return f"{rel_type}:{relationship.get('source', 'unknown')}:{relationship.get('target', 'unknown')}"

    def _resolve_relationship_ids(self, relationships: List[Dict[str, Any]]) -> None:
        """関係性のIDを解決"""
        for rel in relationships:
            rel_type = rel['relationship_type']
            
            if rel_type == 'FunctionCalls':
                # 関数名から実際のIDを解決
                source_name = rel.get('source_function', '')
                target_name = rel.get('target_function', '')
                
                if source_name in self.function_id_map:
                    rel['source_function_id'] = self.function_id_map[source_name]
                
                # target_function_idが"unknown_"で始まる場合は解決を試行
                if rel.get('target_function_id', '').startswith('unknown_'):
                    if target_name in self.function_id_map:
                        rel['target_function_id'] = self.function_id_map[target_name]
            
            elif rel_type == 'Inheritance':
                # クラス名から実際のIDを解決
                source_name = rel.get('source_class', '')
                target_name = rel.get('target_class', '')
                
                if source_name in self.class_id_map:
                    rel['source_class_id'] = self.class_id_map[source_name]
                
                if rel.get('target_class_id', '').startswith('unknown_'):
                    if target_name in self.class_id_map:
                        rel['target_class_id'] = self.class_id_map[target_name]