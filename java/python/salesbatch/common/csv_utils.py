"""CSV出力の共通部品（Java: CsvUtils）。

値にカンマ・ダブルクォート・改行が含まれる場合だけダブルクォートで囲み、中のダブルクォートは2つ重ねる。

標準の csv.writer は使わない。項目が空欄1つだけの行を "" と出力するなど細部が Java と異なり、
Python のバージョンで挙動が変わる可能性もあるため、Java と同じ規則をそのまま実装している。
"""

from collections.abc import Iterable

DELIMITER = ","
LINE_SEPARATOR = "\n"


def escape(value: object) -> str:
    s = "" if value is None else str(value)
    if "," in s or '"' in s or "\n" in s or "\r" in s:
        return '"' + s.replace('"', '""') + '"'
    return s


def to_line(values: Iterable[object]) -> str:
    """値のリストを1行分のCSV文字列にする（改行は含まない）。"""
    return DELIMITER.join(escape(v) for v in values)
