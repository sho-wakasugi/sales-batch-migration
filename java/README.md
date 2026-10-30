# 売上CSV集計バッチ（sales-batch）

売上CSVを読み込んで入力チェックを行い、正常データを売上テーブルに登録したうえで、店舗別・月別の売上を集計して CSV に出力する業務バッチです。
Java の学習用であり、あとで Python へ移行したときに **同じ入力で結果が一致するか（現新一致）を検証するための元システム** として作っています。

## 技術構成

| 項目 | 内容 |
|---|---|
| 言語 | Java 21 |
| フレームワーク | Spring Boot 3.5 / Spring Batch 5 |
| ビルド | Maven 3.9（Maven Wrapper 同梱。Maven のインストールは不要） |
| DB | H2 Database（ファイルモード、`data/salesdb.mv.db`） |
| DB アクセス | MyBatis |
| テスト | JUnit 5 |

## 前提

- JDK 21 がインストールされ、`java -version` が 21 を表示すること
- Windows（PowerShell）で動作確認しています
- 初回のビルドでは Maven 本体と依存ライブラリをインターネットからダウンロードします

## 使い方（PowerShell）

### 1. ビルド（テストも実行されます）

```powershell
.\mvnw.cmd clean package
```

`target\sales-batch.jar` が作られます。テストを飛ばす場合は `.\mvnw.cmd clean package -DskipTests` を使います。

### 2. 実行

```powershell
# 通常実行（売上テーブルにデータを追加登録する）
java -jar target\sales-batch.jar

# 比較検証用（売上テーブルを全件削除してから登録する）
java -jar target\sales-batch.jar clear=true
```

jar を作らずに Maven から直接実行することもできます。

```powershell
.\mvnw.cmd spring-boot:run
.\mvnw.cmd spring-boot:run "-Dspring-boot.run.arguments=clear=true"
```

### 3. 結果の確認

```powershell
Get-Content -Encoding UTF8 output\summary.csv
Get-Content -Encoding UTF8 output\error.csv
```

- 出力ファイルは UTF-8（BOM 無し）です。PowerShell 5.1 では `-Encoding UTF8` を付けないと文字化けします
- Excel で開くと文字化けすることがあります。その場合は「データ」→「テキストまたは CSV から」で UTF-8 を指定して開いてください

### 4. テストだけ実行

```powershell
.\mvnw.cmd test
```

## 処理の流れ

```
salesJob
 ├─ prepareStep : 入力ファイルの存在確認、出力フォルダ作成、（clear=true のとき）売上テーブル全件削除
 ├─ importStep  : input/sales.csv 読込 → 入力チェック → 正常行は売上テーブルに登録 / エラー行は output/error.csv
 └─ summaryStep : 売上テーブルを店舗別・月別に集計 → output/summary.csv
```

ジョブ終了時に、読込件数・登録件数・エラー件数・集計出力件数をログに出力します。

```
========== 処理結果 ==========
読込件数　: 100
登録件数　: 90
エラー件数: 10
集計出力件数: 12
終了ステータス: COMPLETED
```

### 売上テーブルの扱い（clear パラメータ）

| 実行方法 | 売上テーブル | summary.csv の集計対象 |
|---|---|---|
| `clear` 指定なし（通常） | 削除せず追加登録（蓄積） | テーブル全体（過去の登録分を含む） |
| `clear=true`（比較検証用） | 全件削除してから登録 | 今回の入力ファイル分だけ |

- `clear` は実行のたびに指定します。前回の指定は引き継ぎません
- 同じファイルを `clear` なしで2回取り込むと、同じデータが2重に登録されます（重複チェックはしていません）
- **現新一致の検証では、Java 版・Python 版とも `clear=true` 相当で実行して出力を比較してください**

## 入出力仕様（現新一致の比較基準）

Python 版はこの仕様に合わせて実装します。

### 共通

| 項目 | 仕様 |
|---|---|
| 文字コード | UTF-8（BOM 無し） |
| 改行コード | 出力は LF。入力は LF / CRLF どちらでも可 |
| ヘッダー | 入力の1行目はヘッダーとして読み飛ばす。出力の1行目にもヘッダーを付ける |
| CSV のクォート | 入力はダブルクォートで囲んだ値に対応する。出力では、カンマ・ダブルクォート・改行を含む値だけをダブルクォートで囲み、中の `"` は `""` にする（Python の `csv` モジュールの `QUOTE_MINIMAL` と同じ） |

### 入力：`input/sales.csv`

```
売上日,店舗コード,商品コード,数量,単価
2026-01-05,S001,P001,3,120
```

### 入力チェック

各項目の前後の空白は取り除いて（trim）からチェックします。

| 項目 | チェック | エラー理由 |
|---|---|---|
| （行全体） | 項目数が5であること | `項目数が不正です（期待値:5、実際:N）` |
| 売上日 | 必須 | `売上日は必須です` |
| 売上日 | `yyyy-MM-dd`（ゼロ埋め）形式の実在する日付 | `売上日はyyyy-MM-dd形式の正しい日付で入力してください` |
| 店舗コード | 必須 | `店舗コードは必須です` |
| 商品コード | 必須 | `商品コードは必須です` |
| 数量 | 必須 | `数量は必須です` |
| 数量 | 整数（`-?[0-9]+`、long の範囲内） | `数量は整数で入力してください` |
| 数量 | 1以上 | `数量は1以上で入力してください` |
| 単価 | 必須 | `単価は必須です` |
| 単価 | 整数（`-?[0-9]+`、long の範囲内） | `単価は整数で入力してください` |
| 単価 | 0以上 | `単価は0以上で入力してください` |
| 売上金額 | 数量×単価が long の範囲に収まる | `売上金額（数量×単価）が大きすぎます` |

チェックの規則は次のとおりです。

- 項目数が5でない行は、項目数エラーだけを出します（各項目のチェックは行いません）
- 各項目は「必須 → 形式 → 範囲」の順にチェックし、1つ目のエラーが見つかった時点でその項目のチェックをやめます
- 1行に複数の項目エラーがある場合は、**項目順（売上日 → 店舗コード → 商品コード → 数量 → 単価）にすべて** を `;` 区切りで出力します
- `2026/01/05`、`2026-1-5`、`2026-02-30` はいずれも日付エラーです
- `+1`、`1.0`、`１`（全角）は整数エラーです
- 空行は項目数エラーになります

### 出力：`output/error.csv`

```
行番号,売上日,店舗コード,商品コード,数量,単価,エラー理由
37,2026-02-30,S001,P004,1,1500,売上日はyyyy-MM-dd形式の正しい日付で入力してください
```

- 行番号は、ヘッダーを1行目として数えた入力ファイル上の行番号です
- 項目値は入力のまま出力します（trim しません）。項目が足りない場合は空欄にし、多い場合は6項目目以降を切り捨てます
- 入力の順に出力します。エラーが0件でもヘッダーだけのファイルを出力します

### 売上テーブル（SALES）

| 列 | 型 | 内容 |
|---|---|---|
| id | BIGINT | 自動採番 |
| sales_date | DATE | 売上日 |
| store_code | VARCHAR | 店舗コード（trim 後） |
| product_code | VARCHAR | 商品コード（trim 後） |
| quantity | BIGINT | 数量 |
| unit_price | BIGINT | 単価 |
| amount | BIGINT | 売上金額 = 数量 × 単価（整数で計算） |
| line_no | INT | 入力ファイル上の行番号 |
| created_at | TIMESTAMP | 登録日時 |

### 出力：`output/summary.csv`

```
店舗コード,年月,売上金額,件数
S001,2026-01,45150,8
```

- 店舗コードと年月（`yyyy-MM`）ごとに、売上金額の合計と件数を出力します
- 店舗コードの昇順、次に年月の昇順に並べます（文字列としての比較）

### 終了コード

| 終了コード | 意味 |
|---|---|
| 0 | 正常終了（入力エラー行があっても、処理を最後まで実行できれば 0） |
| 5 | 異常終了（入力ファイルが無い、DB エラーなど。Spring Boot の標準の値） |

## ログ

コンソールと `logs/sales-batch.log` の両方に出力します。

## DB の中身を確認する

H2 の Shell で SQL を実行できます（H2 のバージョンは `$env:USERPROFILE\.m2\repository\com\h2database\h2\` で確認してください）。

```powershell
java -cp "$env:USERPROFILE\.m2\repository\com\h2database\h2\2.3.232\h2-2.3.232.jar" org.h2.tools.Shell `
  -url "jdbc:h2:file:./data/salesdb;AUTO_SERVER=TRUE" -user sa -sql "SELECT * FROM sales ORDER BY id"
```

DB を完全に初期化したい場合は、`data` フォルダを削除してください（Spring Batch の実行履歴も消えます）。

## テストデータ

`input/sales.csv` には100行のデータが入っています（正常90行、エラー10行）。エラー行の内容は次のとおりです。

| 行番号 | 内容 |
|---|---|
| 7 | 店舗コードが空 |
| 17 | 数量が数値でない |
| 27 | 日付の形式が誤り（`2026/01/20`） |
| 37 | 存在しない日付（`2026-02-30`） |
| 47 | 数量が0 |
| 57 | 数量がマイナス |
| 67 | 単価が小数 |
| 77 | 項目数が不足 |
| 87 | 複数のエラー（日付・商品コード・数量・単価） |
| 97 | 売上日が空 |

このほかに、単価0の正常行（13行目）と、前後に空白がある正常行（58行目）も入っています。

## ディレクトリ構成

```
sales-batch/
├─ mvnw.cmd, mvnw, .mvn/              Maven Wrapper
├─ pom.xml
├─ input/sales.csv                    入力データ
├─ output/                            出力先（実行時に作成。Git 管理外）
├─ data/                              H2 の DB ファイル（実行時に作成。Git 管理外）
├─ logs/                              ログ（実行時に作成。Git 管理外）
└─ src/
   ├─ main/java/com/example/salesbatch/
   │   ├─ SalesBatchApplication.java       起動クラス
   │   ├─ SalesProperties.java             設定値（入出力ファイルのパス）
   │   ├─ common/                          共通部品
   │   │   ├─ exception/                     例外クラス（BatchException ほか）
   │   │   ├─ validation/FieldValidator      入力チェック
   │   │   └─ csv/CsvUtils                   CSV 出力（クォート処理）
   │   ├─ sales/                           売上の業務処理（入力チェック、登録、集計の型と Mapper）
   │   └─ batch/                           ジョブ定義、前処理、件数ログ
   ├─ main/resources/
   │   ├─ application.yml                  設定
   │   ├─ schema.sql                       売上テーブル定義
   │   └─ mapper/SalesMapper.xml           SQL
   └─ test/                              単体テスト・結合テスト
```

入出力ファイルのパスは `application.yml` の `sales.*` で設定しています。実行時に `--sales.input-file=別のファイル.csv` のように指定して変更することもできます。
