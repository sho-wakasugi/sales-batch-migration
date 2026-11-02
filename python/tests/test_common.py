"""Java 互換処理と CSV 出力のテスト（Python 版で追加）。"""

import pytest

from salesbatch.common import csv_utils, javacompat


@pytest.mark.parametrize("ch", [" ", "\t", "\n", "\r", "\u000b", "\u000c", "\u001f", "　", " "])
def test_is_whitespace_Javaで空白とみなす文字(ch):
    assert javacompat.is_whitespace(ch)


@pytest.mark.parametrize("ch", [" ", " ", " ", "\u0085", "a", "​"])
def test_is_whitespace_Javaで空白とみなさない文字(ch):
    # \u0085 と ​ は Python の isspace() / strip() では空白扱いになる
    assert not javacompat.is_whitespace(ch)


def test_strip_NBSPは残しタブと全角スペースは除く():
    assert javacompat.strip("\t　 S001  \t") == "S001 "


def test_utf16_collation_絵文字は半角カナより前():
    # UTF-8 のバイト順だと逆になる
    assert javacompat.utf16_collation("S\U0001F600", "Sｱ") < 0
    assert "S\U0001F600".encode() > "Sｱ".encode()


def test_utf16_collation_同じなら0():
    assert javacompat.utf16_collation("S001", "S001") == 0


@pytest.mark.parametrize(
    ("value", "expected"),
    [("a", "a"), ("a,b", '"a,b"'), ('a"b', '"a""b"'), ("a\nb", '"a\nb"'), ("a\rb", '"a\rb"'),
     (" a ", " a "), ("", ""), (None, ""), (123, "123")],
)
def test_escape(value, expected):
    assert csv_utils.escape(value) == expected


def test_to_line():
    assert csv_utils.to_line([1, "P,1", "", "理由"]) == '1,"P,1",,理由'
