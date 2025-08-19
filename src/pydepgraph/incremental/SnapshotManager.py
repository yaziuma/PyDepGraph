# src/pydepgraph/incremental/SnapshotManager.py

import subprocess
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone

from ..models import ExtractionResult, Module, ModuleImport, FunctionCall, Inheritance, Contains, Function, Class
from ..exceptions import PyDepGraphError

class SnapshotManager:
    """
    Manages saving and loading analysis result snapshots corresponding to Git commits.
    """
    SNAPSHOT_DIR_NAME = ".pydepgraph/snapshots"
    SNAPSHOT_VERSION = "1.0"

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.snapshot_dir = self.repo_path / self.SNAPSHOT_DIR_NAME
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def _get_commit_hash(self, ref: str = "HEAD") -> str:
        """Resolves a Git reference to a full commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", ref],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise PyDepGraphError(f"Could not resolve git reference '{ref}': {e}")

    def save_snapshot(self, result: ExtractionResult) -> str:
        """Saves the extraction result as a snapshot for the current HEAD."""
        commit_hash = self._get_commit_hash()
        snapshot_file = self.snapshot_dir / f"{commit_hash}.json"

        self._write_snapshot_file(snapshot_file, commit_hash, result)

        return commit_hash

    def _write_snapshot_file(self, path: Path, commit_hash: str, result: ExtractionResult):
        """Serializes and writes the snapshot data to a file."""
        snapshot_data = {
            "version": self.SNAPSHOT_VERSION,
            "commit_hash": commit_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "graph": self._serialize_result(result)
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, indent=2)

    def load_snapshot(self, ref: str) -> ExtractionResult:
        """Loads a snapshot for a given Git reference."""
        commit_hash = self._get_commit_hash(ref)
        snapshot_file = self.snapshot_dir / f"{commit_hash}.json"

        if not snapshot_file.is_file():
            raise PyDepGraphError(f"Snapshot not found for commit reference '{ref}' (resolved to {commit_hash})")

        with open(snapshot_file, 'r', encoding='utf-8') as f:
            snapshot_data = json.load(f)

        return self._deserialize_result(snapshot_data)

    def _serialize_result(self, result: ExtractionResult) -> Dict[str, Any]:
        """Serializes an ExtractionResult object to a JSON-compatible dictionary."""
        nodes = []
        edges = []

        # Serialize nodes
        for module in result.modules:
            nodes.append({"id": module.name, "type": "module", "path": module.file_path, "is_external": module.is_external})
        # The result from the new AST analysis returns dicts, not objects. Handle both.
        for func in result.functions:
            name = func.get("name") if isinstance(func, dict) else func.name
            nodes.append({"id": name, "type": "function"})
        for cls in result.classes:
            name = cls.get("name") if isinstance(cls, dict) else cls.name
            nodes.append({"id": name, "type": "class"})

        # Serialize edges
        for imp in result.module_imports:
            edges.append({"source": imp.source_module, "target": imp.target_module, "type": "import"})
        for call in result.function_calls:
            edges.append({"source": call.source_function, "target": call.target_function, "type": "call"})
        for inh in result.inheritance:
            edges.append({"source": inh.child_class, "target": inh.parent_class, "type": "inherit"})

        return {"nodes": nodes, "edges": edges}

    def _deserialize_result(self, snapshot_data: Dict[str, Any]) -> ExtractionResult:
        """Deserializes a dictionary back into an ExtractionResult object."""
        graph = snapshot_data.get("graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        modules, functions, classes = [], [], []
        module_imports, function_calls, inheritance = [], [], []

        # Deserialize nodes
        for node in nodes:
            if node["type"] == "module":
                modules.append(Module(name=node["id"], file_path=node.get("path", ""), is_external=node.get("is_external", False)))
            elif node["type"] == "function":
                # Note: we are losing details here, but this is per design doc.
                functions.append(Function(name=node["id"], qualified_name=node["id"], file_path=""))
            elif node["type"] == "class":
                classes.append(Class(name=node["id"], qualified_name=node["id"], file_path=""))

        # Deserialize edges
        for edge in edges:
            if edge["type"] == "import":
                module_imports.append(ModuleImport(source_module=edge["source"], target_module=edge["target"]))
            elif edge["type"] == "call":
                function_calls.append(FunctionCall(source_function=edge["source"], target_function=edge["target"]))
            elif edge["type"] == "inherit":
                inheritance.append(Inheritance(child_class=edge["source"], parent_class=edge["target"]))

        metadata = {
            "version": snapshot_data.get("version"),
            "commit_hash": snapshot_data.get("commit_hash"),
            "created_at": snapshot_data.get("created_at"),
        }

        return ExtractionResult(
            modules=modules, functions=functions, classes=classes,
            module_imports=module_imports, function_calls=function_calls,
            inheritance=inheritance, contains=[], metadata=metadata
        )
