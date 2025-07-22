from typing import Dict, Optional, TYPE_CHECKING

# from prolog.core.types import Variable, Term, Atom, Number, String, PrologType
# 上記のフルインポートは循環参照のリスクがあるため、型ヒントでは文字列リテラルを使用
# from typing import TYPE_CHECKING # この行は Union を追加した行と重複するため削除

if TYPE_CHECKING:
    from pyprolog.core.types import PrologType, Variable


class BindingEnvironment:
    def __init__(self, parent: Optional["BindingEnvironment"] = None):
        self.bindings: Dict[str, "PrologType"] = {}
        self.parent: Optional["BindingEnvironment"] = parent

    def bind(self, var_name: str, value: "PrologType"):
        """変数を値に束縛する"""
        # Prologでは再束縛は通常単一化の失敗として扱われる。
        # ここでは単純に上書きするが、単一化ロジックで矛盾をチェックする。
        # 既に束縛されていて、異なる値に束縛しようとした場合は、
        # unify ロジック側で失敗として扱われるべき。
        # ここでチェックを入れると、unify のロジックと重複する可能性がある。
        # 例えば、X=Y, X=a. の場合、Yもaに束縛される。
        # unify(X,Y) -> env1 (X -> Y)
        # unify(X,a) in env1 -> deref(X)=Y, deref(a)=a. unify(Y,a) -> env2 (X->Y, Y->a)
        # この bind は、dereference 後の変数に対する束縛に使われる。
        self.bindings[var_name] = value

    def get_value(self, var_name: str) -> Optional["PrologType"]:
        """変数の値を取得する。見つからなければNoneを返す"""
        if var_name in self.bindings:
            return self.bindings[var_name]
        if self.parent:
            return self.parent.get_value(var_name)
        return None

    def is_unbound(self, var_name: str) -> bool:
        """Checks if a variable is unbound in the current environment and its parents."""
        return self.get_value(var_name) is None

    def copy(self) -> "BindingEnvironment":
        """環境のシャローコピーを作成する"""
        # 親環境は共有し、現在のレベルの束縛のみをコピーする
        new_env = BindingEnvironment(self.parent)
        new_env.bindings = self.bindings.copy()  # 現在の束縛をコピー
        return new_env

    def __repr__(self) -> str:
        items = []
        env: Optional[BindingEnvironment] = self
        level = 0
        while env:
            level_items = []
            for k, v in env.bindings.items():
                # 変数自身への束縛は表示しない (例: X=X)
                if (
                    isinstance(v, Variable) and v.name == k
                ):  # Variable型をインポートする必要がある
                    continue
                level_items.append(f"{k}: {v}")
            if level_items:
                items.append(f"L{level}: {{{', '.join(level_items)}}}")
            env = env.parent
            level += 1
        return "Env(" + "; ".join(items) + ")"

    def unify(self, term1, term2):
        """
        簡単な単一化メソッド（merge_bindings.py との互換性のため）
        """
        # Variable オブジェクトの場合
        if isinstance(term1, Variable):
            try:
                self.bind(term1.name, term2)
                return True
            except Exception:
                return False
        elif isinstance(term2, Variable):
            try:
                self.bind(term2.name, term1)
                return True
            except Exception:
                return False

        # 文字列キー（変数名）の場合
        elif isinstance(term1, str):
            try:
                self.bind(term1, term2)
                return True
            except Exception:
                return False
        elif isinstance(term2, str):
            try:
                self.bind(term2, term1)
                return True
            except Exception:
                return False

        # PrologType同士の場合は等価性チェック
        elif term1 == term2:
            return True

        else:
            return False

    def merge_with(self, other):
        """
        他の環境またはバインディング辞書とマージ

        Args:
            other: マージする対象（BindingEnvironmentまたはdict）

        Returns:
            BindingEnvironment: マージされた新しい環境
        """
        merged = self.copy()

        if isinstance(other, BindingEnvironment):
            # 他の環境の束縛をコピー
            for var_name, value in other.bindings.items():
                merged.bind(var_name, value)

            # 親環境も考慮（再帰的にマージ）
            if other.parent and not merged.parent:
                merged.parent = other.parent
            elif other.parent and merged.parent:
                merged.parent = merged.parent.merge_with(other.parent)

        elif isinstance(other, dict):
            # 辞書の場合は直接束縛
            for var_name, value in other.items():
                merged.bind(var_name, value)

        return merged

    def to_dict(self):
        """
        バインディング環境を辞書に変換

        Returns:
            dict: バインディング辞書
        """
        result = {}

        # 現在の環境の束縛を取得
        # type: ignore[misc]
        for var_name, value in self.bindings.items():  # type: ignore
            # 自分自身への束縛（X -> X）は除外
            if not (isinstance(value, Variable) and value.name == var_name):
                result[var_name] = value

        # 親環境の束縛も取得（子が優先）
        if self.parent:
            parent_dict = self.parent.to_dict()
            for var_name, value in parent_dict.items():
                if var_name not in result:
                    result[var_name] = value

        return result


# __repr__ で Variable を使うため、ここでインポート (TYPE_CHECKING の外)
# unify, to_dict でも Variable を使うため、この位置で正しい
from pyprolog.core.types import Variable
