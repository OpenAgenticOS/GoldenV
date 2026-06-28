param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$exe = Join-Path $ProjectRoot "dist\GoldenV\GoldenV.exe"
if (-not (Test-Path $exe)) {
    if ($env:CI -eq "true") {
        throw "未找到 $exe，PyInstaller 打包失败"
    }
    Write-Warning "未找到 $exe，尝试源码 headless 测试"
    Set-Location $ProjectRoot
    python -m goldenv.app --headless-test --simulate
    exit $LASTEXITCODE
}

Set-Location (Split-Path $exe)
& $exe --headless-test --simulate
if ($LASTEXITCODE -ne 0) { throw "冒烟测试失败" }
Write-Host "冒烟测试通过"
