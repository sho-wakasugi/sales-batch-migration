package com.example.salesbatch.sales;

import org.springframework.batch.item.file.LineMapper;
import org.springframework.batch.item.file.transform.DelimitedLineTokenizer;

import java.util.List;

/**
 * CSVの1行を {@link SalesCsvRow} に変換する。
 * 項目数が違っても例外にせず、そのまま渡して入力チェックでエラーにする。
 */
public class SalesCsvLineMapper implements LineMapper<SalesCsvRow> {

    private final DelimitedLineTokenizer tokenizer = new DelimitedLineTokenizer();

    public SalesCsvLineMapper() {
        tokenizer.setStrict(false);
    }

    @Override
    public SalesCsvRow mapLine(String line, int lineNumber) {
        return new SalesCsvRow(lineNumber, List.of(tokenizer.tokenize(line).getValues()));
    }
}
