param(
    [switch]$IncludeDahuaSdk
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== GoldenV Windows 打包 ==="

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "未找到 python"
}

if ($IncludeDahuaSdk) {
    Write-Host "--- 收集大华 SDK 运行时（仅开发/联调用，生产包不依赖此项）---"
    & "$PSScriptRoot\fetch_dahua_sdk.ps1" -ProjectRoot $ProjectRoot
} else {
    Write-Host "--- 跳过大华 SDK 打包：工控机需用户自行安装 MV Viewer ---"
}

$env:PIP_CONFIG_FILE = Join-Path $ProjectRoot "pip.conf"
python -m pip install -U pip
pip install -r requirements.txt
pip install pyinstaller

if (Test-Path "dist\GoldenV") { Remove-Item "dist\GoldenV" -Recurse -Force }
New-Item -ItemType Directory -Force -Path "Output" | Out-Null
python -m PyInstaller packaging\goldenv.spec --noconfirm --distpath dist --workpath build
if (-not (Test-Path "dist\GoldenV\GoldenV.exe")) {
    throw "PyInstaller 未生成 dist\GoldenV\GoldenV.exe"
}

$dist = Join-Path $ProjectRoot "dist\GoldenV"
if ($IncludeDahuaSdk) {
    New-Item -ItemType Directory -Force -Path (Join-Path $dist "scripts") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $dist "redist") | Out-Null
    Copy-Item "packaging\install_dahua_runtime.ps1" (Join-Path $dist "scripts\") -Force -ErrorAction SilentlyContinue
    if (Test-Path "packaging\redist") {
        Copy-Item "packaging\redist\*" (Join-Path $dist "redist\") -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path "vendor\dahua\manifest.json") {
        New-Item -ItemType Directory -Force -Path (Join-Path $dist "dahua") | Out-Null
        Copy-Item "vendor\dahua\manifest.json" (Join-Path $dist "dahua\") -Force
    }
}

& "$PSScriptRoot\smoke_test_win.ps1" -ProjectRoot $ProjectRoot

$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($iscc) {
    & $iscc "packaging\installer.iss"
    Write-Host "安装包: Output\GoldenV_Setup.exe"
} else {
    Write-Warning "未找到 Inno Setup，跳过安装包。dist\GoldenV 已就绪。"
}

Write-Host "打包完成"
