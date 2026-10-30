package com.example.salesbatch.common.validation;

import com.example.salesbatch.common.exception.ValidationException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class FieldValidatorTest {

    @Test
    void isBlank_nullや空白はtrue() {
        assertTrue(FieldValidator.isBlank(null));
        assertTrue(FieldValidator.isBlank(""));
        assertTrue(FieldValidator.isBlank("  "));
        assertFalse(FieldValidator.isBlank("a"));
    }

    @ParameterizedTest
    @ValueSource(strings = {"0", "1", "-5", "123456", "9223372036854775807"})
    void isInteger_整数はtrue(String value) {
        assertTrue(FieldValidator.isInteger(value));
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "abc", "1.5", "1e3", "+1", " 1", "１", "9223372036854775808"})
    void isInteger_整数でなければfalse(String value) {
        assertFalse(FieldValidator.isInteger(value));
    }

    @ParameterizedTest
    @ValueSource(strings = {"2026-01-01", "2026-12-31", "2024-02-29"})
    void isDate_正しい日付はtrue(String value) {
        assertTrue(FieldValidator.isDate(value));
    }

    @ParameterizedTest
    @ValueSource(strings = {"2026/01/01", "2026-1-1", "20260101", "2026-02-30", "2026-02-29", "2026-13-01", "abcd-ef-gh"})
    void isDate_形式誤りや存在しない日付はfalse(String value) {
        assertFalse(FieldValidator.isDate(value));
    }

    @Test
    void required_前後の空白を除いた値を返す() {
        FieldValidator v = new FieldValidator();
        assertEquals("S001", v.required(" S001 ", "店舗コード"));
        assertFalse(v.hasErrors());
    }

    @Test
    void required_空ならエラー() {
        FieldValidator v = new FieldValidator();
        assertNull(v.required(" ", "店舗コード"));
        assertEquals(List.of("店舗コードは必須です"), v.getErrors());
    }

    @Test
    void requiredInteger_必須エラーのときは数値エラーを重ねない() {
        FieldValidator v = new FieldValidator();
        assertNull(v.requiredInteger("", "数量"));
        assertEquals(List.of("数量は必須です"), v.getErrors());
    }

    @Test
    void requiredInteger_数値でなければエラー() {
        FieldValidator v = new FieldValidator();
        assertNull(v.requiredInteger("1.5", "単価"));
        assertEquals(List.of("単価は整数で入力してください"), v.getErrors());
    }

    @Test
    void requiredDate_正しければ日付を返す() {
        FieldValidator v = new FieldValidator();
        assertEquals(LocalDate.of(2026, 1, 5), v.requiredDate("2026-01-05", "売上日"));
        assertFalse(v.hasErrors());
    }

    @Test
    void requiredDate_存在しない日付はエラー() {
        FieldValidator v = new FieldValidator();
        assertNull(v.requiredDate("2026-02-30", "売上日"));
        assertEquals(List.of("売上日はyyyy-MM-dd形式の正しい日付で入力してください"), v.getErrors());
    }

    @Test
    void min_境界値() {
        FieldValidator v = new FieldValidator();
        v.min(1L, 1, "数量");
        assertFalse(v.hasErrors());
        v.min(0L, 1, "数量");
        assertEquals(List.of("数量は1以上で入力してください"), v.getErrors());
    }

    @Test
    void min_nullなら何もしない() {
        FieldValidator v = new FieldValidator();
        v.min(null, 1, "数量");
        assertFalse(v.hasErrors());
    }

    @Test
    void throwIfInvalid_エラーを全件保持した例外を投げる() {
        FieldValidator v = new FieldValidator();
        v.required("", "店舗コード");
        v.requiredInteger("x", "数量");
        ValidationException e = assertThrows(ValidationException.class, v::throwIfInvalid);
        assertEquals("店舗コードは必須です;数量は整数で入力してください", e.getJoinedReasons());
    }

    @Test
    void throwIfInvalid_エラーが無ければ何もしない() {
        assertDoesNotThrow(new FieldValidator()::throwIfInvalid);
    }
}
