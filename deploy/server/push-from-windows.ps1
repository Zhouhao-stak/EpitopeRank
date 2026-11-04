# One-command incremental deploy from Windows to 123.255.66.81.
#
#   $env:SSHPASS = '...'          # optional; without it ssh/scp prompt
#   .\deploy\server\push-from-windows.ps1
#   .\deploy\server\push-from-windows.ps1 -SkipUpdate   # upload only
#
# It packages the source tree (no venv/dist/public_datasets), uploads it to
# ~/epitoperank/.upload, and runs deploy/server/update-container.sh on the host.
# The container image is never rebuilt.

param(
    [string]$TargetHost = "123.255.66.81",
    [int]$Port = 39145,
    [string]$User = "wang_zi_wei",
    [string]$RemoteRoot = "epitoperank",
    [switch]$SkipUpdate
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location $root
try {
    $paths = @(
        "epitoperank", "deploy", "docs", "examples", "scripts", "tests",
        "run.py", "serve_ui.py", "desktop_ui.py", "pytest.ini",
        "README.md", "requirements.txt", "requirements-dev.txt"
    )
    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    $name = "epitoperank-server-$ts.tar.gz"
    $bundle = Join-Path $root "dist\$name"
    New-Item -ItemType Directory -Force -Path (Join-Path $root "dist") | Out-Null

    Write-Host "[1/4] packaging $name"
    tar -czf $bundle `
        --exclude="__pycache__" --exclude="*.pyc" --exclude=".pytest_cache" --exclude="*.log" `
        @paths
    if ($LASTEXITCODE -ne 0) { throw "tar failed" }
    $size = [math]::Round((Get-Item $bundle).Length / 1MB, 2)
    Write-Host "      $size MB"

    $ssh = @("-o", "StrictHostKeyChecking=no", "-p", "$Port")
    $scp = @("-o", "StrictHostKeyChecking=no", "-P", "$Port")
    $sshExe = "ssh"
    $scpExe = "scp"
    if ($env:SSHPASS) {
        $sshExe = "sshpass"
        $scpExe = "sshpass"
        $ssh = @("-e", "ssh") + $ssh
        $scp = @("-e", "scp") + $scp
    }

    $remote = "$User@$TargetHost"
    Write-Host "[2/4] create remote .upload"
    & $sshExe @ssh $remote "mkdir -p ~/$RemoteRoot/.upload"
    if ($LASTEXITCODE -ne 0) { throw "remote mkdir failed" }

    Write-Host "[3/4] upload"
    & $scpExe @scp $bundle "${remote}:~/$RemoteRoot/.upload/$name"
    if ($LASTEXITCODE -ne 0) { throw "scp failed" }

    # Upload the deploy tooling *before* invoking it: a bundle extracted by an
    # older update-container.sh cannot update the script that is already
    # running, so the launcher files must land first.
    & $scpExe @scp `
        (Join-Path $PSScriptRoot "update-container.sh") `
        (Join-Path $PSScriptRoot "rollback-container.sh") `
        (Join-Path $PSScriptRoot "docker-compose.server.yml") `
        "${remote}:~/$RemoteRoot/deploy/server/"
    if ($LASTEXITCODE -ne 0) { throw "deploy tooling upload failed" }

    if ($SkipUpdate) {
        Write-Host "[4/4] uploaded only; run on server:"
        Write-Host "      cd ~/$RemoteRoot && bash deploy/server/update-container.sh .upload/$name"
        return
    }

    Write-Host "[4/4] run update-container.sh (backup + extract + recreate)"
    & $sshExe @ssh $remote "cd ~/$RemoteRoot && bash deploy/server/update-container.sh .upload/$name"
    if ($LASTEXITCODE -ne 0) { throw "remote update failed; rollback with deploy/server/rollback-container.sh" }
}
finally {
    Pop-Location
}
