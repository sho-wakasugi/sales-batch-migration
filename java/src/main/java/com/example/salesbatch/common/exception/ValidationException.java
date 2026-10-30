package com.example.salesbatch.common.exception;

import java.util.List;

/**
 * 入力チェック違反を表す例外。
 * 1行の中で見つかったエラー理由をすべて保持する。
 */
public class ValidationException extends BatchException {

    /** エラー理由を連結するときの区切り文字 */
    public static final String REASON_DELIMITER = ";";

    private final List<String> reasons;

    public ValidationException(List<String> reasons) {
        super(String.join(REASON_DELIMITER, reasons));
        this.reasons = List.copyOf(reasons);
    }

    public List<String> getReasons() {
        return reasons;
    }

    /** エラー理由を「;」区切りの1つの文字列にして返す。 */
    public String getJoinedReasons() {
        return String.join(REASON_DELIMITER, reasons);
    }
}
