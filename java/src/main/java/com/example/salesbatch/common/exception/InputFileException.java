package com.example.salesbatch.common.exception;

/**
 * 入力ファイルが存在しない・読めない場合の例外。
 * 処理を続けられないため、ジョブは異常終了する。
 */
public class InputFileException extends BatchException {

    public InputFileException(String message) {
        super(message);
    }

    public InputFileException(String message, Throwable cause) {
        super(message, cause);
    }
}
