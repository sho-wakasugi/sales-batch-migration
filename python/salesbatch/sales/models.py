"""売上の型（Java: SalesCsvRow / Sales / SalesError / ImportItem / SalesSummary）。"""

from dataclasses import dataclass

# 項目数（売上日、店舗コード、商品コード、数量、単価）
COLUMN_COUNT = 5


@dataclass(frozen=True)
class SalesCsvRow:
    """入力CSVの1行。チェック前なので全項目を文字列のまま持つ。

    line_no: 入力ファイル上の行番号（ヘッダーを1行目として数える）
    fields:  項目の値（CSVのクォートは外した状態、空白は未加工）
    """

    line_no: int
    fields: tuple[str, ...]

    def field(self, index: int) -> str | None:
        """index 番目の値。項目が足りない場合は None。"""
        return self.fields[index] if index < len(self.fields) else None


@dataclass(frozen=True)
class Sales:
    """入力チェックを通過した売上データ（売上テーブルの1行）。

    sales_date は yyyy-MM-dd の文字列で持つ（datetime.date は0年を扱えないため）。
    amount は売上金額（数量 × 単価）。
    """

    line_no: int
    sales_date: str
    store_code: str
    product_code: str
    quantity: int
    unit_price: int
    amount: int


@dataclass(frozen=True)
class SalesError:
    """入力チェックでエラーになった行。error.csv に出力する。

    reason はエラー理由（複数ある場合は「;」区切り）。
    """

    line_no: int
    fields: tuple[str, ...]
    reason: str

    def to_csv_values(self) -> list[object]:
        """error.csv の1行分の値（行番号、5項目、エラー理由）。

        項目数が足りない場合は空欄で埋め、多い場合は6項目目以降を切り捨てる。
        """
        padded = [self.fields[i] if i < len(self.fields) else "" for i in range(COLUMN_COUNT)]
        return [self.line_no, *padded, self.reason]


# 入力チェック後の1行。正常データかエラーのどちらか（Java: sealed interface ImportItem）
type ImportItem = Sales | SalesError


@dataclass(frozen=True)
class SalesSummary:
    """店舗別・月別の集計結果（summary.csv の1行）。sales_month は yyyy-MM。"""

    store_code: str
    sales_month: str
    total_amount: int
    sales_count: int

    def to_csv_values(self) -> list[object]:
        return [self.store_code, self.sales_month, self.total_amount, self.sales_count]
