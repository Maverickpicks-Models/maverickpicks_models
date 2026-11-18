# Returns the full path of a real Python 3.11+ (skips the Microsoft Store "python" alias).
function Get-MpmPython {
    if ($env:MPM_PYTHON -and (Test-Path $env:MPM_PYTHON)) { return $env:MPM_PYTHON }
    $cands = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in "-3.12","-3.13","-3.11","-3") {
            try { $p = & py $v -c "import sys; print(sys.executable)" 2>$null; if ($LASTEXITCODE -eq 0 -and $p) { $cands += $p.Trim() } } catch {}
        }
    }
    foreach ($c in (Get-Command python, python3 -All -ErrorAction SilentlyContinue)) {
        if ($c.Source -notlike "*WindowsApps*") { $cands += $c.Source }
    }
    $cands += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "C:\Program Files\Python3*\python.exe", "C:\Python3*\python.exe", "$env:USERPROFILE\anaconda3\python.exe", "$env:USERPROFILE\miniconda3\python.exe" -ErrorAction SilentlyContinue | ForEach-Object FullName
    foreach ($p in $cands) {
        if ($p -and (Test-Path $p)) {
            $ok = & $p -c "import sys; print(sys.version_info >= (3,11))" 2>$null
            if ($ok -eq "True") { return $p }
        }
    }
    throw "No Python 3.11+ found. Install from python.org (tick 'Add to PATH'), or set `$env:MPM_PYTHON to the full path of python.exe."
}
