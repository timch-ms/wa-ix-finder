$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"

if (-not (Test-Path $edge)) {
    throw "Microsoft Edge was not found at $edge"
}

try {
    $existing = Invoke-RestMethod -Uri "http://127.0.0.1:4174/api/health" -TimeoutSec 1
    if ($existing.ok -and $existing.service -eq "auto-dev-cache") {
        Start-Process -FilePath $edge -ArgumentList "http://127.0.0.1:4174/auto-dev.html"
        Write-Host "Auto.dev WA iX Finder is already running with PID $($existing.pid)."
        return
    }
}
catch {
    # No cache server is listening yet.
}

$key = $env:AUTO_DEV_API_KEY
$credentialPointer = [IntPtr]::Zero
if (-not $key) {
    $secureKey = Read-Host "Auto.dev API key" -AsSecureString
    try {
        $credentialPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
        $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($credentialPointer)
    }
    finally {
        if ($credentialPointer -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($credentialPointer)
        }
    }
}

$env:AUTO_DEV_API_KEY = $key
try {
    $server = Start-Process -FilePath "python" `
        -ArgumentList (Join-Path $root "auto_dev\server.py") `
        -WorkingDirectory $root `
        -PassThru
}
finally {
    Remove-Item Env:AUTO_DEV_API_KEY -ErrorAction SilentlyContinue
    $key = $null
}

$ready = $false
foreach ($attempt in 1..30) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:4174/api/health" -TimeoutSec 1
        if ($health.ok -and $health.service -eq "auto-dev-cache") {
            $ready = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $ready) {
    throw "The Auto.dev cache server did not become ready within 30 seconds."
}

Start-Process -FilePath $edge -ArgumentList "http://127.0.0.1:4174/auto-dev.html"
Write-Host "Auto.dev WA iX Finder is running at http://127.0.0.1:4174/auto-dev.html"
Write-Host "Daily cache server PID: $($server.Id)"
