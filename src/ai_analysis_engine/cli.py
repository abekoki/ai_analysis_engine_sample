import os
import sys
import datetime
from pathlib import Path
from typing import Optional

import click

from .expectation_parser import parse_expectations
from .data_analyzer import analyze_data
from .hypothesis_generator import generate_hypothesis
from .report_generator import create_graph, generate_report


def _read_text_file(path: Optional[str]) -> str:
    """テキストファイルをUTF-8で読み込み、未指定時は空文字を返す。

    Windows環境でも文字化けしないよう encoding を明示。
    """
    if not path:
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--data-path", required=True, type=click.Path(exists=True, dir_okay=False), help="CSVデータへのパス")
@click.option("--spec-path", required=False, type=click.Path(exists=True, dir_okay=False), help="仕様書(Markdown)へのパス")
@click.option("--code-path", required=False, type=click.Path(exists=True, dir_okay=False), help="ソースコード(Python)へのパス")
@click.option("--expectation-file", required=False, type=click.Path(exists=True, dir_okay=False), help="期待値テキストへのパス")
@click.option("--expectation-text", required=False, type=str, help="期待値テキスト(直接入力)")
@click.option("--output-dir", required=False, type=click.Path(file_okay=False), default="output", show_default=True, help="出力ディレクトリ")
@click.option("--template-path", required=False, type=click.Path(exists=True, dir_okay=False), default="templates/report_template.html", show_default=True, help="HTMLテンプレートのパス")
def main(
    data_path: str,
    spec_path: Optional[str],
    code_path: Optional[str],
    expectation_file: Optional[str],
    expectation_text: Optional[str],
    output_dir: str,
    template_path: str,
):
    """CSV・仕様書・ソースコード・期待値を元に異常解析レポート(HTML)を生成します。"""

    # 期待値の取得（ファイル優先、なければ引数）
    if expectation_file:
        expectation_raw_text = _read_text_file(expectation_file)
    else:
        if not expectation_text:
            raise click.UsageError("--expectation-file または --expectation-text のいずれかを指定してください。")
        expectation_raw_text = expectation_text

    # 期待値の構造化
    structured_expectations = parse_expectations(expectation_raw_text)

    # データ解析
    analysis_results = analyze_data(data_path, structured_expectations)

    # 仕様書・ソースコードから仮説を生成（省略可）
    spec_text = _read_text_file(spec_path)
    code_text = _read_text_file(code_path)
    hypothesis_text = generate_hypothesis(analysis_results, spec_text, code_text)

    # 出力ディレクトリの用意
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # グラフ生成（可能な場合のみ）
    graph_path = create_graph(analysis_results, output_path)

    # レポート生成
    report_html_path = output_path / "report.html"
    generate_report(
        data_path=data_path,
        expectation_text=expectation_raw_text,
        results=analysis_results,
        hypothesis=hypothesis_text,
        template_path=template_path,
        output_html_path=report_html_path,
    )

    click.echo(str(report_html_path))


