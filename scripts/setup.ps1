# One-time setup. Run from the repo root in PowerShell:  .\scripts\setup.ps1 -Server ECG-L028
param([string]$Server = "ECG-L028")
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\find_python.ps1"
Write-Host "Creating database objects on $Server ..."
foreach ($f in "001_schema.sql","002_seed_teams.sql","003_config.sql","010_nhl_schema.sql","011_watchlist.sql","012_close_cleanup.sql","013_stale_lines.sql") {
    sqlcmd -S $Server -E -b -I -i "sql\$f"          # -I = QUOTED_IDENTIFIER ON
    if ($LASTEXITCODE -ne 0) { throw "sqlcmd failed on $f" }
}
$py = Get-MpmPython
Write-Host "Using Python: $py"
& $py -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
Write-Host ""
Write-Host "Setup done. Next:"
Write-Host "  1) Store your Odds API key:"
Write-Host "     sqlcmd -S $Server -E -d MaverickPicks -Q `"UPDATE core.config SET config_value=N'<KEY>' WHERE config_key='ODDS_API_KEY'`""
Write-Host "  2) Test:  & `"$py`" -m mpm.oddsapi --league NBA --test"
