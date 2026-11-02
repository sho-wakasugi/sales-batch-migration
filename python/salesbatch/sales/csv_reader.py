"""入力CSVの読込（Java: FlatFileItemReader ＋ SalesCsvLineMapper ＋ DelimitedLineTokenizer）。

標準の csv モジュールは使わない。Java（Spring Batch）とは次の点で結果が変わるため、
Spring Batch の処理をそのまま移植している。
- csv はクォート内の改行で次の行とつなげるが、Java は1行ずつ処理する
- 項目の途中のクォート（P"001）、クォートの外の空白（ "P001" ）、閉じていないクォートの扱い
- Java は「#」で始まる行をコメントとして読み飛ばす（FlatFileItemReader の既定動作）
"""

from collections.abc import Iterator
from pathlib import Path

from salesbatch.common.exceptions import BatchException
from salesbatch.sales.models import SalesCsvRow

DELIMITER = ","
QUOTE = '"'
COMMENT_PREFIX = "#"
LINES_TO_SKIP = 1  # ヘッダー行


class FlatFileParseException(BatchException):
    """行を項目に分割できなかった（Java: FlatFileParseException）。ジョブは異常終了する。"""

    def __init__(self, line_no: int, path: Path, line: str):
        super().__init__(f"Parsing error at line: {line_no} in resource=[{path}], input=[{line}]")
        self.line_no = line_no


def tokenize(line: str) -> list[str]:
    """1行を項目に分割する（Java: DelimitedLineTokenizer.doTokenize の移植）。

    - クォートの中のカンマは区切りとみなさない（クォートは項目の途中にあっても有効）
    - 前後の空白（制御文字を含む ' ' 以下の文字）を除いた結果がクォートで囲まれていれば、
      外側のクォートを外し、"" を " に戻す。囲まれていなければ元の文字列のまま返す
    - 空行は項目0件になる
    """
    tokens: list[str] = []
    in_quoted = False
    last_cut = 0
    length = len(line)
    for i, ch in enumerate(line):
        is_end = i == length - 1
        is_delimiter = ch == DELIMITER
        if (is_delimiter and not in_quoted) or is_end:
            end_position = (length - last_cut) if is_end else (i - last_cut)
            if is_end and is_delimiter:
                end_position -= 1
            tokens.append(_substring_with_trimmed_whitespace_and_quotes_if_quotes_present(line, last_cut, end_position))
            if is_end and is_delimiter:
                tokens.append("")
            last_cut = i + 1
        elif ch == QUOTE:
            in_quoted = not in_quoted
    return tokens


def _substring_with_trimmed_whitespace_and_quotes_if_quotes_present(chars: str, offset: int, count: int) -> str:
    start = offset
    length = count
    while start < start + length - 1 and chars[start] <= " ":
        start += 1
        length -= 1
    while start < start + length and start + length - 1 < len(chars) and chars[start + length - 1] <= " ":
        length -= 1

    if len(chars) >= 2 and chars[start] == QUOTE and chars[start + length - 1] == QUOTE:
        if length < 2:
            # 項目が「"」1文字だけの場合。Java は StringIndexOutOfBoundsException になる
            raise ValueError("quoted field is too short")
        return chars[start + 1:start + length - 1].replace(QUOTE + QUOTE, QUOTE)
    return chars[offset:offset + count]


class SalesCsvReader:
    """入力CSVを1行ずつ読み、SalesCsvRow を返す（Java: FlatFileItemReader）。

    - 文字コードは UTF-8。不正なバイトは U+FFFD に置き換える（Java の InputStreamReader と同じ）
    - 改行は LF / CRLF / CR のいずれも1行の終わりとみなす（Java の BufferedReader.readLine と同じ）
    - 行番号は、ヘッダー・コメント行も含めた物理的な行番号
    """

    def __init__(self, path: Path):
        self._path = path
        self._file = None
        self._line_count = 0

    def open(self) -> None:
        self._file = open(self._path, encoding="utf-8", errors="replace", newline=None)
        self._line_count = 0
        for _ in range(LINES_TO_SKIP):
            self._read_line()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self) -> "SalesCsvReader":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __iter__(self) -> Iterator[SalesCsvRow]:
        while (row := self.read()) is not None:
            yield row

    def read(self) -> SalesCsvRow | None:
        """次の1行を返す。ファイルの終わりなら None。"""
        line = self._read_line()
        if line is None:
            return None
        try:
            return SalesCsvRow(self._line_count, tuple(tokenize(line)))
        except ValueError as e:
            raise FlatFileParseException(self._line_count, self._path, line) from e

    def _read_line(self) -> str | None:
        """コメント行を飛ばして1行読む（Java: FlatFileItemReader.readLine）。"""
        while True:
            line = self._file.readline()
            if line == "":
                return None
            self._line_count += 1
            line = line.removesuffix("\n")
            if not line.startswith(COMMENT_PREFIX):
                return line
