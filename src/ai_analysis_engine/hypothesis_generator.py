import re
from typing import Any, Dict, List


def _find_literal_return_for_frame(code_text: str, frame: int) -> float | None:
    """ソースコード内から `if frame == X: return Y` 形式の Y を探す簡易ロジック。
    実運用ではAST解析を推奨。本サンプルでは正規表現で最小限のみ対応。
    """
    pattern = re.compile(
        rf"if\s+frame\s*==\s*{frame}\s*:\s*\n\s*return\s+(-?\d+(?:\.\d+)?)",
        re.MULTILINE,
    )
    m = pattern.search(code_text)
    if m:
        return float(m.group(1))
    return None


def generate_hypothesis(analysis_results: List[Dict[str, Any]], spec_text: str, code_text: str) -> str:
    """解析結果と仕様書・コードから、素朴な仮説テキストを作る。

    LLMは使わず規則ベースで説明文を組み立てる。
    """
    if not analysis_results:
        return "異常は検出されませんでした。"

    lines: List[str] = []
    for res in analysis_results:
        if not res.get("violations"):
            continue
        rtype = res.get("type")
        if rtype == "equals_at_frame":
            # フレーム固有の戻り値をコードから拾えたら、戻り値不一致を示唆
            # 期待説明からフレーム番号を抽出
            m = re.search(r"フレーム(\d+)", res.get("expected_description", ""))
            frame = int(m.group(1)) if m else None
            literal = _find_literal_return_for_frame(code_text or "", frame) if frame is not None else None
            if literal is not None:
                lines.append(
                    f"フレーム{frame}に対する戻り値がコード内で {literal:g} と固定されている可能性があります。仕様上の期待値と不一致です。"
                )
            else:
                lines.append("フレーム固有の条件分岐または値設定が仕様と不一致の可能性があります。")
        elif rtype == "conditional_constraint":
            lines.append("カテゴリ条件の実装不足、または閾値設定が仕様と一致していない可能性があります。")
        elif rtype.startswith("sum_"):
            lines.append("合計値の算出ロジック（範囲・対象列）が誤っている可能性があります。")

    if not lines:
        return "有意な違反はありませんでした。"

    return "\n".join(lines)


