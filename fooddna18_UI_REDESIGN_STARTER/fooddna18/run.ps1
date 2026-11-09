$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (Test-Path "fooddna18") {
    Set-Location "fooddna18"
} elseif (Test-Path "fooddna18_UI_REDESIGN_STARTER\fooddna18") {
    Set-Location "fooddna18_UI_REDESIGN_STARTER\fooddna18"
}

$pythonExe = if (Test-Path ".\venv\Scripts\python.exe") { ".\venv\Scripts\python.exe" } else { "python" }
& $pythonExe run.py @args
