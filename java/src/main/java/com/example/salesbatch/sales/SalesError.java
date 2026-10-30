package com.example.salesbatch.sales;

import java.util.ArrayList;
import java.util.List;

/**
 * 入力チェックでエラーになった行。error.csv に出力する。
 *
 * @param fields 元の項目値
 * @param reason エラー理由（複数ある場合は「;」区切り）
 */
public record SalesError(int lineNo, List<String> fields, String reason) implements ImportItem {

    /**
     * error.csv の1行分の値（行番号、5項目、エラー理由）。
     * 項目数が足りない場合は空欄で埋め、多い場合は6項目目以降を切り捨てる。
     */
    public List<Object> toCsvValues() {
        List<Object> values = new ArrayList<>();
        values.add(lineNo);
        for (int i = 0; i < SalesCsvRow.COLUMN_COUNT; i++) {
            values.add(i < fields.size() ? fields.get(i) : "");
        }
        values.add(reason);
        return values;
    }
}
