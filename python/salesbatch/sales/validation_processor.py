"""入力CSVの1行をチェックして変換する（Java: SalesValidationProcessor）。

正常なら Sales、エラーなら SalesError に変換する。
エラーがあっても例外で止めず、エラー行として後続に渡す。
"""

from salesbatch.common import javacompat
from salesbatch.common.exceptions import ValidationException
from salesbatch.common.validation import FieldValidator
from salesbatch.sales.models import COLUMN_COUNT, ImportItem, Sales, SalesCsvRow, SalesError


class SalesValidationProcessor:

    def process(self, row: SalesCsvRow) -> ImportItem:
        try:
            return self.to_sales(row)
        except ValidationException as e:
            return SalesError(row.line_no, row.fields, e.joined_reasons)

    def to_sales(self, row: SalesCsvRow) -> Sales:
        """チェックして Sales に変換する。エラーがあれば ValidationException を投げる。"""
        v = FieldValidator()

        # 項目数が違う場合は、どの値が何の項目か判断できないので個別チェックはしない
        if len(row.fields) != COLUMN_COUNT:
            v.add_error(f"項目数が不正です（期待値:{COLUMN_COUNT}、実際:{len(row.fields)}）")
            v.throw_if_invalid()

        sales_date = v.required_date(row.field(0), "売上日")
        store_code = v.required(row.field(1), "店舗コード")
        product_code = v.required(row.field(2), "商品コード")
        quantity = v.required_integer(row.field(3), "数量")
        v.min(quantity, 1, "数量")
        unit_price = v.required_integer(row.field(4), "単価")
        v.min(unit_price, 0, "単価")
        v.throw_if_invalid()

        # Python の int はあふれないので、Java の Math.multiplyExact と同じく long の範囲を確認する
        amount = quantity * unit_price
        if not javacompat.in_long_range(amount):
            v.add_error("売上金額（数量×単価）が大きすぎます")
            v.throw_if_invalid()

        return Sales(row.line_no, sales_date, store_code, product_code, quantity, unit_price, amount)
