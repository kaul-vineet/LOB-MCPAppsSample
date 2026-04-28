<#
.SYNOPSIS
    Set Sail! -- Fire up the GTC fleet and open the dev tunnel to the world.

.EXAMPLE
    .\Set-Sail.ps1                        # Full launch: gateway + tunnel
    .\Set-Sail.ps1 -Provision             # Full launch + push agent package to MOS3
    .\Set-Sail.ps1 -SkipGateway           # Tunnel only  (gateway already running)
    .\Set-Sail.ps1 -SkipTunnel            # Gateway only (no tunnel)
    .\Set-Sail.ps1 -TunnelName gtc-v2     # Named tunnel override

.NOTES
    Requires: Python 3.11+, Dev Tunnels CLI
    -Provision: also patches ai-plugin.dev.json if the tunnel URL changed, then
                uploads the agent package to MOS3 via deploy\Provision-Agent.ps1
#>

param(
    [switch]$SkipGateway,
    [switch]$SkipTunnel,
    [switch]$Provision,
    [string]$TunnelName  = "gtc-v2",
    [int]$GatewayPort    = 8080
)

$ErrorActionPreference = "Stop"
$Root       = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$VenvPython = "$Root\gateway\.venv\Scripts\python.exe"

# ---- Banner ------------------------------------------------------------------

Clear-Host
Write-Host ""
Write-Host "          *  .       .  *    .       *  .  " -ForegroundColor DarkGray
Write-Host "    *  .      [+]        .      *  .       " -ForegroundColor DarkYellow
Write-Host "       .    -/   \-   *    .         *     " -ForegroundColor DarkYellow
Write-Host "  *      .   [===]    .        *  .        " -ForegroundColor DarkGray
Write-Host ""
Write-Host "  ~~~  THE GREAT TRADING COMPANY  ~~~" -ForegroundColor Cyan
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host "       10 LOB MCP Servers  |  Port $GatewayPort" -ForegroundColor Gray
Write-Host ""
Write-Host "          |    |    |"  -ForegroundColor White
Write-Host "         )_)  )_)  )_)"  -ForegroundColor White
Write-Host "        )___))___))___)"  -ForegroundColor White
Write-Host "       )____)____)_____)"  -ForegroundColor White
Write-Host "     _____|____|____|____\"  -ForegroundColor Cyan
Write-Host "  ---------\               /---------" -ForegroundColor Cyan
Write-Host "    ^^^^^ ^^^^^^^^^^^^^^^^  ^^^^^" -ForegroundColor Blue
Write-Host "      ^^^     ^^^^    ^^^    ^^" -ForegroundColor DarkBlue
Write-Host ""
Write-Host "  Salesforce  ServiceNow  SAP  HubSpot" -ForegroundColor DarkGray
Write-Host "  Flight  DocuSign  SAPHR  Workday  ..." -ForegroundColor DarkGray
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host ""

# ---- Pre-flight checks -------------------------------------------------------

Write-Host "  >> Pre-flight checks" -ForegroundColor Cyan
Write-Host ""

$errors = @()

if (-not $SkipGateway) {
    if (-not (Test-Path $VenvPython)) {
        Write-Host "  [ FIRST RUN ] No gateway venv found." -ForegroundColor Yellow
        Write-Host "  [ RIGGING   ] Building the ship -- this takes ~60 seconds..." -ForegroundColor Yellow
        Write-Host ""
        python -m venv "$Root\gateway\.venv"
        $pip = "$Root\gateway\.venv\Scripts\pip.exe"
        & $pip install --upgrade pip --quiet
        Write-Host "  [ LOADING   ] Stowing cargo: shared-mcp-lib..." -ForegroundColor DarkYellow
        & $pip install -e "$Root\shared-mcp-lib" --quiet
        foreach ($pkg in @("sf-mcp-app","snow-mcp-app","sap-mcp-app","hubspot-mcp-app",
                           "flight-mcp-app","docusign-mcp-app","saphr-mcp-app",
                           "workday-mcp-app","coupa-mcp-app","jira-mcp-app","gateway")) {
            Write-Host "  [ LOADING   ] Stowing cargo: $pkg..." -ForegroundColor DarkYellow
            & $pip install -e "$Root\$pkg" --quiet
        }
        Write-Host ""
        Write-Host "  [ READY     ] Ship is rigged and ready to sail." -ForegroundColor Green
    } else {
        Write-Host "  [ HELM      ] Gateway venv -- standing by" -ForegroundColor Green
    }
}

if (-not $SkipTunnel) {
    if (-not (Get-Command devtunnel -ErrorAction SilentlyContinue)) {
        $errors += "  [ ABORT ] Dev Tunnels CLI missing -- https://learn.microsoft.com/azure/developer/dev-tunnels/get-started"
    } else {
        Write-Host "  [ SIGNAL    ] Dev Tunnels CLI -- standing by" -ForegroundColor Green
    }
}

if ($errors.Count -gt 0) {
    Write-Host ""
    foreach ($e in $errors) { Write-Host $e -ForegroundColor Red }
    Write-Host ""
    Write-Host "  Fix the above before setting sail. Anchors aweigh... NOT." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# ---- Start gateway -----------------------------------------------------------

if (-not $SkipGateway) {
    Write-Host "  >> Raising the mainsail (starting gateway)..." -ForegroundColor Cyan

    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "`$host.UI.RawUI.WindowTitle = 'GTC Gateway (port $GatewayPort)'; Set-Location '$Root'; & '$VenvPython' -m gateway"
    )

    $maxWait = 30
    $waited  = 0
    do {
        Start-Sleep 2
        $waited += 2
        $up = $false
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:$GatewayPort" -Method GET -TimeoutSec 2 -ErrorAction Stop
            $up = $true
        } catch {
            if ($_.Exception.Response -ne $null) { $up = $true }
        }
        Write-Host "`r  [ WATCH     ] Waiting for gateway... ${waited}s" -NoNewline -ForegroundColor Yellow
    } while (-not $up -and $waited -lt $maxWait)

    Write-Host ""
    if ($up) {
        Write-Host "  [ SAILS UP  ] Gateway is live --> http://localhost:$GatewayPort" -ForegroundColor Green
    } else {
        Write-Host "  [ SQUALL    ] Gateway not responding after ${maxWait}s -- check the gateway window" -ForegroundColor Yellow
    }
    Write-Host ""
}

# ---- Start tunnel ------------------------------------------------------------

if (-not $SkipTunnel) {
    Write-Host "  >> Opening sea lane (dev tunnel '$TunnelName')..." -ForegroundColor Cyan

    $null = devtunnel show $TunnelName 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ CHARTING  ] Tunnel not found -- charting new course..." -ForegroundColor Yellow
        devtunnel create $TunnelName --allow-anonymous
        devtunnel port create $TunnelName -p $GatewayPort --protocol auto
    } else {
        $portExists = (devtunnel show $TunnelName 2>$null) | Select-String "$GatewayPort"
        if (-not $portExists) {
            devtunnel port create $TunnelName -p $GatewayPort --protocol auto
        }
    }

    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "`$host.UI.RawUI.WindowTitle = 'GTC Tunnel ($TunnelName)'; devtunnel host $TunnelName --allow-anonymous"
    )

    Write-Host "  [ OPEN SEAS ] Tunnel window launched -- public URL in new terminal" -ForegroundColor Green
    Write-Host ""
}

# ---- Provision (optional) ----------------------------------------------------

if ($Provision) {
    Write-Host "  >> Patching tunnel URL and provisioning agent..." -ForegroundColor Cyan
    Write-Host ""

    $pluginPath = "$Root\lob-agent\appPackage\build\ai-plugin.dev.json"

    if (-not $SkipTunnel -and (Test-Path $pluginPath)) {
        $tunnelInfo = (devtunnel show $TunnelName 2>$null) | Out-String
        if ($tunnelInfo -match 'https://(\S+-\d+\.\S+devtunnels\.ms)') {
            $currentBase = "https://$($Matches[1])"
            $pluginRaw   = Get-Content $pluginPath -Raw
            if ($pluginRaw -match '"url"\s*:\s*"(https://[^"]+devtunnels\.ms)') {
                $existingBase = $Matches[1]
                if ($existingBase -ne $currentBase) {
                    Write-Host "  [ CHART     ] Tunnel URL changed -- patching ai-plugin.dev.json" -ForegroundColor Yellow
                    Write-Host "                OLD: $existingBase" -ForegroundColor DarkGray
                    Write-Host "                NEW: $currentBase" -ForegroundColor DarkGray
                    $pluginRaw = $pluginRaw -replace [regex]::Escape($existingBase), $currentBase
                    [System.IO.File]::WriteAllText($pluginPath, $pluginRaw, [System.Text.Encoding]::UTF8)
                } else {
                    Write-Host "  [ CHART     ] Tunnel URL unchanged ($currentBase)" -ForegroundColor Green
                }
            }
        } else {
            Write-Host "  [ CHART     ] Could not read tunnel URL from devtunnel show -- skipping patch" -ForegroundColor Yellow
        }
        Write-Host ""
    }

    & "$Root\deploy\Provision-Agent.ps1"
}

# ---- Summary -----------------------------------------------------------------

Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host "   ALL HANDS ON DECK -- FLEET IS LIVE  " -ForegroundColor Green
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host "  Gateway  -->  http://localhost:$GatewayPort" -ForegroundColor White
Write-Host "  Routes:  /sf  /sn  /sap  /hs  /ft  /ds" -ForegroundColor Gray
Write-Host "           /saphr  /workday  /coupa  /jira" -ForegroundColor Gray
if (-not $SkipTunnel) {
    Write-Host "  Tunnel   -->  check the tunnel window" -ForegroundColor Gray
}
if ($Provision) {
    Write-Host "  MOS3     -->  agent package pushed" -ForegroundColor Gray
}
Write-Host "  To stop:      close the gateway window" -ForegroundColor DarkGray
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  Fair winds and following seas, Captain!" -ForegroundColor Cyan
Write-Host ""
