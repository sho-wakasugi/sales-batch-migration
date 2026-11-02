"""売上テーブルへのアクセス（Java: SalesMapper ＋ mapper/SalesMapper.xml）。"""

import sqlite3
from collections.abc import Iterable, Iterator
from importlib import resources
from pathlib import Path

from salesbatch.common import javacompat
from salesbatch.sales.models import Sales, SalesSummary

# Java（H2）の文字列の並び順に合わせる照合順序
JAVA_COLLATION = "JAVA_UTF16"

_INSERT = """
    INSERT INTO sales (sales_date, store_code, product_code, quantity, unit_price, amount, line_no)
    VALUES (:sales_date, :store_code, :product_code, :quantity, :unit_price, :amount, :line_no)
"""

# 店舗別・月別の売上金額と件数（店舗コード、年月の昇順）
# 年月は H2 の FORMATDATETIME(sales_date, 'yyyy-MM') に合わせる。
# H2 の yyyy は「紀元年」のため、0年（紀元前1年）は 0001 になる。
_SELECT_MONTHLY_SUMMARY = f"""
    SELECT
        store_code,
        CASE WHEN substr(sales_date, 1, 4) = '0000' THEN '0001' ELSE substr(sales_date, 1, 4) END
            || substr(sales_date, 5, 3) AS sales_month,
        SUM(amount)                     AS total_amount,
        COUNT(*)                        AS sales_count
    FROM sales
    GROUP BY store_code, sales_month
    ORDER BY store_code COLLATE {JAVA_COLLATION}, sales_month
"""


def connect(db_file: Path) -> sqlite3.Connection:
    """DB に接続し、テーブルと照合順序を用意する（Java: application.yml の datasource ＋ schema.sql）。"""
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.create_collation(JAVA_COLLATION, javacompat.utf16_collation)
    conn.executescript(resources.files("salesbatch").joinpath("schema.sql").read_text(encoding="utf-8"))
    return conn


class SalesRepository:

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def insert_all(self, sales: Iterable[Sales]) -> None:
        self._conn.executemany(_INSERT, [s.__dict__ for s in sales])

    def delete_all(self) -> int:
        return self._conn.execute("DELETE FROM sales").rowcount

    def count_all(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]

    def select_monthly_summary(self) -> Iterator[SalesSummary]:
        """集計結果を1行ずつ返す（Java: MyBatisCursorItemReader）。

        金額の合計が long を超えると sqlite3 が OverflowError / OperationalError を投げる
        （Java も同じ条件で異常終了する）。
        """
        for row in self._conn.execute(_SELECT_MONTHLY_SUMMARY):
            yield SalesSummary(*row)
