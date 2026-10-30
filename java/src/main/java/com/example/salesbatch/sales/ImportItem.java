package com.example.salesbatch.sales;

/**
 * 入力チェック後の1行。正常データ（{@link Sales}）かエラー（{@link SalesError}）のどちらか。
 */
public sealed interface ImportItem permits Sales, SalesError {

    int lineNo();
}
