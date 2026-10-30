package com.example.salesbatch.batch;

import com.example.salesbatch.SalesProperties;
import com.example.salesbatch.common.exception.InputFileException;
import com.example.salesbatch.sales.SalesMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.StepContribution;
import org.springframework.batch.core.scope.context.ChunkContext;
import org.springframework.batch.core.step.tasklet.Tasklet;
import org.springframework.batch.repeat.RepeatStatus;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 前処理。
 * <ul>
 *   <li>入力ファイルがあるか確認する（無ければ InputFileException で異常終了）</li>
 *   <li>出力先フォルダを作る</li>
 *   <li>ジョブパラメータ clear=true のときだけ売上テーブルを全件削除する（現新比較用）</li>
 * </ul>
 */
@Component
public class PrepareTasklet implements Tasklet {

    /** 売上テーブルを全件削除するかどうかのジョブパラメータ名 */
    public static final String CLEAR_PARAMETER = "clear";

    private static final Logger log = LoggerFactory.getLogger(PrepareTasklet.class);

    private final SalesProperties properties;
    private final SalesMapper salesMapper;

    public PrepareTasklet(SalesProperties properties, SalesMapper salesMapper) {
        this.properties = properties;
        this.salesMapper = salesMapper;
    }

    @Override
    public RepeatStatus execute(StepContribution contribution, ChunkContext chunkContext) throws IOException {
        Path inputFile = properties.inputFile();
        if (!Files.isRegularFile(inputFile) || !Files.isReadable(inputFile)) {
            throw new InputFileException("入力ファイルが見つからないか読み込めません: " + inputFile.toAbsolutePath());
        }
        log.info("入力ファイル: {}", inputFile.toAbsolutePath());

        createParentDirectory(properties.errorFile());
        createParentDirectory(properties.summaryFile());

        Object clear = chunkContext.getStepContext().getJobParameters().get(CLEAR_PARAMETER);
        if ("true".equalsIgnoreCase(String.valueOf(clear))) {
            int deleted = salesMapper.deleteAll();
            log.info("clear=true のため売上テーブルを全件削除しました（{}件）", deleted);
        } else {
            log.info("売上テーブルは削除せず追加登録します（登録済み {}件）", salesMapper.countAll());
        }
        return RepeatStatus.FINISHED;
    }

    private static void createParentDirectory(Path file) throws IOException {
        Path parent = file.toAbsolutePath().getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
    }
}
