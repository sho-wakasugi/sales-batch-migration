"""売上集計ジョブ（Java: SalesJobConfig）。

    salesJob
     ├─ prepare     : 入力ファイル確認、（clear=true なら）売上テーブル全件削除
     ├─ importStep  : CSV読込 → 入力チェック → 正常行はDB登録 / エラー行は error.csv
     └─ summaryStep : 売上テーブルを店舗別・月別に集計 → summary.csv

Spring Batch は使わず、同じ順序・同じチャンク単位（50件ごとにコミット）で処理する。
いずれかの処理で例外が起きたら、以降の処理は行わずジョブを FAILED にする。
"""

import enum
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from salesbatch.batch import job_result
from salesbatch.batch.prepare import prepare
from salesbatch.common import csv_utils
from salesbatch.config import SalesProperties
from salesbatch.sales.csv_reader import SalesCsvReader
from salesbatch.sales.import_writer import SalesImportWriter
from salesbatch.sales.repository import SalesRepository, connect
from salesbatch.sales.validation_processor import SalesValidationProcessor

JOB_NAME = "salesJob"
IMPORT_STEP = "importStep"
SUMMARY_STEP = "summaryStep"

CHUNK_SIZE = 50

SUMMARY_HEADER = ["店舗コード", "年月", "売上金額", "件数"]

log = logging.getLogger(__name__)


class BatchStatus(enum.StrEnum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class StepExecution:
    """ステップの実行結果（Java: StepExecution ＋ ExecutionContext の件数）。"""

    step_name: str
    read_count: int = 0
    write_count: int = 0
    insert_count: int = 0
    error_count: int = 0


@dataclass
class JobExecution:
    """ジョブの実行結果（Java: JobExecution）。"""

    job_name: str
    job_parameters: dict[str, str]
    status: BatchStatus = BatchStatus.STARTED
    step_executions: list[StepExecution] = field(default_factory=list)
    failure_exceptions: list[BaseException] = field(default_factory=list)


def run_job(properties: SalesProperties, job_parameters: Mapping[str, str]) -> JobExecution:
    execution = JobExecution(JOB_NAME, dict(job_parameters))
    job_result.before_job(execution)
    conn = None
    try:
        conn = connect(properties.db_file)
        prepare(properties, conn, execution.job_parameters)
        _import_step(properties, conn, execution)
        _summary_step(properties, conn, execution)
        execution.status = BatchStatus.COMPLETED
    except Exception as e:
        log.debug("ジョブで例外が発生しました", exc_info=True)
        execution.status = BatchStatus.FAILED
        execution.failure_exceptions.append(e)
    finally:
        if conn is not None:
            conn.close()
    job_result.after_job(execution)
    return execution


def _import_step(properties: SalesProperties, conn, execution: JobExecution) -> None:
    step = StepExecution(IMPORT_STEP)
    execution.step_executions.append(step)
    processor = SalesValidationProcessor()
    writer = SalesImportWriter(conn, properties.error_file)

    with SalesCsvReader(properties.input_file) as reader:
        writer.open()
        try:
            while True:
                chunk = []
                try:
                    while len(chunk) < CHUNK_SIZE and (row := reader.read()) is not None:
                        step.read_count += 1
                        chunk.append(row)
                    if not chunk:
                        break
                    writer.write([processor.process(row) for row in chunk])
                    writer.commit()
                except Exception:
                    writer.rollback()
                    raise
                finally:
                    # 件数はコミット済みの分だけを反映する（Java: ExecutionContext の更新はコミット時）
                    step.insert_count = writer.insert_count
                    step.error_count = writer.error_count
                step.write_count += len(chunk)
        finally:
            writer.close()


def _summary_step(properties: SalesProperties, conn, execution: JobExecution) -> None:
    step = StepExecution(SUMMARY_STEP)
    execution.step_executions.append(step)
    repository = SalesRepository(conn)

    with open(properties.summary_file, "w", encoding="utf-8", newline="") as out:
        out.write(csv_utils.to_line(SUMMARY_HEADER) + csv_utils.LINE_SEPARATOR)
        chunk: list[str] = []
        for summary in repository.select_monthly_summary():
            step.read_count += 1
            chunk.append(csv_utils.to_line(summary.to_csv_values()) + csv_utils.LINE_SEPARATOR)
            if len(chunk) == CHUNK_SIZE:
                out.writelines(chunk)
                step.write_count += len(chunk)
                chunk.clear()
        out.writelines(chunk)
        step.write_count += len(chunk)
