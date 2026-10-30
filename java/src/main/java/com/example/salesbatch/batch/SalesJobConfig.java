package com.example.salesbatch.batch;

import com.example.salesbatch.SalesProperties;
import com.example.salesbatch.common.csv.CsvUtils;
import com.example.salesbatch.sales.ImportItem;
import com.example.salesbatch.sales.Sales;
import com.example.salesbatch.sales.SalesCsvLineMapper;
import com.example.salesbatch.sales.SalesCsvRow;
import com.example.salesbatch.sales.SalesError;
import com.example.salesbatch.sales.SalesImportWriter;
import com.example.salesbatch.sales.SalesMapper;
import com.example.salesbatch.sales.SalesValidationProcessor;
import org.apache.ibatis.session.SqlSessionFactory;
import org.mybatis.spring.batch.MyBatisBatchItemWriter;
import org.mybatis.spring.batch.builder.MyBatisBatchItemWriterBuilder;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.configuration.annotation.StepScope;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.file.FlatFileItemReader;
import org.springframework.batch.item.file.FlatFileItemWriter;
import org.springframework.batch.item.file.builder.FlatFileItemReaderBuilder;
import org.springframework.batch.item.file.builder.FlatFileItemWriterBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.FileSystemResource;
import org.springframework.transaction.PlatformTransactionManager;

import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * 売上集計ジョブの定義。
 * <pre>
 * salesJob
 *  ├─ prepareStep : 入力ファイル確認、（clear=true なら）売上テーブル全件削除
 *  └─ importStep  : CSV読込 → 入力チェック → 正常行はDB登録 / エラー行は error.csv
 * </pre>
 */
@Configuration
public class SalesJobConfig {

    public static final String JOB_NAME = "salesJob";
    public static final String IMPORT_STEP = "importStep";

    private static final int CHUNK_SIZE = 50;

    @Bean
    public Job salesJob(JobRepository jobRepository, Step prepareStep, Step importStep) {
        return new JobBuilder(JOB_NAME, jobRepository)
                // 実行ごとに run.id を1つ増やし、何度でも実行できるようにする。
                // 前回のパラメータ（clear など）は引き継がず、毎回コマンドラインの指定だけを使う。
                .incrementer(previous -> new JobParametersBuilder()
                        .addLong("run.id", (previous == null ? 0L : previous.getLong("run.id", 0L)) + 1)
                        .toJobParameters())
                .start(prepareStep)
                .next(importStep)
                .build();
    }

    // ---------------------------------------------------------------
    // prepareStep
    // ---------------------------------------------------------------

    @Bean
    public Step prepareStep(JobRepository jobRepository, PlatformTransactionManager transactionManager,
                            PrepareTasklet prepareTasklet) {
        return new StepBuilder("prepareStep", jobRepository)
                .tasklet(prepareTasklet, transactionManager)
                .build();
    }

    // ---------------------------------------------------------------
    // importStep
    // ---------------------------------------------------------------

    @Bean
    public Step importStep(JobRepository jobRepository, PlatformTransactionManager transactionManager,
                           FlatFileItemReader<SalesCsvRow> salesCsvReader,
                           SalesValidationProcessor salesValidationProcessor,
                           SalesImportWriter salesImportWriter) {
        return new StepBuilder(IMPORT_STEP, jobRepository)
                .<SalesCsvRow, ImportItem>chunk(CHUNK_SIZE, transactionManager)
                .reader(salesCsvReader)
                .processor(salesValidationProcessor)
                .writer(salesImportWriter)
                .build();
    }

    @Bean
    @StepScope
    public FlatFileItemReader<SalesCsvRow> salesCsvReader(SalesProperties properties) {
        return new FlatFileItemReaderBuilder<SalesCsvRow>()
                .name("salesCsvReader")
                .resource(new FileSystemResource(properties.inputFile()))
                .encoding(StandardCharsets.UTF_8.name())
                .linesToSkip(1) // ヘッダー行
                .lineMapper(new SalesCsvLineMapper())
                .build();
    }

    @Bean
    @StepScope
    public SalesImportWriter salesImportWriter(SalesProperties properties, SqlSessionFactory sqlSessionFactory) {
        MyBatisBatchItemWriter<Sales> salesWriter = new MyBatisBatchItemWriterBuilder<Sales>()
                .sqlSessionFactory(sqlSessionFactory)
                .statementId(SalesMapper.INSERT)
                .build();

        FlatFileItemWriter<SalesError> errorWriter = new FlatFileItemWriterBuilder<SalesError>()
                .name("salesErrorWriter")
                .resource(new FileSystemResource(properties.errorFile()))
                .encoding(StandardCharsets.UTF_8.name())
                .lineSeparator(CsvUtils.LINE_SEPARATOR)
                .headerCallback(writer -> writer.write(
                        CsvUtils.toLine(List.of("行番号", "売上日", "店舗コード", "商品コード", "数量", "単価", "エラー理由"))))
                .lineAggregator(error -> CsvUtils.toLine(error.toCsvValues()))
                .build();

        return new SalesImportWriter(salesWriter, errorWriter);
    }
}
