"""ジョブ開始時に開始メッセージを、終了時に処理件数をログに出す（Java: JobResultListener）。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from salesbatch.batch.prepare import CLEAR_PARAMETER

if TYPE_CHECKING:
    from salesbatch.batch.job import JobExecution, StepExecution

log = logging.getLogger(__name__)


def before_job(execution: JobExecution) -> None:
    clear = execution.job_parameters.get(CLEAR_PARAMETER, "指定なし")
    log.info("========== バッチ実行します ==========")
    log.info("ジョブ名: %s、clear: %s", execution.job_name, clear)


def after_job(execution: JobExecution) -> None:
    from salesbatch.batch.job import IMPORT_STEP, SUMMARY_STEP, BatchStatus

    import_step = _find_step(execution, IMPORT_STEP)
    summary_step = _find_step(execution, SUMMARY_STEP)

    log.info("========== 処理結果 ==========")
    if import_step is not None:
        read_count = import_step.read_count
        insert_count = import_step.insert_count
        error_count = import_step.error_count
        log.info("読込件数　: %d", read_count)
        log.info("登録件数　: %d", insert_count)
        log.info("エラー件数: %d", error_count)
        if read_count != insert_count + error_count:
            log.warning("読込件数と（登録件数＋エラー件数）が一致しません")
    else:
        log.info("取込処理は実行されませんでした")
    if summary_step is not None:
        log.info("集計出力件数: %d", summary_step.write_count)
    log.info("終了ステータス: %s", execution.status)

    if execution.status != BatchStatus.COMPLETED:
        for e in execution.failure_exceptions:
            log.error("異常終了しました: %s", e)


def _find_step(execution: JobExecution, step_name: str) -> StepExecution | None:
    return next((s for s in execution.step_executions if s.step_name == step_name), None)
