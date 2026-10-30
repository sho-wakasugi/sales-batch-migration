"""共通例外（Java: common/exception パッケージ）。"""


class BatchException(Exception):
    """本バッチで発生する業務例外の基底クラス（Java: BatchException）。"""


class InputFileException(BatchException):
    """入力ファイルが存在しない・読めない場合の例外。ジョブは異常終了する（Java: InputFileException）。"""


class ValidationException(BatchException):
    """入力チェック違反。1行の中で見つかったエラー理由をすべて保持する（Java: ValidationException）。"""

    REASON_DELIMITER = ";"

    def __init__(self, reasons: list[str]):
        self.reasons = list(reasons)
        super().__init__(self.joined_reasons)

    @property
    def joined_reasons(self) -> str:
        """エラー理由を「;」区切りの1つの文字列にして返す（Java: getJoinedReasons）。"""
        return self.REASON_DELIMITER.join(self.reasons)
