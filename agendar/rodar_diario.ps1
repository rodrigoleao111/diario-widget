# Coleta e exporta o diário dos últimos 3 dias (cobre dia sem PC ligado e commits atrasados).
$raiz = Split-Path $PSScriptRoot -Parent
$py = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
$desde = (Get-Date).AddDays(-3).ToString("yyyy-MM-dd")
$ate = (Get-Date).ToString("yyyy-MM-dd")
Set-Location $raiz
"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm') ===" | Out-File -Append -Encoding utf8 diario.log
& $py -X utf8 -m diario coletar --desde $desde *>&1 | Out-File -Append -Encoding utf8 diario.log
& $py -X utf8 -m diario exportar --desde $desde --ate $ate *>&1 | Out-File -Append -Encoding utf8 diario.log
