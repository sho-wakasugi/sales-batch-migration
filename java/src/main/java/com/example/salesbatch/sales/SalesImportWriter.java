package com.example.salesbatch.sales;

import org.springframework.batch.item.Chunk;
import org.springframework.batch.item.ExecutionContext;
import org.springframework.batch.item.ItemStreamWriter;
import org.springframework.batch.item.ItemWriter;
import org.springframework.batch.item.file.FlatFileItemWriter;

/**
 * 入力チェック後のデータを振り分けて書き込む。
 * 正常データは売上テーブルへ登録し、エラー行は error.csv へ出力する。
 * <p>
 * 登録件数・エラー件数はステップの ExecutionContext に保存し、ジョブ終了時のログで使う。
 */
public class SalesImportWriter implements ItemStreamWriter<ImportItem> {

    public static final String INSERT_COUNT_KEY = "sales.insertCount";
    public static final String ERROR_COUNT_KEY = "sales.errorCount";

    private final ItemWriter<Sales> salesWriter;
    private final FlatFileItemWriter<SalesError> errorWriter;

    private long insertCount;
    private long errorCount;

    public SalesImportWriter(ItemWriter<Sales> salesWriter, FlatFileItemWriter<SalesError> errorWriter) {
        this.salesWriter = salesWriter;
        this.errorWriter = errorWriter;
    }

    @Override
    public void write(Chunk<? extends ImportItem> chunk) throws Exception {
        Chunk<Sales> salesChunk = new Chunk<>();
        Chunk<SalesError> errorChunk = new Chunk<>();
        for (ImportItem item : chunk) {
            switch (item) {
                case Sales sales -> salesChunk.add(sales);
                case SalesError error -> errorChunk.add(error);
            }
        }

        if (!salesChunk.isEmpty()) {
            salesWriter.write(salesChunk);
        }
        if (!errorChunk.isEmpty()) {
            errorWriter.write(errorChunk);
        }
        insertCount += salesChunk.size();
        errorCount += errorChunk.size();
    }

    @Override
    public void open(ExecutionContext executionContext) {
        errorWriter.open(executionContext);
        insertCount = executionContext.getLong(INSERT_COUNT_KEY, 0L);
        errorCount = executionContext.getLong(ERROR_COUNT_KEY, 0L);
    }

    @Override
    public void update(ExecutionContext executionContext) {
        errorWriter.update(executionContext);
        executionContext.putLong(INSERT_COUNT_KEY, insertCount);
        executionContext.putLong(ERROR_COUNT_KEY, errorCount);
    }

    @Override
    public void close() {
        errorWriter.close();
    }
}
