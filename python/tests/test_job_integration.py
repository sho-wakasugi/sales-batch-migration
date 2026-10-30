"""ジョブ全体を実行し、出力ファイルと件数を検証する（Java: SalesJobIntegrationTest と同じ観点）。

期待値ファイルは Java 側のもの（src/test/resources/integration）と、
境界ケースを Java で実際に実行した出力（tests/data/expected）をそのまま使う。
"""

from pathlib import Path

import pytest

from salesbatch.__main__ import EXIT_FAILED, main
from salesbatch.batch.job import IMPORT_STEP, SUMMARY_STEP, BatchStatus, run_job
from salesbatch.config import SalesProperties

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JAVA_RESOURCES = PROJECT_ROOT / "src" / "test" / "resources" / "integration"
DATA = Path(__file__).resolve().parent / "data"


def make_properties(tmp_path: Path, input_file: Path) -> SalesProperties:
    return SalesProperties(
        input_file=input_file,
        error_file=tmp_path / "output" / "error.csv",
        summary_file=tmp_path / "output" / "summary.csv",
        db_file=tmp_path / "data" / "salesdb.sqlite3",
        log_file=None,
    )


def step(execution, name):
    return next(s for s in execution.step_executions if s.step_name == name)


def read(path: Path) -> bytes:
    # 改行コードや BOM の違いも検出できるよう、バイト列で比較する
    return path.read_bytes()


def test_clear指定で実行すると出力ファイルと件数が期待どおりになる(tmp_path):
    properties = make_properties(tmp_path, JAVA_RESOURCES / "sales.csv")
    execution = run_job(properties, {"clear": "true"})

    assert execution.status == BatchStatus.COMPLETED
    assert read(properties.error_file) == read(JAVA_RESOURCES / "expected_error.csv")
    assert read(properties.summary_file) == read(JAVA_RESOURCES / "expected_summary.csv")

    import_step = step(execution, IMPORT_STEP)
    assert import_step.read_count == 11
    assert import_step.insert_count == 7
    assert import_step.error_count == 4


def test_clear指定なしで再実行すると売上が蓄積される(tmp_path):
    properties = make_properties(tmp_path, JAVA_RESOURCES / "sales.csv")
    run_job(properties, {"clear": "true"})
    execution = run_job(properties, {})

    assert execution.status == BatchStatus.COMPLETED
    assert properties.summary_file.read_text(encoding="utf-8") == (
        "店舗コード,年月,売上金額,件数\n"
        "S001,2026-01,3360,4\n"
        "S001,2026-02,700,4\n"
        "S002,2025-12,9600,2\n"
        "S002,2026-01,720,2\n"
        "S010,2026-03,1200,2\n"
    )


# ---------------------------------------------------------------
# Python 版で追加した観点（境界ケースで Java の実際の出力と一致すること）
# ---------------------------------------------------------------

@pytest.mark.parametrize(
    ("name", "counts"),
    [
        ("edge_cases", (38, 18, 20, 11)),
        ("edge_comment", (4, 2, 2, 1)),
    ],
)
def test_境界ケースでJavaの出力とバイト単位で一致する(tmp_path, name, counts):
    properties = make_properties(tmp_path, DATA / f"{name}.csv")
    execution = run_job(properties, {"clear": "true"})

    assert execution.status == BatchStatus.COMPLETED
    assert read(properties.error_file) == read(DATA / "expected" / f"{name}_error.csv")
    assert read(properties.summary_file) == read(DATA / "expected" / f"{name}_summary.csv")
    import_step = step(execution, IMPORT_STEP)
    summary_step = step(execution, SUMMARY_STEP)
    assert (import_step.read_count, import_step.insert_count, import_step.error_count,
            summary_step.write_count) == counts


def test_集計金額がlongを超えるとJavaと同じく異常終了する(tmp_path):
    properties = make_properties(tmp_path, DATA / "failure_sum_overflow.csv")
    execution = run_job(properties, {"clear": "true"})

    assert execution.status == BatchStatus.FAILED
    assert step(execution, IMPORT_STEP).insert_count == 2
    assert step(execution, SUMMARY_STEP).write_count == 0
    assert properties.summary_file.read_text(encoding="utf-8") == "店舗コード,年月,売上金額,件数\n"


def test_分割できない行があるとJavaと同じく異常終了しチャンク全体を取り消す(tmp_path):
    properties = make_properties(tmp_path, DATA / "failure_single_quote.csv")
    execution = run_job(properties, {"clear": "true"})

    assert execution.status == BatchStatus.FAILED
    import_step = step(execution, IMPORT_STEP)
    assert (import_step.read_count, import_step.insert_count, import_step.error_count) == (1, 0, 0)
    assert not properties.summary_file.exists()


def test_入力ファイルが無ければ終了コード5(tmp_path):
    exit_code = main([f"--input-file={tmp_path / 'nothing.csv'}", f"--db-file={tmp_path / 'db.sqlite3'}",
                      "--log-file="])
    assert exit_code == EXIT_FAILED
