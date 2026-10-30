package com.example.salesbatch.sales;

import java.time.LocalDate;

/**
 * 入力チェックを通過した売上データ（売上テーブルの1行）。
 *
 * @param amount 売上金額（数量 × 単価）
 */
public record Sales(
        int lineNo,
        LocalDate salesDate,
        String storeCode,
        String productCode,
        long quantity,
        long unitPrice,
        long amount) implements ImportItem {
}
