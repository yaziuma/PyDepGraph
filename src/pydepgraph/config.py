# pydepgraph/config.py
import tomllib
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from .exceptions import PyDepGraphError


@dataclass
class ExtractorConfig:
    """Extractor設定"""
    enabled: bool = True
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatabaseConfig:
    """データベース設定"""
    path: str = "pydepgraph.db"
    enable_wal: bool = True
    buffer_pool_size: str = "128MB"


@dataclass
class AnalysisConfig:
    """分析設定"""
    include_tests: bool = True
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "__pycache__",
        ".git",
        ".pytest_cache",
        "*.pyc",
        "venv",
        ".venv"
    ])
    max_file_size_mb: int = 10
    timeout_seconds: int = 300


@dataclass
class Config:
    """設定クラス"""
    extractors: Dict[str, ExtractorConfig] = field(default_factory=dict)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> "Config":
        """設定ファイルから設定を読み込み"""
        if not config_path.exists():
            # デフォルト設定を返す
            return cls.get_default_config()
        
        try:
            with open(config_path, 'rb') as f:
                data = tomllib.load(f)
            
            return cls._from_dict(data)
            
        except tomllib.TOMLDecodeError as e:
            raise PyDepGraphError(f"Invalid TOML configuration file: {e}")
        except Exception as e:
            raise PyDepGraphError(f"Error reading configuration file: {e}")
    
    @classmethod
    def get_default_config(cls) -> "Config":
        """デフォルト設定を取得"""
        extractors = {
            "tach": ExtractorConfig(enabled=True),
            "code2flow": ExtractorConfig(enabled=True, options={"fallback_to_ast": True}),
            "dependency_file": ExtractorConfig(enabled=True)
        }
        
        return cls(
            extractors=extractors,
            database=DatabaseConfig(),
            analysis=AnalysisConfig()
        )
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "Config":
        """辞書から設定オブジェクトを作成（default merge方式）"""
        config = cls.get_default_config()

        # Extractors
        if "extractors" in data:
            extractors = {}
            for name, extractor_data in data["extractors"].items():
                if isinstance(extractor_data, dict):
                    enabled = extractor_data.get("enabled", True)
                    options = extractor_data.get("options", {})
                    extractors[name] = ExtractorConfig(enabled=enabled, options=options)
                else:
                    # Boolean shorthand
                    extractors[name] = ExtractorConfig(enabled=bool(extractor_data))
            config.extractors.update(extractors)
        
        # Database
        if "database" in data:
            db_data = data["database"]
            config.database.path = db_data.get("path", config.database.path)
            config.database.enable_wal = db_data.get("enable_wal", config.database.enable_wal)
            config.database.buffer_pool_size = db_data.get("buffer_pool_size", config.database.buffer_pool_size)
        
        # Analysis
        if "analysis" in data:
            analysis_data = data["analysis"]
            config.analysis.include_tests = analysis_data.get("include_tests", config.analysis.include_tests)
            config.analysis.exclude_patterns = analysis_data.get("exclude_patterns", config.analysis.exclude_patterns)
            config.analysis.max_file_size_mb = analysis_data.get("max_file_size_mb", config.analysis.max_file_size_mb)
            config.analysis.timeout_seconds = analysis_data.get("timeout_seconds", config.analysis.timeout_seconds)

        return config
    
    def validate(self) -> None:
        """設定値の検証"""
        # Database path validation
        if not self.database.path:
            raise PyDepGraphError("Database path cannot be empty")
        
        # Analysis validation
        if self.analysis.max_file_size_mb <= 0:
            raise PyDepGraphError("max_file_size_mb must be positive")
        
        if self.analysis.timeout_seconds <= 0:
            raise PyDepGraphError("timeout_seconds must be positive")
        
        # Extractor validation
        enabled_extractors = [name for name, config in self.extractors.items() if config.enabled]
        if not enabled_extractors:
            raise PyDepGraphError("At least one extractor must be enabled")
    
    def to_dict(self) -> Dict[str, Any]:
        """設定を辞書形式で取得"""
        return {
            "extractors": {
                name: {
                    "enabled": config.enabled,
                    "options": config.options
                } for name, config in self.extractors.items()
            },
            "database": {
                "path": self.database.path,
                "enable_wal": self.database.enable_wal,
                "buffer_pool_size": self.database.buffer_pool_size
            },
            "analysis": {
                "include_tests": self.analysis.include_tests,
                "exclude_patterns": self.analysis.exclude_patterns,
                "max_file_size_mb": self.analysis.max_file_size_mb,
                "timeout_seconds": self.analysis.timeout_seconds
            }
        }
