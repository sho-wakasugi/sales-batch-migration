package com.example.salesbatch.common.exception;

/**
 * 本バッチで発生する業務例外の基底クラス。
 * 個別の例外はこのクラスを継承して作る。
 */
public class BatchException extends RuntimeException {

    public BatchException(String message) {
        super(message);
    }

    public BatchException(String message, Throwable cause) {
        super(message, cause);
    }
}
