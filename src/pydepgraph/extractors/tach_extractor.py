# pydepgraph/extractors/tach_extractor.py

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any
import logging

from .base import ExtractorBase, ExtractionResult
from ..exceptions import PrologExecutionError

logger = logging.getLogger(__name__)

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
            all_modules.update(imported_modules)

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
                    'import_type': 'direct',
                    'import_alias': '',
                    'line_number': 0,
                    'is_conditional': False,
                }
                relationships.append(relationship)

        logger.info(f"Tach extraction completed: {len(modules)} modules, {len(relationships)} relationships")

        return ExtractionResult(
            modules=modules,
            functions=[],
            classes=[],
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
            'lines_of_code': 0,
            'complexity_score': 0.0,
            'is_external': self._is_external_module(module_path),
            'is_test': self._is_test_module(module_path),
        }

    def _is_external_module(self, module_path: str) -> bool:
        """外部モジュールかどうかを判定"""
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
