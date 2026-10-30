"""Java: SalesValidationProcessorTest と同じ観点のテスト。"""

from salesbatch.sales.models import Sales, SalesCsvRow, SalesError
from salesbatch.sales.validation_processor import SalesValidationProcessor

processor = SalesValidationProcessor()


def process(*fields):
    return processor.process(SalesCsvRow(2, tuple(fields)))


def test_正常行はSalesに変換し金額を計算する():
    item = process("2026-01-05", " S001 ", "P100", "3", "1200")
    assert item == Sales(2, "2026-01-05", "S001", "P100", 3, 1200, 3600)


def test_単価0は正常():
    assert isinstance(process("2026-01-05", "S001", "P100", "1", "0"), Sales)


def test_数量0はエラー():
    error = process("2026-01-05", "S001", "P100", "0", "100")
    assert isinstance(error, SalesError)
    assert error.reason == "数量は1以上で入力してください"


def test_単価マイナスはエラー():
    error = process("2026-01-05", "S001", "P100", "1", "-1")
    assert isinstance(error, SalesError)
    assert error.reason == "単価は0以上で入力してください"


def test_複数のエラーは項目順にすべて出す():
    error = process("2026/01/05", "", "P100", "abc", "1.5")
    assert isinstance(error, SalesError)
    assert error.reason == (
        "売上日はyyyy-MM-dd形式の正しい日付で入力してください;店舗コードは必須です;"
        "数量は整数で入力してください;単価は整数で入力してください"
    )
    assert error.fields == ("2026/01/05", "", "P100", "abc", "1.5")


def test_項目数が違う行はエラー():
    error = process("2026-01-05", "S001", "P100", "1")
    assert isinstance(error, SalesError)
    assert error.reason == "項目数が不正です（期待値:5、実際:4）"
    assert error.to_csv_values() == [2, "2026-01-05", "S001", "P100", "1", "", "項目数が不正です（期待値:5、実際:4）"]


def test_金額がlongを超える場合はエラー():
    error = process("2026-01-05", "S001", "P100", "9223372036854775807", "2")
    assert isinstance(error, SalesError)
    assert error.reason == "売上金額（数量×単価）が大きすぎます"


# ---------------------------------------------------------------
# Python 版で追加した観点
# ---------------------------------------------------------------

def test_金額がちょうどlong最大値なら正常():
    item = process("2026-01-05", "S001", "P100", "9223372036854775807", "1")
    assert item == Sales(2, "2026-01-05", "S001", "P100", 9223372036854775807, 1, 9223372036854775807)


def test_項目数が多い行は6項目目以降を切り捨てて出力する():
    error = process("2026-01-05", "S001", "P100", "1", "100", "X")
    assert error.to_csv_values() == [2, "2026-01-05", "S001", "P100", "1", "100", "項目数が不正です（期待値:5、実際:6）"]


def test_0年の日付は正常で文字列のまま持つ():
    item = process("0000-01-01", "S001", "P100", "1", "100")
    assert isinstance(item, Sales)
    assert item.sales_date == "0000-01-01"
