"""売上CSV集計バッチの起動処理（Java: SalesBatchApplication）。

    python -m salesbatch [--input-file=...] [clear=true]

key=value 形式の引数はジョブパラメータ、--xxx はパスの設定（Java の --sales.xxx に相当）。
ジョブの結果を終了コードとして返す（正常:0、ジョブ失敗:5 … Java（Spring Boot）と同じ値）。
"""

import argparse
import logging
import sys
from pathlib import Path

from salesbatch.batch.job import BatchStatus, run_job
from salesbatch.config import SalesProperties

EXIT_COMPLETED = 0
EXIT_FAILED = 5

LOG_FORMAT = "%(asctime)s %(levelname)5s %(process)d --- [sales-batch] %(name)-36s : %(message)s"


def parse_args(argv: list[str]) -> tuple[SalesProperties, dict[str, str]]:
    defaults = SalesProperties()
    parser = argparse.ArgumentParser(prog="python -m salesbatch", description="売上CSV集計バッチ")
    parser.add_argument("--input-file", type=Path, default=defaults.input_file)
    parser.add_argument("--error-file", type=Path, default=defaults.error_file)
    parser.add_argument("--summary-file", type=Path, default=defaults.summary_file)
    parser.add_argument("--db-file", type=Path, default=defaults.db_file)
    parser.add_argument("--log-file", default=str(defaults.log_file), help="空文字にするとファイルに出力しない")
    parser.add_argument("job_parameters", nargs="*", metavar="key=value", help="ジョブパラメータ（例: clear=true）")
    args = parser.parse_args(argv)

    job_parameters = {}
    for parameter in args.job_parameters:
        key, sep, value = parameter.partition("=")
        if not sep or not key:
            parser.error(f"ジョブパラメータは key=value 形式で指定してください: {parameter}")
        job_parameters[key] = value

    properties = SalesProperties(
        input_file=args.input_file,
        error_file=args.error_file,
        summary_file=args.summary_file,
        db_file=args.db_file,
        log_file=Path(args.log_file) if args.log_file else None,
    )
    return properties, job_parameters


def configure_logging(log_file: Path | None) -> None:
    # 絵文字などコンソールの文字コードで表せない文字があってもログ出力で落ちないようにする
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=handlers, force=True)


def main(argv: list[str] | None = None) -> int:
    properties, job_parameters = parse_args(sys.argv[1:] if argv is None else argv)
    configure_logging(properties.log_file)
    execution = run_job(properties, job_parameters)
    return EXIT_COMPLETED if execution.status == BatchStatus.COMPLETED else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
