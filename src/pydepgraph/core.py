# pydepgraph/core.py
import logging
from pathlib import Path
from typing import Optional

from .config import Config
from .database import GraphDatabase
from .extractors.tach_extractor import TachExtractor
from .extractors.code2flow_extractor import Code2FlowExtractor
from .services.data_integrator import DataIntegrator
from .models import ExtractionResult
from .exceptions import PyDepGraphError


logger = logging.getLogger(__name__)


class PyDepGraphCore:
    """PyDepGraphのコア機能を提供するクラス"""
    
    def __init__(self, config: Config):
        self.config = config
        self.database: Optional[GraphDatabase] = None
        
        # 設定の検証
        config.validate()
    
    def analyze_project(self, project_path: str) -> ExtractionResult:
        """プロジェクト全体の依存関係分析を実行"""
        project_path = Path(project_path).resolve()
        
        if not project_path.exists():
            raise PyDepGraphError(f"Project path does not exist: {project_path}")
        
        if not project_path.is_dir():
            raise PyDepGraphError(f"Project path is not a directory: {project_path}")
        
        logger.info(f"Starting analysis of project: {project_path}")
        
        try:
            # Initialize database
            self._initialize_database()
            
            # Run extractors
            extraction_results = []
            
            # Tach extractor
            if self.config.extractors.get("tach", {}).enabled:
                logger.info("Running Tach extractor...")
                tach_extractor = TachExtractor()
                tach_result = tach_extractor.extract(str(project_path))
                extraction_results.append(tach_result)
                logger.info(f"Tach extractor found {len(tach_result.modules)} modules")
            
            # Code2Flow extractor
            if self.config.extractors.get("code2flow", {}).enabled:
                logger.info("Running Code2Flow extractor...")
                code2flow_extractor = Code2FlowExtractor()
                code2flow_result = code2flow_extractor.extract(str(project_path))
                extraction_results.append(code2flow_result)
                logger.info(f"Code2Flow extractor found {len(code2flow_result.functions)} functions, {len(code2flow_result.classes)} classes")
            
            if not extraction_results:
                raise PyDepGraphError("No extractors were enabled or executed successfully")
            
            # Integrate results
            logger.info("Integrating extraction results...")
            integrator = DataIntegrator()
            integrated_result = integrator.integrate_results(extraction_results)
            
            logger.info(f"Integration complete - {len(integrated_result.modules)} modules, "
                       f"{len(integrated_result.functions)} functions, "
                       f"{len(integrated_result.classes)} classes")
            
            # Store in database
            logger.info("Storing results in database...")
            self._store_results(integrated_result)
            
            logger.info("Analysis completed successfully")
            return integrated_result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    
    def _initialize_database(self):
        """データベースを初期化"""
        if self.database is None:
            self.database = GraphDatabase(self.config.database.path)
            self.database.initialize_schema()
    
    def _store_results(self, result: ExtractionResult):
        """分析結果をデータベースに保存"""
        if self.database is None:
            raise PyDepGraphError("Database not initialized")
        
        # Convert to database format (all results are now proper objects)
        modules_data = []
        for i, module in enumerate(result.modules, 1):
            modules_data.append({
                "id": str(i),  # String IDに変更
                "name": module.name,
                "file_path": module.file_path,
                "package": module.package or "",
                "lines_of_code": module.lines_of_code or 0,
                "complexity_score": module.complexity_score or 0.0,
                "is_external": module.is_external,
                "is_test": module.is_test
            })
        
        functions_data = []
        for i, function in enumerate(result.functions, 1):
            functions_data.append({
                "id": str(i),  # String IDに変更
                "name": function.name,
                "qualified_name": function.qualified_name,
                "file_path": function.file_path,
                "line_number": function.line_number or 0,
                "cyclomatic_complexity": function.cyclomatic_complexity or 1,
                "parameter_count": function.parameter_count or 0,
                "is_method": function.is_method,
                "is_static": function.is_static,
                "is_class_method": function.is_class_method
            })
        
        classes_data = []
        for i, cls in enumerate(result.classes, 1):
            classes_data.append({
                "id": str(i),  # String IDに変更
                "name": cls.name,
                "qualified_name": cls.qualified_name,
                "file_path": cls.file_path,
                "line_number": cls.line_number or 0,
                "method_count": cls.method_count or 0,
                "inheritance_depth": cls.inheritance_depth or 1,
                "is_abstract": cls.is_abstract
            })
        
        # Create mapping for relationships - file_pathをキーとして使用
        module_path_to_id = {module["file_path"]: module["id"] for module in modules_data}
        function_name_to_id = {func["qualified_name"]: func["id"] for func in functions_data}
        class_name_to_id = {cls["qualified_name"]: cls["id"] for cls in classes_data}
        
        logger.debug(f"Class name to ID mapping keys: {list(class_name_to_id.keys())[:5]}")
        
        # Module imports - file_pathでマッピング
        imports_data = []
        for i, imp in enumerate(result.module_imports, 1):
            source_id = module_path_to_id.get(imp.source_module)
            target_id = module_path_to_id.get(imp.target_module)
            
            if source_id and target_id:
                imports_data.append({
                    "id": str(i),  # String IDに変更
                    "source_module_id": source_id,
                    "target_module_id": target_id,
                    "import_type": imp.import_type,
                    "import_alias": imp.import_alias,
                    "line_number": imp.line_number or 0,
                    "is_conditional": imp.is_conditional
                })
            else:
                logger.debug(f"Skipping import relationship: {imp.source_module} -> {imp.target_module} (source_id: {source_id}, target_id: {target_id})")
        
        # Function calls
        calls_data = []
        for i, call in enumerate(result.function_calls, 1):
            source_id = function_name_to_id.get(call.source_function)
            target_id = function_name_to_id.get(call.target_function)
            
            if source_id and target_id:
                calls_data.append({
                    "id": str(i),  # String IDに変更
                    "relationship_type": "FunctionCalls",
                    "source_function_id": source_id,
                    "target_function_id": target_id,
                    "call_type": call.call_type,
                    "line_number": call.line_number or 0,
                    "is_conditional": call.is_conditional
                })
            else:
                logger.debug(f"Skipping function call: {call.source_function} -> {call.target_function} (source_id: {source_id}, target_id: {target_id})")
        
        # Inheritance relationships
        inheritance_data = []
        for i, inh in enumerate(result.inheritance, 1):
            source_id = class_name_to_id.get(inh.child_class)
            target_id = class_name_to_id.get(inh.parent_class)
            
            if source_id and target_id:
                inheritance_data.append({
                    "id": str(i),  # String IDに変更
                    "relationship_type": "Inheritance",
                    "source_class_id": source_id,
                    "target_class_id": target_id,
                    "inheritance_type": inh.inheritance_type,
                    "line_number": inh.line_number or 0
                })
                logger.debug(f"Added inheritance: {inh.child_class} -> {inh.parent_class}")
            else:
                logger.debug(f"Skipping inheritance: {inh.child_class} -> {inh.parent_class} (source_id: {source_id}, target_id: {target_id})")
                if i <= 3:  # 最初の数件の詳細ログ
                    logger.debug(f"  Available class names: {list(class_name_to_id.keys())[:3]}")
                    logger.debug(f"  Looking for: child='{inh.child_class}', parent='{inh.parent_class}'")
        
        # Bulk insert into database with detailed logging
        logger.info(f"Preparing to insert: {len(modules_data)} modules, {len(functions_data)} functions, {len(classes_data)} classes")
        logger.info(f"Relationships: {len(imports_data)} imports, {len(calls_data)} function calls, {len(inheritance_data)} inheritance")
        
        if modules_data:
            self.database.bulk_insert_modules(modules_data)
        
        if functions_data:
            self.database.bulk_insert_functions(functions_data)
        
        if classes_data:
            self.database.bulk_insert_classes(classes_data)
        
        if imports_data:
            self.database.bulk_insert_module_imports(imports_data)
        
        if calls_data:
            self.database.bulk_insert_function_calls(calls_data)
        
        if inheritance_data:
            self.database.bulk_insert_inheritance(inheritance_data)
    
    def close(self):
        """リソースをクリーンアップ"""
        if self.database:
            self.database.close()
            self.database = None