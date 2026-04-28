<#
.SYNOPSIS
    Provision-Agent -- Build zip + push to MOS3 in one shot.
    Token is cached after first sign-in; no browser needed on subsequent runs.

.EXAMPLE
    .\deploy\Provision-Agent.ps1
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)

# ── Config ──────────────────────────────────────────────────────────────────

$ClientId  = "7ea7c24c-b1f6-4a20-9d11-9ae12e9e7ac0"
$TenantId  = "8b7a11d9-6513-4d54-a468-f6630df73c8b"
$Scope     = "https://titles.prod.mos.microsoft.com/.default"
$AuthBase  = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0"
$MOS3Url   = "https://titles.prod.mos.microsoft.com"
$TokenCache= "$Root\.mos3_token_cache.json"

$BuildDir  = "$Root\lob-agent\appPackage\build"
$SrcDir    = "$Root\lob-agent\appPackage"
$TmpDir    = "$Root\lob-agent\appPackage\_tmp_zip"
$ZipPath   = "$BuildDir\appPackage.dev.zip"
$EnvFile   = "$Root\lob-agent\env\.env.dev"

# ── Banner ───────────────────────────────────────────────────────────────────

Clear-Host
Write-Host ""
Write-Host "  Provision-Agent -- GTC Declarative Agent" -ForegroundColor Cyan
Write-Host "  =========================================" -ForegroundColor DarkCyan
Write-Host ""

# ── Step 1: Get token (cached or device code) ────────────────────────────────

Write-Host "  [1/3] Acquiring MOS3 token..." -ForegroundColor Cyan

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
        Write-Host "  [OK] Token from cache (no sign-in needed)" -ForegroundColor Green
    } catch {
        Write-Host "  [..] Cached token expired -- falling back to device code" -ForegroundColor Yellow
        $token = $null
    }
}

if (-not $token) {
    $dcResp = Invoke-RestMethod -Method Post -Uri "$AuthBase/devicecode" `
        -ContentType "application/x-www-form-urlencoded" `
        -Body "client_id=$ClientId&scope=$([Uri]::EscapeDataString($Scope))"

    Write-Host ""
    Write-Host "  =========================================" -ForegroundColor Yellow
    Write-Host "  ACTION REQUIRED (one-time sign-in):" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Open:  https://microsoft.com/devicelogin" -ForegroundColor White
    Write-Host "  2. Enter: $($dcResp.user_code)" -ForegroundColor Green
    Write-Host "  3. Sign in as: admin@M365CPI17930677.onmicrosoft.com" -ForegroundColor White
    Write-Host ""
    Write-Host "  =========================================" -ForegroundColor Yellow
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
    Write-Host "  [OK] Signed in -- token cached for next run" -ForegroundColor Green
}

# ── Step 2: Build zip ────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  [2/3] Building app package..." -ForegroundColor Cyan

# Embed current instruction.txt into declarativeAgent.dev.json
$daFile = "$BuildDir\declarativeAgent.dev.json"
Set-ItemProperty $daFile -Name IsReadOnly -Value $false -ErrorAction SilentlyContinue
$instructions = (Get-Content "$SrcDir\instruction.txt" -Raw).TrimEnd()
$da = Get-Content $daFile -Raw | ConvertFrom-Json
$da.instructions = $instructions
$da | ConvertTo-Json -Depth 10 | Set-Content $daFile -Encoding UTF8

# Build zip
if (Test-Path $TmpDir) { Remove-Item $TmpDir -Recurse -Force }
New-Item $TmpDir -ItemType Directory | Out-Null

Copy-Item "$BuildDir\manifest.dev.json"         "$TmpDir\manifest.json"
Copy-Item "$BuildDir\declarativeAgent.dev.json"  "$TmpDir\declarativeAgent.json"
Copy-Item "$SrcDir\instruction.txt"              "$TmpDir\instruction.txt"
Copy-Item "$SrcDir\color.png"                    "$TmpDir\color.png"
Copy-Item "$SrcDir\outline.png"                  "$TmpDir\outline.png"

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
Write-Host "  [OK] Zip built: $sizeKB KB  |  Instructions: $($instructions.Length) chars" -ForegroundColor Green

# ── Step 3: Upload to MOS3 ───────────────────────────────────────────────────

Write-Host ""
Write-Host "  [3/3] Uploading to MOS3..." -ForegroundColor Cyan

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
Write-Host "  [OK] Uploaded" -ForegroundColor Green

# Poll if async
if ($uploadResp.operationId -or ($uploadResp.statusId -and -not $uploadResp.titlePreview)) {
    $pollId = if ($uploadResp.operationId) { $uploadResp.operationId } else { $uploadResp.statusId }
    Write-Host "  [..] Polling async status..." -ForegroundColor Gray
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

# Extract IDs
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
    Write-Host "  [NOTE] IDs unchanged (title updated in place)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  =========================================" -ForegroundColor DarkCyan
Write-Host "  AGENT PROVISIONED" -ForegroundColor Green
Write-Host "  =========================================" -ForegroundColor DarkCyan
Write-Host "  Test in Teams Copilot -- ask for latest leads" -ForegroundColor Gray
Write-Host ""
