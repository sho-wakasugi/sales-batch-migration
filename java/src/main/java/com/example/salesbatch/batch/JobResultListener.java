package com.example.salesbatch.batch;

import com.example.salesbatch.sales.SalesImportWriter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.BatchStatus;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobExecutionListener;
import org.springframework.batch.core.StepExecution;
import org.springframework.batch.item.ExecutionContext;
import org.springframework.stereotype.Component;

/**
 * ジョブ開始時に開始メッセージを、終了時に処理件数（読込・登録・エラー・集計出力）をログに出す。
 */
@Component
public class JobResultListener implements JobExecutionListener {

    private static final Logger log = LoggerFactory.getLogger(JobResultListener.class);

    @Override
    public void beforeJob(JobExecution jobExecution) {
        Object clear = jobExecution.getJobParameters().getParameters().containsKey(PrepareTasklet.CLEAR_PARAMETER)
                ? jobExecution.getJobParameters().getString(PrepareTasklet.CLEAR_PARAMETER)
                : "指定なし";
        log.info("========== バッチ実行します ==========");
        log.info("ジョブ名: {}、clear: {}", jobExecution.getJobInstance().getJobName(), clear);
    }

    @Override
    public void afterJob(JobExecution jobExecution) {
        StepExecution importStep = findStep(jobExecution, SalesJobConfig.IMPORT_STEP);
        StepExecution summaryStep = findStep(jobExecution, SalesJobConfig.SUMMARY_STEP);

        log.info("========== 処理結果 ==========");
        if (importStep != null) {
            ExecutionContext context = importStep.getExecutionContext();
            long readCount = importStep.getReadCount();
            long insertCount = context.getLong(SalesImportWriter.INSERT_COUNT_KEY, 0L);
            long errorCount = context.getLong(SalesImportWriter.ERROR_COUNT_KEY, 0L);
            log.info("読込件数　: {}", readCount);
            log.info("登録件数　: {}", insertCount);
            log.info("エラー件数: {}", errorCount);
            if (readCount != insertCount + errorCount) {
                log.warn("読込件数と（登録件数＋エラー件数）が一致しません");
            }
        } else {
            log.info("取込処理は実行されませんでした");
        }
        if (summaryStep != null) {
            log.info("集計出力件数: {}", summaryStep.getWriteCount());
        }
        log.info("終了ステータス: {}", jobExecution.getStatus());

        if (jobExecution.getStatus() != BatchStatus.COMPLETED) {
            for (Throwable e : jobExecution.getAllFailureExceptions()) {
                log.error("異常終了しました: {}", e.getMessage());
            }
        }
    }

    private static StepExecution findStep(JobExecution jobExecution, String stepName) {
        return jobExecution.getStepExecutions().stream()
                .filter(step -> step.getStepName().equals(stepName))
                .findFirst()
                .orElse(null);
    }
}
