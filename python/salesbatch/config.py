"""設定値（Java: SalesProperties ＋ application.yml）。

パスは実行時のカレントフォルダからの相対パス。python フォルダで実行する前提で、
入力は Java 版と同じ input/sales.csv を使い、出力・DB・ログは python フォルダの下に作る。
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SalesProperties:
    input_file: Path = Path("../input/sales.csv")
    error_file: Path = Path("output/error.csv")
    summary_file: Path = Path("output/summary.csv")
    db_file: Path = Path("data/salesdb.sqlite3")
    log_file: Path | None = Path("logs/sales-batch.log")
