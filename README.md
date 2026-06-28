# GoldenV — 黄金镯子内径视觉检测 + 电子秤对接

Windows 工控机桌面应用（简体中文），支持**大华 GigE 工业相机**内径测量与可配置串口电子秤读数。

## 快速开始（开发 / Ubuntu 24.04）

依赖安装默认使用**清华大学 PyPI 镜像**（见 [`pip.conf`](pip.conf)）。

```bash
chmod +x scripts/setup_dev.sh
./scripts/setup_dev.sh
source .venv/bin/activate
python -m goldenv.app --simulate
```

手动指定镜像：

```bash
export PIP_CONFIG_FILE=$PWD/pip.conf
pip install -r requirements.txt -r requirements-dev.txt
```

## 运行

```bash
python -m goldenv.app --config configs/station.yaml --simulate
```

- `--simulate`：使用模拟相机与模拟电子秤（无硬件）
- `--headless-test`：无 GUI 冒烟测试

## 大华相机 SDK（用户自行安装）

大华 MV Viewer / 工业相机 SDK 为**商业软件**，GoldenV **安装包内不包含**，也无法从公网自动下载。

**工控机部署时**，用户需自行安装 MV Viewer（通常随相机光盘或大华技术支持获取），安装时建议勾选 **GigE 网卡过滤驱动**。安装完成后 GoldenV 会自动从以下路径发现 SDK：

- `C:\Program Files\HuarayTech\MV Viewer`
- `C:\Program Files\DaHuaTech\MV Viewer`

也可设置环境变量 `DAHUA_SDK_PATH` 指向 SDK 根目录。未检测到 SDK 时，程序降级为模拟相机。

开发机若需联调真实相机，可在构建时加 `-IncludeDahuaSdk` 将 SDK 打入测试包（**不推荐用于生产交付**）：

```powershell
powershell -File scripts/build_win.ps1 -IncludeDahuaSdk
```

## 工控机部署前置条件

| 项目 | 是否必须 | 说明 |
|------|----------|------|
| **GoldenV 安装包** | 是 | `GoldenV_Setup.exe`，已内含 Python / Qt / OpenCV，**无需 pip** |
| **大华 MV Viewer** | 用大华 GigE 相机时 | 用户手动安装；含 MVSDK、取流 DLL、GigE 过滤驱动 |
| **Visual C++ 运行库 x64** | 通常已有 | Win10/11 多数已带；缺失时安装包可静默安装（需构建机放入 `packaging/redist/vc_redist.x64.exe`） |
| **USB 转串口驱动** | 视电子秤接口 | USB-RS232 转接头需 CH340 / FTDI / Prolific 等对应驱动 |
| **Python / pip** | 否 | 生产环境不需要 |
| **网络配置** | GigE 相机时 | 工控机网口与相机同网段、防火墙放行、必要时设静态 IP |

### 电子秤（RS232）

- 确认 COM 口号（设备管理器），在 GoldenV 设置中配置
- USB 转串口需先装好芯片驱动，否则不会出现 COM 口

### 大华 GigE 相机

1. 安装 MV Viewer（含 GigE 驱动）
2. 用 MV Viewer 确认能搜到相机、能预览
3. 在 `station.yaml` 中设置 `kind: dahua` 与相机 IP
4. 启动 GoldenV 并连接设备

## 相机配置（大华 GigE）

```yaml
cameras:
  - id: cam_top
    kind: dahua
    ip: 192.168.1.100
    exposure_us: 8000
    gain: 1.0
```

需安装大华 MV Viewer。无 SDK 时自动回退模拟相机。

## 配置

- 工位配置：[`configs/station.yaml`](configs/station.yaml)
- 电子秤协议库：[`configs/scale_protocols/`](configs/scale_protocols/)

## Windows 打包

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_win.ps1
```

默认**不打包**大华 SDK。脚本会：

1. 使用国内 pip 镜像安装依赖
2. PyInstaller 打 onedir 包（Python / Qt / OpenCV 自包含）
3. Inno Setup 生成安装包（如已安装）

构建机额外需要：**Python 3.11+**、**Inno Setup 6**（可选）。仅在本地联调真实相机时才需要安装 MV Viewer 并加 `-IncludeDahuaSdk`。

## 通过 GitHub Actions 打 Windows 包（推荐）

无需 Windows 构建机：在 GitHub 云端 Windows Runner 上打包，再拉回本地。

### 前置条件

1. 代码已推送到 GitHub 仓库
2. 本机安装 [GitHub CLI](https://cli.github.com/) 并登录：

```bash
gh auth login
```

### 方式一：本地脚本一键触发 + 下载

```bash
python scripts/fetch_win_build.py
python scripts/fetch_win_build.py --ref main --output Output/ci_build
```

脚本会触发 `build-windows.yml`，等待构建完成后将 `GoldenV_Setup.exe` 与 `dist/GoldenV/` 下载到 `Output/ci_build/`。

### 方式二：GitHub 网页手动触发

1. 仓库 → **Actions** → **Build Windows** → **Run workflow**
2. 填写 **Release 标签**（如 `v0.1.0`）→ Run
3. 构建完成后在 [Releases](https://github.com/OpenAgenticOS/GoldenV/releases) 页面下载

### 方式三：打 tag 自动发 Release（推荐交付）

```bash
git tag v0.1.0
git push origin v0.1.0
```

推送 `v*` 标签后会自动构建，并在 Releases 发布：

- `GoldenV_Setup.exe` — Windows 安装包
- `GoldenV-portable-win64.zip` — 免安装绿色版

公开下载地址：https://github.com/OpenAgenticOS/GoldenV/releases/latest

### CI 说明

| 工作流 | 触发 | 作用 |
|--------|------|------|
| `ci.yml` | push / PR | Ubuntu 跑 pytest |
| `build-windows.yml` | 推送 `v*` tag / 手动 | Windows 打包并发布 Release |

## 测试

```bash
export PIP_CONFIG_FILE=$PWD/pip.conf
pytest
```

## 架构

- `goldenv/ui/` — PySide6 中文界面
- `goldenv/cameras/` — 大华 GigE / 模拟 / USB 相机 Adapter
- `goldenv/scales/` — 串口秤 + YAML 协议解析
- `goldenv/vision/` — 内径测量算法
- `goldenv/services/` — 业务服务层
