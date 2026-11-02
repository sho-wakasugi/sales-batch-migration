# 売上CSV集計バッチ（Java / Spring Batch）

売上データの CSV を読み込み、入力チェックをしたうえで DB に登録し、店舗別・月別に集計して CSV に出力する業務バッチです。

## 目的

- **Java・Spring Batch の学習**：業務バッチでよくある処理（ファイル取込、入力チェック、エラー行の出力、DB 登録、集計、件数ログ）を一通り実装しました。
- **Python 移行の「元システム」**：このバッチを Python に移行し、同じデータで結果が一致するか（現新一致）を検証するための基準として作りました。そのため、入力チェックの順番やエラー文言、文字コード、改行、並び順などの入出力の仕様を、細かく決めています。

## 使用技術

| 分類 | 技術 |
|---|---|
| 言語 | Java 21 |
| フレームワーク | Spring Boot 3.5 / Spring Batch 5 |
| DB / DB アクセス | H2 Database（ファイルモード）/ MyBatis |
| ビルド | Maven（Maven Wrapper 同梱。Maven のインストールは不要） |
| テスト | JUnit 5 / spring-batch-test |
| 実行環境 | Windows（PowerShell） |

## 処理の流れ

```
input/sales.csv
     │
     ▼
salesJob
 ├─ prepareStep : 入力ファイルの存在確認、出力フォルダ作成
 │                （clear=true を指定したときだけ売上テーブルを全件削除）
 ├─ importStep  : CSV読込 → 入力チェック ─┬─ 正常行 → 売上テーブルに登録（MyBatis）
 │               （50件ごとにコミット）     └─ エラー行 → output/error.csv（行番号・理由付き）
 └─ summaryStep : 売上テーブルを店舗別・月別に集計 → output/summary.csv
     │
     ▼
ログ：読込件数・登録件数・エラー件数・集計出力件数・終了ステータス
```

設計で工夫した点は次のとおりです。

- **入力チェックとエラー処理**
  - 必須・数値・日付形式・最小値のチェックを、共通部品（`FieldValidator`）にまとめました。
  - 1行に複数のエラーがあれば、理由をすべて出力します。エラー行があっても処理は止めません。
- **例外クラス**
  - 業務例外の基底クラス（`BatchException`）を作り、入力ファイルの異常と入力チェックの違反を区別しました。
- **振り分けと型安全**
  - 正常行とエラー行を、Java 21 の sealed interface とパターンマッチで振り分けています。
- **件数の照合**
  - ジョブの終了時に「読込＝登録＋エラー」を確認し、合わなければ警告を出します。
- **再実行**
  - 売上テーブルは通常は追加登録（蓄積）します。比較検証のときだけ `clear=true` で全件削除してから登録します。

## 実行方法

### 前提

- JDK 21（`java -version` で 21 と表示されること）
- Maven のインストールは不要です。初回のビルドで、Maven Wrapper が Maven 本体と依存ライブラリをダウンロードします

### ビルドと実行（PowerShell）

リポジトリのフォルダで実行します。

```powershell
# ビルド（テストも実行されます）。target\sales-batch.jar が作られます
.\mvnw.cmd clean package

# 実行（売上テーブルにデータを追加登録する）
java -jar target\sales-batch.jar

# 比較検証用の実行（売上テーブルを全件削除してから登録する）
java -jar target\sales-batch.jar clear=true
```

| 入出力 | パス |
|---|---|
| 入力 | `input/sales.csv` |
| エラー行 | `output/error.csv` |
| 集計結果 | `output/summary.csv` |
| DB（H2） | `data/salesdb.mv.db` |
| ログ | `logs/sales-batch.log`（コンソールにも出力） |

- 入力ファイルの場所は、`--sales.input-file=別のファイル.csv` を付けて変更できます。
- 終了コードは、正常終了なら 0、異常終了（入力ファイルが無いなど）なら 5 です。

### 結果の確認

```powershell
Get-Content -Encoding UTF8 output\summary.csv
Get-Content -Encoding UTF8 output\error.csv
```

出力ファイルは UTF-8（BOM 無し）、改行は LF です。Windows PowerShell 5.1 では `-Encoding UTF8` を付けないと文字化けします。

### テストだけ実行

```powershell
.\mvnw.cmd test
```

## テスト

JUnit 5 で **44件**のテストがあり、すべて成功しています。

| テストクラス | 件数 | 内容 |
|---|---|---|
| `FieldValidatorTest` | 34 | 入力チェック部品の境界値（うるう年、存在しない日付、long の上限、全角数字など） |
| `SalesValidationProcessorTest` | 7 | 正常行とエラー行の振り分け、エラー理由の文言、項目数の不正、金額のあふれ |
| `SalesJobIntegrationTest` | 2 | ジョブ全体を実行し、出力 CSV が期待値ファイルと完全に一致すること、再実行で売上が蓄積されること |
| `PrepareTaskletTest` | 1 | 入力ファイルが無いときの異常終了 |

テストデータの `input/sales.csv`（100行）には、わざとエラーにした行を10行入れています。

## Python版との関係

**Python 版：[../python/](../python/README.md)**（全体の概要はリポジトリ直下の [README](../README.md)）

このバッチを Python 3.12（標準ライブラリ ＋ SQLite）に移行したものです。

- **構成をそろえた**：Java のクラスと Python のモジュールを1対1で対応させています。
- **結果の一致を確認した**：比較スクリプトで両方を同じ入力で実行し、次の結果が一致することを確認しました。
  - error.csv と summary.csv（バイト単位）
  - 売上テーブルの中身
  - 件数
  - 終了コード
- **「仕様」ではなく「Java の実際の動き」を基準にした**：移行の途中で、このバッチを境界ケースで動かしました。その結果、仕様書に書いていない動きが見つかりました。
  - `#` で始まる行が、エラーにならずに読み飛ばされる
  - 集計の合計が long の上限を超えると、ジョブが異常終了する

  こうした動きの記録と、移行で判断した点は、[python/docs/migration-notes.md](../python/docs/migration-notes.md) にまとめています。
- **リポジトリの構成**：Python 版は、最初は Java 版のリポジトリの中で作りました。その後、別のリポジトリに分け、最後に公開用として1つのリポジトリ（`java/` と `python/`）にまとめています。この経緯は、コミット履歴に残っています。
