<#
.SYNOPSIS
  現新比較：Java版と Python版を同じ入力で実行し、結果が一致するかを確認する。

.DESCRIPTION
  入力ファイルごとに、Java版・Python版をそれぞれ新しいDBで clear=true を付けて実行し、次を比較する。
    - error.csv / summary.csv（バイト単位）
    - 売上テーブルの内容（id・登録日時を除く。line_no 順に CSV に書き出して比較）
    - ログの件数（読込・登録・エラー・集計出力）と終了ステータス
    - 終了コード
  結果は python\output\compare\<入力ファイル名>\{java,python} に残る。

  事前に Java をビルド（.\mvnw.cmd package）し、python\.venv を作っておくこと。

.EXAMPLE
  .\python\tools\compare.ps1
  .\python\tools\compare.ps1 -InputFiles input\sales.csv
#>
param(
    [string[]]$InputFiles = @(
        "input\sales.csv",
        "python\tests\data\edge_cases.csv",
        "python\tests\data\edge_comment.csv",
        "python\tests\data\failure_sum_overflow.csv",
        "python\tests\data\failure_single_quote.csv"
    )
)

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$jar = Join-Path $root "target\sales-batch.jar"
$python = Join-Path $root "python\.venv\Scripts\python.exe"
$exportTool = Join-Path $root "python\tools\export_sales.py"
$h2Jar = Get-ChildItem "$env:USERPROFILE\.m2\repository\com\h2database\h2" -Recurse -Filter "h2-*.jar" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1

if (-not (Test-Path $jar)) { Write-Host "Java版の jar がありません。先に .\mvnw.cmd package を実行してください: $jar"; exit 2 }
if (-not (Test-Path $python)) { Write-Host "Python の仮想環境がありません。python\README.md の手順で作成してください: $python"; exit 2 }
if (-not $h2Jar) { Write-Host "H2 の jar が見つかりません（Java版を一度ビルドしてください）"; exit 2 }

# ログから比較対象の行（件数・終了ステータス）を取り出す
function Get-Counts([string]$logFile) {
    if (-not (Test-Path $logFile)) { return @() }
    Get-Content -Encoding UTF8 $logFile |
        Where-Object { $_ -match '(読込件数|登録件数|エラー件数|集計出力件数|終了ステータス|一致しません)' } |
        ForEach-Object { ($_ -split ' : ', 2)[1].Trim() }
}

# 2つのファイルが同じか（両方とも無い場合も「同じ」とする）
function Test-SameFile([string]$a, [string]$b) {
    $existsA = Test-Path $a
    $existsB = Test-Path $b
    if (-not $existsA -and -not $existsB) { return $true }
    if ($existsA -ne $existsB) { return $false }
    return (Get-FileHash $a).Hash -eq (Get-FileHash $b).Hash
}

$results = @()
foreach ($inputFile in $InputFiles) {
    $inputPath = (Resolve-Path (Join-Path $root $inputFile)).Path
    $name = [IO.Path]::GetFileNameWithoutExtension($inputPath)
    $dir = Join-Path $root "python\output\compare\$name"
    $javaDir = Join-Path $dir "java"
    $pyDir = Join-Path $dir "python"
    if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
    New-Item -ItemType Directory -Force $javaDir, $pyDir | Out-Null

    # Java版
    java -jar $jar "--sales.input-file=$inputPath" "--sales.error-file=$javaDir\error.csv" `
        "--sales.summary-file=$javaDir\summary.csv" "--logging.file.name=$javaDir\batch.log" `
        "--spring.datasource.url=jdbc:h2:file:$javaDir\db" clear=true | Out-Null
    $javaExit = $LASTEXITCODE
    $javaExport = Join-Path $javaDir "sales_table.csv"
    java -cp $h2Jar.FullName org.h2.tools.Shell -url "jdbc:h2:file:$javaDir\db" -user sa -sql `
        "CALL CSVWRITE('$javaExport', 'SELECT LINE_NO, SALES_DATE, STORE_CODE, PRODUCT_CODE, QUANTITY, UNIT_PRICE, AMOUNT FROM sales ORDER BY line_no', 'charset=UTF-8')" | Out-Null
    # CSVWRITE の改行は OS の既定（Windows は CRLF）なので LF にそろえる
    $text = [IO.File]::ReadAllText($javaExport, [Text.Encoding]::UTF8).Replace("`r`n", "`n")
    [IO.File]::WriteAllText($javaExport, $text, (New-Object Text.UTF8Encoding $false))

    # Python版
    Push-Location (Join-Path $root "python")
    try {
        & $python -m salesbatch "--input-file=$inputPath" "--error-file=$pyDir\error.csv" `
            "--summary-file=$pyDir\summary.csv" "--db-file=$pyDir\salesdb.sqlite3" "--log-file=$pyDir\batch.log" clear=true | Out-Null
        $pyExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    & $python -I $exportTool "$pyDir\salesdb.sqlite3" "$pyDir\sales_table.csv"

    $javaCounts = Get-Counts "$javaDir\batch.log"
    $pyCounts = Get-Counts "$pyDir\batch.log"

    $checks = [ordered]@{
        "error.csv"   = Test-SameFile "$javaDir\error.csv" "$pyDir\error.csv"
        "summary.csv" = Test-SameFile "$javaDir\summary.csv" "$pyDir\summary.csv"
        "売上テーブル" = Test-SameFile $javaExport "$pyDir\sales_table.csv"
        "件数ログ"    = (($javaCounts -join "|") -eq ($pyCounts -join "|"))
        "終了コード"  = ($javaExit -eq $pyExit)
    }
    $ok = -not ($checks.Values -contains $false)
    $results += [pscustomobject]@{
        入力         = $inputFile
        結果         = if ($ok) { "一致" } else { "不一致" }
        "error.csv"  = if ($checks["error.csv"]) { "OK" } else { "NG" }
        "summary.csv" = if ($checks["summary.csv"]) { "OK" } else { "NG" }
        売上テーブル = if ($checks["売上テーブル"]) { "OK" } else { "NG" }
        件数ログ     = if ($checks["件数ログ"]) { "OK" } else { "NG" }
        終了コード   = "$javaExit / $pyExit"
    }
    if (-not $checks["件数ログ"]) {
        Write-Host "[$name] 件数ログの差異  Java: $($javaCounts -join ', ')"
        Write-Host "[$name]                 Python: $($pyCounts -join ', ')"
    }
}

$results | Format-Table -AutoSize
if ($results.結果 -contains "不一致") {
    Write-Host "不一致があります。python\output\compare\ の出力を確認してください。"
    exit 1
}
Write-Host "すべての入力で Java版と Python版の結果が一致しました。"
exit 0
