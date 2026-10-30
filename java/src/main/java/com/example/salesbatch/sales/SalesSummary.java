package com.example.salesbatch.sales;

import java.util.List;

/**
 * 店舗別・月別の集計結果（summary.csv の1行）。
 *
 * @param salesMonth  年月（yyyy-MM）
 * @param totalAmount 売上金額の合計
 * @param salesCount  件数
 */
public record SalesSummary(String storeCode, String salesMonth, long totalAmount, long salesCount) {

    public List<Object> toCsvValues() {
        return List.of(storeCode, salesMonth, totalAmount, salesCount);
    }
}
