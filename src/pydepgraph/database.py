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
        """グラフデータベースのスキーマを初期化（非破壊）"""
        logger.info("Initializing database schema (non-destructive)...")

        # 通常初期化では既存テーブルを削除しない
        self._create_tables_if_needed()

        logger.info("Database schema initialized successfully")

    def reset_schema(self) -> None:
        """グラフデータベースのスキーマを再作成（破壊的）"""
        logger.warning("Resetting database schema (destructive)...")
        self._drop_existing_tables()
        self._create_tables_if_needed()
        logger.info("Database schema reset successfully")

    def _create_tables_if_needed(self) -> None:
        """必要なテーブルを作成"""
        # ノードテーブル作成
        self._create_module_table()
        self._create_function_table()
        self._create_class_table()

        # エッジテーブル作成
        self._create_module_imports_table()
        self._create_function_calls_table()
        self._create_inheritance_table()
        self._create_contains_table()

    def delete_project_data(self, project_root: str) -> None:
        """指定プロジェクト配下の既存グラフデータのみを削除する。"""
        normalized_root = Path(project_root).resolve()
        normalized_root_str = str(normalized_root)
        basename = normalized_root.name

        logger.info(
            "Deleting existing graph data for project scope: %s",
            normalized_root_str,
        )

        # 絶対パス / 相対パスが混在するケースに備えて、保守的に複数条件で照合する。
        # false positive を避けるため、曖昧な条件は使わない。
        params = {
            "project_root": normalized_root_str,
            "project_prefix_slash": f"{normalized_root_str}/",
            "project_prefix_backslash": f"{normalized_root_str}\\",
            "project_basename": basename,
            "project_basename_prefix_slash": f"{basename}/",
            "project_basename_prefix_backslash": f"{basename}\\",
        }

        relationship_delete_queries = [
            """
            MATCH (source:Module)-[r:ModuleImports]->(target:Module)
            WHERE
                (
                    source.file_path IS NOT NULL AND source.file_path <> "" AND (
                        source.file_path = $project_root OR
                        source.file_path STARTS WITH $project_prefix_slash OR
                        source.file_path STARTS WITH $project_prefix_backslash OR
                        source.file_path = $project_basename OR
                        source.file_path STARTS WITH $project_basename_prefix_slash OR
                        source.file_path STARTS WITH $project_basename_prefix_backslash
                    )
                )
                OR
                (
                    target.file_path IS NOT NULL AND target.file_path <> "" AND (
                        target.file_path = $project_root OR
                        target.file_path STARTS WITH $project_prefix_slash OR
                        target.file_path STARTS WITH $project_prefix_backslash OR
                        target.file_path = $project_basename OR
                        target.file_path STARTS WITH $project_basename_prefix_slash OR
                        target.file_path STARTS WITH $project_basename_prefix_backslash
                    )
                )
            DELETE r
            """,
            """
            MATCH (source:Function)-[r:FunctionCalls]->(target:Function)
            WHERE
                (
                    source.file_path IS NOT NULL AND source.file_path <> "" AND (
                        source.file_path = $project_root OR
                        source.file_path STARTS WITH $project_prefix_slash OR
                        source.file_path STARTS WITH $project_prefix_backslash OR
                        source.file_path = $project_basename OR
                        source.file_path STARTS WITH $project_basename_prefix_slash OR
                        source.file_path STARTS WITH $project_basename_prefix_backslash
                    )
                )
                OR
                (
                    target.file_path IS NOT NULL AND target.file_path <> "" AND (
                        target.file_path = $project_root OR
                        target.file_path STARTS WITH $project_prefix_slash OR
                        target.file_path STARTS WITH $project_prefix_backslash OR
                        target.file_path = $project_basename OR
                        target.file_path STARTS WITH $project_basename_prefix_slash OR
                        target.file_path STARTS WITH $project_basename_prefix_backslash
                    )
                )
            DELETE r
            """,
            """
            MATCH (source:Class)-[r:Inheritance]->(target:Class)
            WHERE
                (
                    source.file_path IS NOT NULL AND source.file_path <> "" AND (
                        source.file_path = $project_root OR
                        source.file_path STARTS WITH $project_prefix_slash OR
                        source.file_path STARTS WITH $project_prefix_backslash OR
                        source.file_path = $project_basename OR
                        source.file_path STARTS WITH $project_basename_prefix_slash OR
                        source.file_path STARTS WITH $project_basename_prefix_backslash
                    )
                )
                OR
                (
                    target.file_path IS NOT NULL AND target.file_path <> "" AND (
                        target.file_path = $project_root OR
                        target.file_path STARTS WITH $project_prefix_slash OR
                        target.file_path STARTS WITH $project_prefix_backslash OR
                        target.file_path = $project_basename OR
                        target.file_path STARTS WITH $project_basename_prefix_slash OR
                        target.file_path STARTS WITH $project_basename_prefix_backslash
                    )
                )
            DELETE r
            """,
            """
            MATCH (source:Class)-[r:Contains]->(target:Function)
            WHERE
                (
                    source.file_path IS NOT NULL AND source.file_path <> "" AND (
                        source.file_path = $project_root OR
                        source.file_path STARTS WITH $project_prefix_slash OR
                        source.file_path STARTS WITH $project_prefix_backslash OR
                        source.file_path = $project_basename OR
                        source.file_path STARTS WITH $project_basename_prefix_slash OR
                        source.file_path STARTS WITH $project_basename_prefix_backslash
                    )
                )
                OR
                (
                    target.file_path IS NOT NULL AND target.file_path <> "" AND (
                        target.file_path = $project_root OR
                        target.file_path STARTS WITH $project_prefix_slash OR
                        target.file_path STARTS WITH $project_prefix_backslash OR
                        target.file_path = $project_basename OR
                        target.file_path STARTS WITH $project_basename_prefix_slash OR
                        target.file_path STARTS WITH $project_basename_prefix_backslash
                    )
                )
            DELETE r
            """,
        ]

        node_delete_queries = [
            """
            MATCH (m:Module)
            WHERE
                m.file_path IS NOT NULL AND m.file_path <> "" AND (
                    m.file_path = $project_root OR
                    m.file_path STARTS WITH $project_prefix_slash OR
                    m.file_path STARTS WITH $project_prefix_backslash OR
                    m.file_path = $project_basename OR
                    m.file_path STARTS WITH $project_basename_prefix_slash OR
                    m.file_path STARTS WITH $project_basename_prefix_backslash
                )
            DELETE m
            """,
            """
            MATCH (f:Function)
            WHERE
                f.file_path IS NOT NULL AND f.file_path <> "" AND (
                    f.file_path = $project_root OR
                    f.file_path STARTS WITH $project_prefix_slash OR
                    f.file_path STARTS WITH $project_prefix_backslash OR
                    f.file_path = $project_basename OR
                    f.file_path STARTS WITH $project_basename_prefix_slash OR
                    f.file_path STARTS WITH $project_basename_prefix_backslash
                )
            DELETE f
            """,
            """
            MATCH (c:Class)
            WHERE
                c.file_path IS NOT NULL AND c.file_path <> "" AND (
                    c.file_path = $project_root OR
                    c.file_path STARTS WITH $project_prefix_slash OR
                    c.file_path STARTS WITH $project_prefix_backslash OR
                    c.file_path = $project_basename OR
                    c.file_path STARTS WITH $project_basename_prefix_slash OR
                    c.file_path STARTS WITH $project_basename_prefix_backslash
                )
            DELETE c
            """,
        ]

        for query in relationship_delete_queries:
            self.connection.execute(query, params)

        for query in node_delete_queries:
            self.connection.execute(query, params)

        logger.info("Project-scoped graph cleanup completed: %s", normalized_root_str)

    def _drop_existing_tables(self) -> None:
        """既存テーブルの削除（開発時用）"""
        try:
            # エッジテーブルから削除
            self.connection.execute("DROP TABLE IF EXISTS Contains;")
            self.connection.execute("DROP TABLE IF EXISTS Inheritance;")
            self.connection.execute("DROP TABLE IF EXISTS FunctionCalls;")
            self.connection.execute("DROP TABLE IF EXISTS ModuleImports;")
            # ノードテーブルを削除
            self.connection.execute("DROP TABLE IF EXISTS Class;")
            self.connection.execute("DROP TABLE IF EXISTS Function;")
            self.connection.execute("DROP TABLE IF EXISTS Module;")
        except Exception as e:
            logger.debug(f"Table drop failed (expected): {e}")

    def _create_module_table(self) -> None:
        """Moduleノードテーブル作成"""
        try:
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
                role STRING,
                PRIMARY KEY (id)
            );
            """
            self.connection.execute(query)
            logger.debug("Module table created")
        except Exception as e:
            logger.debug(f"Module table already exists or create skipped: {e}")

    def _create_module_imports_table(self) -> None:
        """ModuleImportsエッジテーブル作成"""
        try:
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
        except Exception as e:
            logger.debug(f"ModuleImports table already exists or create skipped: {e}")

    def _create_function_table(self) -> None:
        """Functionノードテーブル作成"""
        try:
            query = """
            CREATE NODE TABLE Function (
                id STRING,
                name STRING,
                qualified_name STRING,
                file_path STRING,
                line_number INT32,
                cyclomatic_complexity INT32,
                parameter_count INT32,
                is_method BOOLEAN,
                is_static BOOLEAN,
                is_class_method BOOLEAN,
                class_id STRING,
                PRIMARY KEY (id)
            );
            """
            self.connection.execute(query)
            logger.debug("Function table created")
        except Exception as e:
            logger.debug(f"Function table already exists or create skipped: {e}")

    def _create_class_table(self) -> None:
        """Classノードテーブル作成"""
        try:
            query = """
            CREATE NODE TABLE Class (
                id STRING,
                name STRING,
                qualified_name STRING,
                file_path STRING,
                line_number INT32,
                method_count INT32,
                inheritance_depth INT32,
                is_abstract BOOLEAN,
                PRIMARY KEY (id)
            );
            """
            self.connection.execute(query)
            logger.debug("Class table created")
        except Exception as e:
            logger.debug(f"Class table already exists or create skipped: {e}")

    def _create_function_calls_table(self) -> None:
        """FunctionCallsエッジテーブル作成"""
        try:
            query = """
            CREATE REL TABLE FunctionCalls (
                FROM Function TO Function,
                call_type STRING,
                line_number INT32
            );
            """
            self.connection.execute(query)
            logger.debug("FunctionCalls table created")
        except Exception as e:
            logger.debug(f"FunctionCalls table already exists or create skipped: {e}")

    def _create_inheritance_table(self) -> None:
        """Inheritanceエッジテーブル作成"""
        try:
            query = """
            CREATE REL TABLE Inheritance (
                FROM Class TO Class,
                line_number INT32
            );
            """
            self.connection.execute(query)
            logger.debug("Inheritance table created")
        except Exception as e:
            logger.debug(f"Inheritance table already exists or create skipped: {e}")

    def _create_contains_table(self) -> None:
        """Containsエッジテーブル作成"""
        try:
            query = """
            CREATE REL TABLE Contains (
                FROM Class TO Function,
                line_number INT32
            );
            """
            self.connection.execute(query)
            logger.debug("Contains table created")
        except Exception as e:
            logger.debug(f"Contains table already exists or create skipped: {e}")

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
                is_test: $is_test,
                role: $role
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
                'role': module.get('role', ''),
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
                name: $name,
                qualified_name: $qualified_name,
                file_path: $file_path,
                line_number: $line_number,
                cyclomatic_complexity: $cyclomatic_complexity,
                parameter_count: $parameter_count,
                is_method: $is_method,
                is_static: $is_static,
                is_class_method: $is_class_method,
                class_id: $class_id
            })
            """

            params = {
                'id': function['id'],
                'name': function['name'],
                'qualified_name': function['qualified_name'],
                'file_path': function['file_path'],
                'line_number': function['line_number'],
                'cyclomatic_complexity': function['cyclomatic_complexity'],
                'parameter_count': function['parameter_count'],
                'is_method': function['is_method'],
                'is_static': function['is_static'],
                'is_class_method': function['is_class_method'],
                'class_id': function.get('class_id', ''),
            }

            self.connection.execute(query, params)

        logger.info(f"Successfully inserted {len(functions)} functions")

    def bulk_insert_classes(self, classes: List[Dict[str, Any]]) -> None:
        """クラスを一括挿入"""
        if not classes:
            logger.warning("No classes to insert")
            return

        logger.info(f"Inserting {len(classes)} classes...")

        for class_data in classes:
            query = """
            CREATE (c:Class {
                id: $id,
                name: $name,
                qualified_name: $qualified_name,
                file_path: $file_path,
                line_number: $line_number,
                method_count: $method_count,
                inheritance_depth: $inheritance_depth,
                is_abstract: $is_abstract
            })
            """

            params = {
                'id': class_data['id'],
                'name': class_data['name'],
                'qualified_name': class_data['qualified_name'],
                'file_path': class_data['file_path'],
                'line_number': class_data['line_number'],
                'method_count': class_data['method_count'],
                'inheritance_depth': class_data['inheritance_depth'],
                'is_abstract': class_data['is_abstract'],
            }

            self.connection.execute(query, params)

        logger.info(f"Successfully inserted {len(classes)} classes")

    def bulk_insert_function_calls(self, relationships: List[Dict[str, Any]]) -> None:
        """関数呼び出し関係を一括挿入"""
        if not relationships:
            logger.warning("No function call relationships to insert")
            return

        logger.info(f"Inserting {len(relationships)} function call relationships...")

        for rel in relationships:
            if rel['relationship_type'] != 'FunctionCalls':
                continue

            query = """
            MATCH (source:Function {id: $source_id}), (target:Function {id: $target_id})
            CREATE (source)-[r:FunctionCalls {
                call_type: $call_type,
                line_number: $line_number
            }]->(target)
            """

            params = {
                'source_id': rel['source_function_id'],
                'target_id': rel['target_function_id'],
                'call_type': rel.get('call_type', 'direct'),
                'line_number': rel.get('line_number', 0),
            }

            try:
                self.connection.execute(query, params)
            except Exception as e:
                logger.warning(f"Failed to insert function call relationship: {e}")

        logger.info(f"Successfully inserted function call relationships")

    def bulk_insert_inheritance(self, relationships: List[Dict[str, Any]]) -> None:
        """継承関係を一括挿入"""
        if not relationships:
            logger.warning("No inheritance relationships to insert")
            return

        logger.info(f"Inserting inheritance relationships...")

        for rel in relationships:
            if rel['relationship_type'] != 'Inheritance':
                continue

            query = """
            MATCH (source:Class {id: $source_id}), (target:Class {id: $target_id})
            CREATE (source)-[r:Inheritance {
                line_number: $line_number
            }]->(target)
            """

            params = {
                'source_id': rel['source_class_id'],
                'target_id': rel['target_class_id'],
                'line_number': rel.get('line_number', 0),
            }

            try:
                self.connection.execute(query, params)
            except Exception as e:
                logger.warning(f"Failed to insert inheritance relationship: {e}")

        logger.info(f"Successfully inserted inheritance relationships")

    def bulk_insert_contains(self, relationships: List[Dict[str, Any]]) -> None:
        """包含関係を一括挿入"""
        if not relationships:
            logger.warning("No contains relationships to insert")
            return

        logger.info(f"Inserting contains relationships...")

        for rel in relationships:
            if rel['relationship_type'] != 'Contains':
                continue

            query = """
            MATCH (source:Class {id: $source_id}), (target:Function {id: $target_id})
            CREATE (source)-[r:Contains {
                line_number: $line_number
            }]->(target)
            """

            params = {
                'source_id': rel['source_class_id'],
                'target_id': rel['target_function_id'],
                'line_number': rel.get('line_number', 0),
            }

            try:
                self.connection.execute(query, params)
            except Exception as e:
                logger.warning(f"Failed to insert contains relationship: {e}")

        logger.info(f"Successfully inserted contains relationships")

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Cypherクエリを実行"""
        try:
            if params:
                result = self.connection.execute(query, params)
            else:
                result = self.connection.execute(query)

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
