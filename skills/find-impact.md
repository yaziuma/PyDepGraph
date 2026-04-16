指定されたファイルを変更した場合の影響範囲を分析してください。

対象: $ARGUMENTS

以下を実行:

```bash
uv run pydepgraph inspect $ARGUMENTS
uv run pydepgraph query imports --format json
uv run pydepgraph query calls --format json
```

imports の結果から対象モジュールを target_module に持つ関係を抽出し、影響を受けるファイルそれぞれに `uv run pydepgraph inspect <file>` を実行してください。

以下の形式で影響分析レポートを出力:
- **変更対象**: ファイル名、公開インターフェース
- **直接影響**: このモジュールを直接 import しているモジュール一覧
- **間接影響**: 直接影響のさらに上流（2段階まで）
- **影響を受ける関数/クラス**: 具体的な名前リスト
- **リスク評価**: 影響範囲に基づく変更リスク（低/中/高）
- **推奨事項**: 変更を安全に行うための具体的なステップ
