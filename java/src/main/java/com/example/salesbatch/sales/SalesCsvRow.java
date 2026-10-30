package com.example.salesbatch.sales;

import java.util.List;

/**
 * 入力CSVの1行。チェック前なので全項目を文字列のまま持つ。
 *
 * @param lineNo 入力ファイル上の行番号（ヘッダーを1行目として数える）
 * @param fields 項目の値（CSVのクォートは外した状態、空白は未加工）
 */
public record SalesCsvRow(int lineNo, List<String> fields) {

    /** 項目数（売上日、店舗コード、商品コード、数量、単価） */
    public static final int COLUMN_COUNT = 5;

    public SalesCsvRow {
        fields = List.copyOf(fields);
    }

    /** index 番目の値。項目が足りない場合は null。 */
    public String field(int index) {
        return index < fields.size() ? fields.get(index) : null;
    }
}
