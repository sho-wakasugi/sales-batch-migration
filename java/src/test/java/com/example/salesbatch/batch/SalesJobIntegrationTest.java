package com.example.salesbatch.batch;

import com.example.salesbatch.sales.SalesImportWriter;
import org.junit.jupiter.api.Test;
import org.springframework.batch.core.BatchStatus;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.StepExecution;
import org.springframework.batch.test.JobLauncherTestUtils;
import org.springframework.batch.test.context.SpringBatchTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 小さな入力CSVでジョブ全体を実行し、出力ファイルと件数を検証する。
 */
@SpringBatchTest
@SpringBootTest(properties = {
        "spring.batch.job.enabled=false",
        "spring.datasource.url=jdbc:h2:mem:testdb;DB_CLOSE_DELAY=-1",
        "logging.file.name="
})
class SalesJobIntegrationTest {

    private static final Path RESOURCES = Path.of("src/test/resources/integration");
    private static final Path OUTPUT = Path.of("target/test-output");

    @Autowired
    private JobLauncherTestUtils jobLauncherTestUtils;

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("sales.input-file", () -> RESOURCES.resolve("sales.csv").toString());
        registry.add("sales.error-file", () -> OUTPUT.resolve("error.csv").toString());
        registry.add("sales.summary-file", () -> OUTPUT.resolve("summary.csv").toString());
    }

    // 注意: @SpringBatchTest は JobExecution を返すメソッドをテスト用ファクトリとみなすため、
    // ヘルパーは JobParameters を返す形にしている
    private JobParameters parameters(boolean clear) {
        var builder = jobLauncherTestUtils.getUniqueJobParametersBuilder();
        if (clear) {
            builder.addString(PrepareTasklet.CLEAR_PARAMETER, "true");
        }
        return builder.toJobParameters();
    }

    private static String read(Path path) throws IOException {
        return Files.readString(path, StandardCharsets.UTF_8);
    }

    @Test
    void clear指定で実行すると出力ファイルと件数が期待どおりになる() throws Exception {
        JobExecution execution = jobLauncherTestUtils.launchJob(parameters(true));

        assertEquals(BatchStatus.COMPLETED, execution.getStatus());
        assertEquals(read(RESOURCES.resolve("expected_error.csv")), read(OUTPUT.resolve("error.csv")));
        assertEquals(read(RESOURCES.resolve("expected_summary.csv")), read(OUTPUT.resolve("summary.csv")));

        StepExecution importStep = execution.getStepExecutions().stream()
                .filter(s -> s.getStepName().equals(SalesJobConfig.IMPORT_STEP))
                .findFirst().orElseThrow();
        assertEquals(11, importStep.getReadCount());
        assertEquals(7, importStep.getExecutionContext().getLong(SalesImportWriter.INSERT_COUNT_KEY));
        assertEquals(4, importStep.getExecutionContext().getLong(SalesImportWriter.ERROR_COUNT_KEY));
    }

    @Test
    void clear指定なしで再実行すると売上が蓄積される() throws Exception {
        jobLauncherTestUtils.launchJob(parameters(true));
        JobExecution execution = jobLauncherTestUtils.launchJob(parameters(false));

        assertEquals(BatchStatus.COMPLETED, execution.getStatus());
        assertEquals("""
                店舗コード,年月,売上金額,件数
                S001,2026-01,3360,4
                S001,2026-02,700,4
                S002,2025-12,9600,2
                S002,2026-01,720,2
                S010,2026-03,1200,2
                """, read(OUTPUT.resolve("summary.csv")));
    }
}
