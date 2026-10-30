"""現新比較用：SQLite の売上テーブルを、H2 の CSVWRITE と同じ形式の CSV に書き出す。

H2 の CSVWRITE の形式：ヘッダーは列名（大文字）、全項目をダブルクォートで囲み、中の " は "" にする。
id と created_at は Java と Python で一致しないため比較対象から外し、line_no の順に並べる。

    python export_sales.py <SQLiteファイル> <出力CSV>
"""

import sqlite3
import sys

COLUMNS = ["LINE_NO", "SALES_DATE", "STORE_CODE", "PRODUCT_CODE", "QUANTITY", "UNIT_PRICE", "AMOUNT"]
QUERY = f"SELECT {', '.join(COLUMNS)} FROM sales ORDER BY line_no"


def quote(value: object) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def main(db_file: str, out_file: str) -> None:
    conn = sqlite3.connect(db_file)
    try:
        with open(out_file, "w", encoding="utf-8", newline="") as out:
            out.write(",".join(map(quote, COLUMNS)) + "\n")
            for row in conn.execute(QUERY):
                out.write(",".join(map(quote, row)) + "\n")
    finally:
        conn.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
