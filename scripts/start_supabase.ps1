<# Start API, worker and UI using a locally stored PostgreSQL URL. #>
[CmdletBinding()]
param(
    [string]$Python = '.venv\Scripts\python.exe',
    [switch]$NoBrowser,
    [switch]$Check,
    [ValidateRange(1024,65535)][int]$ApiPort = 8000,
    [ValidateRange(1024,65535)][int]$UiPort = 4200
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$secretPath = Join-Path $projectRoot 'runtime\supabase\database-url.txt'
$previousUrl = $env:ARENA_DATABASE_URL
try {
    if (!$env:ARENA_DATABASE_URL) {
        if (!(Test-Path -LiteralPath $secretPath)) {
            throw 'Guarda la URL de Session pooler en runtime\supabase\database-url.txt, sin comillas y en una sola línea.'
        }
        $env:ARENA_DATABASE_URL = ([IO.File]::ReadAllText($secretPath)).Trim()
    }
    if ($env:ARENA_DATABASE_URL -notmatch '^postgres(ql)?://') { throw 'La configuración debe ser una URL PostgreSQL.' }
    & (Join-Path $PSScriptRoot 'dev.ps1') -Python $Python -ApiPort $ApiPort -UiPort $UiPort -NoBrowser:$NoBrowser -Check:$Check
} finally {
    $env:ARENA_DATABASE_URL = $previousUrl
}
