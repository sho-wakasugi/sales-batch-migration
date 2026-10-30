# 売上CSV集計バッチ（Python版）

Java版（リポジトリ直下）の売上CSV集計バッチを Python に移行したものです。
同じ入力に対して Java版と**同じ結果**（error.csv、summary.csv、売上テーブル、件数、終了コード）になることを目標にしています。

- 入出力の仕様：リポジトリ直下の [README.md](../README.md) の「入出力仕様」
- 移行で注意した点・判断した点：[docs/migration-notes.md](../docs/migration-notes.md)

## 前提

- Python 3.12
- バッチ本体は標準ライブラリだけで動きます。テストには pytest を使います

## 準備（初回のみ、PowerShell）

`python` フォルダで実行します。

```powershell
cd python
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 実行

`python` フォルダで実行します。

```powershell
# 通常実行（売上テーブルにデータを追加登録する）
.venv\Scripts\python.exe -m salesbatch

# 比較検証用（売上テーブルを全件削除してから登録する）
.venv\Scripts\python.exe -m salesbatch clear=true
```

バッチ本体は標準ライブラリだけで動くので、`.venv\Scripts\python.exe` の代わりに `python` で実行しても構いません。

| 項目 | 既定のパス（python フォルダから見た相対パス） | 変更するオプション |
|---|---|---|
| 入力 | `../input/sales.csv`（Java版と同じファイル） | `--input-file=...` |
| エラー出力 | `output/error.csv` | `--error-file=...` |
| 集計出力 | `output/summary.csv` | `--summary-file=...` |
| DB（SQLite） | `data/salesdb.sqlite3` | `--db-file=...` |
| ログ | `logs/sales-batch.log` | `--log-file=...`（空にするとファイルに出さない） |

終了コードは Java版と同じで、正常終了なら 0、異常終了なら 5 です。

### 結果の確認

```powershell
Get-Content -Encoding UTF8 output\summary.csv
Get-Content -Encoding UTF8 output\error.csv
```

DB の中身は、Python の sqlite3 モジュールで見られます。

```powershell
.venv\Scripts\python.exe -c "import sqlite3; c = sqlite3.connect('data/salesdb.sqlite3'); print(c.execute('SELECT COUNT(*) FROM sales').fetchone()); [print(r) for r in c.execute('SELECT * FROM sales ORDER BY id LIMIT 5')]"
```

## テスト

```powershell
.venv\Scripts\python.exe -m pytest
```

- Java の JUnit テストと同じ観点のテストがあります。期待値ファイルは Java側のもの（`src/test/resources/integration`）をそのまま使っています
- 境界ケースのテストもあります。`tests/data/` の入力を Java版で実際に実行した出力（`tests/data/expected/`）と、バイト単位で一致するかを確かめます

## 現新比較（Java版と Python版の結果を突き合わせる）

リポジトリ直下で実行します。先に Java版をビルドしておいてください（`.\mvnw.cmd package`）。

```powershell
.\python\tools\compare.ps1                              # 既定の5ファイルで比較
.\python\tools\compare.ps1 -InputFiles input\sales.csv  # 入力を指定して比較
```

入力ファイルごとに、両方を新しい DB で `clear=true` を付けて実行し、次の項目を比較します。

| 比較項目 | 比較方法 |
|---|---|
| error.csv / summary.csv | バイト単位 |
| 売上テーブル | id と登録日時を除き、行番号順に CSV へ書き出して比較 |
| ログの件数と終了ステータス | 件数・ステータスの行を比較 |
| 終了コード | 値を比較 |

出力は `python\output\compare\<入力名>\{java,python}` に残ります。

```
入力                                       結果 error.csv summary.csv 売上テーブル 件数ログ 終了コード
input\sales.csv                            一致 OK        OK          OK           OK       0 / 0
python\tests\data\edge_cases.csv           一致 OK        OK          OK           OK       0 / 0
python\tests\data\edge_comment.csv         一致 OK        OK          OK           OK       0 / 0
python\tests\data\failure_sum_overflow.csv 一致 OK        OK          OK           OK       5 / 5
python\tests\data\failure_single_quote.csv 一致 OK        OK          OK           OK       5 / 5
```

## ディレクトリ構成（Java との対応）

```
python/
├─ salesbatch/
│   ├─ __main__.py                 起動・引数・終了コード   ← SalesBatchApplication
│   ├─ config.py                   設定値                   ← SalesProperties / application.yml
│   ├─ schema.sql                  売上テーブル定義         ← schema.sql
│   ├─ common/
│   │   ├─ exceptions.py           共通例外                 ← common/exception/*
│   │   ├─ validation.py           入力チェック             ← FieldValidator
│   │   ├─ csv_utils.py            CSV出力                  ← CsvUtils
│   │   └─ javacompat.py           Java互換処理（空白判定、long範囲、文字列の並び順）
│   ├─ sales/
│   │   ├─ models.py               型                       ← SalesCsvRow / Sales / SalesError / SalesSummary
│   │   ├─ csv_reader.py           CSV読込                  ← FlatFileItemReader / DelimitedLineTokenizer
│   │   ├─ validation_processor.py 入力チェックと変換       ← SalesValidationProcessor
│   │   ├─ repository.py           DBアクセス               ← SalesMapper / SalesMapper.xml
│   │   └─ import_writer.py        登録とエラー出力         ← SalesImportWriter
│   └─ batch/
│       ├─ job.py                  ジョブの流れ             ← SalesJobConfig
│       ├─ prepare.py              前処理                   ← PrepareTasklet
│       └─ job_result.py           開始・件数ログ           ← JobResultListener
├─ tests/                          pytest
│   └─ data/                       境界ケースの入力と、Java版の実際の出力（期待値）
└─ tools/
    ├─ compare.ps1                 現新比較
    └─ export_sales.py             比較用に SQLite の売上テーブルを CSV に書き出す
```
