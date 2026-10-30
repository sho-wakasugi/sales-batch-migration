package com.example.salesbatch.sales;

import com.example.salesbatch.common.exception.ValidationException;
import com.example.salesbatch.common.validation.FieldValidator;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.stereotype.Component;

import java.time.LocalDate;

/**
 * 入力CSVの1行をチェックし、正常なら {@link Sales}、エラーなら {@link SalesError} に変換する。
 * エラーがあっても例外で止めず、エラー行として後続に渡す。
 */
@Component
public class SalesValidationProcessor implements ItemProcessor<SalesCsvRow, ImportItem> {

    @Override
    public ImportItem process(SalesCsvRow row) {
        try {
            return toSales(row);
        } catch (ValidationException e) {
            return new SalesError(row.lineNo(), row.fields(), e.getJoinedReasons());
        }
    }

    /** チェックして Sales に変換する。エラーがあれば ValidationException を投げる。 */
    Sales toSales(SalesCsvRow row) {
        FieldValidator v = new FieldValidator();

        // 項目数が違う場合は、どの値が何の項目か判断できないので個別チェックはしない
        if (row.fields().size() != SalesCsvRow.COLUMN_COUNT) {
            v.addError("項目数が不正です（期待値:" + SalesCsvRow.COLUMN_COUNT + "、実際:" + row.fields().size() + "）");
            v.throwIfInvalid();
        }

        LocalDate salesDate = v.requiredDate(row.field(0), "売上日");
        String storeCode = v.required(row.field(1), "店舗コード");
        String productCode = v.required(row.field(2), "商品コード");
        Long quantity = v.requiredInteger(row.field(3), "数量");
        v.min(quantity, 1, "数量");
        Long unitPrice = v.requiredInteger(row.field(4), "単価");
        v.min(unitPrice, 0, "単価");
        v.throwIfInvalid();

        long amount;
        try {
            amount = Math.multiplyExact(quantity, unitPrice);
        } catch (ArithmeticException e) {
            v.addError("売上金額（数量×単価）が大きすぎます");
            v.throwIfInvalid();
            throw e; // ここには来ない（コンパイラ向け）
        }

        return new Sales(row.lineNo(), salesDate, storeCode, productCode, quantity, unitPrice, amount);
    }
}
