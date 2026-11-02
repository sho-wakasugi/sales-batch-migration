"""Java: FieldValidatorTest と同じ観点のテスト。"""

import pytest

from salesbatch.common.exceptions import ValidationException
from salesbatch.common.validation import FieldValidator


def test_is_blank_noneや空白はtrue():
    assert FieldValidator.is_blank(None)
    assert FieldValidator.is_blank("")
    assert FieldValidator.is_blank("  ")
    assert not FieldValidator.is_blank("a")


@pytest.mark.parametrize("value", ["0", "1", "-5", "123456", "9223372036854775807"])
def test_is_integer_整数はtrue(value):
    assert FieldValidator.is_integer(value)


@pytest.mark.parametrize("value", ["", "abc", "1.5", "1e3", "+1", " 1", "１", "9223372036854775808"])
def test_is_integer_整数でなければfalse(value):
    assert not FieldValidator.is_integer(value)


@pytest.mark.parametrize("value", ["2026-01-01", "2026-12-31", "2024-02-29"])
def test_is_date_正しい日付はtrue(value):
    assert FieldValidator.is_date(value)


@pytest.mark.parametrize(
    "value", ["2026/01/01", "2026-1-1", "20260101", "2026-02-30", "2026-02-29", "2026-13-01", "abcd-ef-gh"]
)
def test_is_date_形式誤りや存在しない日付はfalse(value):
    assert not FieldValidator.is_date(value)


def test_required_前後の空白を除いた値を返す():
    v = FieldValidator()
    assert v.required(" S001 ", "店舗コード") == "S001"
    assert not v.has_errors()


def test_required_空ならエラー():
    v = FieldValidator()
    assert v.required(" ", "店舗コード") is None
    assert v.errors == ["店舗コードは必須です"]


def test_required_integer_必須エラーのときは数値エラーを重ねない():
    v = FieldValidator()
    assert v.required_integer("", "数量") is None
    assert v.errors == ["数量は必須です"]


def test_required_integer_数値でなければエラー():
    v = FieldValidator()
    assert v.required_integer("1.5", "単価") is None
    assert v.errors == ["単価は整数で入力してください"]


def test_required_date_正しければ日付を返す():
    v = FieldValidator()
    assert v.required_date("2026-01-05", "売上日") == "2026-01-05"
    assert not v.has_errors()


def test_required_date_存在しない日付はエラー():
    v = FieldValidator()
    assert v.required_date("2026-02-30", "売上日") is None
    assert v.errors == ["売上日はyyyy-MM-dd形式の正しい日付で入力してください"]


def test_min_境界値():
    v = FieldValidator()
    v.min(1, 1, "数量")
    assert not v.has_errors()
    v.min(0, 1, "数量")
    assert v.errors == ["数量は1以上で入力してください"]


def test_min_noneなら何もしない():
    v = FieldValidator()
    v.min(None, 1, "数量")
    assert not v.has_errors()


def test_throw_if_invalid_エラーを全件保持した例外を投げる():
    v = FieldValidator()
    v.required("", "店舗コード")
    v.required_integer("x", "数量")
    with pytest.raises(ValidationException) as e:
        v.throw_if_invalid()
    assert e.value.joined_reasons == "店舗コードは必須です;数量は整数で入力してください"


def test_throw_if_invalid_エラーが無ければ何もしない():
    FieldValidator().throw_if_invalid()


# ---------------------------------------------------------------
# ここから Python 版で追加した観点（Java と挙動を合わせた箇所）
# ---------------------------------------------------------------

@pytest.mark.parametrize("value", ["0000-01-01", "0000-02-29", "9999-12-31"])
def test_is_date_0年や9999年もJavaと同じく正しい日付(value):
    assert FieldValidator.is_date(value)


@pytest.mark.parametrize("value", ["1900-02-29", "２０２６-01-05", "2026-01-05\n"])
def test_is_date_平年の2月29日や全角数字や改行付きはfalse(value):
    assert not FieldValidator.is_date(value)


@pytest.mark.parametrize("value", ["1_000", "٣", "-9223372036854775809", "1\n"])
def test_is_integer_Pythonのintなら通るがJavaでは整数でない値はfalse(value):
    assert not FieldValidator.is_integer(value)


def test_is_integer_long最小値はtrue():
    assert FieldValidator.is_integer("-9223372036854775808")


def test_required_NBSPは空白とみなさない():
    v = FieldValidator()
    assert v.required(" S001 ", "店舗コード") == " S001 "
    assert not v.has_errors()


def test_required_全角スペースは空白とみなす():
    v = FieldValidator()
    assert v.required("　", "数量") is None
    assert v.errors == ["数量は必須です"]
