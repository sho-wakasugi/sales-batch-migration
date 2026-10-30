"""入力チェックの共通部品（Java: FieldValidator）。

1行分のチェックごとにインスタンスを作り、各項目をチェックしてエラー理由を貯めていく。
最後に throw_if_invalid() を呼ぶと、エラーがあれば ValidationException を投げる。

各チェックメソッドは、値が正しければ変換後の値を、エラーなら None を返す。
必須エラーのときは、その項目の以降のチェック（数値・日付など）は行わない。
"""

import calendar
import re

from salesbatch.common import javacompat
from salesbatch.common.exceptions import ValidationException

# 日付形式（ゼロ埋めした yyyy-MM-dd）
DATE_PATTERN = "yyyy-MM-dd"

# \d は全角数字などにも一致するため [0-9] を使う
_INTEGER_PATTERN = re.compile(r"-?[0-9]+")
_DATE_SHAPE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


class FieldValidator:

    def __init__(self) -> None:
        self._errors: list[str] = []

    # ---------------------------------------------------------------
    # 判定だけを行う static メソッド（単体でも使える）
    # ---------------------------------------------------------------

    @staticmethod
    def is_blank(value: str | None) -> bool:
        """None・空文字・空白のみなら True。"""
        return javacompat.is_blank(value)

    @staticmethod
    def is_integer(value: str | None) -> bool:
        """符号（-）付きも含む整数で、long の範囲に収まれば True。"""
        if value is None or not _INTEGER_PATTERN.fullmatch(value):
            return False
        return javacompat.in_long_range(int(value))

    @staticmethod
    def is_date(value: str | None) -> bool:
        """yyyy-MM-dd 形式で、実在する日付なら True。

        datetime.date は0年を扱えないが、Java（LocalDate）は 0000-01-01 も正しい日付とするため、
        年月日を自前で検証する（うるう年は先発グレゴリオ暦の規則で、0年はうるう年）。
        """
        if value is None or not _DATE_SHAPE_PATTERN.fullmatch(value):
            return False
        year, month, day = int(value[0:4]), int(value[5:7]), int(value[8:10])
        if not 1 <= month <= 12:
            return False
        days = 29 if month == 2 and calendar.isleap(year) else _DAYS_IN_MONTH[month - 1]
        return 1 <= day <= days

    # ---------------------------------------------------------------
    # エラー理由を貯めながらチェックするメソッド
    # ---------------------------------------------------------------

    def required(self, value: str | None, label: str) -> str | None:
        """必須チェック。正しければ前後の空白を除いた値を返す。"""
        if self.is_blank(value):
            self._errors.append(f"{label}は必須です")
            return None
        return javacompat.strip(value)

    def required_integer(self, value: str | None, label: str) -> int | None:
        """必須＋整数チェック。正しければ整数値を返す。"""
        v = self.required(value, label)
        if v is None:
            return None
        if not self.is_integer(v):
            self._errors.append(f"{label}は整数で入力してください")
            return None
        return int(v)

    def required_date(self, value: str | None, label: str) -> str | None:
        """必須＋日付チェック。正しければ yyyy-MM-dd の文字列を返す。"""
        v = self.required(value, label)
        if v is None:
            return None
        if not self.is_date(v):
            self._errors.append(f"{label}は{DATE_PATTERN}形式の正しい日付で入力してください")
            return None
        return v

    def min(self, value: int | None, minimum: int, label: str) -> None:
        """最小値チェック。value が None（前のチェックでエラー）の場合は何もしない。"""
        if value is not None and value < minimum:
            self._errors.append(f"{label}は{minimum}以上で入力してください")

    def add_error(self, reason: str) -> None:
        """上記以外のチェックで見つかったエラー理由を追加する。"""
        self._errors.append(reason)

    def has_errors(self) -> bool:
        return bool(self._errors)

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    def throw_if_invalid(self) -> None:
        """エラーが1件以上あれば ValidationException を投げる。"""
        if self._errors:
            raise ValidationException(self._errors)
