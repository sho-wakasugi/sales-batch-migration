package com.example.salesbatch.common.csv;

import java.util.List;
import java.util.stream.Collectors;

/**
 * CSV出力の共通部品。
 * <p>
 * 値にカンマ・ダブルクォート・改行が含まれる場合だけダブルクォートで囲み、
 * 中のダブルクォートは2つ重ねる（RFC 4180 / Python csv モジュールの QUOTE_MINIMAL と同じ）。
 */
public final class CsvUtils {

    public static final String DELIMITER = ",";
    public static final String LINE_SEPARATOR = "\n";

    private CsvUtils() {
    }

    public static String escape(Object value) {
        String s = value == null ? "" : value.toString();
        if (s.contains(",") || s.contains("\"") || s.contains("\n") || s.contains("\r")) {
            return "\"" + s.replace("\"", "\"\"") + "\"";
        }
        return s;
    }

    /** 値のリストを1行分のCSV文字列にする（改行は含まない）。 */
    public static String toLine(List<?> values) {
        return values.stream().map(CsvUtils::escape).collect(Collectors.joining(DELIMITER));
    }
}
