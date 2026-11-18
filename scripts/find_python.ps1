# Returns the full path of the Python to use (skips the Microsoft Store "python" alias).
# Preference: a Python 3.9+ that already has pyodbc + openpyxl + pdfplumber + requests installed,
# newest stable first; otherwise the newest stable 3.9+. Override with $env:MPM_PYTHON.
function Get-MpmPython {
    if ($env:MPM_PYTHON -and (Test-Path $env:MPM_PYTHON)) { return $env:MPM_PYTHON }
    $cands = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in "-3.13","-3.12","-3.11","-3.10","-3.9","-3") {
            try { $p = & py $v -c "import sys; print(sys.executable)" 2>$null; if ($LASTEXITCODE -eq 0 -and $p) { $cands += $p.Trim() } } catch {}
        }
    }
    foreach ($c in (Get-Command python, python3 -All -ErrorAction SilentlyContinue)) {
        if ($c.Source -notlike "*WindowsApps*") { $cands += $c.Source }
    }
    $cands += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "$env:LOCALAPPDATA\Python\pythoncore-3*\python.exe", "C:\Program Files\Python3*\python.exe", "C:\Python3*\python.exe", "$env:USERPROFILE\anaconda3\python.exe", "$env:USERPROFILE\miniconda3\python.exe" -ErrorAction SilentlyContinue | ForEach-Object FullName
    $cands = $cands | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique
    $ok = @()
    foreach ($p in $cands) {
        $v = & $p -c "import sys; print('%d.%d' % sys.version_info[:2]) if sys.version_info >= (3,9) else None; print(sys.version_info.releaselevel)" 2>$null
        if ($v -and $v[0] -ne "None") { $ok += [pscustomobject]@{ Path = $p; Ver = [version]$v[0]; Final = ($v[1] -eq "final") } }
    }
    if (-not $ok) { throw "No Python 3.9+ found. Install Python 3.12 from python.org, or set `$env:MPM_PYTHON to python.exe." }
    $ok = $ok | Sort-Object @{e={$_.Final};Descending=$true}, @{e={$_.Ver};Descending=$true}
    foreach ($c in $ok) {
        & $c.Path -c "import pyodbc, openpyxl, pdfplumber, requests" 2>$null
        if ($LASTEXITCODE -eq 0) { return $c.Path }
    }
    return $ok[0].Path
}
