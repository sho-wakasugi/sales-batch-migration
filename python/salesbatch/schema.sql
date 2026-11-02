-- 売上テーブル（データは蓄積する。clear=true で実行したときだけ全件削除する）
-- SQLite には DATE 型が無いため、売上日は yyyy-MM-dd の文字列で持つ
-- AUTOINCREMENT は、H2 と同じく削除後も id を再利用しないようにするため
CREATE TABLE IF NOT EXISTS sales (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sales_date   TEXT    NOT NULL,
    store_code   TEXT    NOT NULL,
    product_code TEXT    NOT NULL,
    quantity     INTEGER NOT NULL,
    unit_price   INTEGER NOT NULL,
    amount       INTEGER NOT NULL,
    line_no      INTEGER NOT NULL,
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime'))
);
