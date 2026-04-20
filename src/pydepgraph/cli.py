# pydepgraph/cli.py
import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from .config import Config
from .core import PyDepGraphCore
from .services.analytics_service import GraphAnalyticsService
from .services.query_service import BasicQueryService, ExtendedQueryService
from .database import GraphDatabase
from .exceptions import PyDepGraphError
from .incremental import SnapshotManager, GraphComparator
from .reporting.evolution_reporter import EvolutionReporter

logger = logging.getLogger(__name__)


def setup_logging(verbose: int = 0):
    """ログレベルを設定"""
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    
    # ライブラリとしては、ルートロガーのレベルのみ設定
    # ハンドラやフォーマッタの設定はアプリケーション側に委ねる
    logging.getLogger().setLevel(level)


def create_parser() -> argparse.ArgumentParser:
    """CLIパーサーを作成"""
    parser = argparse.ArgumentParser(
        prog='pydepgraph',
        description='Python dependency graph analysis tool'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (use -v, -vv for more verbose)'
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('pydepgraph.toml'),
        help='Path to configuration file (default: pydepgraph.toml)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze project dependencies')
    analyze_parser.add_argument(
        'project_path',
        nargs='?',
        default='.',
        help='Path to project directory (default: current directory)'
    )
    analyze_parser.add_argument(
        '--output',
        choices=['json', 'table'],
        default='table',
        help='Output format (default: table)'
    )
    analyze_parser.add_argument(
        '--database',
        help='Database file path (overrides config)'
    )
    
    # query command
    query_parser = subparsers.add_parser('query', help='Query dependency relationships')
    query_parser.add_argument(
        'query_type',
        choices=['modules', 'functions', 'classes', 'imports', 'calls', 'role', 'context'],
        help='Type of entities to query'
    )
    query_parser.add_argument(
        '--filter',
        help='Filter expression for query'
    )
    query_parser.add_argument(
        '--format',
        choices=['json', 'table'],
        default='table',
        help='Output format (default: table)'
    )
    query_parser.add_argument(
        '--type',
        dest='node_type',
        choices=['module'],
        default='module',
        help='Node type for role query (default: module)'
    )
    query_parser.add_argument(
        '--value',
        help='Role value to filter by (for role query)'
    )
    query_parser.add_argument(
        '--target',
        help='Target Python file path for context query'
    )
    query_parser.add_argument(
        '--depth',
        type=int,
        default=1,
        help='Dependency depth for context query (default: 1)'
    )
    query_parser.add_argument(
        '--project-root',
        help='Project root path for local module resolution in context query'
    )
    
    # analytics command
    analytics_parser = subparsers.add_parser('analytics', help='Perform graph analytics')
    analytics_parser.add_argument(
        'analysis_type',
        choices=['stats', 'cycles', 'importance', 'depth'],
        help='Type of analysis to perform'
    )
    analytics_parser.add_argument(
        '--node-type',
        choices=['module', 'function', 'class'],
        default='module',
        help='Type of nodes to analyze (default: module)'
    )
    analytics_parser.add_argument(
        '--root',
        help='Root node for depth analysis'
    )
    analytics_parser.add_argument(
        '--format',
        choices=['json', 'table'],
        default='table',
        help='Output format (default: table)'
    )
    
    # report command
    report_parser = subparsers.add_parser('report', help='Generate analysis report')
    report_parser.add_argument(
        '--output-file',
        help='Output file path (default: stdout)'
    )
    report_parser.add_argument(
        '--format',
        choices=['json', 'html', 'markdown', 'table'],
        default='markdown',
        help='Report format (default: markdown)'
    )
    report_parser.add_argument(
        '--metrics',
        action='store_true',
        default=False,
        help='Include detailed module metrics and centrality scores'
    )
    report_parser.add_argument(
        '--sort-by',
        choices=['fan_in', 'fan_out', 'betweenness', 'closeness'],
        default=None,
        help='Sort metrics by the specified column (requires --metrics)'
    )

    # evolution command
    evolution_parser = subparsers.add_parser('evolution', help='Compare dependency graphs between Git commits')
    evolution_parser.add_argument(
        '--from',
        dest='from_ref',
        default='HEAD~1',
        help='Starting Git reference (default: HEAD~1)'
    )
    evolution_parser.add_argument(
        '--to',
        dest='to_ref',
        default='HEAD',
        help='Ending Git reference (default: HEAD)'
    )
    evolution_parser.add_argument(
        'project_path',
        nargs='?',
        default='.',
        help='Path to project directory (default: current directory)'
    )

    # inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect AST structure of a file or node (LLM-friendly)')
    inspect_parser.add_argument(
        'target',
        help='File path or node name to inspect'
    )
    inspect_parser.add_argument(
        '--format',
        choices=['json', 'table'],
        default='json',
        help='Output format (default: json)'
    )
    inspect_parser.add_argument(
        '--skeleton',
        action='store_true',
        help='Output Python skeleton instead of JSON/table'
    )
    inspect_parser.add_argument(
        '--target-function',
        help='Output full source for a specific function name in target file'
    )

    return parser


def format_output(data: Any, format_type: str = 'table') -> str:
    """データを指定形式でフォーマット"""
    if format_type == 'json':
        # Handle NaN and None values for better JSON output
        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif str(obj) == 'nan':
                return None
            else:
                return obj
        
        cleaned_data = clean_for_json(data)
        return json.dumps(cleaned_data, indent=2, ensure_ascii=False)
    elif format_type == 'table':
        return format_table(data)
    else:
        return str(data)


def format_table(data: Any) -> str:
    """データをテーブル形式でフォーマット"""
    if isinstance(data, dict):
        if 'node_counts' in data and 'edge_counts' in data:
            # Graph statistics
            lines = ["Graph Statistics:"]
            lines.append("=" * 20)
            lines.append(f"Nodes: {data['node_counts']['total']}")
            lines.append(f"  - Modules: {data['node_counts']['modules']}")
            lines.append(f"  - Functions: {data['node_counts']['functions']}")
            lines.append(f"  - Classes: {data['node_counts']['classes']}")
            lines.append(f"Edges: {data['edge_counts']['total']}")
            lines.append(f"  - Imports: {data['edge_counts']['imports']}")
            lines.append(f"  - Function Calls: {data['edge_counts']['function_calls']}")
            lines.append(f"  - Inheritance: {data['edge_counts']['inheritance']}")
            lines.append(f"Density: {data['graph_metrics']['density']}")
            lines.append(f"Total Lines of Code: {data['graph_metrics']['total_lines_of_code']}")
            lines.append(f"Average Complexity: {data['graph_metrics']['average_complexity']}")
            return '\n'.join(lines)
        else:
            # Generic dict formatting
            lines = []
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            return '\n'.join(lines)
    elif isinstance(data, list):
        if not data:
            return "No results found"
        elif isinstance(data[0], list):
            # Cycles or paths
            lines = []
            for i, item in enumerate(data, 1):
                lines.append(f"{i}. {' -> '.join(item)}")
            return '\n'.join(lines)
        else:
            # Simple list
            return '\n'.join(str(item) for item in data)
    else:
        return str(data)


def cmd_analyze(args: argparse.Namespace, config: Config) -> int:
    """analyze コマンドの実行"""
    try:
        print(f"Analyzing project: {args.project_path}")
        
        # Initialize core
        core = PyDepGraphCore(config)
        
        # Run analysis
        result = core.analyze_project(args.project_path)
        
        if args.output == 'json':
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"Analysis completed successfully!")
            print(f"Modules found: {len(result.modules)}")
            print(f"Functions found: {len(result.functions)}")
            print(f"Classes found: {len(result.classes)}")
            print(f"Import relationships: {len(result.module_imports)}")
            print(f"Function calls: {len(result.function_calls)}")
        
        return 0
        
    except PyDepGraphError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_query(args: argparse.Namespace, config: Config) -> int:
    """query コマンドの実行"""
    try:
        if args.query_type == 'context':
            if not args.target:
                print("Error: --target is required for context query", file=sys.stderr)
                return 1
            from .inspect import render_context
            output = render_context(
                target=args.target,
                depth=getattr(args, 'depth', 1),
                project_root=getattr(args, 'project_root', None),
            )
            print(output)
            return 0

        # Initialize database and services
        database = GraphDatabase(config.database.path)
        query_service = ExtendedQueryService(database)

        results = []

        if args.query_type == 'modules':
            results = query_service.get_all_modules()
        elif args.query_type == 'functions':
            results = query_service.get_all_functions()
        elif args.query_type == 'classes':
            results = query_service.get_all_classes()
        elif args.query_type == 'imports':
            results = query_service.get_all_module_imports()
        elif args.query_type == 'calls':
            results = query_service.get_all_function_calls()
        elif args.query_type == 'role':
            role_value = getattr(args, 'value', None)
            if not role_value:
                print("Error: --value is required for role query", file=sys.stderr)
                return 1
            results = query_service.find_modules_by_role(role_value)

        if args.filter:
            # Apply simple name filtering
            if results and (hasattr(results[0], 'name') or (isinstance(results[0], dict) and 'name' in results[0])):
                results = [r for r in results if args.filter.lower() in (r.name if hasattr(r, 'name') else r['name']).lower()]

        output_data = [r.to_dict() if hasattr(r, 'to_dict') else (r if isinstance(r, dict) else r.__dict__) for r in results]
        print(format_output(output_data, args.format))

        return 0

    except PyDepGraphError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_analytics(args: argparse.Namespace, config: Config) -> int:
    """analytics コマンドの実行"""
    try:
        # Initialize database and analytics service
        database = GraphDatabase(config.database.path)
        analytics_service = GraphAnalyticsService(database)
        
        if args.analysis_type == 'stats':
            result = analytics_service.get_graph_statistics()
        elif args.analysis_type == 'cycles':
            result = analytics_service.detect_circular_dependencies(args.node_type)
        elif args.analysis_type == 'importance':
            result = analytics_service.calculate_importance_scores(args.node_type)
        elif args.analysis_type == 'depth':
            if not args.root:
                print("Error: --root is required for depth analysis", file=sys.stderr)
                return 1
            result = analytics_service.analyze_dependency_depth(args.root, args.node_type)
        
        print(format_output(result, args.format))
        return 0
        
    except PyDepGraphError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_report(args: argparse.Namespace, config: Config) -> int:
    """report コマンドの実行"""
    try:
        # Initialize services
        database = GraphDatabase(config.database.path)
        analytics_service = GraphAnalyticsService(database)
        query_service = ExtendedQueryService(database)

        # Generate comprehensive report
        stats = analytics_service.get_graph_statistics()
        cycles = analytics_service.detect_circular_dependencies()
        importance = analytics_service.calculate_importance_scores()

        report_data = {
            "summary": stats,
            "circular_dependencies": cycles,
            "important_modules": dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10])
        }

        # Handle --metrics flag
        if getattr(args, 'metrics', False):
            metrics = analytics_service.get_all_metrics()
            sort_key = getattr(args, 'sort_by', None)
            if sort_key:
                metrics = sorted(metrics, key=lambda m: m.get(sort_key, 0), reverse=True)
            report_data["metrics"] = metrics

        if args.format == 'json':
            output = json.dumps(report_data, indent=2, ensure_ascii=False)
        elif args.format == 'markdown':
            output = generate_markdown_report(report_data)
        elif args.format == 'table':
            output = _format_report_table(report_data)
        else:
            output = format_output(report_data, 'table')

        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Report saved to {args.output_file}")
        else:
            print(output)

        return 0

    except PyDepGraphError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def _format_report_table(report_data: Dict[str, Any]) -> str:
    """レポートデータをテーブル形式でフォーマット"""
    lines = []

    # Summary section
    summary = report_data.get("summary", {})
    if summary:
        node_counts = summary.get("node_counts", {})
        edge_counts = summary.get("edge_counts", {})
        graph_metrics = summary.get("graph_metrics", {})
        lines.append("Graph Summary")
        lines.append("=" * 40)
        lines.append(f"Total Nodes: {node_counts.get('total', 0)}")
        lines.append(f"Total Edges: {edge_counts.get('total', 0)}")
        lines.append(f"Density: {graph_metrics.get('density', 0)}")
        lines.append(f"Total LOC: {graph_metrics.get('total_lines_of_code', 0)}")
        lines.append("")

    # Metrics section
    metrics = report_data.get("metrics")
    if metrics:
        lines.append("Module Metrics & Centrality")
        lines.append("=" * 40)
        headers = list(metrics[0].keys())
        header_line = "  ".join(f"{h:>12}" for h in headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))
        for row in metrics:
            values = []
            for h in headers:
                val = row.get(h, "")
                if isinstance(val, float):
                    values.append(f"{val:>12.4f}")
                else:
                    values.append(f"{str(val):>12}")
            lines.append("  ".join(values))
        lines.append("")

    return "\n".join(lines)


def generate_markdown_report(data: Dict[str, Any]) -> str:
    """Markdownレポートを生成"""
    lines = [
        "# PyDepGraph Analysis Report",
        "",
        "## Summary",
        "",
        f"- Total Nodes: {data['summary']['node_counts']['total']}",
        f"- Total Edges: {data['summary']['edge_counts']['total']}",
        f"- Graph Density: {data['summary']['graph_metrics']['density']}",
        f"- Total Lines of Code: {data['summary']['graph_metrics']['total_lines_of_code']}",
        "",
        "## Circular Dependencies",
        "",
    ]
    
    if data['circular_dependencies']:
        for i, cycle in enumerate(data['circular_dependencies'], 1):
            lines.append(f"{i}. {' → '.join(cycle)}")
    else:
        lines.append("No circular dependencies found.")
    
    lines.extend([
        "",
        "## Top 10 Important Modules",
        "",
    ])
    
    for module, score in data['important_modules'].items():
        lines.append(f"- {module}: {score:.4f}")
    
    return '\n'.join(lines)


def cmd_evolution(args: argparse.Namespace, config: Config) -> int:
    """evolution コマンドの実行"""
    try:
        project_path = getattr(args, 'project_path', '.')
        from_ref = args.from_ref
        to_ref = args.to_ref

        manager = SnapshotManager(project_path)

        # Load snapshots for each reference
        result_before = manager.load_snapshot(from_ref)
        result_after = manager.load_snapshot(to_ref)

        # Compare the two snapshots
        comparator = GraphComparator()
        comparison = comparator.compare(result_before, result_after)

        # Print evolution report
        reporter = EvolutionReporter(comparison, ref_from=from_ref, ref_to=to_ref)
        reporter.print_report()

        return 0

    except PyDepGraphError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_inspect(args: argparse.Namespace, config: Config) -> int:
    """inspect コマンドの実行 - LLMフレンドリーなAST構造要約"""
    try:
        from .inspect import inspect_target, render_skeleton, render_target_function

        if getattr(args, 'target_function', None):
            print(render_target_function(args.target, args.target_function))
            return 0

        if getattr(args, 'skeleton', False):
            print(render_skeleton(args.target))
            return 0

        result = inspect_target(args.target)

        output_format = getattr(args, 'format', 'json')
        if output_format == 'json':
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # table format
            for item in result.get("definitions", []):
                kind = item.get("type", "")
                name = item.get("name", "")
                sig = item.get("signature", "")
                print(f"[{kind}] {name}: {sig}")

        return 0

    except PyDepGraphError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """メイン関数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    setup_logging(args.verbose)
    
    try:
        # Load configuration
        config = Config.load_from_file(args.config)
        
        # Execute command
        if args.command == 'analyze':
            return cmd_analyze(args, config)
        elif args.command == 'query':
            return cmd_query(args, config)
        elif args.command == 'analytics':
            return cmd_analytics(args, config)
        elif args.command == 'report':
            return cmd_report(args, config)
        elif args.command == 'evolution':
            return cmd_evolution(args, config)
        elif args.command == 'inspect':
            return cmd_inspect(args, config)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.verbose >= 2:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
