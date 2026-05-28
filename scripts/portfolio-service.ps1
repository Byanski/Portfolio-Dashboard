$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $Root "logs"
$PidFile = Join-Path $LogDir "vite.pid"
$ServiceLog = Join-Path $LogDir "portfolio-service.log"
$OutLog = Join-Path $LogDir "vite.out.log"
$ErrLog = Join-Path $LogDir "vite.err.log"
$GeneratorLog = Join-Path $LogDir "generator.log"
$GeneratorErrLog = Join-Path $LogDir "generator.err.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-ServiceLog {
  param([string]$Message)

  $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $ServiceLog -Value "[$stamp] $Message"
}

function Stop-Portfolio {
  if (Test-Path $PidFile) {
    $pidText = Get-Content -Path $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pidText -match "^\d+$") {
      $existing = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
      if ($existing) {
        Write-ServiceLog "Stopping Vite process tree rooted at PID $pidText"
        Stop-Process -Id $existing.Id -Force -ErrorAction SilentlyContinue
      }
    }
  }

  $viteProcesses = Get-CimInstance Win32_Process |
    Where-Object {
      $_.CommandLine -like "*portfolio website*" -and
      ($_.CommandLine -like "*vite*--port*5173*" -or $_.CommandLine -like "*npm*run*dev*")
    }

  foreach ($process in $viteProcesses) {
    Write-ServiceLog "Stopping stale process $($process.ProcessId): $($process.Name)"
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
  }
}

function Start-Portfolio {
  Stop-Portfolio

  Write-ServiceLog "Starting Vite on 0.0.0.0:5173"
  $process = Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173" `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -PassThru

  Set-Content -Path $PidFile -Value $process.Id
  Write-ServiceLog "Started Vite root PID $($process.Id)"
}

function Update-PortfolioData {
  Write-ServiceLog "Regenerating portfolio data from portfolio.config.json"
  $process = Start-Process `
    -FilePath "python" `
    -ArgumentList "scripts\generate_portfolio.py", "--config", "portfolio.config.json" `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $GeneratorLog `
    -RedirectStandardError $GeneratorErrLog `
    -PassThru `
    -Wait

  if ($process.ExitCode -eq 0) {
    Write-ServiceLog "Portfolio data regenerated"
  }
  else {
    Write-ServiceLog "Portfolio data generation failed with exit code $($process.ExitCode)"
  }
}

$ignoredSegments = @("\node_modules\", "\dist\", "\.git\", "\logs\", "\.portfolio-cache\")
$watchedExtensions = @(".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".md")
$global:PortfolioPendingRestart = $false
$global:PortfolioLastRestartRequest = Get-Date "2000-01-01"
$global:PortfolioPendingGenerate = $false
$global:PortfolioSuppressEventsUntil = Get-Date "2000-01-01"

function Should-RestartForPath {
  param([string]$Path)

  foreach ($segment in $ignoredSegments) {
    if ($Path -like "*$segment*") {
      return $false
    }
  }

  $extension = [System.IO.Path]::GetExtension($Path)
  return $watchedExtensions -contains $extension
}

Write-ServiceLog "Portfolio service runner booting"
Start-Portfolio

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $Root
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true
$watcher.NotifyFilter = [System.IO.NotifyFilters]"FileName, LastWrite, CreationTime"

$handler = {
  if ((Get-Date) -lt $global:PortfolioSuppressEventsUntil) {
    return
  }

  if (Should-RestartForPath -Path $Event.SourceEventArgs.FullPath) {
    if ([System.IO.Path]::GetFileName($Event.SourceEventArgs.FullPath) -eq "portfolio.config.json") {
      $global:PortfolioPendingGenerate = $true
    }
    $global:PortfolioPendingRestart = $true
    $global:PortfolioLastRestartRequest = Get-Date
    Write-ServiceLog "Change detected: $($Event.SourceEventArgs.FullPath)"
  }
}

$subscriptions = @(
  Register-ObjectEvent -InputObject $watcher -EventName Changed -Action $handler
  Register-ObjectEvent -InputObject $watcher -EventName Created -Action $handler
  Register-ObjectEvent -InputObject $watcher -EventName Deleted -Action $handler
  Register-ObjectEvent -InputObject $watcher -EventName Renamed -Action $handler
)

try {
  while ($true) {
    Start-Sleep -Seconds 2

    if ($global:PortfolioPendingRestart -and ((Get-Date) - $global:PortfolioLastRestartRequest).TotalSeconds -ge 3) {
      $global:PortfolioPendingRestart = $false
      if ($global:PortfolioPendingGenerate) {
        $global:PortfolioPendingGenerate = $false
        $global:PortfolioSuppressEventsUntil = (Get-Date).AddMinutes(2)
        Update-PortfolioData
        $global:PortfolioSuppressEventsUntil = (Get-Date).AddSeconds(3)
      }
      Write-ServiceLog "Restarting after file change debounce"
      Start-Portfolio
    }

    if (Test-Path $PidFile) {
      $pidText = Get-Content -Path $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($pidText -match "^\d+$") {
        $running = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
        if (-not $running) {
          Write-ServiceLog "Vite process is not running; restarting"
          Start-Portfolio
        }
      }
    }
  }
}
finally {
  foreach ($subscription in $subscriptions) {
    Unregister-Event -SubscriptionId $subscription.Id -ErrorAction SilentlyContinue
  }

  $watcher.Dispose()
  Stop-Portfolio
  Write-ServiceLog "Portfolio service runner stopped"
}
