# One-time setup. Run from the repo root in PowerShell:  .\scripts\setup.ps1
param([string]$Server = "ECG-L028")
$ErrorActionPreference = "Stop"
Write-Host "Creating database objects on $Server ..."
sqlcmd -S $Server -E -b -i sql\001_schema.sql
sqlcmd -S $Server -E -b -i sql\002_seed_teams.sql
sqlcmd -S $Server -E -b -i sql\003_config.sql
Write-Host "Installing the Python package (editable) ..."
python -m pip install -e .
Write-Host ""
Write-Host "Next: put your Odds API key in the database:"
Write-Host "  sqlcmd -S $Server -E -d MaverickPicks -Q `"UPDATE core.config SET config_value=N'<KEY>' WHERE config_key='ODDS_API_KEY'`""
Write-Host "Then test:  python -m mpm.oddsapi --league NBA --test"
