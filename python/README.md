# 売上CSV集計バッチ（Python版）― Java からの移行と現新一致の検証

Java（Spring Batch）で作った売上CSV集計バッチを、Python に移行したものです。
移行元の Java版と**同じ入力に対して同じ結果になること（現新一致）**を、比較スクリプトで検証しています。

- 全体の概要：リポジトリ直下の [README](../README.md)
- 移行元（Java版）：[../java/](../java/README.md)
- 移行の詳しい記録：[docs/migration-notes.md](docs/migration-notes.md)

## 移行の概要

| 項目 | Java版（移行元） | Python版（このフォルダ） |
|---|---|---|
| 言語 | Java 21 | Python 3.12 |
| バッチの枠組み | Spring Boot 3.5 / Spring Batch 5 | なし（同じ3ステップを関数で順に呼ぶ） |
| DB / DB アクセス | H2 / MyBatis | SQLite / sqlite3（標準ライブラリ） |
| CSV の読み書き | FlatFileItemReader / FlatFileItemWriter | 自前実装（Spring Batch の処理を移植） |
| テスト | JUnit 5（44件） | pytest（118件） |
| 外部ライブラリ | Spring など | **テスト用の pytest だけ**（本体は標準ライブラリだけで動く） |

処理の内容は Java版と同じです。

1. `input/sales.csv` を読み込む
2. 入力チェックを行う（必須、数値、日付形式、数量は1以上）。エラー行は理由付きで `output/error.csv` に出す
3. 正常データを売上テーブルに登録する
4. 店舗別・月別に集計して `output/summary.csv` に出す
5. 件数をログに出す

Java のクラスと Python のモジュールは、1対1で対応させています（最後の「ディレクトリ構成」を参照）。

## 現新一致の検証結果

`tools/compare.ps1` で、Java版と Python版を同じ入力・新しい DB で実行しました。**5種類の入力すべてで一致**しています。

| 入力 | 内容 | 結果 | 終了コード（Java / Python） |
|---|---|---|---|
| `input/sales.csv` | 本番想定の100行（エラー行10行を含む） | 一致 | 0 / 0 |
| `tests/data/edge_cases.csv` | 境界ケース38行（特殊な空白、全角数字、long の上限、0年、クォート、CRLF、絵文字、不正なバイトなど） | 一致 | 0 / 0 |
| `tests/data/edge_comment.csv` | `#` で始まる行を含む | 一致 | 0 / 0 |
| `tests/data/failure_sum_overflow.csv` | 集計の合計が long の上限を超える | 一致 | 5 / 5 |
| `tests/data/failure_single_quote.csv` | 項目が `"` 1文字だけの行を含む | 一致 | 5 / 5 |

比較した項目は次のとおりです。

| 比較項目 | 比較方法 |
|---|---|
| error.csv / summary.csv | バイト単位（文字コード・改行・クォートの違いも検出できる） |
| 売上テーブル | id と登録日時を除き、行番号順に CSV へ書き出して比較 |
| ログの件数と終了ステータス | 読込・登録・エラー・集計出力の件数と、終了ステータスの行を比較 |
| 終了コード | 値を比較 |

異常終了するケースは、Java と同じ条件で、同じように異常終了することを確かめています。終了コードや件数だけでなく、途中までのファイルの状態も一致しています。

## 移行で判断が必要だった点

最も大きな判断は、**移行の基準を「仕様書」ではなく「Java の実際の動き」にしたこと**です。

境界ケースで Java版を実際に動かしたところ、仕様書（Java版の README）に書いていない動きがいくつも見つかりました。現新一致を目的とする以上、Python の自然な書き方ではなく、Java の動きに合わせました。

| 観点 | Java の実際の動き | Python の素直な書き方との違い | 対応 |
|---|---|---|---|
| CSV の分割 | 項目の途中の `"` からクォート中の扱いになる。クォートの外の空白は削除する | `csv` モジュールでは結果が変わる | Spring Batch の `DelimitedLineTokenizer` を移植し、Spring Batch 本体と同じ分割結果になることを確認 |
| `#` で始まる行 | コメントとして黙って読み飛ばす（Spring Batch の既定の動き） | 普通に1行として読む | 同じく読み飛ばす（Java側の問題点として記録） |
| 前後の空白（trim） | NBSP（U+00A0）は空白とみなさない | `str.strip()` は NBSP も削除する | Java の `Character.isWhitespace` と同じ判定を実装 |
| 整数 | `long` の範囲。全角数字はエラー | `int` に上限が無く、`\d` は全角数字にも一致する | `[0-9]` と long の範囲チェックで再現 |
| 日付 | `0000-01-01` を正しい日付として扱い、集計では `0001-01` と出す（H2 の紀元年） | `datetime.date` は0年を扱えない | 日付は文字列で持ち、年月日を自前で検証 |
| 並び順 | UTF-16 の単位で比較する | SQLite は UTF-8 のバイト順（絵文字と半角カナの順序が逆になる） | SQLite に Java と同じ照合順序を登録 |
| CSV 出力・改行 | 必要なときだけクォートする。改行は LF | `csv.writer` は細部の規則が違う。Windows では CRLF になる | Java の CsvUtils と同じ規則で実装。`newline=""` で LF に固定 |
| 異常終了 | 集計のあふれや分割の失敗でジョブが FAILED（終了コード 5） | 正しく処理できてしまう | 同じ条件で FAILED にする |

Java版で見つかった問題（`#` の行が消える、集計のあふれでジョブが止まる など）は、今回は Java を修正していません。仕様として決め直すべき点として、[docs/migration-notes.md](docs/migration-notes.md) の5章にまとめています。

## AI の使い方

開発には **Claude Code**（Anthropic の AI コーディングエージェント、モデルは Claude Opus 5.5）を使いました。AI が関わったコミットには、`Co-Authored-By: Claude` を付けています。

### 進め方

1. **本人が要件と方針を指示する**：使用技術、標準ライブラリを優先すること、Java のコードは変更しないこと、テストの観点を Java と合わせること、などです。
2. **AI が計画を出し、本人が確認してから実装する**：作業の前に必ず計画を日本語で説明させ、確認してから進めました。計画の段階で、AI が出した確認事項に本人が答えて決めた例は次のとおりです。
   - 移行の基準を「Java の実際の動き」にする
   - 入出力の配置（入力は共有し、出力は分ける）
   - Spring Batch の実行履歴は移行しない
3. **AI が実装とテストを行い、区切りごとにコミットする**
4. **本人が結果を確認し、方針を修正する**：本人の判断で修正した例は次のとおりです。
   - Java版：毎回テーブルを全件削除する案に対して、「それではバッチの意味がない。比較検証のときだけ削除する」と修正した
   - Python版：最初は Java のリポジトリの中に作ったものを、別のリポジトリに分けた
   - 公開前：コミット履歴の作成者情報を整理し、両方の履歴を残したまま1つのリポジトリにまとめた

### AI の出力をそのまま信用しないための工夫

- **AI の推測ではなく、Java を実際に動かして期待値を作った**：境界ケースの CSV を Java版で実行し、その出力を期待値にしました。Python の出力は、これとバイト単位で比較しています。
- **ライブラリの動きは、本体を直接呼んで確かめた**：次の2つは、AI の知識だけに頼らず、Java で実際に実行して Python 側のテストと照らし合わせました。
  - CSV の分割は、Spring Batch の `DelimitedLineTokenizer` を直接呼び出した
  - 空白の判定は、Java の `Character.isWhitespace` を実行した
- **一致の確認を自動化した**：比較スクリプトで、ファイル・DB・件数・終了コードをまとめて突き合わせます。比較が空振りしていないこと（空のファイル同士で一致していないか）も確かめました。

## 実行方法

### 前提

- Python 3.12
- 現新比較を行う場合は、JDK 21 も必要です（Java版はリポジトリ内の [java/](../java/README.md)）

### 準備（初回のみ、PowerShell）

`python` フォルダで実行します（以降のコマンドも同じです）。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### 実行

```powershell
# 通常実行（売上テーブルにデータを追加登録する）
.venv\Scripts\python.exe -m salesbatch

# 比較検証用（売上テーブルを全件削除してから登録する）
.venv\Scripts\python.exe -m salesbatch clear=true
```

| 入出力 | 既定のパス | 変更するオプション |
|---|---|---|
| 入力 | `input/sales.csv`（Java版と同じ内容） | `--input-file=...` |
| エラー行 | `output/error.csv` | `--error-file=...` |
| 集計結果 | `output/summary.csv` | `--summary-file=...` |
| DB（SQLite） | `data/salesdb.sqlite3` | `--db-file=...` |
| ログ | `logs/sales-batch.log`（コンソールにも出力） | `--log-file=...`（空にするとファイルに出さない） |

終了コードは Java版と同じで、正常終了なら 0、異常終了なら 5 です。

### 結果の確認

```powershell
Get-Content -Encoding UTF8 output\summary.csv
Get-Content -Encoding UTF8 output\error.csv
```

### テスト

```powershell
.venv\Scripts\python.exe -m pytest
```

テストは `python` フォルダだけでも実行できます。合計は **118件**で、すべて成功しています（`java` フォルダが無い場合、`test_java_copies.py` の5件はスキップされます）。

| テストファイル | 件数 | 内容 |
|---|---|---|
| `test_field_validator.py` | 47 | 入力チェック（Java の `FieldValidatorTest` の34件と、Java と挙動を合わせた点） |
| `test_common.py` | 28 | Java 互換処理（空白判定、並び順）と CSV 出力 |
| `test_csv_reader.py` | 20 | CSV の分割、コメント行、改行、不正なバイト（期待値は Spring Batch で確認した結果） |
| `test_validation_processor.py` | 10 | 正常行とエラー行の振り分け（Java の7件と、追加の観点） |
| `test_job_integration.py` | 7 | ジョブ全体の実行。Java の期待値ファイルや Java の実際の出力とのバイト一致、異常終了 |
| `test_java_copies.py` | 5 | Java版のファイルのコピーが、元のファイルと同じ内容であること |
| `test_prepare.py` | 1 | 入力ファイルが無いときの異常終了 |

### 現新比較（Java版と突き合わせる）

先に Java版をビルドしておきます（`java` フォルダで `.\mvnw.cmd package`）。

```powershell
.\tools\compare.ps1                              # 既定の5ファイルで比較
.\tools\compare.ps1 -InputFiles input\sales.csv  # 入力を指定して比較
.\tools\compare.ps1 -JavaProject C:\work\java    # Java版の場所を指定（省略時はリポジトリ内の java フォルダ）
```

比較の結果は `output\compare\<入力名>\{java,python}` に残ります。

### Java版から持ってきたファイル

次のファイルは Java版のコピーです。`python` フォルダだけでテストを動かせるように持っています。Java版の側を変えた場合は、こちらも更新してください（更新し忘れると `test_java_copies.py` が失敗します）。

| python フォルダ | java フォルダ |
|---|---|
| `input/sales.csv` | `input/sales.csv` |
| `tests/data/java_integration/*` | `src/test/resources/integration/*` |
| `tests/data/expected/*` | （Java版で境界ケースを実行した出力） |

## ディレクトリ構成（Java との対応）

```
python/
├─ input/sales.csv                 入力データ（Java版のコピー）
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
│   └─ data/                       境界ケースの入力、Java版の出力（期待値）、Java版のテスト用ファイル
├─ tools/
│   ├─ compare.ps1                 現新比較
│   └─ export_sales.py             比較用に SQLite の売上テーブルを CSV に書き出す
└─ docs/migration-notes.md         移行メモ（対応表、注意点、判断の理由、Java版の問題点）
```
