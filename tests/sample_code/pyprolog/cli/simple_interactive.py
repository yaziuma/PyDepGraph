#!/usr/bin/env python3
"""
Simple Interactive Prolog CLI
シンプルな対話型Prologシステム
"""

import os
import sys
from typing import List, Optional, Any, Dict # Added Any, Dict

from colorama import Fore, Style, init

from pyprolog.parser.parser import Parser # Not strictly needed here anymore
from pyprolog.parser.scanner import Scanner # Not strictly needed here anymore
from pyprolog.core.types import Variable, Term, Atom, Number # Added Term, Atom, Number
from pyprolog.core.errors import InterpreterError, ScannerError, PrologError
from pyprolog.runtime.interpreter import Runtime
from pyprolog.util.variable_mapper import VariableMapper # Added VariableMapper

# カラー初期化
init(autoreset=True)


class SimplePrologInteractive:
    """シンプルな対話型Prologシステム"""

    def __init__(self):
        self.runtime: Optional[Runtime] = None
        self.variable_mapper = VariableMapper() # Added VariableMapper instance
        self.session_history: List[str] = [] # Consider changing to List[Dict[str, Any]] like enhanced REPL if more info is stored
        self.current_rules_file: Optional[str] = None

        print(self._get_welcome_message())

    def _get_welcome_message(self) -> str:
        """ウェルカムメッセージを取得"""
        return f"""{Fore.CYAN}
╔════════════════════════════════════════════════════════════╗
║                  PyProlog 対話型システム                    ║
║                     Simple Interactive                    ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.GREEN}使用方法:{Style.RESET_ALL}
  • Prologクエリを入力してください（例: likes(mary, X).）
  • {Fore.YELLOW}:help{Style.RESET_ALL} でコマンド一覧を表示
  • {Fore.YELLOW}:load <ファイル>{Style.RESET_ALL} でPrologファイルを読み込み
  • {Fore.YELLOW}:quit{Style.RESET_ALL} で終了

{Fore.BLUE}コマンド例:{Style.RESET_ALL}
  :load sample_usage/family.pl  # ファイル読み込み
  parent(X, Y).                 # クエリ実行
  :show_rules                   # 現在のルール表示
"""

    def _get_help_message(self) -> str:
        """ヘルプメッセージを取得"""
        return f"""{Fore.CYAN}━━━ PyProlog コマンド一覧 ━━━{Style.RESET_ALL}

{Fore.YELLOW}ファイル操作:{Style.RESET_ALL}
  :load <ファイル>     - Prologファイルを読み込み
  :reload             - 現在のファイルを再読み込み

{Fore.YELLOW}システム操作:{Style.RESET_ALL}
  :show_rules         - 現在読み込まれているルールを表示
  :clear              - 現在のルールをクリア
  :status             - システム状態を表示

{Fore.YELLOW}REPL制御:{Style.RESET_ALL}
  :help               - このヘルプを表示
  :quit, :exit        - システムを終了

{Fore.YELLOW}Prolog述語例:{Style.RESET_ALL}
  member(X, [1,2,3]).        - リストのメンバーチェック
  append([1,2], [3,4], L).   - リスト結合
  X is 2 + 3.                - 算術評価
  likes(mary, X).            - 基本的なクエリ

{Fore.GREEN}ヒント:{Style.RESET_ALL} ↑↓キーで前の入力を再利用
"""

    def _format_success(self, text: str) -> str:
        """成功メッセージのフォーマット"""
        return f"{Fore.GREEN}{text}{Style.RESET_ALL}"

    def _format_error(self, text: str) -> str:
        """エラーメッセージのフォーマット"""
        return f"{Fore.RED}{text}{Style.RESET_ALL}"

    def _format_warning(self, text: str) -> str:
        """警告メッセージのフォーマット"""
        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"

    def _format_info(self, text: str) -> str:
        """情報メッセージのフォーマット"""
        return f"{Fore.BLUE}{text}{Style.RESET_ALL}"

    def _init_runtime(self, rules_file: Optional[str] = None) -> bool:
        """ランタイムを初期化"""
        try:
            if rules_file and os.path.exists(rules_file):
                # ファイルからルールを読み込み
                with open(rules_file, "r", encoding="utf-8") as f:
                    rules_text = f.read()

                parsed_rules = Parser(Scanner(rules_text).scan_tokens())._parse_rule()

                # Similar to enhanced REPL, using Runtime's own parsing capabilities is preferred.
                # For now, direct parsing with the passed mapper.
                temp_scanner = Scanner(rules_text, variable_mapper=self.variable_mapper)
                temp_parser = Parser(temp_scanner.scan_tokens(), variable_mapper=self.variable_mapper)
                parsed_items = temp_parser.parse()

                rules_list = [item for item in parsed_items if item is not None]
                self.runtime = Runtime(rules_list, variable_mapper=self.variable_mapper) # Pass variable_mapper

                self.current_rules_file = rules_file
                if not rules_list:
                    print(self._format_warning(f"ファイル '{rules_file}' からルールを読み込めませんでした、または空です。"))
                else:
                    print(self._format_success(f"ファイル '{rules_file}' のルールでランタイムを初期化しました。"))
                return True
            else:
                # 空のランタイムを作成
                self.runtime = Runtime([], variable_mapper=self.variable_mapper) # Pass variable_mapper
                print(self._format_info("空のランタイムを初期化しました"))
                return True

        except Exception as e:
            print(self._format_error(f"ランタイム初期化エラー: {e}"))
            return False

    def _handle_command(self, command: str) -> bool:
        """コマンドを処理（True=継続、False=終了）"""
        parts = command.strip().split()
        cmd = parts[0].lower()

        if cmd in [":quit", ":exit"]:
            return False

        elif cmd == ":help":
            print(self._get_help_message())

        elif cmd == ":load":
            if len(parts) < 2:
                print(self._format_error("使用法: :load <ファイルパス>"))
                return True

            file_path = parts[1]
            if not os.path.exists(file_path):
                print(self._format_error(f"ファイル '{file_path}' が見つかりません"))
                return True

            self._init_runtime(file_path)

        elif cmd == ":reload":
            if self.current_rules_file:
                self._init_runtime(self.current_rules_file)
            else:
                print(self._format_warning("再読み込みするファイルがありません"))

        elif cmd == ":show_rules":
            if self.runtime and self.runtime.rules:
                print(
                    self._format_info(f"現在のルール ({len(self.runtime.rules)} 件):")
                )
                for i, rule in enumerate(self.runtime.rules, 1):
                    print(f"  {i:2d}. {rule}")
            else:
                print(self._format_warning("ルールが読み込まれていません"))

        elif cmd == ":clear":
            self.runtime = Runtime([], variable_mapper=self.variable_mapper) # Pass variable_mapper
            self.variable_mapper.clear_mapping() # Clear mapper state
            self.current_rules_file = None
            print(self._format_success("ルールと変数マッピングをクリアしました"))

        elif cmd == ":status":
            self._show_status()

        else:
            print(self._format_error(f"不明なコマンド: {cmd}"))
            print("':help' でコマンド一覧を確認してください")

        return True

    def _show_status(self):
        """システム状態を表示"""
        print(f"{Fore.CYAN}━━━ システム状態 ━━━{Style.RESET_ALL}")
        print(f"現在のファイル: {self.current_rules_file or '(なし)'}")
        print(f"読み込み済みルール数: {len(self.runtime.rules) if self.runtime else 0}")
        print(f"実行済みクエリ数: {len(self.session_history)}")
        print(f"ランタイム状態: {'初期化済み' if self.runtime else '未初期化'}")

    def _format_term_for_display(self, term: Any) -> str:
        if isinstance(term, Variable):
            return term.name # Already Japanese name
        elif isinstance(term, Term):
            arg_strs = [self._format_term_for_display(arg) for arg in term.args]
            functor_display = term.functor.name if isinstance(term.functor, Atom) else str(term.functor)
            if isinstance(term.functor, Variable):
                 functor_display = term.functor.name # Already Japanese name

            if not arg_strs:
                return functor_display
            else:
                return f"{functor_display}({', '.join(arg_strs)})"
        elif isinstance(term, list): # Prolog list representation (from findall or direct)
            if not term: # Empty Python list or empty Prolog list Atom('[]')
                return "[]"

            # Handle Term('.', ...) structure for Prolog lists
            if isinstance(term, Term) and term.functor.name == '.' and len(term.args) == 2:
                elements_str = []
                current = term
                while isinstance(current, Term) and current.functor.name == '.' and len(current.args) == 2:
                    elements_str.append(self._format_term_for_display(current.args[0]))
                    current = current.args[1]

                if isinstance(current, Atom) and current.name == "[]": # Proper list
                    return f"[{', '.join(elements_str)}]"
                else: # Improper list
                    if elements_str:
                         return f"[{', '.join(elements_str)} | {self._format_term_for_display(current)}]"
                    else: # Should not happen with initial Term('.',...)
                        return str(term)
            elif isinstance(term, Atom) and term.name == "[]": # Empty Prolog list Atom
                return "[]"
            # If term is a Python list (e.g. from findall)
            elif isinstance(term, list) and not isinstance(term, Term):
                 return f"[{', '.join(self._format_term_for_display(item) for item in term)}]"
            return str(term) # Fallback
        else: # Atom, Number, String
            return str(term)

    def _display_query_results(self, solutions: List[Dict[Variable, Any]]): # Type hint for solutions
        """クエリ結果を表示"""
        if not solutions:
            print(self._format_warning("解が見つかりませんでした"))
            return

        print(self._format_success(f"{len(solutions)} 件の解が見つかりました:"))

        for i, solution_dict in enumerate(solutions, 1):
            if solution_dict:
                bindings = []
                for var_obj, value in solution_dict.items():
                    # var_obj.name should be Japanese here
                    bindings.append(f"{var_obj.name} = {self._format_term_for_display(value)}")
                if bindings:
                    print(f"  {i:2d}. {', '.join(bindings)}")
                else: # No variables in query, but it's true
                    print(f"  {i:2d}. true")
            else: # Query was false
                  # This depends on how Runtime.query signals "false".
                  # If it's an empty list, the top check handles it.
                  # If it's a list containing None or an empty dict for false, this is needed.
                  # For now, assume empty dict in list means "true", and truly no solution is empty list.
                  # If solution_dict can be None or some other signal for "false":
                print(f"  {i:2d}. false")


    def _execute_query(self, query_text: str):
        """クエリを実行"""
        if not self.runtime:
            self._init_runtime() # Will use self.variable_mapper

        try:
            self.session_history.append(query_text) # Simple history, just the query string

            solutions = []
            if self.runtime is not None:
                # queryメソッドを使用, it handles parsing with variable_mapper
                solutions = self.runtime.query(query_text)

                # 結果表示
                self._display_query_results(solutions)
            else:
                print(self._format_error("ランタイムが初期化されていません"))

        except PrologError as e: # Catch specific Prolog errors
            error_msg = f"Prologエラー: {str(e)}"
            print(self._format_error(error_msg))
        except (InterpreterError, ScannerError) as e: # Catch other known errors
            error_msg = f"実行/スキャンエラー: {str(e)}"
            error_msg = f"Prologエラー: {str(e)}"
            print(self._format_error(error_msg))

        except Exception as e:
            error_msg = f"システムエラー: {str(e)}"
            print(self._format_error(error_msg))

    def run(self):
        """メインのREPLループを実行"""
        try:
            while True:
                try:
                    # プロンプト表示と入力受付
                    user_input = input("Prolog> ").strip()

                    # 空入力をスキップ
                    if not user_input:
                        continue

                    # コマンド処理
                    if user_input.startswith(":"):
                        if not self._handle_command(user_input):
                            break  # 終了コマンド
                    else:
                        # Prologクエリとして実行
                        self._execute_query(user_input)

                except KeyboardInterrupt:
                    print(f"\n{self._format_warning('割り込まれました (Ctrl+C)')}")
                    print("':quit' で終了、':help' でヘルプを表示")

        except KeyboardInterrupt:
            pass  # 外側のキャッチ

        finally:
            print(f"\n{self._format_info('PyProlog セッションを終了します')}")
            if self.session_history:
                print(f"実行されたクエリ数: {len(self.session_history)}")


def main():
    """メイン関数"""
    try:
        repl = SimplePrologInteractive()
        repl.run()
    except Exception as e:
        print(f"{Fore.RED}システム初期化エラー: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
