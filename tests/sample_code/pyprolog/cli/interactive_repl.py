#!/usr/bin/env python3
"""
Enhanced interactive REPL for PyProlog
対話型Prologインタープリター - 拡張版
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# coloramaは既存REPLで使用されているのでそのまま使用
from colorama import Fore, Style, init

from pyprolog.parser.parser import Parser # Not strictly needed here anymore for _execute_query
from pyprolog.parser.scanner import Scanner # Not strictly needed here anymore for _execute_query
from pyprolog.core.types import Variable, Term, Atom, Number # Added Term, Atom, Number
from pyprolog.core.errors import InterpreterError, ScannerError, PrologError
from pyprolog.parser.types import FALSE # Potentially unused after changes
from pyprolog.runtime.interpreter import Runtime
from pyprolog.util.variable_mapper import VariableMapper # Added VariableMapper
from pyprolog.core.binding_environment import BindingEnvironment # Potentially unused after changes

# カラー初期化
init(autoreset=True)


class InteractiveProlog:
    """拡張された対話型Prologシステム"""

    def __init__(self):
        self.runtime: Optional[Runtime] = None
        self.variable_mapper = VariableMapper() # Added VariableMapper instance
        self.session_history: List[Dict[str, Any]] = []
        self.home_path = str(Path.home())
        self.session_start_time = datetime.now()
        self.current_rules_file: Optional[str] = None

        print(self._get_welcome_message())

    def _get_welcome_message(self) -> str:
        """ウェルカムメッセージを取得"""
        return f"""{Fore.CYAN}
╔════════════════════════════════════════════════════════════╗
║                  PyProlog 対話型システム                    ║
║                     Enhanced REPL v1.0                    ║
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
  :save_session       - セッション履歴を保存

{Fore.YELLOW}システム操作:{Style.RESET_ALL}
  :show_rules         - 現在読み込まれているルールを表示
  :clear              - 現在のルールをクリア
  :status             - システム状態を表示
  :debug_on/off       - デバッグモードの切り替え

{Fore.YELLOW}REPL制御:{Style.RESET_ALL}
  :help               - このヘルプを表示
  :quit, :exit        - システムを終了

{Fore.YELLOW}Prolog述語例:{Style.RESET_ALL}
  member(X, [1,2,3]).        - リストのメンバーチェック
  append([1,2], [3,4], L).   - リスト結合
  X is 2 + 3.                - 算術評価
  findall(X, goal(X), List). - 解の収集

{Fore.GREEN}ヒント:{Style.RESET_ALL} タブキーで自動補完、↑↓で履歴移動
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

                rules = Parser(Scanner(rules_text).scan_tokens())._parse_rule()
                # _parse_ruleが単一のルールを返す場合はリストに変換
                # This parsing logic for rules might need adjustment if _parse_rule is not suitable for full file parsing.
                # Assuming Runtime's consult or add_rule will be used instead for robust file handling.
                # For now, this direct parsing is kept, but Runtime should handle it via its variable_mapper.
                rules_text_for_scanner = rules_text # Use original rules_text for scanner
                # Scanner and Parser in _init_runtime should ideally also use self.variable_mapper
                # However, Runtime() itself will create its own Scanner/Parser with the mapper.
                # The ideal way is: self.runtime = Runtime(variable_mapper=self.variable_mapper); self.runtime.consult(rules_file)
                # For now, sticking to minimal changes as per specific instructions for VariableMapper propagation.
                temp_scanner = Scanner(rules_text_for_scanner, variable_mapper=self.variable_mapper)
                temp_parser = Parser(temp_scanner.scan_tokens(), variable_mapper=self.variable_mapper)
                parsed_items = temp_parser.parse() # parse() returns a list of rules/facts

                rules_list = [item for item in parsed_items if item is not None]
                self.runtime = Runtime(rules_list, variable_mapper=self.variable_mapper) # Pass variable_mapper

                self.current_rules_file = rules_file
                # If consult is used, it would print its own messages.
                # print(self._format_success(f"ファイル '{rules_file}' を読み込みました")) # This might be redundant if consult is used
                # For now, let's assume the above direct rule loading is intended to stay.
                # If Runtime.consult was used, the message would be handled by it.
                # To avoid double messages if consult is implemented later with its own prints:
                if not rules_list: # If parsing resulted in no rules, it's likely an issue or empty file.
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

        elif cmd == ":save_session":
            self._save_session()

        elif cmd in [":debug_on", ":debug_off"]:
            debug_state = "ON" if cmd == ":debug_on" else "OFF"
            print(self._format_info(f"デバッグモード: {debug_state}"))
            # TODO: 実際のデバッグ制御を実装

        else:
            print(self._format_error(f"不明なコマンド: {cmd}"))
            print("':help' でコマンド一覧を確認してください")

        return True

    def _show_status(self):
        """システム状態を表示"""
        print(f"{Fore.CYAN}━━━ システム状態 ━━━{Style.RESET_ALL}")
        print(
            f"セッション開始時刻: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"現在のファイル: {self.current_rules_file or '(なし)'}")
        print(f"読み込み済みルール数: {len(self.runtime.rules) if self.runtime else 0}")
        print(f"実行済みクエリ数: {len(self.session_history)}")
        print(f"ランタイム状態: {'初期化済み' if self.runtime else '未初期化'}")

    def _save_session(self):
        """セッション履歴を保存"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prolog_session_{timestamp}.json"

            session_data = {
                "start_time": self.session_start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "rules_file": self.current_rules_file,
                "history": self.session_history,
            }

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            print(self._format_success(f"セッションを '{filename}' に保存しました"))

        except Exception as e:
            print(self._format_error(f"セッション保存エラー: {e}"))

    def _display_query_results(self, goal, solutions: List):
        """クエリ結果を表示"""
        if not solutions:
            print(self._format_warning("解が見つかりませんでした"))
            return

        print(self._format_success(f"{len(solutions)} 件の解が見つかりました:"))

        # solutions is List[Dict[Variable, Any]] where Variable keys are Japanese names
        # and values are terms with Japanese variable names.
        for i, solution_dict in enumerate(solutions, 1):
            if solution_dict:  # 解がある場合
                bindings = []
                # solution_dict のキーは日本語名に変換済みの Variable オブジェクト
                for var_obj, value in solution_dict.items():
                    bindings.append(f"{var_obj.name} = {self._format_term_for_display(value)}")
                if bindings:
                    print(f"  {i:2d}. {', '.join(bindings)}")
                else:  # 変数がないクエリ (例: true.)
                    print(f"  {i:2d}. true")
            else:  # 解なし (例: fail.)
                # This case might be covered by the initial "解が見つかりませんでした"
                # or Runtime.query might return an empty list for fail, not list of empty dicts.
                # Assuming Runtime.query returns list of dicts, and empty dict means "true" with no bindings.
                # If solutions itself is empty, the top message handles it.
                # If solution_dict is None or truly empty (not just no vars), it's 'false' or 'true' respectively.
                # This part of the logic depends on exact output of Runtime.query for no-solution vs solution-with-no-vars
                print(f"  {i:2d}. false") # Or handle as per Runtime.query's specific output for 'fail.'

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
        elif isinstance(term, list): # Prolog list representation
            if not term:
                return "[]"
            elements_str = []
            current = term
            # This logic assumes internal list representation; might need adjustment
            # based on how lists are actually structured by the parser/runtime
            # For now, assuming it's a Python list of terms if it comes from findall etc.
            # If it's the Term('.', ...) structure, that needs specific handling.
            # The provided snippet for list formatting handles Term('.',...)
            # Let's refine it based on typical Prolog list structure from `Runtime`

            # Attempt to handle Term('.', ...) structure for Prolog lists
            # This part is a bit complex as the internal representation must be known
            # If `value_fully_dereferenced` from Runtime already converts Prolog lists to Python lists of terms,
            # then simple iteration is fine. If it's still `Term('.', ...)` then more complex.
            # The `_convert_vars_to_japanese` in Runtime suggests it handles nested Terms.
            # Assuming `term` here could be a Python list from `findall` or a Prolog list structure.

            # Let's assume `term` is a Python list if it's from `findall` results,
            # or a `Term` object if it's a direct Prolog list.
            # The original `_format_term_for_display` had a good starting point for `Term('.', ...)`
            if isinstance(term, list) and not (isinstance(term, Term)): # Python list from findall etc.
                return f"[{', '.join(self._format_term_for_display(item) for item in term)}]"

            # Handling for Term('.', ...) structure (Prolog internal list)
            # This part of the original snippet is kept and adapted:
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
                    else: # Should not happen if initial term was Term('.',...)
                        return str(term)
            elif isinstance(term, Atom) and term.name == "[]": # Empty Prolog list
                return "[]"
            # Fallback for other list-like things or complex terms not fitting above
            return str(term)
        else: # Atom, Number, String
            return str(term)

    def _execute_query(self, query_text: str):
        """クエリを実行"""
        if not self.runtime:
            # Pass self.variable_mapper when auto-initializing runtime
            self._init_runtime() # _init_runtime now uses self.variable_mapper

        try:
            # クエリ履歴に追加
            query_record = {
                "timestamp": datetime.now().isoformat(),
                "query": query_text,
                "success": False,
                "results_count": 0,
                "error": None,
            }

            # パースして実行 - Runtime.query handles parsing internally
            # goal = Parser(Scanner(query_text).scan_tokens())._parse_term() # This is no longer needed here

            solutions = []
            # クエリ実行
            if self.runtime is not None:
                # Runtime.query now handles scanning and parsing with the shared VariableMapper
                solutions = self.runtime.query(query_text)
                # query_record["results_count"] will be set based on len(solutions)

            # 結果表示
            # _display_query_results no longer needs the 'goal' argument as solutions dict has var names
            self._display_query_results(None, solutions) # Pass None for goal, or adapt _display_query_results

            # 履歴更新
            query_record["success"] = True
            query_record["results_count"] = len(solutions) if solutions else 0

        except PrologError as e: # Catch specific Prolog errors first
            error_msg = f"Prologエラー: {str(e)}"
            print(self._format_error(error_msg))
            query_record["error"] = str(e)
        except (InterpreterError, ScannerError) as e: # Catch other known interpreter/scanner errors
            error_msg = f"実行/スキャンエラー: {str(e)}"
            print(self._format_error(error_msg))
            query_record["error"] = str(e)

        except Exception as e:
            error_msg = f"システムエラー: {str(e)}"
            print(self._format_error(error_msg))
            query_record["error"] = str(e)

        finally:
            self.session_history.append(query_record)

    def run(self):
        """メインのREPLループを実行"""
        try:
            while True:
                try:
                    # シンプルなプロンプト表示と入力受付
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
        repl = InteractiveProlog()
        repl.run()
    except Exception as e:
        print(f"{Fore.RED}システム初期化エラー: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
