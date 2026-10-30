package com.example.salesbatch.sales;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class SalesValidationProcessorTest {

    private final SalesValidationProcessor processor = new SalesValidationProcessor();

    private ImportItem process(String... fields) {
        return processor.process(new SalesCsvRow(2, List.of(fields)));
    }

    @Test
    void 正常行はSalesに変換し金額を計算する() {
        ImportItem item = process("2026-01-05", " S001 ", "P100", "3", "1200");
        Sales sales = assertInstanceOf(Sales.class, item);
        assertEquals(new Sales(2, LocalDate.of(2026, 1, 5), "S001", "P100", 3, 1200, 3600), sales);
    }

    @Test
    void 単価0は正常() {
        assertInstanceOf(Sales.class, process("2026-01-05", "S001", "P100", "1", "0"));
    }

    @Test
    void 数量0はエラー() {
        SalesError error = assertInstanceOf(SalesError.class, process("2026-01-05", "S001", "P100", "0", "100"));
        assertEquals("数量は1以上で入力してください", error.reason());
    }

    @Test
    void 単価マイナスはエラー() {
        SalesError error = assertInstanceOf(SalesError.class, process("2026-01-05", "S001", "P100", "1", "-1"));
        assertEquals("単価は0以上で入力してください", error.reason());
    }

    @Test
    void 複数のエラーは項目順にすべて出す() {
        SalesError error = assertInstanceOf(SalesError.class, process("2026/01/05", "", "P100", "abc", "1.5"));
        assertEquals("売上日はyyyy-MM-dd形式の正しい日付で入力してください;店舗コードは必須です;"
                + "数量は整数で入力してください;単価は整数で入力してください", error.reason());
        assertEquals(List.of("2026/01/05", "", "P100", "abc", "1.5"), error.fields());
    }

    @Test
    void 項目数が違う行はエラー() {
        SalesError error = assertInstanceOf(SalesError.class, process("2026-01-05", "S001", "P100", "1"));
        assertEquals("項目数が不正です（期待値:5、実際:4）", error.reason());
        assertEquals(List.of(2, "2026-01-05", "S001", "P100", "1", "", "項目数が不正です（期待値:5、実際:4）"),
                error.toCsvValues());
    }

    @Test
    void 金額がlongを超える場合はエラー() {
        SalesError error = assertInstanceOf(SalesError.class,
                process("2026-01-05", "S001", "P100", "9223372036854775807", "2"));
        assertEquals("売上金額（数量×単価）が大きすぎます", error.reason());
    }
}
