# pydepgraph/services/data_integrator.py

from typing import Dict, List, Any, Union
import logging
from ..models import (
    Module, Function, Class, ModuleImport, FunctionCall, 
    Inheritance, Contains, ExtractionResult
)
from ..extractors.base import RawExtractionResult as ExtractorResult

logger = logging.getLogger(__name__)


class DataIntegrator:
    """抽出器の結果を統合してmodels.pyの形式に変換"""
    
    def integrate_results(self, extractor_results: List[ExtractorResult]) -> ExtractionResult:
        """
        複数の抽出器結果を統合してmodels.ExtractionResultに変換
        
        Args:
            extractor_results: 抽出器から返された結果のリスト
            
        Returns:
            ExtractionResult: 統合された結果
        """
        all_modules = []
        all_functions = []
        all_classes = []
        all_module_imports = []
        all_function_calls = []
        all_inheritance = []
        all_contains = []
        combined_metadata = {}
        
        for result in extractor_results:
            # 各抽出器からの結果を統合
            all_modules.extend(self._convert_modules(result.modules))
            all_functions.extend(self._convert_functions(result.functions))
            all_classes.extend(self._convert_classes(result.classes))
            all_module_imports.extend(self._convert_relationships(result.relationships, "ModuleImports"))
            all_function_calls.extend(self._convert_relationships(result.relationships, "FunctionCalls"))
            all_inheritance.extend(self._convert_relationships(result.relationships, "Inheritance"))
            all_contains.extend(self._convert_relationships(result.relationships, "Contains"))
            combined_metadata.update(result.metadata)
        
        # 重複除去
        all_modules = self._deduplicate_modules(all_modules)
        all_functions = self._deduplicate_functions(all_functions)
        all_classes = self._deduplicate_classes(all_classes)
        all_module_imports = self._deduplicate_module_imports(all_module_imports)
        all_function_calls = self._deduplicate_function_calls(all_function_calls)
        all_inheritance = self._deduplicate_inheritance(all_inheritance)
        all_contains = self._deduplicate_contains(all_contains)
        
        return ExtractionResult(
            modules=all_modules,
            functions=all_functions,
            classes=all_classes,
            module_imports=all_module_imports,
            function_calls=all_function_calls,
            inheritance=all_inheritance,
            contains=all_contains,
            metadata=combined_metadata
        )
    
    def _convert_modules(self, modules: List[Dict[str, Any]]) -> List[Module]:
        """Dict形式のモジュールをModuleオブジェクトに変換"""
        converted = []
        for module_data in modules:
            try:
                module = Module(
                    name=module_data.get("name", ""),
                    file_path=module_data.get("file_path", ""),
                    package=module_data.get("package"),
                    lines_of_code=module_data.get("lines_of_code"),
                    complexity_score=module_data.get("complexity_score"),
                    is_external=module_data.get("is_external", False),
                    is_test=module_data.get("is_test", False),
                    extractor=module_data.get("extractor")
                )
                converted.append(module)
            except Exception as e:
                logger.warning(f"Failed to convert module {module_data}: {e}")
        return converted
    
    def _convert_functions(self, functions: List[Dict[str, Any]]) -> List[Function]:
        """Dict形式の関数をFunctionオブジェクトに変換"""
        converted = []
        for func_data in functions:
            try:
                function = Function(
                    name=func_data.get("name", ""),
                    qualified_name=func_data.get("qualified_name", func_data.get("name", "")),
                    file_path=func_data.get("file_path", ""),
                    line_number=func_data.get("line_number"),
                    cyclomatic_complexity=func_data.get("cyclomatic_complexity"),
                    parameter_count=func_data.get("parameter_count"),
                    return_type=func_data.get("return_type"),
                    docstring=func_data.get("docstring"),
                    is_method=func_data.get("is_method", False),
                    is_static=func_data.get("is_static", False),
                    is_class_method=func_data.get("is_class_method", False),
                    extractor=func_data.get("extractor")
                )
                converted.append(function)
            except Exception as e:
                logger.warning(f"Failed to convert function {func_data}: {e}")
        return converted
    
    def _convert_classes(self, classes: List[Dict[str, Any]]) -> List[Class]:
        """Dict形式のクラスをClassオブジェクトに変換"""
        converted = []
        for class_data in classes:
            try:
                cls = Class(
                    name=class_data.get("name", ""),
                    qualified_name=class_data.get("qualified_name", class_data.get("name", "")),
                    file_path=class_data.get("file_path", ""),
                    line_number=class_data.get("line_number"),
                    method_count=class_data.get("method_count"),
                    inheritance_depth=class_data.get("inheritance_depth"),
                    is_abstract=class_data.get("is_abstract", False),
                    docstring=class_data.get("docstring"),
                    extractor=class_data.get("extractor")
                )
                converted.append(cls)
            except Exception as e:
                logger.warning(f"Failed to convert class {class_data}: {e}")
        return converted
    
    def _convert_relationships(self, relationships: List[Dict[str, Any]], rel_type: str) -> List[Union[ModuleImport, FunctionCall, Inheritance, Contains]]:
        """関係性をそれぞれの型に変換"""
        converted = []
        for rel_data in relationships:
            try:
                if rel_data.get("relationship_type") != rel_type:
                    continue
                    
                if rel_type == "ModuleImports":
                    rel = ModuleImport(
                        source_module=rel_data.get("source_module", ""),
                        target_module=rel_data.get("target_module", ""),
                        import_type=rel_data.get("import_type", "standard"),
                        import_alias=rel_data.get("import_alias"),
                        line_number=rel_data.get("line_number"),
                        is_conditional=rel_data.get("is_conditional", False),
                        extractor=rel_data.get("extractor")
                    )
                elif rel_type == "FunctionCalls":
                    rel = FunctionCall(
                        source_function=rel_data.get("source_function", ""),
                        target_function=rel_data.get("target_function", ""),
                        call_type=rel_data.get("call_type", "direct"),
                        line_number=rel_data.get("line_number"),
                        is_conditional=rel_data.get("is_conditional", False),
                        extractor=rel_data.get("extractor")
                    )
                elif rel_type == "Inheritance":
                    rel = Inheritance(
                        child_class=rel_data.get("child_class") or rel_data.get("source_class", ""),
                        parent_class=rel_data.get("parent_class") or rel_data.get("target_class", ""),
                        inheritance_type=rel_data.get("inheritance_type", "direct"),
                        line_number=rel_data.get("line_number"),
                        extractor=rel_data.get("extractor")
                    )
                elif rel_type == "Contains":
                    rel = Contains(
                        container=rel_data.get("source_class", ""),
                        contained=rel_data.get("target_function", ""),
                        contained_type=rel_data.get("contained_type", "function"),
                        extractor=rel_data.get("extractor")
                    )
                else:
                    continue
                    
                converted.append(rel)
            except Exception as e:
                logger.warning(f"Failed to convert relationship {rel_data}: {e}")
        return converted
    
    def _deduplicate_modules(self, modules: List[Module]) -> List[Module]:
        """モジュールの重複除去"""
        seen = set()
        unique = []
        for module in modules:
            key = (module.name, module.file_path)
            if key not in seen:
                seen.add(key)
                unique.append(module)
        return unique
    
    def _deduplicate_functions(self, functions: List[Function]) -> List[Function]:
        """関数の重複除去"""
        seen = set()
        unique = []
        for function in functions:
            key = (function.qualified_name, function.file_path)
            if key not in seen:
                seen.add(key)
                unique.append(function)
        return unique
    
    def _deduplicate_classes(self, classes: List[Class]) -> List[Class]:
        """クラスの重複除去"""
        seen = set()
        unique = []
        for cls in classes:
            key = (cls.qualified_name, cls.file_path)
            if key not in seen:
                seen.add(key)
                unique.append(cls)
        return unique
    
    def _deduplicate_module_imports(self, imports: List[ModuleImport]) -> List[ModuleImport]:
        """モジュールインポートの重複除去"""
        seen = set()
        unique = []
        for imp in imports:
            key = (imp.source_module, imp.target_module)
            if key not in seen:
                seen.add(key)
                unique.append(imp)
        return unique
    
    def _deduplicate_function_calls(self, calls: List[FunctionCall]) -> List[FunctionCall]:
        """関数呼び出しの重複除去"""
        seen = set()
        unique = []
        for call in calls:
            key = (call.source_function, call.target_function)
            if key not in seen:
                seen.add(key)
                unique.append(call)
        return unique
    
    def _deduplicate_inheritance(self, inheritance: List[Inheritance]) -> List[Inheritance]:
        """継承関係の重複除去"""
        seen = set()
        unique = []
        for inh in inheritance:
            key = (inh.child_class, inh.parent_class)
            if key not in seen:
                seen.add(key)
                unique.append(inh)
        return unique
    
    def _deduplicate_contains(self, contains: List[Contains]) -> List[Contains]:
        """包含関係の重複除去"""
        seen = set()
        unique = []
        for cont in contains:
            key = (cont.container, cont.contained, cont.contained_type)
            if key not in seen:
                seen.add(key)
                unique.append(cont)
        return unique