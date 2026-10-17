param([string]$in, [string]$out, [string]$font = "Nirmala UI", [int]$size = 12, [int]$bold = 0, [int]$italic = 0)
$ErrorActionPreference = "Stop"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$word = New-Object -ComObject Word.Application
$word.Visible = $false; $word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Add()
  $text = [System.IO.File]::ReadAllText((Join-Path $dir $in), [System.Text.Encoding]::UTF8)
  $doc.Content.InsertAfter($text)
  $f = $doc.Content.Font
  $f.Name = $font; $f.NameBi = $font; $f.NameOther = $font; $f.Size = $size; $f.SizeBi = $size
  $f.Bold = $bold; $f.BoldBi = $bold; $f.Italic = $italic; $f.ItalicBi = $italic
  $tmp = Join-Path $env:TEMP $out
  $doc.SaveAs2([ref](Join-Path $env:TEMP $out), [ref]17)
  $doc.Close(0)
  Move-Item -Force $tmp (Join-Path $dir $out)
  "ok $out"
} finally { $word.Quit(); [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null }
