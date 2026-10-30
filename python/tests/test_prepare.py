"""Java: PrepareTaskletTest と同じ観点のテスト。"""

import pytest

from salesbatch.batch.prepare import prepare
from salesbatch.common.exceptions import InputFileException
from salesbatch.config import SalesProperties


def test_入力ファイルが無ければInputFileExceptionを投げる(tmp_path):
    properties = SalesProperties(
        input_file=tmp_path / "nothing.csv",
        error_file=tmp_path / "error.csv",
        summary_file=tmp_path / "summary.csv",
    )
    with pytest.raises(InputFileException) as e:
        prepare(properties, None, {})
    assert "nothing.csv" in str(e.value)
