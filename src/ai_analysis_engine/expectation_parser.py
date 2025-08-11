import re
from typing import Dict, List


def _normalize_text(text: str) -> str:
    """全角読点や改行などで分割しやすいよう、末尾の空白等を整理する。"""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _split_phrases(text: str) -> List[str]:
    """日本語の読点(、)および改行で分割。空要素は除去。"""
    tokens = re.split(r"[、\n]+", text)
    return [t.strip() for t in tokens if t.strip()]


def parse_expectations(expectation_text: str) -> List[Dict]:
    """期待値の自然言語テキストを簡易ルールで構造化する。

    本サンプルは LLM を使わず、代表的な日本語表現の正規表現パターンのみ対応。
    - フレーム10では値が5であるべき
    - categoryがAの場合、値は10未満
    - フレーム1から10の合計が50であるべき
    - valueの合計は50であるべき
    戻り値は各要素が辞書のリスト。
    """
    text = _normalize_text(expectation_text)
    phrases = _split_phrases(text)

    expectations: List[Dict] = []

    # パターン1: フレームXでは値がYであるべき
    p_frame_equals = re.compile(r"フレーム(?P<frame>\d+)では?値が(?P<value>-?\d+(?:\.\d+)?)であるべき")

    # パターン2: {col}が{val}の場合、値は{num}{比較語}
    # 例) categoryがAの場合、値は10未満 / 10以下 / 10以上
    p_conditional = re.compile(
        r"(?P<column>[A-Za-z0-9_ぁ-んァ-ヶ一-龠]+)が(?P<category>[^ 、。]+)の場合、?値は(?P<number>-?\d+(?:\.\d+)?)(?P<compare>未満|以下|以上)"
    )

    # パターン3: フレームSからEの合計がVであるべき
    p_sum_range = re.compile(
        r"フレーム(?P<start>\d+)から(?P<end>\d+)の合計が?(?P<value>-?\d+(?:\.\d+)?)であるべき"
    )

    # パターン4: 列Xの合計はYであるべき
    p_sum_col = re.compile(r"(?P<column>[A-Za-z0-9_ぁ-んァ-ヶ一-龠]+)の合計は(?P<value>-?\d+(?:\.\d+)?)であるべき")

    for phrase in phrases:
        m1 = p_frame_equals.fullmatch(phrase)
        if m1:
            expectations.append(
                {
                    "type": "equals_at_frame",
                    "frame": int(m1.group("frame")),
                    "expected_value": float(m1.group("value")),
                }
            )
            continue

        m2 = p_conditional.fullmatch(phrase)
        if m2:
            compare_word = m2.group("compare")
            if compare_word == "未満":
                comparator = "<"
            elif compare_word == "以下":
                comparator = "<="
            else:
                comparator = ">="

            expectations.append(
                {
                    "type": "conditional_constraint",
                    "condition_column": m2.group("column"),
                    "condition_value": m2.group("category"),
                    "comparator": comparator,
                    "threshold": float(m2.group("number")),
                }
            )
            continue

        m3 = p_sum_range.fullmatch(phrase)
        if m3:
            expectations.append(
                {
                    "type": "sum_range",
                    "range_start": int(m3.group("start")),
                    "range_end": int(m3.group("end")),
                    "column": "value",
                    "expected_sum": float(m3.group("value")),
                }
            )
            continue

        m4 = p_sum_col.fullmatch(phrase)
        if m4:
            expectations.append(
                {
                    "type": "sum_column",
                    "column": m4.group("column"),
                    "expected_sum": float(m4.group("value")),
                }
            )
            continue

        # 未対応は補助情報として生の文を残す
        expectations.append({"type": "raw", "text": phrase})

    return expectations


