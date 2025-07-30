# PyDepGraph Phase 4 詳細設計書
## CLI実装（Week 7-8）

## 📋 Phase 4 概要

**目標**: コマンドラインインターフェースの完成

**実装対象**:
- Click-based CLI（analyze, deps, path, cycles）
- 結果出力（JSON/YAML形式）
- 設定管理（TOML設定ファイル）
- ログ出力とユーザビリティ向上

## 🎯 CLI構造設計

### コマンド体系
```
pydepgraph
├── analyze         # プロジェクト分析実行
├── search          # 要素検索
├── deps           # 依存関係表示
├── path           # 依存パス検索
├── cycles         # 循環依存検出
├── stats          # 統計情報表示
├── config         # 設定管理
└── export         # 結果エクスポート
```

## 🔧 メインCLI実装

```python
import click
import json
import yaml
import time
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from pydepgraph.extractors import TachExtractor, Code2FlowExtractor
from pydepgraph.normalizer import DataNormalizer
from pydepgraph.database import GraphDatabase
from pydepgraph.services import QueryService, GraphAnalyticsService
from pydepgraph.config import ConfigManager
from pydepgraph.exceptions import PrologExecutionError

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# メインCLIグループ
@click.group()
@click.option('--config', '-c', type=click.Path(), help='設定ファイルパス')
@click.option('--verbose', '-v', is_flag=True, help='詳細ログ出力')
@click.option('--quiet', '-q', is_flag=True, help='エラー以外の出力を抑制')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool, quiet: bool):
    """PyDepGraph - Python依存関係分析ツール"""
    
    # ログレベル設定
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # コンテキスト初期化
    ctx.ensure_object(dict)
    
    # 設定管理初期化
    config_manager = ConfigManager(config)
    ctx.obj['config'] = config_manager
    
    # データベースパス設定
    db_path = config_manager.get('database.path', '.pydepgraph/graph.db')
    ctx.obj['db_path'] = db_path

# === analyze コマンド ===

@cli.command()
@click.argument('project_path', type=click.Path(exists=True), default='.')
@click.option('--output', '-o', type=click.Choice(['json', 'yaml']), help='結果出力形式')
@click.option('--output-file', type=click.Path(), help='出力ファイルパス')
@click.option('--include-external', is_flag=True, help='外部依存関係も含める')
@click.option('--extractors', multiple=True, type=click.Choice(['tach', 'code2flow']),
              help='使用する抽出器（複数指定可能）')
@click.option('--force', is_flag=True, help='既存データベースを強制再作成')
@click.pass_context
def analyze(ctx, project_path: str, output: Optional[str], output_file: Optional[str],
           include_external: bool, extractors: tuple, force: bool):
    """プロジェクトを分析してグラフデータベースを構築"""
    
    config = ctx.obj['config']
    db_path = ctx.obj['db_path']
    
    project_path = Path(project_path).resolve()
    
    click.echo(f"🔍 プロジェクト分析を開始: {project_path}")
    
    try:
        # データベース初期化
        database = GraphDatabase(str(db_path))
        
        if force or not Path(db_path).exists():
            click.echo("📦 データベースを初期化しています...")
            database.initialize_schema()
        
        # 抽出器設定
        available_extractors = {
            'tach': TachExtractor(),
            'code2flow': Code2FlowExtractor(),
        }
        
        if extractors:
            selected_extractors = [available_extractors[name] for name in extractors if name in available_extractors]
        else:
            # デフォルトは全て使用
            selected_extractors = list(available_extractors.values())
        
        # 分析実行
        extraction_results = []
        failed_extractors = []
        
        with click.progressbar(selected_extractors, label='抽出器実行中') as bar:
            for extractor in bar:
                try:
                    result = extractor.extract(str(project_path))
                    extraction_results.append(result)
                    click.echo(f"✅ {extractor.__class__.__name__} 完了")
                except Exception as e:
                    failed_extractors.append((extractor.__class__.__name__, str(e)))
                    click.echo(f"❌ {extractor.__class__.__name__} 失敗: {e}")
        
        if not extraction_results:
            raise click.ClickException("すべての抽出器が失敗しました")
        
        # データ統合
        click.echo("🔄 データを統合しています...")
        normalizer = DataNormalizer()
        normalized_result = normalizer.normalize_extraction_results(extraction_results)
        
        # データベース挿入
        click.echo("💾 データベースに保存しています...")
        
        if normalized_result.modules:
            database.bulk_insert_modules(normalized_result.modules)
        
        if normalized_result.functions:
            database.bulk_insert_functions(normalized_result.functions)
        
        if normalized_result.classes:
            database.bulk_insert_classes(normalized_result.classes)
        
        # 関係性挿入
        database.bulk_insert_module_imports(normalized_result.relationships)
        database.bulk_insert_function_calls(normalized_result.relationships)
        database.bulk_insert_contains(normalized_result.relationships)
        
        # 結果出力
        click.echo(f"""
✅ 分析完了!

📊 結果:
  - モジュール: {len(normalized_result.modules)}
  - 関数: {len(normalized_result.functions)}  
  - クラス: {len(normalized_result.classes)}
  - 関係性: {len(normalized_result.relationships)}
""")
        
        if failed_extractors:
            click.echo("⚠️  失敗した抽出器:")
            for name, error in failed_extractors:
                click.echo(f"  - {name}: {error}")
        
        # 結果ファイル出力
        if output:
            analytics = GraphAnalyticsService(database)
            stats = analytics.get_graph_statistics()
            
            output_data = {
                'project_path': str(project_path),
                'analysis_timestamp': time.time(),
                'statistics': stats,
                'extractors_used': [ext.__class__.__name__ for ext in selected_extractors],
                'failed_extractors': failed_extractors,
            }
            
            output_path = Path(output_file) if output_file else project_path / f"analysis_results.{output}"
            
            if output == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
            elif output == 'yaml':
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(output_data, f, default_flow_style=False, allow_unicode=True)
            
            click.echo(f"📄 分析結果を {output_path} に出力しました")
        
        database.close()
        
    except Exception as e:
        raise click.ClickException(f"分析に失敗しました: {e}")

# === search コマンド ===

@cli.command()
@click.argument('query')
@click.option('--type', '-t', type=click.Choice(['module', 'function', 'class', 'all']),
              default='all', help='検索対象の種類')
@click.option('--fuzzy', '-f', is_flag=True, help='あいまい検索を有効化')
@click.option('--regex', '-r', is_flag=True, help='正規表現検索を有効化')
@click.option('--limit', '-l', type=int, default=20, help='結果表示件数')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='出力形式')
@click.pass_context
def search(ctx, query: str, type: str, fuzzy: bool, regex: bool, limit: int, output: str):
    """要素を名前で検索"""
    
    db_path = ctx.obj['db_path']
    
    if not Path(db_path).exists():
        raise click.ClickException("データベースが見つかりません。先に 'analyze' を実行してください。")
    
    try:
        database = GraphDatabase(str(db_path))
        query_service = QueryService(database)
        
        if regex:
            result = query_service.search_by_pattern(query, type)
        else:
            result = query_service.search_by_name(query, type, fuzzy)
        
        if not result.items:
            click.echo(f"❌ '{query}' に一致する{type}が見つかりませんでした")
            return
        
        # 結果表示
        limited_items = result.items[:limit]
        
        if output == 'table':
            click.echo(f"🔍 検索結果: {len(limited_items)}/{result.total_count} 件 ({result.query_time:.3f}秒)")
            click.echo()
            
            for item in limited_items:
                click.echo(f"📄 {item['type'].upper()}: {item['name']}")
                click.echo(f"   パス: {item['path']}")
                if 'module' in item and item['module']:
                    click.echo(f"   モジュール: {item['module']}")
                if 'class_name' in item and item['class_name']:
                    click.echo(f"   クラス: {item['class_name']}")
                click.echo()
        
        elif output == 'json':
            click.echo(json.dumps({
                'query': query,
                'total_count': result.total_count,
                'query_time': result.query_time,
                'items': limited_items
            }, indent=2, ensure_ascii=False))
        
        elif output == 'yaml':
            click.echo(yaml.dump({
                'query': query,
                'total_count': result.total_count,
                'query_time': result.query_time,
                'items': limited_items
            }, default_flow_style=False, allow_unicode=True))
        
        database.close()
        
    except Exception as e:
        raise click.ClickException(f"検索に失敗しました: {e}")

# === deps コマンド ===

@cli.command()
@click.argument('target')
@click.option('--direction', '-d', type=click.Choice(['outgoing', 'incoming', 'both']),
              default='outgoing', help='依存関係の方向')
@click.option('--depth', type=int, default=1, help='検索深度')
@click.option('--type', '-t', type=click.Choice(['function', 'module']),
              default='function', help='依存関係の種類')
@click.option('--include-external', is_flag=True, help='外部依存関係も含める')
@click.option('--output', '-o', type=click.Choice(['tree', 'list', 'json']),
              default='tree', help='出力形式')
@click.pass_context
def deps(ctx, target: str, direction: str, depth: int, type: str, 
         include_external: bool, output: str):
    """依存関係を表示"""
    
    db_path = ctx.obj['db_path']
    
    if not Path(db_path).exists():
        raise click.ClickException("データベースが見つかりません。先に 'analyze' を実行してください。")
    
    try:
        database = GraphDatabase(str(db_path))
        query_service = QueryService(database)
        
        if type == 'function':
            dependencies = query_service.find_function_dependencies(target, direction, depth)
        else:
            dependencies = query_service.find_module_dependencies(target, direction, depth, include_external)
        
        if not dependencies:
            click.echo(f"❌ '{target}' の依存関係が見つかりませんでした")
            return
        
        direction_text = {'outgoing': '呼び出し先', 'incoming': '呼び出し元', 'both': '依存関係'}[direction]
        click.echo(f"📋 {target} の{direction_text} ({len(dependencies)}件):")
        click.echo()
        
        if output == 'tree':
            # 深度別にグループ化
            depth_groups = {}
            for dep in dependencies:
                d = dep.get('depth', 1)
                if d not in depth_groups:
                    depth_groups[d] = []
                depth_groups[d].append(dep)
            
            for d in sorted(depth_groups.keys()):
                if d > 1:
                    click.echo(f"  深度 {d}:")
                
                for dep in depth_groups[d]:
                    prefix = "  " + "  " * (d - 1) + "├─ "
                    if type == 'function':
                        name = dep.get('qualified_name', dep['name'])
                        if dep.get('module_name'):
                            click.echo(f"{prefix}{name} ({dep['module_name']})")
                        else:
                            click.echo(f"{prefix}{name}")
                    else:
                        click.echo(f"{prefix}{dep['file_path']}")
                        if dep.get('package'):
                            click.echo(f"      パッケージ: {dep['package']}")
        
        elif output == 'list':
            for dep in dependencies:
                if type == 'function':
                    name = dep.get('qualified_name', dep['name'])
                    click.echo(f"  → {name}")
                    if dep.get('module_name'):
                        click.echo(f"      ({dep['module_name']})")
                else:
                    click.echo(f"  → {dep['file_path']}")
        
        elif output == 'json':
            click.echo(json.dumps({
                'target': target,
                'direction': direction,
                'type': type,
                'depth': depth,
                'dependencies': dependencies
            }, indent=2, ensure_ascii=False))
        
        database.close()
        
    except Exception as e:
        raise click.ClickException(f"依存関係の取得に失敗しました: {e}")

# === path コマンド ===

@cli.command()
@click.argument('source')
@click.argument('target')
@click.option('--type', '-t', type=click.Choice(['function', 'module', 'any']),
              default='any', help='パスの種類')
@click.option('--all-paths', '-a', is_flag=True, help='全パスを表示（最短パスのみでなく）')
@click.option('--max-depth', type=int, default=5, help='最大検索深度')
@click.option('--output', '-o', type=click.Choice(['path', 'json']),
              default='path', help='出力形式')
@click.pass_context
def path(ctx, source: str, target: str, type: str, all_paths: bool, 
         max_depth: int, output: str):
    """2つの要素間の依存パスを検索"""
    
    db_path = ctx.obj['db_path']
    
    if not Path(db_path).exists():
        raise click.ClickException("データベースが見つかりません。先に 'analyze' を実行してください。")
    
    try:
        database = GraphDatabase(str(db_path))
        query_service = QueryService(database)
        
        if all_paths:
            paths = query_service.find_all_paths(source, target, max_depth, type)
            if not paths:
                click.echo(f"❌ {source} から {target} への依存パスが見つかりませんでした")
                return
            
            click.echo(f"🛤️  {source} → {target} への依存パス ({len(paths)}件):")
            click.echo()
            
            if output == 'path':
                for i, p in enumerate(paths, 1):
                    click.echo(f"パス {i} (深度: {p.depth}):")
                    for j, step in enumerate(p.path):
                        if j < len(p.path) - 1:
                            click.echo(f"  {step} →")
                        else:
                            click.echo(f"  {step}")
                    click.echo()
            else:  # json
                paths_data = [
                    {
                        'path': p.path,
                        'depth': p.depth,
                        'path_type': p.path_type,
                        'relationships': p.relationships
                    } for p in paths
                ]
                click.echo(json.dumps({
                    'source': source,
                    'target': target,
                    'paths': paths_data
                }, indent=2, ensure_ascii=False))
        
        else:
            # 最短パスのみ
            shortest_path = query_service.find_shortest_path(source, target, type)
            
            if not shortest_path:
                click.echo(f"❌ {source} から {target} への依存パスが見つかりませんでした")
                return
            
            if output == 'path':
                click.echo(f"🛤️  {source} → {target} への最短パス:")
                click.echo(f"深度: {shortest_path.depth}")
                click.echo()
                
                for i, step in enumerate(shortest_path.path):
                    if i < len(shortest_path.path) - 1:
                        click.echo(f"  {step} →")
                    else:
                        click.echo(f"  {step}")
            else:  # json
                click.echo(json.dumps({
                    'source': source,
                    'target': target,
                    'path': shortest_path.path,
                    'depth': shortest_path.depth,
                    'path_type': shortest_path.path_type,
                    'relationships': shortest_path.relationships
                }, indent=2, ensure_ascii=False))
        
        database.close()
        
    except Exception as e:
        raise click.ClickException(f"パス検索に失敗しました: {e}")

# === cycles コマンド ===

@cli.command()
@click.option('--level', '-l', type=click.Choice(['module', 'function']),
              default='module', help='検索レベル')
@click.option('--max-length', type=int, default=10, help='最大循環長')
@click.option('--output', '-o', type=click.Choice(['list', 'json']),
              default='list', help='出力形式')
@click.pass_context
def cycles(ctx, level: str, max_length: int, output: str):
    """循環依存を検出"""
    
    db_path = ctx.obj['db_path']
    
    if not Path(db_path).exists():
        raise click.ClickException("データベースが見つかりません。先に 'analyze' を実行してください。")
    
    try:
        database = GraphDatabase(str(db_path))
        analytics = GraphAnalyticsService(database)
        
        circular_deps = analytics.find_circular_dependencies(level, max_length)
        
        if not circular_deps:
            click.echo(f"✅ {level}レベルで循環依存は検出されませんでした")
            return
        
        if output == 'list':
            click.echo(f"🔄 検出された循環依存 ({len(circular_deps)}件):")
            click.echo()
            
            for i, cycle in enumerate(circular_deps, 1):
                click.echo(f"{i}. 循環長: {len(cycle)}")
                click.echo(f"   {' → '.join(cycle)} → {cycle[0]}")
                click.echo()
        
        else:  # json
            click.echo(json.dumps({
                'level': level,
                'max_length': max_length,
                'cycles': circular_deps,
                'count': len(circular_deps)
            }, indent=2, ensure_ascii=False))
        
        database.close()
        
    except Exception as e:
        raise click.ClickException(f"循環依存の検出に失敗しました: {e}")

# === stats コマンド ===

@cli.command()
@click.option('--detailed', '-d', is_flag=True, help='詳細統計を表示')
@click.option('--centrality', '-c', is_flag=True, help='中心性分析を含める')
@click.option('--output', '-o', type=click.Choice(['table', 'json']),
              default='table', help='出力形式')
@click.pass_context
def stats(ctx, detailed: bool, centrality: bool, output: str):
    """統計情報を表示"""
    
    db_path = ctx.obj['db_path']
    
    if not Path(db_path).exists():
        raise click.ClickException("データベースが見つかりません。先に 'analyze' を実行してください。")
    
    try:
        database = GraphDatabase(str(db_path))
        analytics = GraphAnalyticsService(database)
        
        # 基本統計
        basic_stats = analytics.get_graph_statistics()
        
        if output == 'table':
            click.echo("📊 プロジェクト統計:")
            click.echo()
            click.echo(f"  モジュール数:           {basic_stats['module_count']:,}")
            click.echo(f"  外部モジュール数:       {basic_stats['external_module_count']:,}")
            click.echo(f"  関数数:                 {basic_stats['function_count']:,}")
            click.echo(f"  クラス数:               {basic_stats['class_count']:,}")
            click.echo(f"  モジュール依存関係数:   {basic_stats['module_imports_count']:,}")
            click.echo(f"  関数呼び出し関係数:     {basic_stats['function_calls_count']:,}")
            click.echo()
            click.echo(f"  平均関数数/モジュール:  {basic_stats['avg_functions_per_module']:.1f}")
            click.echo(f"  平均メソッド数/クラス:  {basic_stats['avg_methods_per_class']:.1f}")
            
            if detailed:
                # アーキテクチャ分析
                violations = analytics.analyze_architecture_violations()
                if violations:
                    click.echo()
                    click.echo("⚠️  アーキテクチャ課題:")
                    for v in violations[:5]:  # 上位5件
                        severity_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(v['severity'], '⚪')
                        click.echo(f"  {severity_icon} {v['description']}")
                else:
                    click.echo()
                    click.echo("✅ アーキテクチャ違反は検出されませんでした")
            
            if centrality:
                click.echo()
                click.echo("🎯 中心性分析（上位5位）:")
                
                # 関数の中心性
                func_centrality = analytics.calculate_degree_centrality("function", "both")
                if func_centrality:
                    click.echo("  📋 重要な関数:")
                    for i, func in enumerate(func_centrality[:5], 1):
                        click.echo(f"    {i}. {func['name']} (結合度: {func['total_degree']})")
                
                # モジュールの中心性
                mod_centrality = analytics.calculate_degree_centrality("module", "both")
                if mod_centrality:
                    click.echo("  📦 重要なモジュール:")
                    for i, mod in enumerate(mod_centrality[:5], 1):
                        mod_name = Path(mod['name']).stem
                        click.echo(f"    {i}. {mod_name} (結合度: {mod['total_degree']})")
        
        else:  # json
            data = {'basic_statistics': basic_stats}
            
            if detailed:
                violations = analytics.analyze_architecture_violations()
                data['architecture_violations'] = violations
            
            if centrality:
                data['centrality'] = {
                    'functions': analytics.calculate_degree_centrality("function", "both")[:10],
                    'modules': analytics.calculate_degree_centrality("module", "both")[:10]
                }
            
            click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        
        database.close()
        
    except Exception as e:
        raise click.ClickException(f"統計情報の取得に失敗しました: {e}")

# === config コマンド ===

@cli.command()
@click.argument('action', type=click.Choice(['show', 'set', 'reset']))
@click.argument('key', required=False)
@click.argument('value', required=False)
@click.pass_context
def config(ctx, action: str, key: Optional[str], value: Optional[str]):
    """設定を管理"""
    
    config_manager = ctx.obj['config']
    
    if action == 'show':
        if key:
            # 特定のキーの値を表示
            val = config_manager.get(key)
            if val is not None:
                click.echo(f"{key} = {val}")
            else:
                click.echo(f"❌ '{key}' は設定されていません")
        else:
            # 全設定を表示
            all_config = config_manager.get_all()
            click.echo("⚙️  現在の設定:")
            click.echo()
            for k, v in all_config.items():
                click.echo(f"  {k} = {v}")
    
    elif action == 'set':
        if not key or value is None:
            raise click.ClickException("set には key と value が必要です")
        
        config_manager.set(key, value)
        click.echo(f"✅ {key} = {value} に設定しました")
    
    elif action == 'reset':
        if key:
            config_manager.reset(key)
            click.echo(f"✅ {key} をデフォルト値にリセットしました")
        else:
            config_manager.reset_all()
            click.echo("✅ 全設定をデフォルト値にリセットしました")

# === export コマンド ===

@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'yaml', 'csv', 'graphml']),
              default='json', help='出力形式')
@click.option('--output-file', '-o', type=click.Path(), required=True, help='出力ファイル')
@click.option('--include-external', is_flag=True, help='外部依存関係も含める')
@click.option('--level', type=click.Choice(['module', 'function', 'all']),
              default='all', help='エクスポートレベル')
@click.pass_context
def export(ctx, format: str, output_file: str, include_external: bool, level: str):
    """分析結果をエクスポート"""
    
    db_path = ctx.obj['db_path']
    
    if not Path(db_path).exists():
        raise click.ClickException("データベースが見つかりません。先に 'analyze' を実行してください。")
    
    try:
        database = GraphDatabase(str(db_path))
        query_service = QueryService(database)
        analytics = GraphAnalyticsService(database)
        
        # データ収集
        export_data = {
            'metadata': {
                'export_timestamp': time.time(),
                'include_external': include_external,
                'level': level
            }
        }
        
        if level in ['module', 'all']:
            modules = query_service.get_all_modules(include_external)
            export_data['modules'] = modules
        
        if level in ['function', 'all']:
            # 関数データは大きくなる可能性があるため、基本情報のみ
            functions_query = """
            MATCH (f:Function)
            RETURN f.id as id, f.name as name, f.qualified_name as qualified_name,
                   f.module_name as module_name, f.class_name as class_name,
                   f.is_method as is_method, f.is_private as is_private
            ORDER BY f.qualified_name
            """
            functions = database.execute_query(functions_query)
            export_data['functions'] = functions
        
        # 統計情報
        stats = analytics.get_graph_statistics()
        export_data['statistics'] = stats
        
        # フォーマット別出力
        output_path = Path(output_file)
        
        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        elif format == 'yaml':
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
        
        elif format == 'csv':
            # CSV形式では統計情報のみ
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Metric', 'Value'])
                for key, value in stats.items():
                    writer.writerow([key, value])
        
        elif format == 'graphml':
            # GraphML形式（将来実装）
            raise click.ClickException("GraphML形式は未実装です")
        
        click.echo(f"✅ データを {output_path} にエクスポートしました")
        
        database.close()
        
    except Exception as e:
        raise click.ClickException(f"エクスポートに失敗しました: {e}")

# === メイン実行部 ===

if __name__ == '__main__':
    cli()
```

## ⚙️ 設定管理実装

```python
# pydepgraph/config.py

import toml
import json
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """設定管理クラス"""
    
    DEFAULT_CONFIG = {
        'database': {
            'path': '.pydepgraph/graph.db',
            'connection_pool_size': 5,
            'query_timeout': 30
        },
        'extractors': {
            'tach': {
                'enabled': True,
                'timeout': 300
            },
            'code2flow': {
                'enabled': True, 
                'timeout': 600,
                'max_depth': 10
            }
        },
        'analysis': {
            'include_tests': True,
            'exclude_patterns': [
                '__pycache__/*',
                '*.pyc',
                '.git/*',
                'venv/*',
                '.venv/*',
                'node_modules/*'
            ],
            'max_depth': 100
        },
        'output': {
            'default_format': 'table',
            'max_results': 100
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = self._find_config_file(config_file)
        self.config = self._load_config()
    
    def _find_config_file(self, config_file: Optional[str]) -> Optional[Path]:
        """設定ファイルを探す"""
        
        if config_file:
            path = Path(config_file)
            if path.exists():
                return path
            else:
                logger.warning(f"指定された設定ファイルが見つかりません: {config_file}")
        
        # デフォルトの場所を検索
        search_paths = [
            Path.cwd() / 'pydepgraph.toml',
            Path.cwd() / '.pydepgraph.toml',
            Path.home() / '.pydepgraph' / 'config.toml',
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info(f"設定ファイルを発見: {path}")
                return path
        
        return None
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込み"""
        
        config = self.DEFAULT_CONFIG.copy()
        
        if self.config_file:
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = toml.load(f)
                    config = self._deep_merge(config, file_config)
                    logger.info(f"設定ファイルを読み込み: {self.config_file}")
            except Exception as e:
                logger.error(f"設定ファイルの読み込みに失敗: {e}")
        
        return config
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """辞書を再帰的にマージ"""
        
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """設定値を設定"""
        
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        # ファイルに保存
        if self.config_file:
            self._save_config()
    
    def reset(self, key: Optional[str] = None) -> None:
        """設定をリセット"""
        
        if key:
            default_value = self.get_default(key)
            if default_value is not None:
                self.set(key, default_value)
        else:
            self.config = self.DEFAULT_CONFIG.copy()
            if self.config_file:
                self._save_config()
    
    def get_default(self, key: str) -> Any:
        """デフォルト値を取得"""
        
        keys = key.split('.')
        value = self.DEFAULT_CONFIG
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """全設定を取得"""
        return self.config.copy()
    
    def _save_config(self) -> None:
        """設定をファイルに保存"""
        
        if not self.config_file:
            self.config_file = Path.cwd() / 'pydepgraph.toml'
        
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                toml.dump(self.config, f)
            logger.info(f"設定を保存: {self.config_file}")
        except Exception as e:
            logger.error(f"設定の保存に失敗: {e}")
```

## 📄 デフォルト設定ファイル

```toml
# pydepgraph.toml - PyDepGraph設定ファイル

[database]
path = ".pydepgraph/graph.db"
connection_pool_size = 5
query_timeout = 30

[extractors.tach]
enabled = true
timeout = 300

[extractors.code2flow]
enabled = true
timeout = 600
max_depth = 10

[analysis]
include_tests = true
exclude_patterns = [
    "__pycache__/*",
    "*.pyc", 
    ".git/*",
    "venv/*",
    ".venv/*",
    "node_modules/*"
]
max_depth = 100

[output]
default_format = "table"
max_results = 100
```

## 🧪 Phase 4 成功基準とテスト

### 成功基準
- [x] 全CLIコマンドが期待通りに動作する
- [x] 設定ファイルによるカスタマイズが可能
- [x] エラー時に分かりやすいメッセージを表示する

### CLIテスト例
```bash
# 基本的な動作テスト
pydepgraph analyze ./test_project
pydepgraph search "init" --type function
pydepgraph deps "MyClass.__init__" --direction outgoing
pydepgraph path "main" "helper_function" 
pydepgraph cycles --level module
pydepgraph stats --detailed --centrality
pydepgraph export --format json --output-file results.json

# 設定管理テスト
pydepgraph config show
pydepgraph config set database.path "custom.db"
pydepgraph config reset database.path

# エラーハンドリングテスト
pydepgraph analyze ./nonexistent_project  # エラーメッセージ確認
pydepgraph search ""  # 空文字列検索
```

Phase 4では、使いやすいCLIインターフェースと柔軟な設定管理機能を実装し、実用的なツールとして完成させます。