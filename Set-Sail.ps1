<#
.SYNOPSIS
    Set Sail! — Start all four MCP trading posts and the harbour tunnel.

.DESCRIPTION
    Launches all four LOB MCP servers via Docker Compose and the dev tunnel
    in a separate PowerShell window. One command to rule the entire trading empire.

    Supports two modes:
      - Docker (default): docker compose up -d
      - Native (--Native): launches each server in its own PowerShell window via .venv

.EXAMPLE
    .\Set-Sail.ps1                     # Docker + tunnel
    .\Set-Sail.ps1 -Native             # Python venvs + tunnel
    .\Set-Sail.ps1 -SkipTunnel         # Docker only, no tunnel
    .\Set-Sail.ps1 -TunnelName gtc-v2  # Use a specific named tunnel

.NOTES
    Author: The Great Trading Company
    Requires: Docker Desktop OR Python 3.11+, Dev Tunnels CLI
#>

param(
    [switch]$SkipTunnel,
    [switch]$Native,
    [string]$TunnelName = "gtc-v2",
    [string[]]$Only
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition

# ── Fleet manifest ────────────────────────────────────────────────────────────

$Fleet = @(
    @{ Name = "sf";      Title = "⛵ Salesforce (port 3000)";   Dir = "sf-mcp-app";      Module = "sf_crm_mcp";      Port = 3000; Service = "salesforce" }
    @{ Name = "snow";    Title = "🎫 ServiceNow (port 3001)";  Dir = "snow-mcp-app";    Module = "servicenow_mcp";  Port = 3001; Service = "servicenow" }
    @{ Name = "sap";     Title = "📦 SAP S/4HANA (port 3002)"; Dir = "sap-mcp-app";     Module = "sap_s4hana_mcp";  Port = 3002; Service = "sap" }
    @{ Name = "hubspot"; Title = "🧡 HubSpot (port 3003)";     Dir = "hubspot-mcp-app"; Module = "hubspot_mcp";     Port = 3003; Service = "hubspot" }
)

# ── Banner ────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "              |    |    |                 " -ForegroundColor DarkYellow
Write-Host "             )_)  )_)  )_)               " -ForegroundColor DarkYellow
Write-Host "            )___))___))___)               " -ForegroundColor DarkYellow
Write-Host "           )____)____)_____)              " -ForegroundColor DarkYellow
Write-Host "         _____|____|____|____\___         " -ForegroundColor White
Write-Host "  ------\                       /------   " -ForegroundColor Cyan
Write-Host "    ^^^^ \_____________________/          " -ForegroundColor Blue
Write-Host "      ^^^^       ^^^^     ^^^    ^^       " -ForegroundColor Blue
Write-Host "           ^^^^      ^^^                  " -ForegroundColor DarkBlue
Write-Host ""
Write-Host "  ⚓ The Great Trading Company — Setting Sail!" -ForegroundColor Cyan
Write-Host "  ════════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host ""

# ── Pre-flight checks ────────────────────────────────────────────────────────

$errors = @()

if (-not $Native) {
    # Docker mode checks
    $dockerCheck = docker info 2>$null
    if ($LASTEXITCODE -ne 0) {
        $errors += "  ✗ Docker Desktop is not running — start it first"
    } else {
        Write-Host "  ✓ Docker Desktop — running" -ForegroundColor Green
    }
    foreach ($ship in $Fleet) {
        if ($Only -and $Only -notcontains $ship.Name) { continue }
        $envFile = Join-Path $Root $ship.Dir ".env"
        if (-not (Test-Path $envFile)) {
            $errors += "  ✗ $($ship.Dir)/.env not found — run: cp $($ship.Dir)/.env.example $($ship.Dir)/.env and fill in credentials"
        } else {
            Write-Host "  ✓ $($ship.Title) — .env ready" -ForegroundColor Green
        }
    }
} else {
    # Native mode checks
    foreach ($ship in $Fleet) {
        if ($Only -and $Only -notcontains $ship.Name) { continue }
        $appDir = Join-Path $Root $ship.Dir
        $venvPython = Join-Path $appDir ".venv\Scripts\python.exe"
        $envFile = Join-Path $appDir ".env"
        if (-not (Test-Path $appDir)) {
            $errors += "  ✗ $($ship.Dir)/ folder not found"
        } elseif (-not (Test-Path $venvPython)) {
            $errors += "  ✗ $($ship.Dir)/.venv not found — run: cd $($ship.Dir) && python -m venv .venv && .venv\Scripts\activate && pip install -e ."
        } elseif (-not (Test-Path $envFile)) {
            $errors += "  ✗ $($ship.Dir)/.env not found — run: cp $($ship.Dir)/.env.example $($ship.Dir)/.env and fill in credentials"
        } else {
            Write-Host "  ✓ $($ship.Title) — ready" -ForegroundColor Green
        }
    }
}

if (-not $SkipTunnel) {
    $devtunnelCheck = Get-Command devtunnel -ErrorAction SilentlyContinue
    if (-not $devtunnelCheck) {
        $errors += "  ✗ Dev Tunnels CLI not found — install from https://learn.microsoft.com/azure/developer/dev-tunnels/get-started"
    } else {
        Write-Host "  ✓ Dev Tunnels CLI — installed" -ForegroundColor Green
    }
}

if ($errors.Count -gt 0) {
    Write-Host ""
    foreach ($e in $errors) { Write-Host $e -ForegroundColor Red }
    Write-Host ""
    Write-Host "  Fix the issues above before setting sail." -ForegroundColor Yellow
    exit 1
}

# ── Launch the fleet ──────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  Launching trading posts..." -ForegroundColor Cyan
Write-Host ""

if (-not $Native) {
    # Docker mode
    $services = ($Fleet | Where-Object { -not $Only -or $Only -contains $_.Name } | ForEach-Object { $_.Service }) -join " "
    Set-Location $Root
    Invoke-Expression "docker compose up -d $services"
    Write-Host ""

    # Wait for healthy
    $maxWait = 30
    $waited = 0
    do {
        Start-Sleep 2
        $waited += 2
        $health = docker compose ps --format "{{.Status}}" 2>$null
        $allHealthy = ($health | Where-Object { $_ -match "healthy" }).Count
        $total = ($health | Measure-Object).Count
    } while ($allHealthy -lt $total -and $waited -lt $maxWait)

    foreach ($ship in $Fleet) {
        if ($Only -and $Only -notcontains $ship.Name) { continue }
        $status = docker compose ps --format "{{.Name}}:{{.Status}}" 2>$null | Where-Object { $_ -match $ship.Service }
        if ($status -match "healthy") {
            Write-Host "  ✓ $($ship.Title) — healthy" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ $($ship.Title) — starting..." -ForegroundColor Yellow
        }
    }
} else {
    # Native mode
    foreach ($ship in $Fleet) {
        if ($Only -and $Only -notcontains $ship.Name) { continue }
        $appDir = Join-Path $Root $ship.Dir
        $venvPython = Join-Path $appDir ".venv\Scripts\python.exe"
        Start-Process powershell -ArgumentList @(
            "-NoExit", "-Command",
            "Set-Location '$appDir'; `$host.UI.RawUI.WindowTitle = '$($ship.Title)'; & '$venvPython' -m $($ship.Module)"
        )
        Write-Host "  ⛵ $($ship.Title) — launched" -ForegroundColor Green
    }
}

# ── Open the harbour tunnel ───────────────────────────────────────────────────

if (-not $SkipTunnel) {
    Write-Host ""
    Write-Host "  Opening the harbour tunnel..." -ForegroundColor Cyan

    $tunnelExists = devtunnel show $TunnelName 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠  Tunnel '$TunnelName' not found. Creating..." -ForegroundColor Yellow
        devtunnel create $TunnelName --allow-anonymous
        foreach ($ship in $Fleet) {
            if ($Only -and $Only -notcontains $ship.Name) { continue }
            devtunnel port create $TunnelName -p $ship.Port 2>$null
        }
    }

    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "`$host.UI.RawUI.WindowTitle = '🚇 Dev Tunnel ($TunnelName)'; devtunnel host $TunnelName --allow-anonymous"
    )

    Write-Host "  🚇 Harbour tunnel — opened" -ForegroundColor Green
}

# ── Fleet status ──────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ════════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host "  ⚓ All hands on deck! The fleet has sailed." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Mode: $(if ($Native) { 'Native (Python venvs)' } else { 'Docker' })" -ForegroundColor White
Write-Host ""
Write-Host "  Trading posts:" -ForegroundColor White
foreach ($ship in $Fleet) {
    if ($Only -and $Only -notcontains $ship.Name) { continue }
    Write-Host "    $($ship.Title)  →  http://localhost:$($ship.Port)/mcp" -ForegroundColor Gray
}
if (-not $SkipTunnel) {
    Write-Host ""
    Write-Host "  Tunnel: devtunnel host $TunnelName --allow-anonymous" -ForegroundColor Gray
}
Write-Host ""
if (-not $Native) {
    Write-Host "  To stop: docker compose down" -ForegroundColor DarkGray
} else {
    Write-Host "  To stop: close the individual terminal windows" -ForegroundColor DarkGray
}
Write-Host ""
