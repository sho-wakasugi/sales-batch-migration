"""前処理（Java: PrepareTasklet）。

- 入力ファイルがあるか確認する（無ければ InputFileException で異常終了）
- 出力先フォルダを作る
- ジョブパラメータ clear=true のときだけ売上テーブルを全件削除する（現新比較用）
"""

import logging
import os
import sqlite3
from collections.abc import Mapping
from pathlib import Path

from salesbatch.common.exceptions import InputFileException
from salesbatch.config import SalesProperties
from salesbatch.sales.repository import SalesRepository

# 売上テーブルを全件削除するかどうかのジョブパラメータ名
CLEAR_PARAMETER = "clear"

log = logging.getLogger(__name__)


def prepare(properties: SalesProperties, conn: sqlite3.Connection | None, job_parameters: Mapping[str, str]) -> None:
    input_file = properties.input_file
    if not input_file.is_file() or not os.access(input_file, os.R_OK):
        raise InputFileException(f"入力ファイルが見つからないか読み込めません: {input_file.resolve()}")
    log.info("入力ファイル: %s", input_file.resolve())

    _create_parent_directory(properties.error_file)
    _create_parent_directory(properties.summary_file)

    repository = SalesRepository(conn)
    if str(job_parameters.get(CLEAR_PARAMETER)).lower() == "true":
        deleted = repository.delete_all()
        conn.commit()
        log.info("clear=true のため売上テーブルを全件削除しました（%d件）", deleted)
    else:
        log.info("売上テーブルは削除せず追加登録します（登録済み %d件）", repository.count_all())


def _create_parent_directory(file: Path) -> None:
    file.absolute().parent.mkdir(parents=True, exist_ok=True)
