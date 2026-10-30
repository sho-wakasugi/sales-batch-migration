package com.example.salesbatch.common.validation;

import com.example.salesbatch.common.exception.ValidationException;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * 入力チェックの共通部品。
 * <p>
 * 1行分のチェックごとにインスタンスを作り、各項目をチェックしてエラー理由を貯めていく。
 * 最後に {@link #throwIfInvalid()} を呼ぶと、エラーがあれば {@link ValidationException} を投げる。
 * <p>
 * 各チェックメソッドは、値が正しければ変換後の値を、エラーなら null を返す。
 * 必須エラーのときは、その項目の以降のチェック（数値・日付など）は行わない。
 */
public class FieldValidator {

    /** 日付形式（ゼロ埋めした yyyy-MM-dd） */
    public static final String DATE_PATTERN = "yyyy-MM-dd";

    private static final Pattern INTEGER_PATTERN = Pattern.compile("-?[0-9]+");
    private static final Pattern DATE_SHAPE_PATTERN = Pattern.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}");
    // STRICT にすると 2026-02-30 のような存在しない日付をエラーにできる（年は uuuu で指定する）
    private static final DateTimeFormatter DATE_FORMATTER =
            DateTimeFormatter.ofPattern("uuuu-MM-dd").withResolverStyle(ResolverStyle.STRICT);

    private final List<String> errors = new ArrayList<>();

    // ---------------------------------------------------------------
    // 判定だけを行う static メソッド（単体でも使える）
    // ---------------------------------------------------------------

    /** null・空文字・空白のみなら true。 */
    public static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    /** 符号（-）付きも含む整数で、long の範囲に収まれば true。 */
    public static boolean isInteger(String value) {
        if (value == null || !INTEGER_PATTERN.matcher(value).matches()) {
            return false;
        }
        try {
            Long.parseLong(value);
            return true;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    /** yyyy-MM-dd 形式で、実在する日付なら true。 */
    public static boolean isDate(String value) {
        if (value == null || !DATE_SHAPE_PATTERN.matcher(value).matches()) {
            return false;
        }
        try {
            LocalDate.parse(value, DATE_FORMATTER);
            return true;
        } catch (DateTimeParseException e) {
            return false;
        }
    }

    // ---------------------------------------------------------------
    // エラー理由を貯めながらチェックするメソッド
    // ---------------------------------------------------------------

    /** 必須チェック。正しければ前後の空白を除いた値を返す。 */
    public String required(String value, String label) {
        if (isBlank(value)) {
            errors.add(label + "は必須です");
            return null;
        }
        return value.strip();
    }

    /** 必須＋整数チェック。正しければ整数値を返す。 */
    public Long requiredInteger(String value, String label) {
        String v = required(value, label);
        if (v == null) {
            return null;
        }
        if (!isInteger(v)) {
            errors.add(label + "は整数で入力してください");
            return null;
        }
        return Long.parseLong(v);
    }

    /** 必須＋日付チェック。正しければ日付を返す。 */
    public LocalDate requiredDate(String value, String label) {
        String v = required(value, label);
        if (v == null) {
            return null;
        }
        if (!isDate(v)) {
            errors.add(label + "は" + DATE_PATTERN + "形式の正しい日付で入力してください");
            return null;
        }
        return LocalDate.parse(v, DATE_FORMATTER);
    }

    /** 最小値チェック。value が null（前のチェックでエラー）の場合は何もしない。 */
    public void min(Long value, long min, String label) {
        if (value != null && value < min) {
            errors.add(label + "は" + min + "以上で入力してください");
        }
    }

    /** 上記以外のチェックで見つかったエラー理由を追加する。 */
    public void addError(String reason) {
        errors.add(reason);
    }

    public boolean hasErrors() {
        return !errors.isEmpty();
    }

    public List<String> getErrors() {
        return List.copyOf(errors);
    }

    /** エラーが1件以上あれば ValidationException を投げる。 */
    public void throwIfInvalid() {
        if (hasErrors()) {
            throw new ValidationException(errors);
        }
    }
}
