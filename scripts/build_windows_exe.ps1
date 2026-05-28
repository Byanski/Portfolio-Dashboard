$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Find-Python {
  foreach ($candidate in @("python", "python3", "py")) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
      return $candidate
    }
  }

  throw "Python was not found. Install Python 3, then run this script again."
}

$Python = Find-Python

& $Python -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Installing PyInstaller..."
  & $Python -m pip install pyinstaller
}

Write-Host "Building PortfolioBuilderInstaller.exe..."
& $Python -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name PortfolioBuilderInstaller `
  --add-data "templates;templates" `
  --add-data "scripts\generate_portfolio.py;scripts" `
  scripts\installer_gui.py

$RootExe = Join-Path $Root "PortfolioBuilderInstaller.exe"
Copy-Item -Path (Join-Path $Root "dist\PortfolioBuilderInstaller.exe") -Destination $RootExe -Force

Write-Host "Built dist\PortfolioBuilderInstaller.exe"
Write-Host "Copied PortfolioBuilderInstaller.exe to the project root."
Write-Host "Distribute it with the project folder so package.json, src, scripts, and templates are beside it."
