package com.example.salesbatch;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.nio.file.Path;

/**
 * application.yml の sales.* の設定値。
 *
 * @param inputFile   入力CSV（売上データ）
 * @param errorFile   エラー行の出力先
 * @param summaryFile 集計結果の出力先
 */
@ConfigurationProperties("sales")
public record SalesProperties(Path inputFile, Path errorFile, Path summaryFile) {
}
