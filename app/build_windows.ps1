# Build Episode1.exe on Windows (x64).
# Requirements: Python 3.11 x64, Git optional.
# Run in PowerShell from this directory:  .\build_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv-win\Scripts\python.exe")) {
    python -m venv .venv-win
}
$py = ".venv-win\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
& $py -m pip install "pyinstaller==6.22.3"

if (Test-Path "build\Episode1") { Remove-Item -Recurse -Force "build\Episode1" }
if (Test-Path "dist\Episode1") { Remove-Item -Recurse -Force "dist\Episode1" }
if (Test-Path "dist\Episode1-Windows-x64.zip") { Remove-Item -Force "dist\Episode1-Windows-x64.zip" }

& $py -m PyInstaller `
  --noconfirm --clean --windowed `
  --name Episode1 `
  --icon assets\icon.ico `
  --add-data "..\arm\armctl.py;arm" `
  --add-data "..\arm\config\joints.json;arm\config" `
  --add-data "..\kinematics\__init__.py;kinematics" `
  --add-data "..\kinematics\episode1_model.py;kinematics" `
  --add-data "assets;assets" `
  --additional-hooks-dir hooks `
  --collect-all numpy `
  --collect-submodules x42s_stepper `
  --collect-submodules can `
  --collect-submodules serial `
  --collect-submodules episode1_app `
  main.py

Compress-Archive -Path "dist\Episode1\*" -DestinationPath "dist\Episode1-Windows-x64.zip" -Force
Write-Host "Built: $PWD\dist\Episode1\Episode1.exe"
Write-Host "Zip:   $PWD\dist\Episode1-Windows-x64.zip"
