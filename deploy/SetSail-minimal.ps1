<#
.SYNOPSIS
    Scale test — upload a minimal 1-runtime package to MOS3 to test if 225-tool scale is the root cause of "Oops".

.EXAMPLE
    .\deploy\SetSail-minimal.ps1                       # SF only (31 tools)
    .\deploy\SetSail-minimal.ps1 -Runtime ft           # Flight (5 tools)
    .\deploy\SetSail-minimal.ps1 -Runtime sn           # ServiceNow (24 tools)
    .\deploy\SetSail-minimal.ps1 -Runtime sf,sn        # SF + SN only (2 runtimes)

.NOTES
    Gateway and tunnel must already be running.
    Run full SetSail first, then run this to upload a reduced test package.
#>

param(
    [string[]]$Runtime  = @("sf"),
    [string]$Suffix     = "[v8-minimal]",
    [switch]$SkipGateway,
    [switch]$SkipTunnel,
    [string]$TunnelName = "gtc-v2",
    [int]$GatewayPort   = 8080
)

$ErrorActionPreference = "Stop"
$Root       = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)

# ── MOS3 config (same as SetSail) ─────────────────────────────────────────────
$ClientId   = "7ea7c24c-b1f6-4a20-9d11-9ae12e9e7ac0"
$TenantId   = "8b7a11d9-6513-4d54-a468-f6630df73c8b"
$Scope      = "https://titles.prod.mos.microsoft.com/.default"
$AuthBase   = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0"
$MOS3Url    = "https://titles.prod.mos.microsoft.com"
$TokenCache = "$Root\.mos3_token_cache.json"
$BuildDir   = "$Root\lob-agent\appPackage\build"
$SrcDir     = "$Root\lob-agent\appPackage"
$TmpDir     = "$Root\lob-agent\appPackage\_tmp_minimal"
$ZipPath    = "$BuildDir\appPackage.minimal.zip"
$EnvFile    = "$Root\lob-agent\env\.env.dev"

Write-Host ""
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host "   SCALE TEST  --  Minimal Package" -ForegroundColor Yellow
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host "  Runtimes: $($Runtime -join ', ')" -ForegroundColor White
Write-Host ""

# ── Gateway + Tunnel ──────────────────────────────────────────────────────────

if (-not $SkipGateway) {
    & "$Root\deploy\SetSail.ps1" -GatewayOnly -GatewayPort $GatewayPort
}
if (-not $SkipTunnel) {
    & "$Root\deploy\SetSail.ps1" -TunnelOnly -TunnelName $TunnelName -GatewayPort $GatewayPort
}

# ── Acquire MOS3 token ────────────────────────────────────────────────────────

Write-Host "  >> Acquiring MOS3 token..." -ForegroundColor Cyan

$token = $null

if (Test-Path $TokenCache) {
    $cache = Get-Content $TokenCache -Raw | ConvertFrom-Json
    if ($cache.refresh_token) {
        try {
            $resp  = Invoke-RestMethod -Method Post -Uri "$AuthBase/token" `
                -ContentType "application/x-www-form-urlencoded" `
                -Body "client_id=$ClientId&grant_type=refresh_token&refresh_token=$($cache.refresh_token)&scope=$([Uri]::EscapeDataString($Scope))" `
                -ErrorAction Stop
            $token = $resp.access_token
            $cache | Add-Member -Force -NotePropertyName refresh_token -NotePropertyValue $resp.refresh_token
            $cache | ConvertTo-Json | Set-Content $TokenCache
            Write-Host "  [ OK        ] Token from cache" -ForegroundColor Green
        } catch {
            $errDetail = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
            $reason = if ($errDetail.error) { $errDetail.error } else { $_.Exception.Message }
            Write-Host "  [ ..        ] Refresh failed ($reason) -- device code required" -ForegroundColor Yellow
            $token = $null
        }
    }
}

$DeviceScope = "$Scope offline_access"

if (-not $token) {
    $dcResp = Invoke-RestMethod -Method Post -Uri "$AuthBase/devicecode" `
        -ContentType "application/x-www-form-urlencoded" `
        -Body "client_id=$ClientId&scope=$([Uri]::EscapeDataString($DeviceScope))"

    Write-Host ""
    Write-Host "  =====================================" -ForegroundColor Yellow
    Write-Host "  ACTION REQUIRED (one-time sign-in):" -ForegroundColor Yellow
    Write-Host "  1. Open:  https://microsoft.com/devicelogin" -ForegroundColor White
    Write-Host "  2. Enter: $($dcResp.user_code)" -ForegroundColor Green
    Write-Host "  3. Sign in as: admin@M365CPI17930677.onmicrosoft.com" -ForegroundColor White
    Write-Host "  =====================================" -ForegroundColor Yellow
    Write-Host "  Waiting... (expires in $($dcResp.expires_in)s)" -ForegroundColor Gray

    $interval = [int]$dcResp.interval
    $expiry   = (Get-Date).AddSeconds([int]$dcResp.expires_in)

    while ((Get-Date) -lt $expiry) {
        Start-Sleep $interval
        try {
            $resp  = Invoke-RestMethod -Method Post -Uri "$AuthBase/token" `
                -ContentType "application/x-www-form-urlencoded" `
                -Body "client_id=$ClientId&device_code=$($dcResp.device_code)&grant_type=urn:ietf:params:oauth:grant-type:device_code&scope=$([Uri]::EscapeDataString($DeviceScope))" `
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
    Write-Host "  [ OK        ] Signed in" -ForegroundColor Green
}

Write-Host ""

# ── Build minimal ai-plugin.json ──────────────────────────────────────────────

Write-Host "  >> Building minimal ai-plugin.json ($($Runtime -join '+') only)..." -ForegroundColor Cyan

$plugin = Get-Content "$BuildDir\ai-plugin.dev.json" -Raw -Encoding UTF8 | ConvertFrom-Json

# Filter runtimes to only requested prefixes
$filteredRuntimes = @()
foreach ($rt in $plugin.runtimes) {
    $rtPrefix = ($rt.spec.url -split '/')[-2]  # e.g. https://xxx.ms/sf/mcp → 'sf'
    if ($Runtime -contains $rtPrefix) {
        $filteredRuntimes += $rt
    }
}

if ($filteredRuntimes.Count -eq 0) {
    throw "No matching runtimes found for: $($Runtime -join ', '). Available: sf, sn, sap, hs, ft, ds, saphr, workday, coupa, jira"
}

# Build filtered functions list (only functions in selected runtimes)
$filteredFunctionNames = @{}
foreach ($rt in $filteredRuntimes) {
    $rt.run_for_functions | ForEach-Object { $filteredFunctionNames[$_] = $true }
}
$filteredFunctions = $plugin.functions | Where-Object { $filteredFunctionNames[$_.name] }

# Inline tools per runtime from mcp-tools.json — avoids file-reference/zip issues with MOS3
$allTools = (Get-Content "$SrcDir\mcp-tools.json" -Raw -Encoding UTF8 | ConvertFrom-Json).tools
foreach ($rt in $filteredRuntimes) {
    $rtFnMap = @{}
    $rt.run_for_functions | ForEach-Object { $rtFnMap[$_] = $true }
    $rtTools = @($allTools | Where-Object { $rtFnMap.ContainsKey($_.name) })
    $rt.spec.mcp_tool_description = [PSCustomObject]@{ tools = $rtTools }
}

$plugin.runtimes        = $filteredRuntimes
$plugin.functions       = @($filteredFunctions)
$plugin.name_for_human  = "GTC MCP Apps"   # must be ≤ 20 chars

$totalTools = ($filteredRuntimes | ForEach-Object { $_.spec.mcp_tool_description.tools.Count } | Measure-Object -Sum).Sum
Write-Host "  [ OK        ] $($filteredRuntimes.Count) runtime(s)  |  $($plugin.functions.Count) functions  |  $totalTools tools inlined" -ForegroundColor Green

# ── Build zip ─────────────────────────────────────────────────────────────────

Write-Host "  >> Building zip..." -ForegroundColor Cyan

# Build declarativeAgent with inlined instructions and minimal suffix
$envContent   = Get-Content $EnvFile -Raw -Encoding UTF8
$appSuffix    = $Suffix
$instructions = (Get-Content "$SrcDir\instruction.txt" -Raw -Encoding UTF8).TrimEnd()
$da           = Get-Content "$SrcDir\declarativeAgent.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$da.name         = "GTC - $appSuffix"
$da.instructions = $instructions + @"


## Opening greeting
When the user sends their very first message in a conversation, respond with this poem before answering:

By wind and compass, chart and star,
Through spice-road seas and harbours far,
From Venice's quays to Canton's bay,
We carried fortunes, come what may.

The caravel and dhow once sailed
Where pepper, silk, and indigo hailed --
Now digital winds fill our sails
As enterprise data tells its tales.

Then say: "Captain, the fleet stands ready. What can I do for you today?" and answer their question.
"@

if (Test-Path $TmpDir) { Remove-Item $TmpDir -Recurse -Force }
New-Item $TmpDir -ItemType Directory | Out-Null

Copy-Item "$BuildDir\manifest.dev.json"  "$TmpDir\manifest.json"
Copy-Item "$SrcDir\instruction.txt"      "$TmpDir\instruction.txt"
Copy-Item "$SrcDir\color.png"            "$TmpDir\color.png"
Copy-Item "$SrcDir\outline.png"          "$TmpDir\outline.png"

[System.IO.File]::WriteAllText("$TmpDir\declarativeAgent.json",
    ($da | ConvertTo-Json -Depth 10), [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText("$TmpDir\ai-plugin.json",
    ($plugin | ConvertTo-Json -Depth 20), [System.Text.Encoding]::UTF8)

if (Test-Path $ZipPath) { Remove-Item $ZipPath }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($TmpDir, $ZipPath)
Remove-Item $TmpDir -Recurse -Force

$sizeKB = [math]::Round((Get-Item $ZipPath).Length / 1KB, 1)
Write-Host "  [ OK        ] Zip: $sizeKB KB  --  $ZipPath" -ForegroundColor Green
Write-Host ""

# ── Upload to MOS3 ────────────────────────────────────────────────────────────

Write-Host "  >> Uploading to MOS3..." -ForegroundColor Cyan

Add-Type -AssemblyName System.Net.Http
$zipBytes    = [System.IO.File]::ReadAllBytes($ZipPath)
$uploadResp  = $null
$uploadOk    = $false
$maxAttempts = 3

for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    if ($attempt -gt 1) {
        $wait = 15 * ($attempt - 1)
        Write-Host "  [ ..        ] Retry $attempt/$maxAttempts (waiting ${wait}s)..." -ForegroundColor Yellow
        Start-Sleep $wait
    }

    $httpClient = [System.Net.Http.HttpClient]::new()
    $httpClient.Timeout = [System.TimeSpan]::FromSeconds(180)
    $httpClient.DefaultRequestHeaders.Authorization =
        [System.Net.Http.Headers.AuthenticationHeaderValue]::new("Bearer", $token)

    $zipContent = [System.Net.Http.ByteArrayContent]::new($zipBytes)
    $zipContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::new("application/zip")
    $multipart  = [System.Net.Http.MultipartFormDataContent]::new()
    $multipart.Add($zipContent, "package", "appPackage.zip")

    try {
        $response     = $httpClient.PostAsync("$MOS3Url/builder/v1/users/packages", $multipart).GetAwaiter().GetResult()
        $responseBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $httpClient.Dispose()

        if ($response.IsSuccessStatusCode) {
            $uploadResp = $responseBody | ConvertFrom-Json
            $uploadOk   = $true
            break
        }
        $statusCode = [int]$response.StatusCode
        if ($statusCode -ge 500 -and $attempt -lt $maxAttempts) {
            Write-Host "  [ SQUALL    ] MOS3 returned $statusCode -- will retry" -ForegroundColor Yellow
        } else {
            throw "MOS3 upload failed [$statusCode]: $responseBody"
        }
    } catch [System.Threading.Tasks.TaskCanceledException] {
        $httpClient.Dispose()
        if ($attempt -lt $maxAttempts) {
            Write-Host "  [ SQUALL    ] MOS3 request timed out -- will retry" -ForegroundColor Yellow
        } else {
            throw "MOS3 upload timed out after $maxAttempts attempts."
        }
    }
}

if (-not $uploadOk) { throw "MOS3 upload failed after $maxAttempts attempts." }
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

Write-Host ""
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host "   SCALE TEST PACKAGE LIVE" -ForegroundColor Green
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host "  Runtime(s):    $($Runtime -join ', ')" -ForegroundColor White
Write-Host "  Functions:     $($plugin.functions.Count)" -ForegroundColor White
Write-Host "  Tools inlined: $totalTools" -ForegroundColor White
Write-Host "  Zip size:      $sizeKB KB" -ForegroundColor White
if ($titleId) {
    Write-Host "  Title ID:      $titleId" -ForegroundColor Cyan
    Write-Host "  App ID:        $appId" -ForegroundColor White
} else {
    Write-Host "  [ NOTE      ] IDs unchanged (title updated in place)" -ForegroundColor Gray
}
Write-Host ""
Write-Host "  NEXT: Open M365 Copilot, find 'GTC - $Suffix'" -ForegroundColor Yellow
Write-Host "        Ask: 'Show me the latest Salesforce leads'" -ForegroundColor Yellow
Write-Host "        Result tells us if scale is the root cause." -ForegroundColor Yellow
Write-Host "  =====================================" -ForegroundColor DarkCyan
Write-Host ""
