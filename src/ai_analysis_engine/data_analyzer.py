from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any

import pandas as pd


@dataclass
class AnalysisResult:
    """レポート出力しやすい構造の解析結果。"""

    title: str
    type: str
    violations: List[Dict[str, Any]]
    expected_description: str


def _format_expected_equals(frame: int, expected_value: float) -> str:
    return f"フレーム{frame}では値が{expected_value:g}であるべき"


def _format_expected_conditional(col: str, val: str, cmp_op: str, thr: float) -> str:
    jp = {"<": "未満", "<=": "以下", ">=": "以上"}.get(cmp_op, cmp_op)
    return f"{col}が{val}の場合、値は{thr:g}{jp}"


def _format_expected_sum_range(start: int, end: int, total: float) -> str:
    return f"フレーム{start}から{end}の合計が{total:g}であるべき"


def _format_expected_sum_col(column: str, total: float) -> str:
    return f"{column}の合計は{total:g}であるべき"


def analyze_data(csv_path: str, structured_expectations: List[Dict]) -> List[Dict[str, Any]]:
    """CSVデータと構造化期待値を比較し、違反行を抽出する。

    - データには少なくとも `frame`, `value` 列がある前提。
    - 条件付きは `condition_column` で絞ってから `value` 列に対する比較を行う。
    戻り値は AnalysisResult 互換の辞書のリスト。
    """
    df = pd.read_csv(csv_path)
    results: List[Dict[str, Any]] = []

    for exp in structured_expectations:
        etype = exp.get("type")
        if etype == "equals_at_frame":
            frame = int(exp["frame"])
            expected_value = float(exp["expected_value"])
            subset = df.loc[df["frame"] == frame, ["frame", "value"]].copy()
            if not subset.empty:
                subset["expected"] = expected_value
                subset["difference"] = subset["value"] - subset["expected"]
                # 差分が0でないもののみ違反として扱う
                violations = (
                    subset.loc[subset["difference"] != 0, ["frame", "value", "expected", "difference"]]
                    .to_dict(orient="records")
                )
            else:
                # フレームが存在しない場合も違反として記録
                violations = [
                    {
                        "frame": frame,
                        "value": None,
                        "expected": expected_value,
                        "difference": None,
                        "note": "該当フレームがデータ内に見つかりません",
                    }
                ]

            results.append(
                {
                    "title": f"フレーム{frame}の期待値チェック",
                    "type": etype,
                    "violations": violations,
                    "expected_description": _format_expected_equals(frame, expected_value),
                }
            )

        elif etype == "conditional_constraint":
            col = str(exp["condition_column"])  # 例: "category"
            val = str(exp["condition_value"])  # 例: "A"
            cmp_op = str(exp["comparator"])  # "<" | "<=" | ">="
            thr = float(exp["threshold"])  # 例: 10

            subset = df.loc[df[col] == val, ["frame", "value"]].copy()
            if cmp_op == "<":
                mask_violate = subset["value"] >= thr
                expected_op = "<"
            elif cmp_op == "<=":
                mask_violate = subset["value"] > thr
                expected_op = "<="
            else:  # ">="
                mask_violate = subset["value"] < thr
                expected_op = ">="

            violations_df = subset.loc[mask_violate].copy()
            violations_df["expected"] = f"{expected_op}{thr:g}"
            violations = violations_df[["frame", "value", "expected"]].to_dict(orient="records")

            results.append(
                {
                    "title": f"条件付き期待値チェック: {col}={val}",
                    "type": etype,
                    "violations": violations,
                    "expected_description": _format_expected_conditional(col, val, cmp_op, thr),
                }
            )

        elif etype == "sum_range":
            start = int(exp["range_start"])
            end = int(exp["range_end"])
            total_expected = float(exp["expected_sum"])
            subset = df.loc[df["frame"].between(start, end), ["frame", "value"]]
            actual_sum = float(subset["value"].sum())
            violations: List[Dict[str, Any]] = []
            if abs(actual_sum - total_expected) > 1e-9:
                violations.append(
                    {
                        "frame": f"{start}-{end}",
                        "value": actual_sum,
                        "expected": total_expected,
                        "difference": actual_sum - total_expected,
                    }
                )

            results.append(
                {
                    "title": f"合計チェック: フレーム{start}-{end}",
                    "type": etype,
                    "violations": violations,
                    "expected_description": _format_expected_sum_range(start, end, total_expected),
                }
            )

        elif etype == "sum_column":
            column = str(exp["column"])  # 例: "value"
            total_expected = float(exp["expected_sum"])
            if column not in df.columns:
                violations = [
                    {
                        "frame": None,
                        "value": None,
                        "expected": total_expected,
                        "difference": None,
                        "note": f"列 '{column}' が見つかりません",
                    }
                ]
            else:
                actual_sum = float(df[column].sum())
                violations = []
                if abs(actual_sum - total_expected) > 1e-9:
                    violations.append(
                        {
                            "frame": "all",
                            "value": actual_sum,
                            "expected": total_expected,
                            "difference": actual_sum - total_expected,
                        }
                    )

            results.append(
                {
                    "title": f"合計チェック: 列{column}",
                    "type": etype,
                    "violations": violations,
                    "expected_description": _format_expected_sum_col(column, total_expected),
                }
            )

        elif etype == "raw":
            # 未対応の文は期待事項としてメモのみ
            results.append(
                {
                    "title": "未対応の期待値(参考)",
                    "type": etype,
                    "violations": [],
                    "expected_description": exp.get("text", ""),
                }
            )

    return results


