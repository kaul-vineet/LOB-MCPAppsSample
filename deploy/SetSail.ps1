<#
.SYNOPSIS
    Set Sail! -- Fire up the GTC fleet, open the dev tunnel, and push the agent to MOS3.

.EXAMPLE
    .\deploy\SetSail.ps1                       # Full launch: gateway + tunnel + MOS3
    .\deploy\SetSail.ps1 -GatewayOnly          # Start (or reattach to) gateway only
    .\deploy\SetSail.ps1 -TunnelOnly           # Start (or reattach to) tunnel only
    .\deploy\SetSail.ps1 -SkipGateway          # Tunnel + MOS3 (gateway already running)
    .\deploy\SetSail.ps1 -SkipTunnel           # Gateway + MOS3 only
    .\deploy\SetSail.ps1 -TunnelName gtc-v2    # Named tunnel override

.NOTES
    Requires: Python 3.11+, Dev Tunnels CLI
#>

param(
    [switch]$SkipGateway,
    [switch]$SkipTunnel,
    [switch]$GatewayOnly,
    [switch]$TunnelOnly,
    [string]$TunnelName  = "gtc-v2",
    [int]$GatewayPort    = 8080
)

$ErrorActionPreference = "Stop"
$Root       = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$VenvPython = "$Root\gateway\.venv\Scripts\python.exe"

# ── MOS3 config ───────────────────────────────────────────────────────────────
$ClientId   = "7ea7c24c-b1f6-4a20-9d11-9ae12e9e7ac0"
$TenantId   = "8b7a11d9-6513-4d54-a468-f6630df73c8b"
$Scope      = "https://titles.prod.mos.microsoft.com/.default"
$AuthBase   = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0"
$MOS3Url    = "https://titles.prod.mos.microsoft.com"
$TokenCache = "$Root\.mos3_token_cache.json"
$BuildDir   = "$Root\lob-agent\appPackage\build"
$SrcDir     = "$Root\lob-agent\appPackage"
$TmpDir     = "$Root\lob-agent\appPackage\_tmp_zip"
$ZipPath    = "$BuildDir\appPackage.dev.zip"
$EnvFile    = "$Root\lob-agent\env\.env.dev"

# ── Banner ────────────────────────────────────────────────────────────────────

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

# ── Pre-flight checks ─────────────────────────────────────────────────────────

Write-Host "  >> Pre-flight checks" -ForegroundColor Cyan
Write-Host ""

$errors = @()

if (-not $SkipGateway -and -not $TunnelOnly) {
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

if (-not $SkipTunnel -and -not $GatewayOnly) {
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

# ── Start gateway ─────────────────────────────────────────────────────────────

if (-not $SkipGateway -and -not $TunnelOnly) {
    $gatewayUp = $false
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$GatewayPort" -Method GET -TimeoutSec 2 -ErrorAction Stop
        $gatewayUp = $true
    } catch {
        if ($_.Exception.Response -ne $null) { $gatewayUp = $true }
    }

    if ($gatewayUp) {
        Write-Host "  [ HELM      ] Gateway already running --> http://localhost:$GatewayPort" -ForegroundColor Green
        Write-Host ""
    } else {
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
            $gatewayUp = $false
            try {
                $null = Invoke-WebRequest -Uri "http://localhost:$GatewayPort" -Method GET -TimeoutSec 2 -ErrorAction Stop
                $gatewayUp = $true
            } catch {
                if ($_.Exception.Response -ne $null) { $gatewayUp = $true }
            }
            Write-Host "`r  [ WATCH     ] Waiting for gateway... ${waited}s" -NoNewline -ForegroundColor Yellow
        } while (-not $gatewayUp -and $waited -lt $maxWait)

        Write-Host ""
        if ($gatewayUp) {
            Write-Host "  [ SAILS UP  ] Gateway is live --> http://localhost:$GatewayPort" -ForegroundColor Green
        } else {
            Write-Host "  [ SQUALL    ] Gateway not responding after ${maxWait}s -- check the gateway window" -ForegroundColor Yellow
        }
        Write-Host ""
    }
}

if ($GatewayOnly) {
    Write-Host "  =====================================" -ForegroundColor DarkCyan
    Write-Host "   GATEWAY ONLY -- DONE" -ForegroundColor Green
    Write-Host "  =====================================" -ForegroundColor DarkCyan
    Write-Host "  Gateway  -->  http://localhost:$GatewayPort" -ForegroundColor White
    Write-Host ""
    exit 0
}

# ── Start tunnel ──────────────────────────────────────────────────────────────

$tunnelUrl = $null

if (-not $SkipTunnel) {
    $existingInfo = (devtunnel show $TunnelName 2>$null) | Out-String
    if ($existingInfo -match 'https://(\S+-\d+\.\S+devtunnels\.ms)') {
        $tunnelUrl = "https://$($Matches[1])"
        Write-Host "  [ SIGNAL    ] Tunnel already hosting --> $tunnelUrl" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "  >> Opening sea lane (dev tunnel '$TunnelName')..." -ForegroundColor Cyan

        if ($LASTEXITCODE -ne 0 -or -not ($existingInfo -match 'Tunnel ID')) {
            Write-Host "  [ CHARTING  ] Tunnel not found -- charting new course..." -ForegroundColor Yellow
            devtunnel create $TunnelName --allow-anonymous
            devtunnel port create $TunnelName -p $GatewayPort --protocol auto
        } else {
            $portExists = $existingInfo | Select-String "$GatewayPort"
            if (-not $portExists) {
                devtunnel port create $TunnelName -p $GatewayPort --protocol auto
            }
        }

        Start-Process powershell -ArgumentList @(
            "-NoExit", "-Command",
            "`$host.UI.RawUI.WindowTitle = 'GTC Tunnel ($TunnelName)'; devtunnel host $TunnelName --allow-anonymous"
        )

        Write-Host "  [ WATCH     ] Waiting for tunnel to register..." -NoNewline -ForegroundColor Yellow
        for ($i = 0; $i -lt 12; $i++) {
            Start-Sleep 3
            $info = (devtunnel show $TunnelName 2>$null) | Out-String
            if ($info -match 'https://(\S+-\d+\.\S+devtunnels\.ms)') {
                $tunnelUrl = "https://$($Matches[1])"
                break
            }
            Write-Host "." -NoNewline -ForegroundColor Yellow
        }
        Write-Host ""
        if ($tunnelUrl) {
            Write-Host "  [ OPEN SEAS ] Tunnel live --> $tunnelUrl" -ForegroundColor Green
        } else {
            Write-Host "  [ OPEN SEAS ] Tunnel window launched (URL not yet visible)" -ForegroundColor Yellow
        }
        Write-Host ""
    }
}

if ($TunnelOnly) {
    Write-Host "  =====================================" -ForegroundColor DarkCyan
    Write-Host "   TUNNEL ONLY -- DONE" -ForegroundColor Green
    Write-Host "  =====================================" -ForegroundColor DarkCyan
    if ($tunnelUrl) {
        Write-Host "  Tunnel   -->  $tunnelUrl" -ForegroundColor White
    } else {
        Write-Host "  Tunnel   -->  check the tunnel window" -ForegroundColor Gray
    }
    Write-Host ""
    exit 0
}

# ── Patch tunnel URL in ai-plugin if it changed ───────────────────────────────

$pluginPath = "$BuildDir\ai-plugin.dev.json"

if (-not $SkipTunnel -and (Test-Path $pluginPath)) {
    Write-Host "  >> Checking tunnel URL..." -ForegroundColor Cyan
    if ($tunnelUrl) {
        $pluginRaw = Get-Content $pluginPath -Raw
        if ($pluginRaw -match '"url"\s*:\s*"(https://[^"]+devtunnels\.ms)') {
            $existingBase = $Matches[1]
            if ($existingBase -ne $tunnelUrl) {
                Write-Host "  [ CHART     ] URL changed -- patching ai-plugin.dev.json" -ForegroundColor Yellow
                Write-Host "                OLD: $existingBase" -ForegroundColor DarkGray
                Write-Host "                NEW: $tunnelUrl"    -ForegroundColor DarkGray
                $pluginRaw = $pluginRaw -replace [regex]::Escape($existingBase), $tunnelUrl
                [System.IO.File]::WriteAllText($pluginPath, $pluginRaw, [System.Text.Encoding]::UTF8)
            } else {
                Write-Host "  [ CHART     ] URL unchanged ($tunnelUrl)" -ForegroundColor Green
            }
        }
    } else {
        Write-Host "  [ CHART     ] Tunnel URL unavailable -- skipping patch (URL in tunnel window)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# ── Sync tool names into manifests ───────────────────────────────────────────

Write-Host "  >> Syncing tool names into manifests..." -ForegroundColor Cyan
& $VenvPython "$Root\deploy\regen_manifests.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ WARN      ] regen_manifests.py exited with errors -- continuing" -ForegroundColor Yellow
}
Write-Host ""

# ── Acquire MOS3 token ────────────────────────────────────────────────────────

Write-Host "  >> Acquiring MOS3 token..." -ForegroundColor Cyan

$token = $null

if (Test-Path $TokenCache) {
    try {
        $cache = Get-Content $TokenCache -Raw | ConvertFrom-Json
        $resp  = Invoke-RestMethod -Method Post -Uri "$AuthBase/token" `
            -ContentType "application/x-www-form-urlencoded" `
            -Body "client_id=$ClientId&grant_type=refresh_token&refresh_token=$($cache.refresh_token)&scope=$([Uri]::EscapeDataString($Scope))" `
            -ErrorAction Stop
        $token = $resp.access_token
        $cache | Add-Member -Force -NotePropertyName refresh_token -NotePropertyValue $resp.refresh_token
        $cache | ConvertTo-Json | Set-Content $TokenCache
        Write-Host "  [ OK        ] Token from cache" -ForegroundColor Green
    } catch {
        Write-Host "  [ ..        ] Cached token expired -- falling back to device code" -ForegroundColor Yellow
        $token = $null
    }
}

if (-not $token) {
    $dcResp = Invoke-RestMethod -Method Post -Uri "$AuthBase/devicecode" `
        -ContentType "application/x-www-form-urlencoded" `
        -Body "client_id=$ClientId&scope=$([Uri]::EscapeDataString($Scope))"

    Write-Host ""
    Write-Host "  =====================================" -ForegroundColor Yellow
    Write-Host "  ACTION REQUIRED (one-time sign-in):" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Open:  https://microsoft.com/devicelogin" -ForegroundColor White
    Write-Host "  2. Enter: $($dcResp.user_code)" -ForegroundColor Green
    Write-Host "  3. Sign in as: admin@M365CPI17930677.onmicrosoft.com" -ForegroundColor White
    Write-Host ""
    Write-Host "  =====================================" -ForegroundColor Yellow
    Write-Host "  Waiting... (expires in $($dcResp.expires_in)s)" -ForegroundColor Gray

    $interval = [int]$dcResp.interval
    $expiry   = (Get-Date).AddSeconds([int]$dcResp.expires_in)

    while ((Get-Date) -lt $expiry) {
        Start-Sleep $interval
        try {
            $resp  = Invoke-RestMethod -Method Post -Uri "$AuthBase/token" `
                -ContentType "application/x-www-form-urlencoded" `
                -Body "client_id=$ClientId&device_code=$($dcResp.device_code)&grant_type=urn:ietf:params:oauth:grant-type:device_code" `
                -ErrorAction Stop
            $token = $resp.access_token
            @{ refresh_token = $resp.refresh_token } | ConvertTo-Json | Set-Content $TokenCache
            break
        } catch {
            $err = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($err.error -eq "authorization_pending") {
                Write-Host "`r  Still waiting..." -NoNewline -ForegroundColor Gray
            } elseif ($err.error -eq "slow_down") {
                $interval += 5
            } else {
                throw "Token error: $($err.error) -- $($err.error_description)"
            }
        }
    }
    if (-not $token) { throw "Device code expired." }
    Write-Host ""
    Write-Host "  [ OK        ] Signed in -- token cached for next run" -ForegroundColor Green
}

Write-Host ""

# ── Build app package zip ─────────────────────────────────────────────────────

Write-Host "  >> Building app package..." -ForegroundColor Cyan

$daFile = "$BuildDir\declarativeAgent.dev.json"
Set-ItemProperty $daFile -Name IsReadOnly -Value $false -ErrorAction SilentlyContinue
$instructions = (Get-Content "$SrcDir\instruction.txt" -Raw).TrimEnd()
$da = Get-Content $daFile -Raw | ConvertFrom-Json
$da.instructions = $instructions
$da | ConvertTo-Json -Depth 10 | Set-Content $daFile -Encoding UTF8

if (Test-Path $TmpDir) { Remove-Item $TmpDir -Recurse -Force }
New-Item $TmpDir -ItemType Directory | Out-Null

Copy-Item "$BuildDir\manifest.dev.json"        "$TmpDir\manifest.json"
Copy-Item "$BuildDir\declarativeAgent.dev.json" "$TmpDir\declarativeAgent.json"
Copy-Item "$SrcDir\instruction.txt"             "$TmpDir\instruction.txt"
Copy-Item "$SrcDir\color.png"                   "$TmpDir\color.png"
Copy-Item "$SrcDir\outline.png"                 "$TmpDir\outline.png"

$plugin = Get-Content "$BuildDir\ai-plugin.dev.json" -Raw | ConvertFrom-Json
foreach ($rt in $plugin.runtimes) {
    if ($rt.spec.PSObject.Properties['mcp_tool_description']) {
        $rt.spec.PSObject.Properties.Remove('mcp_tool_description')
    }
}
$plugin | ConvertTo-Json -Depth 20 | Set-Content "$TmpDir\ai-plugin.json" -Encoding UTF8

if (Test-Path $ZipPath) { Remove-Item $ZipPath }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($TmpDir, $ZipPath)
Remove-Item $TmpDir -Recurse -Force

$sizeKB = [math]::Round((Get-Item $ZipPath).Length / 1KB, 1)
Write-Host "  [ OK        ] Zip built: $sizeKB KB  |  Instructions: $($instructions.Length) chars" -ForegroundColor Green
Write-Host ""

# ── Upload to MOS3 ────────────────────────────────────────────────────────────

Write-Host "  >> Uploading to MOS3..." -ForegroundColor Cyan

Add-Type -AssemblyName System.Net.Http
$httpClient = [System.Net.Http.HttpClient]::new()
$httpClient.Timeout = [System.TimeSpan]::FromSeconds(120)
$httpClient.DefaultRequestHeaders.Authorization =
    [System.Net.Http.Headers.AuthenticationHeaderValue]::new("Bearer", $token)

$zipBytes   = [System.IO.File]::ReadAllBytes($ZipPath)
$zipContent = [System.Net.Http.ByteArrayContent]::new($zipBytes)
$zipContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::new("application/zip")
$multipart  = [System.Net.Http.MultipartFormDataContent]::new()
$multipart.Add($zipContent, "package", "appPackage.zip")

$response     = $httpClient.PostAsync("$MOS3Url/builder/v1/users/packages", $multipart).GetAwaiter().GetResult()
$responseBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()

if (-not $response.IsSuccessStatusCode) {
    throw "MOS3 upload failed [$([int]$response.StatusCode)]: $responseBody"
}

$uploadResp = $responseBody | ConvertFrom-Json
Write-Host "  [ OK        ] Uploaded" -ForegroundColor Green

if ($uploadResp.operationId -or ($uploadResp.statusId -and -not $uploadResp.titlePreview)) {
    $pollId = if ($uploadResp.operationId) { $uploadResp.operationId } else { $uploadResp.statusId }
    Write-Host "  [ ..        ] Polling async status..." -ForegroundColor Gray
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep 3
        $status = Invoke-RestMethod -Method Get `
            -Uri "$MOS3Url/builder/v1/users/packages/status/$pollId" `
            -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 30
        Write-Host "  Status: $($status.status)" -ForegroundColor Gray
        if ($status.status -eq "succeeded") { $uploadResp = $status; break }
        if ($status.status -in @("failed","error")) { throw "MOS3 failed: $($status | ConvertTo-Json -Compress)" }
    }
}

$preview = if ($uploadResp.titlePreview) { $uploadResp.titlePreview } else { $uploadResp }
$titleId = if ($uploadResp.titleId) { $uploadResp.titleId } elseif ($preview.titleId) { $preview.titleId } else { $null }
$appId   = if ($uploadResp.appId)   { $uploadResp.appId }   elseif ($preview.appId)   { $preview.appId }   else { $null }

if ($titleId) {
    $lines = Get-Content $EnvFile
    $lines = $lines | ForEach-Object {
        if ($_ -match "^M365_TITLE_ID=") { "M365_TITLE_ID=$titleId" }
        elseif ($_ -match "^M365_APP_ID=") { "M365_APP_ID=$appId" }
        else { $_ }
    }
    $lines | Set-Content $EnvFile
    Write-Host "  M365_TITLE_ID = $titleId" -ForegroundColor White
    Write-Host "  M365_APP_ID   = $appId"   -ForegroundColor White
} else {
    Write-Host "  [ NOTE      ] IDs unchanged (title updated in place)" -ForegroundColor Gray
}

Write-Host ""

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host "   ALL HANDS ON DECK -- FLEET IS LIVE  " -ForegroundColor Green
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host "  Gateway  -->  http://localhost:$GatewayPort" -ForegroundColor White
Write-Host "  Routes:  /sf  /sn  /sap  /hs  /ft  /ds" -ForegroundColor Gray
Write-Host "           /saphr  /workday  /coupa  /jira" -ForegroundColor Gray
if (-not $SkipTunnel) {
    if ($tunnelUrl) {
        Write-Host "  Tunnel   -->  $tunnelUrl" -ForegroundColor White
    } else {
        Write-Host "  Tunnel   -->  check the tunnel window" -ForegroundColor Gray
    }
}
Write-Host "  MOS3     -->  agent package live in Teams" -ForegroundColor Gray
Write-Host "  To stop:      close the gateway window" -ForegroundColor DarkGray
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  Fair winds and following seas, Captain!" -ForegroundColor Cyan
Write-Host ""
