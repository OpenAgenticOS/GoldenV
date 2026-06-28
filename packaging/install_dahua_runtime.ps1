param(
    [Parameter(Mandatory = $true)]
    [string]$AppDir,
    [switch]$InstallGigEDriver
)

$ErrorActionPreference = "Stop"

Write-Host "=== 配置大华相机运行时 ==="
Write-Host "安装目录: $AppDir"

$dllDirs = @(
    $AppDir,
    (Join-Path $AppDir "_internal"),
    (Join-Path $AppDir "dahua\win64"),
    (Join-Path $AppDir "_internal\dahua\win64")
)

$pathEntries = @()
foreach ($dir in $dllDirs) {
    if (Test-Path $dir) { $pathEntries += $dir }
}

if ($pathEntries.Count -gt 0) {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $prefix = ($pathEntries | Select-Object -Unique) -join ";"
    if ($machinePath -notlike "*$($pathEntries[0])*") {
        [Environment]::SetEnvironmentVariable("Path", "$prefix;$machinePath", "Machine")
        Write-Host "已追加大华 DLL 目录到系统 PATH"
    }
}

[Environment]::SetEnvironmentVariable("DAHUA_SDK_PATH", $AppDir, "Machine")
Write-Host "已设置 DAHUA_SDK_PATH=$AppDir"

$driverDir = Join-Path $AppDir "redist"
if ($InstallGigEDriver -and (Test-Path $driverDir)) {
    $drivers = Get-ChildItem -Path $driverDir -Filter "*.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "GigE|Filter|MV" }
    foreach ($driver in $drivers) {
        Write-Host "安装 GigE 驱动: $($driver.Name)"
        $proc = Start-Process -FilePath $driver.FullName -ArgumentList "/S", "/silent", "/quiet" -Wait -PassThru
        if ($proc.ExitCode -ne 0) {
            Write-Warning "驱动安装返回码 $($proc.ExitCode): $($driver.Name)"
        }
    }
}

$mvImport = Join-Path $AppDir "_internal\DahuaMvImport\MVSDK.py"
if (-not (Test-Path $mvImport)) {
    $mvImport = Join-Path $AppDir "DahuaMvImport\MVSDK.py"
}
if (Test-Path $mvImport) {
    Write-Host "大华 MVSDK Python 模块: 已就绪"
} else {
    Write-Warning "未在安装目录找到 DahuaMvImport/MVSDK.py，请使用完整安装包或先在构建机运行 fetch_dahua_sdk.ps1"
}

Write-Host "大华运行时配置完成"
