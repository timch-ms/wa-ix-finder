$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$profile = Join-Path $env:LOCALAPPDATA "WA-iX-Finder\EdgeProfile"
$extension = Join-Path $root "extension"

if (-not (Test-Path $edge)) {
    throw "Microsoft Edge was not found at $edge"
}

$server = Start-Process -FilePath "python" `
    -ArgumentList (Join-Path $root "collector\server.py") `
    -WorkingDirectory $root `
    -PassThru

Start-Sleep -Seconds 2

$urls = @(
    "http://127.0.0.1:4173/",
    "https://www.bmwseattle.com/inventory/used-bmw-ix/?waixcollector=1",
    "https://www.bmwbellevue.com/inventory/used/bmw-ix.htm?waixcollector=1",
    "https://bmwnorthwest.com/cars/ix?waixcollector=1",
    "https://www.bmwlynnwood.com/searchused.aspx?Model=iX&waixcollector=1",
    "https://www.bmwtricities.com/used-vehicles/?_dFR%5Bmake%5D%5B0%5D=BMW&_dFR%5Bmodel%5D%5B0%5D=iX&waixcollector=1",
    "https://www.bmwofspokane.com/searchused.aspx?Model=iX&waixcollector=1",
    "https://www.bmwofportland.com/searchused.aspx?Model=iX&waixcollector=1",
    "https://www.bmwtigard.com/used-vehicles/?_dFR%5Bmake%5D%5B0%5D=BMW&_dFR%5Bmodel%5D%5B0%5D=iX&waixcollector=1"
)

$arguments = @(
    "--user-data-dir=$profile",
    "--disable-extensions-except=$extension",
    "--load-extension=$extension",
    "--no-first-run"
) + $urls

Start-Process -FilePath $edge -ArgumentList $arguments
Write-Host "WA iX Finder is running at http://127.0.0.1:4173/"
Write-Host "Collector server PID: $($server.Id)"
