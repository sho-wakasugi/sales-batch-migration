package com.example.salesbatch;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 売上CSV集計バッチの起動クラス。
 * ジョブの結果を終了コードとして返す（正常:0、異常:1）。
 */
@SpringBootApplication
public class SalesBatchApplication {

    public static void main(String[] args) {
        System.exit(SpringApplication.exit(SpringApplication.run(SalesBatchApplication.class, args)));
    }
}
