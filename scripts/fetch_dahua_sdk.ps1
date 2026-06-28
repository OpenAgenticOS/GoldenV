param(
    [string]$SdkPath = $env:DAHUA_SDK_PATH,
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

function Find-DahuaSdkRoot {
    param([string]$InitialPath)
    if ($InitialPath -and (Test-Path $InitialPath)) { return $InitialPath }

    $candidates = @(
        "${env:ProgramFiles}\HuarayTech\MV Viewer",
        "${env:ProgramFiles(x86)}\HuarayTech\MV Viewer",
        "${env:ProgramFiles}\HuarayTech\MVViewer",
        "${env:ProgramFiles(x86)}\HuarayTech\MVViewer",
        "${env:ProgramFiles}\DaHuaTech\MV Viewer",
        "${env:ProgramFiles(x86)}\DaHuaTech\MV Viewer",
        "${env:ProgramFiles}\Industrial Camera\MV Viewer",
        "${env:ProgramFiles(x86)}\Industrial Camera\MV Viewer"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

$SdkPath = Find-DahuaSdkRoot -InitialPath $SdkPath
$dest = Join-Path $ProjectRoot "vendor\dahua\win64"
$pyDest = Join-Path $ProjectRoot "vendor\DahuaMvImport"
$redistDest = Join-Path $ProjectRoot "packaging\redist"
$manifestPath = Join-Path $ProjectRoot "vendor\dahua\manifest.json"

New-Item -ItemType Directory -Force -Path $dest, $redistDest | Out-Null

if (-not $SdkPath) {
    $msg = "未找到大华 SDK 安装目录。请先安装 MV Viewer / 工业相机 SDK，或设置 DAHUA_SDK_PATH"
    Write-Warning $msg
    if ($Strict) { throw $msg }
    exit 0
}

Write-Host "使用大华 SDK 路径: $SdkPath"

$searchRoots = @(
    (Join-Path $SdkPath "Runtime\x64"),
    (Join-Path $SdkPath "Runtime\Win64"),
    (Join-Path $SdkPath "Runtime\win64"),
    (Join-Path $SdkPath "Development\Binaries\x64"),
    (Join-Path $SdkPath "Development\Binaries\Win64"),
    (Join-Path $SdkPath "Development\Binaries\win64"),
    $SdkPath
)

$copied = 0
foreach ($root in $searchRoots) {
    if (-not (Test-Path $root)) { continue }
    Get-ChildItem -Path $root -Filter "*.dll" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item $_.FullName -Destination $dest -Force
        $copied++
    }
}

$pyCandidates = @(
    (Join-Path $SdkPath "Development\Samples\Python"),
    (Join-Path $SdkPath "Samples\Python")
)
$pyCopied = $false
foreach ($pySrc in $pyCandidates) {
    if (Test-Path $pySrc) {
        if (Test-Path $pyDest) { Remove-Item $pyDest -Recurse -Force }
        Copy-Item $pySrc -Destination $pyDest -Recurse -Force
        Write-Host "已复制 Python MVSDK 模块 -> vendor\DahuaMvImport"
        $pyCopied = $true
        break
    }
}

$driverPatterns = @("*GigE*Install*.exe", "*GigE*Filter*.exe", "*MVGigE*.exe", "*FilterDriver*.exe")
$driverCopied = 0
foreach ($root in @($SdkPath, (Join-Path $SdkPath "Drivers"), (Join-Path $SdkPath "Runtime"))) {
    if (-not (Test-Path $root)) { continue }
    foreach ($pattern in $driverPatterns) {
        Get-ChildItem -Path $root -Filter $pattern -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item $_.FullName -Destination $redistDest -Force
            $driverCopied++
        }
    }
}

$manifest = @{
    sdk_path = $SdkPath
    dll_count = $copied
    python_modules = $pyCopied
    driver_installers = $driverCopied
    collected_at = (Get-Date).ToString("o")
}
$manifest | ConvertTo-Json | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "已复制 $copied 个 DLL、驱动安装包 $driverCopied 个"
if (-not $pyCopied) {
    Write-Warning "未找到 MVSDK.py，Python 模块未复制"
    if ($Strict) { throw "缺少 DahuaMvImport" }
}
