<#
.SYNOPSIS
Starts the local API, worker and Angular UI, opens the app and stops them on Ctrl+C.
.EXAMPLE
.\scripts\dev.ps1
.EXAMPLE
.\scripts\dev.ps1 -Setup
.EXAMPLE
.\scripts\dev.ps1 -ApiPort 8010 -UiPort 4210 -NoBrowser
.EXAMPLE
.\scripts\dev.ps1 -Check -Database runtime\dev-check\arena.sqlite
#>
[CmdletBinding()]
param(
    [ValidateRange(1024,65535)][int]$ApiPort = 8000,
    [ValidateRange(1024,65535)][int]$UiPort = 4200,
    [string]$Database = 'runtime\dev\arena.sqlite',
    [switch]$Setup,
    [switch]$NoBrowser,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$frontend = Join-Path $projectRoot 'frontend'
$angular = Join-Path $frontend 'node_modules\@angular\cli\bin\ng.js'
$databasePath = if ([IO.Path]::IsPathRooted($Database)) { [IO.Path]::GetFullPath($Database) } else { [IO.Path]::GetFullPath((Join-Path $projectRoot $Database)) }
$originalDb = $env:ARENA_DB
$originalRoot = $env:ARENA_ROOT
$processes = @()
$workerProcess = $null
$sessionDirectory = $null

function Assert-FreePort([int]$Port) {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try { $listener.Start() }
    catch { throw "Port $Port is occupied. Stop that server or choose -ApiPort and -UiPort. No existing process was stopped." }
    finally { $listener.Stop() }
}

function Start-DevProcess([string]$Name, [string]$Executable, [string[]]$Arguments) {
    # Windows paths cannot contain quotes. Quote each argument because Start-Process joins the array.
    $quoted = $Arguments | ForEach-Object { '"' + $_ + '"' }
    $process = Start-Process -FilePath $Executable -ArgumentList $quoted -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $sessionDirectory "$Name.log") -RedirectStandardError (Join-Path $sessionDirectory "$Name.error.log")
    return $process
}

function Assert-Running {
    foreach ($process in $processes) {
        $process.Refresh()
        if ($process.HasExited) { throw "A development service exited (PID $($process.Id)). Check logs in $sessionDirectory." }
    }
}

function Wait-Ready([string]$Url, [string]$Label) {
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    while ([DateTime]::UtcNow -lt $deadline) {
        Assert-Running
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Milliseconds 300
    }
    throw "$Label did not become ready. Check logs in $sessionDirectory."
}

try {
    if ($ApiPort -eq $UiPort) { throw 'API and UI ports must be different.' }
    Assert-FreePort $ApiPort
    Assert-FreePort $UiPort
    $node = (Get-Command node -ErrorAction SilentlyContinue).Source
    $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
    if (!$node -or !$npm) { throw 'Install Node.js 22.12+ (branch 22), then restart PowerShell.' }
    $nodeVersion = [Version]((& $node --version).TrimStart('v'))
    if (!(($nodeVersion.Major -eq 20 -and $nodeVersion -ge [Version]'20.19.0') -or ($nodeVersion.Major -eq 22 -and $nodeVersion -ge [Version]'22.12.0') -or $nodeVersion.Major -eq 24)) {
        throw "Node $nodeVersion is not supported. Use Node 22.12+ (branch 22)."
    }
    if ($Setup) {
        if (!(Test-Path -LiteralPath $python)) {
            & py -3.11 -m venv (Join-Path $projectRoot '.venv')
            if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Install Python 3.11 and its py launcher.' }
        }
        & $python -m pip install -r (Join-Path $projectRoot 'requirements.lock')
        if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
        & $python -m pip install --no-deps --no-build-isolation -e $projectRoot
        if ($LASTEXITCODE -ne 0) { throw 'Project installation failed.' }
        & $npm --prefix $frontend ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    }
    if (!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath $angular)) {
        throw 'Dependencies are missing. Run .\scripts\dev.ps1 -Setup once (requires network access).'
    }
    & $python -c 'import sys, fastapi, uvicorn, arena.worker; assert (3,11) <= sys.version_info[:2] < (3,13), "Use Python 3.11 or 3.12"'
    if ($LASTEXITCODE -ne 0) { throw 'Python dependencies are missing or incompatible. Run .\scripts\dev.ps1 -Setup.' }

    $sessionDirectory = Join-Path $projectRoot ('runtime\dev\sessions\' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $sessionDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($databasePath)) -Force | Out-Null
    $proxyPath = Join-Path $sessionDirectory 'proxy.json'
    $proxy = @{ '/api/**' = @{ target = "http://127.0.0.1:$ApiPort"; secure = $false; pathRewrite = @{ '^/api' = '' } } }
    [IO.File]::WriteAllText($proxyPath, ($proxy | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    $env:ARENA_DB = $databasePath
    $env:ARENA_ROOT = $projectRoot
    $processes += Start-DevProcess 'api' $python @('-m','uvicorn','arena.api:app','--host','127.0.0.1','--port',"$ApiPort")
    $workerProcess = Start-DevProcess 'worker' $python @((Join-Path $PSScriptRoot 'dev_worker.py'),'--db',$databasePath,'--session-directory',$sessionDirectory)
    $processes += $workerProcess
    $processes += Start-DevProcess 'frontend' $node @($angular,'serve','--host','127.0.0.1','--port',"$UiPort",'--proxy-config',$proxyPath)
    Wait-Ready "http://127.0.0.1:$ApiPort/auth/session" 'API'
    Wait-Ready "http://127.0.0.1:$UiPort/api/auth/session" 'Frontend proxy'
    Wait-Ready "http://127.0.0.1:$UiPort/" 'Frontend'
    Assert-Running
    if (!(Test-Path -LiteralPath (Join-Path $sessionDirectory 'worker-ready'))) { throw 'Worker did not become ready. Check worker.error.log.' }
    $url = "http://127.0.0.1:$UiPort/"
    Write-Host "Agent Arena ready: $url"
    Write-Host "Development SQLite: $databasePath"
    Write-Host "Logs: $sessionDirectory"
    Write-Host 'Use the simulator; no model download or Ollama startup is required.'
    if ($Check) { Write-Host 'Startup check passed; stopping the test services.'; return }
    if (!$NoBrowser) { Start-Process -FilePath $url }
    Write-Host 'Keep this terminal open. Ctrl+C stops these services.'
    while ($true) { Assert-Running; Start-Sleep -Seconds 1 }
}
finally {
    if ($processes.Count) { Write-Host 'Stopping development services...' }
    # Ask the worker to cancel cooperatively before stopping the API. Never recover or delete history.
    if ($workerProcess -and $sessionDirectory) {
        New-Item -ItemType File -Path (Join-Path $sessionDirectory 'stop-worker') -Force | Out-Null
        $workerProcess.Refresh()
        if (!$workerProcess.HasExited) { $null = $workerProcess.WaitForExit(15000) }
    }
    foreach ($process in $processes) {
        $process.Refresh()
        if (!$process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
    }
    $env:ARENA_DB = $originalDb
    $env:ARENA_ROOT = $originalRoot
}
