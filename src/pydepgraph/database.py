# pydepgraph/database.py
import kuzu
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class GraphDatabase:
    """Kùzuグラフデータベース操作クラス"""

    def __init__(self, db_path: str):
        """
        データベース初期化

        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.database = kuzu.Database(str(self.db_path))
        self.connection = kuzu.Connection(self.database)

        logger.info(f"Graph database initialized at: {self.db_path}")

    def initialize_schema(self) -> None:
        """グラフデータベースのスキーマを初期化"""

        logger.info("Initializing database schema...")

        # 既存テーブルの確認と削除（開発時）
        self._drop_existing_tables()

        # ノードテーブル作成
        self._create_module_table()

        # エッジテーブル作成
        self._create_module_imports_table()

        logger.info("Database schema initialized successfully")

    def _drop_existing_tables(self) -> None:
        """既存テーブルの削除（開発時用）"""
        try:
            self.connection.execute("DROP TABLE IF EXISTS ModuleImports;")
            self.connection.execute("DROP TABLE IF EXISTS Module;")
        except Exception as e:
            logger.debug(f"Table drop failed (expected): {e}")

    def _create_module_table(self) -> None:
        """Moduleノードテーブル作成"""
        query = """
        CREATE NODE TABLE Module (
            id STRING,
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
        logger.debug("Module table created")

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
        logger.debug("ModuleImports table created")

    def bulk_insert_modules(self, modules: List[Dict[str, Any]]) -> None:
        """モジュールを一括挿入"""
        if not modules:
            logger.warning("No modules to insert")
            return

        logger.info(f"Inserting {len(modules)} modules...")

        for module in modules:
            query = """
            CREATE (m:Module {
                id: $id,
                name: $name,
                file_path: $file_path,
                package: $package,
                lines_of_code: $lines_of_code,
                complexity_score: $complexity_score,
                is_external: $is_external,
                is_test: $is_test
            })
            """

            params = {
                'id': module['id'],
                'name': module['name'],
                'file_path': module['file_path'],
                'package': module['package'],
                'lines_of_code': module['lines_of_code'],
                'complexity_score': module['complexity_score'],
                'is_external': module['is_external'],
                'is_test': module['is_test'],
            }

            self.connection.execute(query, params)

        logger.info(f"Successfully inserted {len(modules)} modules")

    def bulk_insert_module_imports(self, relationships: List[Dict[str, Any]]) -> None:
        """モジュール依存関係を一括挿入"""
        if not relationships:
            logger.warning("No relationships to insert")
            return

        logger.info(f"Inserting {len(relationships)} module import relationships...")

        for rel in relationships:
            query = """
            MATCH (source:Module {id: $source_id}), (target:Module {id: $target_id})
            CREATE (source)-[r:ModuleImports {
                import_type: $import_type,
                import_alias: $import_alias,
                line_number: $line_number,
                is_conditional: $is_conditional
            }]->(target)
            """

            params = {
                'source_id': rel['source_module_id'],
                'target_id': rel['target_module_id'],
                'import_type': rel['import_type'],
                'import_alias': rel['import_alias'],
                'line_number': rel['line_number'],
                'is_conditional': rel['is_conditional'],
            }

            self.connection.execute(query, params)

        logger.info(f"Successfully inserted {len(relationships)} relationships")

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Cypherクエリを実行"""
        try:
            prepared_statement = self.connection.prepare(query)
            if params:
                result = self.connection.execute(prepared_statement, params)
            else:
                result = self.connection.execute(prepared_statement)

            if result.has_next():
                return result.get_as_df().to_dict('records')
            else:
                return []

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            raise

    def close(self) -> None:
        """データベース接続を閉じる"""
        # kuzu-0.5.1にはConnection.close()がないため、何もしない
        logger.info("Database connection implicitly closed by garbage collector")

# class OptimizedGraphDatabase(GraphDatabase):
#     """Optimized version of GraphDatabase with indexing."""
#
#     def optimize_query_plan(self, query: str) -> str:
#         print(f"OptimizedGraphDatabase: Optimizing query: {query}")
#         if "LIMIT" not in query:
#             return query + " LIMIT 1000"
#         return query
