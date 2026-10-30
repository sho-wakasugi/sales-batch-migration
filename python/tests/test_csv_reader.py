"""CSV読込のテスト（Python 版で追加）。期待値は Java（Spring Batch）で実際に確認した結果。"""

import pytest

from salesbatch.sales.csv_reader import FlatFileParseException, SalesCsvReader, tokenize


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("a,b,c", ["a", "b", "c"]),
        ("", []),                                             # 空行は0項目
        ("   ", ["   "]),                                     # 空白だけなら1項目（空白は残る）
        (",,,,", ["", "", "", "", ""]),
        ("a,b,", ["a", "b", ""]),                             # 末尾カンマ
        ("a, b ,c", ["a", " b ", "c"]),                       # クォートが無ければ空白は残る
        ('a,"b,c",d', ["a", "b,c", "d"]),                     # クォート内のカンマ
        ('a,"b""c",d', ["a", 'b"c', "d"]),                    # クォート内のクォート
        ('a, "b" ,c', ["a", "b", "c"]),                       # クォートの外の空白は除く
        ('a,"",c', ["a", "", "c"]),                           # 空のクォート
        ('2026-01-11,S001,P"001,0,100', ["2026-01-11", "S001", 'P"001,0,100']),   # 途中のクォート以降は区切らない
        ('2026-01-11,S001,"P001,0,100', ["2026-01-11", "S001", '"P001,0,100']),   # 閉じていないクォートは残る
        ("a, b ,c", ["a", " b ", "c"]),
    ],
)
def test_tokenize_Javaと同じ分割結果(line, expected):
    assert tokenize(line) == expected


def test_tokenize_ダブルクォート1文字だけの項目はエラー():
    with pytest.raises(ValueError):
        tokenize('a,"')


def write(tmp_path, content: bytes):
    path = tmp_path / "in.csv"
    path.write_bytes(content)
    return path


def read_all(path):
    with SalesCsvReader(path) as reader:
        return [(row.line_no, row.fields) for row in reader]


def test_ヘッダーを飛ばし行番号はヘッダーを1行目として数える(tmp_path):
    path = write(tmp_path, "売上日,店舗\na,b\nc,d\n".encode())
    assert read_all(path) == [(2, ("a", "b")), (3, ("c", "d"))]


def test_シャープで始まる行はコメントとして飛ばすが行番号は進む(tmp_path):
    path = write(tmp_path, b"h\n1\n#2\n #3\n4\n")
    assert read_all(path) == [(2, ("1",)), (4, (" #3",)), (5, ("4",))]


def test_LF_CRLF_CRのどれでも行が終わり最終行の改行は無くてもよい(tmp_path):
    path = write(tmp_path, b"h\r\na\nb\r\nc\rd")
    assert read_all(path) == [(2, ("a",)), (3, ("b",)), (4, ("c",)), (5, ("d",))]


def test_クォート内の改行で次の行とつなげない(tmp_path):
    path = write(tmp_path, b'h\n"a\nb"\n')
    assert read_all(path) == [(2, ('"a',)), (3, ('b"',))]


def test_不正なUTF8バイトはU_FFFDに置き換える(tmp_path):
    path = write(tmp_path, b"h\nP\xff1\n")
    assert read_all(path) == [(2, ("P�1",))]


def test_分割できない行はFlatFileParseException(tmp_path):
    path = write(tmp_path, b'h\nok\nx,"\n')
    with SalesCsvReader(path) as reader:
        assert reader.read().line_no == 2
        with pytest.raises(FlatFileParseException) as e:
            reader.read()
    assert e.value.line_no == 3
    assert "Parsing error at line: 3" in str(e.value)
