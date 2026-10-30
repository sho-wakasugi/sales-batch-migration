-- 売上テーブル（データは蓄積する。clear=true で実行したときだけ全件削除する）
CREATE TABLE IF NOT EXISTS sales (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    sales_date   DATE              NOT NULL,
    store_code   CHARACTER VARYING NOT NULL,
    product_code CHARACTER VARYING NOT NULL,
    quantity     BIGINT            NOT NULL,
    unit_price   BIGINT            NOT NULL,
    amount       BIGINT            NOT NULL,
    line_no      INT               NOT NULL,
    created_at   TIMESTAMP         DEFAULT CURRENT_TIMESTAMP NOT NULL
);
