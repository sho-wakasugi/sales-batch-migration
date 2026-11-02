"""設定値（Java: SalesProperties ＋ application.yml）。

パスは実行時のカレントフォルダからの相対パス（プロジェクトのフォルダで実行する前提）。
input/sales.csv は Java版（sales-batch）の input/sales.csv と同じ内容のコピー。
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SalesProperties:
    input_file: Path = Path("input/sales.csv")
    error_file: Path = Path("output/error.csv")
    summary_file: Path = Path("output/summary.csv")
    db_file: Path = Path("data/salesdb.sqlite3")
    log_file: Path | None = Path("logs/sales-batch.log")
