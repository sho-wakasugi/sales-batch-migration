"""入力チェック後のデータを振り分けて書き込む（Java: SalesImportWriter）。

正常データは売上テーブルへ登録し、エラー行は error.csv へ出力する。
Java の FlatFileItemWriter と同じく、エラー行はコミットのときにファイルへ書き出す
（途中で異常終了した場合、コミットされなかったチャンクのエラー行は出力されない）。
"""

import sqlite3
from pathlib import Path

from salesbatch.common import csv_utils
from salesbatch.sales.models import ImportItem, Sales, SalesError
from salesbatch.sales.repository import SalesRepository

ERROR_HEADER = ["行番号", "売上日", "店舗コード", "商品コード", "数量", "単価", "エラー理由"]


class SalesImportWriter:

    def __init__(self, conn: sqlite3.Connection, error_file: Path):
        self._conn = conn
        self._repository = SalesRepository(conn)
        self._error_file = error_file
        self._out = None
        self._pending_errors: list[str] = []
        self._pending_insert = 0
        self.insert_count = 0
        self.error_count = 0

    def open(self) -> None:
        # newline="" で改行を変換させず、LF のまま書く
        self._out = open(self._error_file, "w", encoding="utf-8", newline="")
        self._out.write(csv_utils.to_line(ERROR_HEADER) + csv_utils.LINE_SEPARATOR)

    def close(self) -> None:
        if self._out is not None:
            self._out.close()
            self._out = None

    def write(self, chunk: list[ImportItem]) -> None:
        sales_chunk: list[Sales] = []
        for item in chunk:
            match item:
                case Sales():
                    sales_chunk.append(item)
                case SalesError():
                    self._pending_errors.append(csv_utils.to_line(item.to_csv_values()) + csv_utils.LINE_SEPARATOR)
        if sales_chunk:
            self._repository.insert_all(sales_chunk)
        self._pending_insert += len(sales_chunk)

    def commit(self) -> None:
        """チャンクの終わりに DB をコミットし、エラー行を書き出して件数に反映する。"""
        self._conn.commit()
        self._out.writelines(self._pending_errors)
        self._out.flush()
        self.insert_count += self._pending_insert
        self.error_count += len(self._pending_errors)
        self._pending_errors.clear()
        self._pending_insert = 0

    def rollback(self) -> None:
        self._conn.rollback()
        self._pending_errors.clear()
        self._pending_insert = 0
