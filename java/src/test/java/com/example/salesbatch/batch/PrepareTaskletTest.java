package com.example.salesbatch.batch;

import com.example.salesbatch.SalesProperties;
import com.example.salesbatch.common.exception.InputFileException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class PrepareTaskletTest {

    @Test
    void 入力ファイルが無ければInputFileExceptionを投げる(@TempDir Path dir) {
        SalesProperties properties = new SalesProperties(
                dir.resolve("nothing.csv"), dir.resolve("error.csv"), dir.resolve("summary.csv"));
        PrepareTasklet tasklet = new PrepareTasklet(properties, null);

        InputFileException e = assertThrows(InputFileException.class, () -> tasklet.execute(null, null));
        assertTrue(e.getMessage().contains("nothing.csv"));
    }
}
