# pydepgraph/extractors/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any
import logging
from pathlib import Path


@dataclass
class ExtractionResult:
    """Represents the result of an extraction process."""

    modules: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    classes: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


logger = logging.getLogger(__name__)

class ExtractorBase(ABC):
    """依存関係抽出器の抽象基底クラス"""

    @abstractmethod
    def extract(self, project_path: str) -> "ExtractionResult":
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
