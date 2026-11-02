# Java → Python 移行メモ（売上CSV集計バッチ）

Java版（Spring Boot / Spring Batch / MyBatis / H2。プロジェクト `sales-batch`）を、Python版（標準ライブラリ / SQLite。このプロジェクト `sales-batch-python`）に移行したときの記録です。

## 1. 結論

- 次の入力について、Java版と Python版の結果が一致することを `tools/compare.ps1` で確認しました。
  - 本番用の `input/sales.csv`（100行）
  - 境界ケースを集めた CSV
  - 異常終了するケース2種
- 比較した項目は次の5つです。
  - error.csv（バイト単位）
  - summary.csv（バイト単位）
  - 売上テーブル（id と登録日時を除く）
  - ログの件数
  - 終了コード
- 移行の基準は **「README に書いた仕様」ではなく「Java版の実際の動き」** にしました。境界ケースで Java を実際に動かしたところ、README に書いていない動きがいくつも見つかったためです（5章）。
- **外部ライブラリはテスト用の pytest だけ**です。バッチ本体は標準ライブラリだけで動きます。使ったのは csv、sqlite3、logging、datetime、unicodedata、re、argparse などです。csv モジュールは CSV の読み書きには使っていません（4章の 4-2、4-3）。

## 2. Java と Python の対応表

### 2-1. クラス・ファイル

| Java | Python | 備考 |
|---|---|---|
| `SalesBatchApplication` | `salesbatch/__main__.py` | 起動処理と終了コード |
| `SalesProperties` ＋ `application.yml` | `salesbatch/config.py`（dataclass） | 設定ファイルは使わず、既定値と引数で指定する |
| `schema.sql`（H2） | `salesbatch/schema.sql`（SQLite） | 型を SQLite 用に変えた（3-6） |
| `BatchException` / `InputFileException` / `ValidationException` | `common/exceptions.py` | 継承の関係も同じ |
| `FieldValidator` | `common/validation.py` | メソッド名は snake_case（`requiredInteger` → `required_integer`） |
| `CsvUtils` | `common/csv_utils.py` | 自前で実装（4-3） |
| （なし） | `common/javacompat.py` | Java と同じ結果にするための互換処理（空白判定、long の範囲、文字列の並び順） |
| `SalesCsvRow` / `Sales` / `SalesError` / `SalesSummary`（record） | `sales/models.py`（`@dataclass(frozen=True)`） | |
| `ImportItem`（sealed interface） | `type ImportItem = Sales \| SalesError` | |
| `FlatFileItemReader` ＋ `SalesCsvLineMapper` ＋ `DelimitedLineTokenizer` | `sales/csv_reader.py` | Spring Batch の処理を移植（4-2） |
| `SalesValidationProcessor` | `sales/validation_processor.py` | |
| `SalesMapper` ＋ `SalesMapper.xml` | `sales/repository.py` | SQL は Python の文字列に書いた |
| `SalesImportWriter` | `sales/import_writer.py` | |
| `SalesJobConfig` | `batch/job.py` | |
| `PrepareTasklet` | `batch/prepare.py` | |
| `JobResultListener` | `batch/job_result.py` | ログの文言は同じ |
| JUnit のテスト4クラス | `tests/test_*.py` | 同じテストケースに、Python版で追加した観点を足した |

### 2-2. ライブラリ

| 用途 | Java | Python |
|---|---|---|
| バッチの枠組み | Spring Batch | なし（`batch/job.py` で順に呼ぶ） |
| DI・設定 | Spring Boot | なし（関数の引数で渡す） |
| DB | H2（ファイルモード） | sqlite3 |
| DB アクセス | MyBatis | sqlite3（SQL を直接書く） |
| CSV の読込 | `FlatFileItemReader` / `DelimitedLineTokenizer` | 自前実装（Spring Batch の移植） |
| CSV の出力 | `FlatFileItemWriter` ＋ `CsvUtils` | `open()` ＋ `csv_utils` |
| 日付 | `LocalDate` / `DateTimeFormatter`（STRICT） | 正規表現と `calendar.isleap` による自前の検証（3-1） |
| 整数 | `long`、`Math.multiplyExact` | `int` ＋ long の範囲チェック（3-2） |
| ログ | SLF4J ＋ Logback | logging |
| 引数 | Spring Boot（`key=value` → ジョブパラメータ） | argparse |
| テスト | JUnit 5（`@ParameterizedTest`） | pytest（`@pytest.mark.parametrize`） |

### 2-3. 仕組み

| 仕組み | Java | Python |
|---|---|---|
| ステップ | prepareStep → importStep → summaryStep | `prepare()` → `_import_step()` → `_summary_step()` |
| チャンク処理 | 50件ごとに読込 → 加工 → 書込 → コミット | 同じ（`CHUNK_SIZE = 50`） |
| トランザクション | Spring の `DataSourceTransactionManager` | `conn.commit()` / `conn.rollback()` をチャンクごとに呼ぶ |
| error.csv への書込のタイミング | FlatFileItemWriter（トランザクション対応）がコミット時に書き出す | エラー行をチャンクの間は溜めておき、コミット時に書き出す |
| 件数の保存 | StepExecution の ExecutionContext（コミット時に更新） | `StepExecution` dataclass（コミット時に更新） |
| リスナー | `JobExecutionListener.beforeJob` / `afterJob` | `job_result.before_job` / `after_job` |
| ジョブの失敗 | ステップの例外 → ジョブが FAILED → 終了コード 5 | 例外を `run_job` で受け止めて FAILED → `main` が 5 を返す |
| 実行履歴 | Spring Batch のメタデータテーブル（BATCH_JOB_EXECUTION など） | 移行しない（4-9） |
| 再実行 | `run.id` を増やして何度でも実行できる | 履歴が無いので、何度でも実行できる |

## 3. 言語やライブラリの違いで注意が必要だった点

### 3-1. 日付の扱い

| 項目 | Java | Python の素直な書き方 | 対応 |
|---|---|---|---|
| 形式チェック | `uuuu-MM-dd` ＋ STRICT。`2026-1-5` はエラー | `strptime("%Y-%m-%d")` は `2026-1-5` を受け付けてしまう | 正規表現 `[0-9]{4}-[0-9]{2}-[0-9]{2}` で形を確かめてから日付を検証する |
| 0年 | `LocalDate` は `0000-01-01` を正しい日付として扱う（0年はうるう年） | `datetime.date` は1年からしか扱えない | 年月日を自前で検証する（`calendar.isleap` は0年も計算できる）。日付は `yyyy-MM-dd` の文字列のまま持つ |
| 集計の年月 | H2 の `FORMATDATETIME(d, 'yyyy-MM')` の `yyyy` は**紀元年**。0年（紀元前1年）は `0001-01` になる | `substr(sales_date, 1, 7)` だと `0000-01` になる | SQL で `0000` を `0001` に置き換える |
| 全角数字 | 正規表現 `[0-9]` には一致しない | `\d` は全角数字などにも一致する | `[0-9]` を使う |

### 3-2. 数値・端数

- **端数は出ません。** 数量・単価は整数だけを受け付け、金額は 数量×単価 の整数の掛け算です。decimal は使っていません（4-6）。
- **整数の上限**：Java の `long` は ±2^63 の範囲ですが、Python の `int` には上限がありません。次の3か所で、long の範囲を明示的にチェックしています。
  - 入力の整数チェック（`9223372036854775808` を Java と同じく「整数で入力してください」にする）
  - 金額の掛け算（Java の `Math.multiplyExact` と同じく「売上金額（数量×単価）が大きすぎます」にする）
- **Python の `int()` が受け付ける書き方**：`int()` は `"1_000"`、`" 1"`、`"١"`（アラビア数字）なども変換してしまいます。そのため、正規表現 `-?[0-9]+` に完全一致した値だけを `int()` に渡します。
- **集計の合計が long を超える場合**：
  - Java：H2 の `SUM` は結果を DECIMAL で返し、MyBatis が long に変換するときに失敗して、ジョブが FAILED になります。
  - Python：SQLite の `SUM` が「integer overflow」エラーになるので、同じく FAILED になります。
  - SQLite は途中の合計があふれた時点でエラーにします。ただし金額は0以上なので、途中であふれるのは最終的な合計があふれるときだけです。そのため結果は Java と同じになります。

### 3-3. 文字コード・改行

| 項目 | Java | Python の対応 |
|---|---|---|
| 入力の文字コード | UTF-8。不正なバイトは U+FFFD（置換文字）になる | `encoding="utf-8", errors="replace"`（0xFF 1バイトで一致を確認） |
| 入力の改行 | `BufferedReader.readLine` は LF・CRLF・CR のどれでも行が終わる | `open(newline=None)`（ユニバーサル改行）で同じ動きになる。`str.splitlines()` は U+2028 などでも分割してしまうので使わない |
| 出力の改行 | `lineSeparator("\n")` で LF | `open(newline="")` で改行の変換を止めて `"\n"` を書く。Windows で `newline` を省略すると CRLF になってしまう |
| 出力の BOM | 無し | `encoding="utf-8"`（`utf-8-sig` は使わない） |
| ログ | Logback がコンソールの文字コードで出力する | 絵文字などコンソールで表示できない文字で落ちないよう、`errors="backslashreplace"` を指定 |

### 3-4. 前後の空白（trim）と空欄の判定

Java の `String.strip()` と `isBlank()` は、`Character.isWhitespace` で空白かどうかを判定します。Python の `str.strip()` と `isspace()` とは、次の文字で結果が違います。

| 文字 | Java | Python の `strip()` |
|---|---|---|
| NBSP（U+00A0）、U+2007、U+202F | 空白ではない | 空白として削除する |
| U+0085（NEL） | 空白ではない | 空白として削除する |
| 全角スペース（U+3000）、タブ | 空白 | 空白 |

このため、Java と同じ判定をする `javacompat.strip` / `is_blank` を作りました。正しさは Java の `Character.isWhitespace` を実際に実行して確かめています。

実際に出る違いの例：

- 店舗コード ` S001 `：Java は NBSP を残したまま登録します。Python の `strip()` を使うと `S001` として登録され、集計が `S001` と合算されてしまいます。
- 数量が NBSP だけの値：Java は「整数で入力してください」エラーになります。Python の `strip()` を使うと「必須です」エラーになり、エラー理由が変わってしまいます。

### 3-5. 並び順

- H2 の `ORDER BY store_code` は、Java の `String.compareTo` と同じく **UTF-16 の単位**で比較します。
- SQLite の標準の比較（BINARY）は **UTF-8 のバイト順**です。
- 絵文字などの補助文字（U+10000 以上）と、U+E000〜U+FFFF の文字（半角カナなど）の順序が逆になります。例えば Java では `S😀` → `Sｱ` の順ですが、SQLite では `Sｱ` → `S😀` の順になります。
- 対応として、`conn.create_collation()` で UTF-16 の順に比較する照合順序 `JAVA_UTF16` を登録し、`ORDER BY store_code COLLATE JAVA_UTF16` を使っています。
- 年月は ASCII だけなので、標準の比較のままで違いはありません。

### 3-6. DB（H2 → SQLite）

| 項目 | H2 | SQLite | 対応 |
|---|---|---|---|
| 日付型 | DATE | 無い | TEXT（`yyyy-MM-dd`）。3-1 のとおり、0年を扱うためにも文字列が都合がよい |
| 自動採番 | 削除しても番号を再利用しない | `INTEGER PRIMARY KEY` だけだと最大値＋1 になるため、全件削除の後は番号が再利用される | `AUTOINCREMENT` を付けて H2 と同じにする |
| 文字列の長さ | `CHARACTER VARYING`（長さの指定なし） | TEXT | 違いなし |
| 年月の取り出し | `FORMATDATETIME` | 無い | `substr` を使う（3-1） |

### 3-7. 例外処理・終了コード

- Java は、ステップで例外が起きると Spring Batch がジョブを FAILED にし、Spring Boot が終了コード 5（`BatchStatus.FAILED` の序数）を返します。
- Python では、`run_job` が例外を受け止めて FAILED にし、`main` が 5 を返します。
- 入力チェックのエラー（`ValidationException`）は、どちらも例外で処理を止めず、エラー行として扱います。
- 異常終了したときの各ファイルの状態も、Java に合わせました。

| 状況 | error.csv | summary.csv | 売上テーブル |
|---|---|---|---|
| 取込の途中で異常終了 | ヘッダーと、コミット済みのチャンクのエラー行 | 作らない | コミット済みのチャンクまで |
| 集計で異常終了 | 正常に出力済み | ヘッダーだけ | 登録済み |

## 4. 単純な変換ではできず、判断が必要だった点

### 4-1. 何を「正」とするか → Java版の実際の動き

- README の仕様には、空行・特殊な空白・クォートの扱い・`#` の行などが書かれていません。
- 移行の目的は現新一致の検証なので、**Java の実際の動きを正**としました。
- 境界ケースを集めた CSV（`tests/data/edge_cases.csv` など）を Java で実行し、その出力を期待値として保存しました。Python の出力がこれとバイト単位で一致することを、テストで確かめています。

### 4-2. CSV の読込に csv モジュールを使わない → Spring Batch の処理を移植

csv モジュールで読むと、次のケースで Java と結果が変わります。

| 入力 | Java（DelimitedLineTokenizer） | csv モジュール |
|---|---|---|
| `S001,P"001,0,100` | 途中の `"` からクォート中の扱いになり、`P"001,0,100` が1項目になる（項目数エラー） | `"` を普通の文字として扱い、4項目になる |
| `S001, "P001" ,0` | クォートの外の空白とクォートを外して `P001` | ` "P001" ` のまま |
| `"P001,0,100`（閉じていない） | `"P001,0,100` を1項目として残す | 次の行まで読み続けて、行がつながる |
| クォートの中で改行 | 行ごとに別のレコードとして扱う | 次の行とつなげて1レコードにする |
| 空行 | 0項目（項目数エラー） | 0項目（同じ） |
| 項目が `"` 1文字だけ | 例外（StringIndexOutOfBounds）→ ジョブが FAILED | エラーにならない |

- 判断：Spring Batch 5.2.3 の `DelimitedLineTokenizer.doTokenize` と、`FlatFileItemReader.readLine` を Python に移植しました。
- 確認：Spring Batch の jar を直接呼び出し、テストに使った入力すべてで同じ分割結果になることを確かめています。

### 4-3. CSV の出力に csv.writer を使わない → CsvUtils と同じ規則を自前で実装

- `csv.writer`（QUOTE_MINIMAL）は、ほとんどの値で Java の CsvUtils と同じ結果になります。
- ただし、空欄1項目だけの行を `""` と出力するなど細部が違います。また、Python のバージョンによって規則が変わる可能性があります。
- 規則は数行で書けるので、Java の CsvUtils と同じ処理を実装しました。

### 4-4. `#` で始まる行 → Java と同じく読み飛ばす

- Spring Batch の FlatFileItemReader は、既定で **`#` で始まる行をコメントとして読み飛ばします**。
- 読み飛ばした行は、読込件数にもエラー件数にも入りません。行番号だけが進みます。行頭に空白がある行は対象外です。
- Java で作るときに意図した仕様ではありませんが、現新一致を優先して同じ動きにしました。5章で仕様として決め直すことを提案しています。

### 4-5. 0年の日付 → `0000-01-01` を受け付け、集計では `0001-01` と出力する

- Java の `LocalDate` と H2 の動きを、そのまま再現しました（3-1）。
- `datetime.date` が使えないため、日付は文字列で持ち、自前で検証しています。

### 4-6. decimal を使わない

- 単価・数量は整数だけを受け付け、金額は整数の掛け算なので、端数は発生しません。
- Python の `int` は正確な整数なので、decimal は不要と判断しました。
- 仕様が変わって単価に小数を許す場合は、Java も `BigDecimal` に変える必要があります。そのときは Python も `decimal.Decimal` を使い、丸め方（`ROUND_HALF_UP` など）をそろえてください。

### 4-7. 文字列の並び順 → SQLite に Java と同じ照合順序を登録する

- 比較の候補は2つありました。
  - SQL では並べず、Python の `sorted(key=...)` で並べる
  - SQLite の照合順序を使う
- Java版の「SQL の `ORDER BY` で並べる」構成に合わせて、照合順序を登録する方を選びました（3-5）。

### 4-8. 異常終了するケースも Java に合わせる

- 境界ケースの中に、Java ではジョブが FAILED になるケースが2つありました。
  - 集計の合計が long を超える
  - 項目が `"` 1文字だけ
- これらを Python で「正しく処理」してしまうと、現新比較では不一致になります。
- そのため Python でも、同じ条件で FAILED（終了コード 5）にしました。異常終了したときの件数とファイルの状態も、Java に合わせています。

### 4-9. Spring Batch の実行履歴は移行しない

- Spring Batch は、メタデータテーブル（BATCH_JOB_EXECUTION など）に実行履歴を保存しています。
- このバッチは再開（restart）の機能を使っておらず、業務の結果にも影響しません。そのため移行しませんでした。
- 実行の記録は、ログ（`logs/sales-batch.log`）で代わりにします。

### 4-10. 実行時の引数 → Java と同じ `key=value` 形式にする

- ジョブパラメータは、Java と同じく `clear=true` の形で渡します。
- パスの変更は `--input-file=...` です。Java の `--sales.input-file=...` に当たります。
- `clear` は Java と同じく、次の実行に引き継ぎません。

### 4-11. Java版とは別のプロジェクトにし、必要なファイルはコピーする

- Python版は、Java版（`sales-batch`）とは別のプロジェクト・別の Git リポジトリにしました。
  - 最初は Java版のリポジトリの `python/` フォルダに作りましたが、あとで分離しました。
  - コミット履歴は `git subtree split` で引き継いでいます。
- Python版だけでテストを実行できるよう、Java版の次のファイルをコピーして持っています。
  - `input/sales.csv`
  - Java のテスト用の期待値（`tests/data/java_integration/`）
- **Java版の側を変えたときは、コピーも更新が必要です。**
- 現新比較（`tools/compare.ps1`）では、両方に同じ入力ファイルを渡します。そのためコピーがずれていても、比較の結果は正しく出ます。Java版の場所は `-JavaProject` で指定します（省略時は同じ階層の `sales-batch`）。

## 5. Java版で見つかった問題（Java は修正していない）

現新比較のために Java を境界ケースで動かした結果、次の点が見つかりました。今回は「Java のコードは変更しない」方針なので、Python も同じ動きにしています。仕様として決め直すかどうかを検討してください。

| # | 内容 | 影響 | 提案 |
|---|---|---|---|
| 1 | 同じ店舗・年月の金額の合計が long を超えると、集計でジョブ全体が異常終了する | 登録はコミット済みなので、summary.csv だけが出ない | 入力チェックで金額の上限を決める。または合計を BigDecimal / NUMERIC で扱う |
| 2 | `#` で始まる行が、エラーにもならず黙って読み飛ばされる | 件数の照合（読込＝登録＋エラー）でも見つけられないまま、データが消える | `FlatFileItemReader` の `comments` を空にし、エラー行として出す |
| 3 | 0年（`0000-01-01`）が正常として登録され、集計では `0001-01` と出力される | 年月が実際と食い違う | 年の範囲（例：1900〜2999）をチェックする |
| 4 | 項目が `"` 1文字だけの行で、ジョブ全体が異常終了する | 1行の不正データで処理全体が止まる。同じチャンクの正常行も取り消される | 分割の失敗を、エラー行として扱う（skip の設定など） |
| 5 | 項目の途中に `"` があると、それ以降が1項目になり、項目数エラーになる | エラー理由が実際の誤りと合わない | 仕様として受け入れるか、クォートの規則を README に書く |

## 6. 未検証・既知の差異

| 項目 | 状況 |
|---|---|
| BOM 付きの入力 | Java・Python とも BOM は1行目（ヘッダー）に含まれ、ヘッダーは読み飛ばすので、同じ結果になるはず。実行しての確認はしていない |
| 不正な UTF-8 のバイト列（複数バイト） | 0xFF 1バイトでは一致を確認した。複雑な不正バイト列で置換文字の数が一致するかは確認していない |
| DB に接続できないときの終了コード | Java は Spring Boot の起動時に失敗するため、終了コード 1 になると考えられる。Python はジョブの中で失敗するため 5 になる（未確認） |
| 引数の誤り | Python は argparse のエラーで、終了コード 2 になる。Java は対応する動きが無い |
| `clear` の値の比較 | Java は `equalsIgnoreCase`、Python は `lower()` で比較する。特殊な文字（トルコ語の ı など）を含む値では結果が違う可能性があるが、実用上は問題ない |
| ログの書式 | 日時・スレッド名などの書式は違う。件数とステータスの行の文言は同じ |
| 登録日時（created_at） | 実行時刻なので比較対象外 |
