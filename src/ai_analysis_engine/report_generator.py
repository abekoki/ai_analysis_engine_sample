from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib

# ヘッドレス環境を想定してAggバックエンドを使用
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from jinja2 import Template  # noqa: E402


def create_graph(results: List[Dict[str, Any]], output_dir: Path) -> Optional[Path]:
    """最初の違反結果について簡易グラフを作る。

    equals_at_frame の違反があれば、期待値と実測値を棒グラフで描画。
    グラフ生成が不可能な場合は None を返す。
    """
    for res in results:
        if res.get("type") == "equals_at_frame" and res.get("violations"):
            first = res["violations"][0]
            if first.get("value") is None:
                continue
            expected = first.get("expected")
            actual = first.get("value")
            frame_label = str(first.get("frame"))

            fig, ax = plt.subplots(figsize=(4, 3))
            ax.bar(["expected", "actual"], [expected, actual], color=["#4caf50", "#f44336"]) 
            ax.set_title(f"Frame {frame_label}")
            ax.set_ylabel("value")
            fig.tight_layout()
            output_dir.mkdir(parents=True, exist_ok=True)
            graph_path = output_dir / "graph.png"
            fig.savefig(graph_path)
            plt.close(fig)
            return graph_path
    return None


def generate_report(
    *,
    data_path: str,
    expectation_text: str,
    results: List[Dict[str, Any]],
    hypothesis: str,
    template_path: str,
    output_html_path: Path,
) -> Path:
    """Jinja2テンプレートでHTMLレポートを生成。"""
    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())

    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rendered = template.render(
        data={
            "source": data_path,
            "expectation": expectation_text,
            "generated_at": generated_at,
        },
        results=results,
        hypothesis=hypothesis,
        graph=str((output_html_path.parent / "graph.png").as_posix()) if (output_html_path.parent / "graph.png").exists() else None,
        summary="初心者向け: 期待値と実測値の差分を確認し、原因の仮説を提示します。",
    )

    output_html_path.write_text(rendered, encoding="utf-8")
    return output_html_path


