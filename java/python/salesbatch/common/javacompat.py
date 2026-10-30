"""Java と結果を一致させるための互換処理。

Python の標準の動きが Java と異なる箇所を、Java の仕様どおりに実装したもの。
（なぜ必要かは docs/migration-notes.md を参照）
"""

import unicodedata

# Java の long の範囲
LONG_MIN = -(2**63)
LONG_MAX = 2**63 - 1

# Character.isWhitespace が true になる制御文字
_JAVA_WHITESPACE_CONTROLS = frozenset("\t\n\u000b\u000c\r\u001c\u001d\u001e\u001f")
# 空白の分類（Zs）でも Character.isWhitespace が false になる「改行しない空白」
_JAVA_NON_BREAKING_SPACES = frozenset("   ")


def is_whitespace(ch: str) -> bool:
    """Java の Character.isWhitespace と同じ判定。

    Python の str.isspace() / str.strip() は NBSP（U+00A0）なども空白とみなすが、Java はみなさない。
    """
    if ch in _JAVA_WHITESPACE_CONTROLS:
        return True
    if ch in _JAVA_NON_BREAKING_SPACES:
        return False
    return unicodedata.category(ch) in ("Zs", "Zl", "Zp")


def strip(value: str) -> str:
    """Java の String.strip() と同じ（前後の Character.isWhitespace な文字を除く）。"""
    start, end = 0, len(value)
    while start < end and is_whitespace(value[start]):
        start += 1
    while end > start and is_whitespace(value[end - 1]):
        end -= 1
    return value[start:end]


def is_blank(value: str | None) -> bool:
    """Java の String.isBlank() と同じ（null も true とする）。"""
    return value is None or strip(value) == ""


def in_long_range(value: int) -> bool:
    return LONG_MIN <= value <= LONG_MAX


def utf16_collation(a: str, b: str) -> int:
    """Java の String.compareTo（UTF-16 の単位で比較）と同じ順序を返す SQLite 用の照合順序。

    H2 の文字列比較はこの順序になる。SQLite の標準（BINARY）は UTF-8 のバイト順なので、
    絵文字などの補助文字（U+10000 以上）と U+E000〜U+FFFF の文字の順序が Java と逆になる。
    """
    ka = a.encode("utf-16-be", "surrogatepass")
    kb = b.encode("utf-16-be", "surrogatepass")
    return (ka > kb) - (ka < kb)
