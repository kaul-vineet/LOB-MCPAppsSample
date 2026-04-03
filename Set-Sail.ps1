<#
.SYNOPSIS
    Set Sail! — Start all four MCP trading posts and the harbour tunnel.

.DESCRIPTION
    Launches all four LOB MCP servers (Salesforce, ServiceNow, SAP, HubSpot)
    and the dev tunnel in separate PowerShell windows. One command to rule
    the entire trading empire.

.EXAMPLE
    .\Set-Sail.ps1
    .\Set-Sail.ps1 -SkipTunnel        # Start servers only, no tunnel
    .\Set-Sail.ps1 -Only sf,sap       # Start only Salesforce and SAP

.NOTES
    Author: The Great Trading Company
    Requires: Python 3.11+, Dev Tunnels CLI, .venv set up in each app folder
#>

param(
    [switch]$SkipTunnel,
    [string[]]$Only
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition

# ── Fleet manifest ────────────────────────────────────────────────────────────

$Fleet = @(
    @{ Name = "sf";      Title = "⛵ Salesforce (port 3000)";   Dir = "sf-mcp-app";      Module = "sf_crm_mcp";      Port = 3000 }
    @{ Name = "snow";    Title = "🎫 ServiceNow (port 3001)";  Dir = "snow-mcp-app";    Module = "servicenow_mcp";  Port = 3001 }
    @{ Name = "sap";     Title = "📦 SAP S/4HANA (port 3002)"; Dir = "sap-mcp-app";     Module = "sap_s4hana_mcp";  Port = 3002 }
    @{ Name = "hubspot"; Title = "🧡 HubSpot (port 3003)";     Dir = "hubspot-mcp-app"; Module = "hubspot_mcp";     Port = 3003 }
)

# ── Pre-flight checks ────────────────────────────────────────────────────────

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

$errors = @()
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

# ── Open the harbour tunnel ───────────────────────────────────────────────────

if (-not $SkipTunnel) {
    Write-Host ""
    Write-Host "  Opening the harbour tunnel..." -ForegroundColor Cyan

    $tunnelExists = devtunnel show gtc-tunnel 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠  Tunnel 'gtc-tunnel' not found. Creating..." -ForegroundColor Yellow
        devtunnel create gtc-tunnel --allow-anonymous
        foreach ($ship in $Fleet) {
            if ($Only -and $Only -notcontains $ship.Name) { continue }
            devtunnel port create gtc-tunnel -p $ship.Port 2>$null
        }
    }

    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "`$host.UI.RawUI.WindowTitle = '🚇 Dev Tunnel (gtc-tunnel)'; devtunnel host gtc-tunnel"
    )

    Write-Host "  🚇 Harbour tunnel — opened" -ForegroundColor Green
}

# ── Fleet status ──────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ════════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host "  ⚓ All hands on deck! The fleet has sailed." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Trading posts:" -ForegroundColor White
foreach ($ship in $Fleet) {
    if ($Only -and $Only -notcontains $ship.Name) { continue }
    Write-Host "    $($ship.Title)  →  http://localhost:$($ship.Port)/mcp" -ForegroundColor Gray
}
if (-not $SkipTunnel) {
    Write-Host ""
    Write-Host "  Tunnel: devtunnel host gtc-tunnel" -ForegroundColor Gray
}
Write-Host ""
Write-Host "  To stop: close the individual terminal windows" -ForegroundColor DarkGray
Write-Host ""
