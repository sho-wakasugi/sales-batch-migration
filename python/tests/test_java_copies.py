"""Java版のファイルのコピーが、元のファイルと同じ内容であることを確かめる。

python フォルダは Java版のファイルのコピーを持っている（python フォルダだけでテストを動かすため）。
Java版の側を変えたのにコピーを更新し忘れた場合に、ここで気づけるようにする。
java フォルダが無い場合（python フォルダだけを取り出したときなど）はスキップする。
"""

from pathlib import Path

import pytest

PYTHON_ROOT = Path(__file__).resolve().parents[1]
JAVA_ROOT = PYTHON_ROOT.parent / "java"
JAVA_INTEGRATION = Path("src/test/resources/integration")
COPY_INTEGRATION = Path("tests/data/java_integration")

# （python フォルダ内のコピー, java フォルダ内の元ファイル）
COPIES = [
    (Path("input/sales.csv"), Path("input/sales.csv")),
    (COPY_INTEGRATION / "sales.csv", JAVA_INTEGRATION / "sales.csv"),
    (COPY_INTEGRATION / "expected_error.csv", JAVA_INTEGRATION / "expected_error.csv"),
    (COPY_INTEGRATION / "expected_summary.csv", JAVA_INTEGRATION / "expected_summary.csv"),
]

pytestmark = pytest.mark.skipif(not JAVA_ROOT.is_dir(), reason="java フォルダが無いため比較できない")


@pytest.mark.parametrize(("copy", "original"), COPIES, ids=[str(c) for c, _ in COPIES])
def test_コピーがJava版の元ファイルとバイト単位で同じ(copy, original):
    assert (PYTHON_ROOT / copy).read_bytes() == (JAVA_ROOT / original).read_bytes()


def test_Java版のテスト用ファイルがすべてコピーされている():
    originals = {p.name for p in (JAVA_ROOT / JAVA_INTEGRATION).iterdir()}
    copies = {p.name for p in (PYTHON_ROOT / COPY_INTEGRATION).iterdir()}
    assert copies == originals
