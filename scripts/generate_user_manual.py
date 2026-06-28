#!/usr/bin/env python3
"""生成 GoldenV 安装使用手册 PDF。"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FONT = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
if not FONT.is_file():
    FONT = Path("/Library/Fonts/Arial Unicode.ttf")

RELEASE_URL = "https://github.com/OpenAgenticOS/GoldenV/releases/latest"
REPO_URL = "https://github.com/OpenAgenticOS/GoldenV"
VC_REDIST_URL = "https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist"
HUARAY_DOWNLOAD = "https://www.huaraytech.com/cn/serviceCenter/download.html"
CH340_DRIVER = "http://www.wch.cn/downloads/CH341SER_EXE.html"
FTDI_DRIVER = "https://ftdichip.com/drivers/vcp-drivers/"


class ManualPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_margins(20, 20, 20)
        self.add_font("uni", "", str(FONT))
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("uni", size=9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "GoldenV 黄金镯子检测系统 — 安装使用手册", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("uni", size=9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"第 {self.page_no()} 页", align="C")

    def title_page(self):
        self.add_page()
        self.ln(35)
        self.set_font("uni", size=24)
        self.set_text_color(20, 20, 20)
        self.cell(0, 14, "GoldenV", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("uni", size=18)
        self.cell(0, 12, "黄金镯子检测系统", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        self.set_font("uni", size=14)
        self.cell(0, 10, "安装与使用手册", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(20)
        self.set_font("uni", size=11)
        self.set_text_color(60, 60, 60)
        self.multi_cell(self.epw, 7, "适用平台：Windows 10 / 11 64 位工控机\n功能：内径视觉测量 + 串口电子秤读数 + 检测记录", align="C")
        self.ln(10)
        self.link_line("软件下载（最新版）", RELEASE_URL)

    def h1(self, text: str):
        self.ln(4)
        self.set_font("uni", size=16)
        self.set_text_color(30, 30, 30)
        self.multi_cell(self.epw, 10, text)
        self.ln(2)

    def h2(self, text: str):
        self.ln(2)
        self.set_font("uni", size=13)
        self.set_text_color(40, 40, 40)
        self.multi_cell(self.epw, 8, text)
        self.ln(1)

    def body(self, text: str):
        self.set_font("uni", size=11)
        self.set_text_color(30, 30, 30)
        self.multi_cell(self.epw, 7, text)
        self.ln(1)

    def bullet(self, text: str):
        self.set_font("uni", size=11)
        self.set_text_color(30, 30, 30)
        self.multi_cell(self.epw, 7, f"• {text}")

    def numbered(self, index: int, text: str):
        self.set_font("uni", size=11)
        self.multi_cell(self.epw, 7, f"{index}. {text}")

    def link_line(self, label: str, url: str):
        self.set_font("uni", size=11)
        self.set_text_color(0, 80, 180)
        self.cell(0, 7, label, link=url, new_x="LMARGIN", new_y="NEXT")
        self.set_font("uni", size=9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, url, link=url, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)
        self.ln(2)


def build_manual() -> Path:
    pdf = ManualPDF()
    pdf.title_page()

    pdf.add_page()
    pdf.h1("1. 软件概述")
    pdf.body(
        "GoldenV 是面向黄金手镯质检的 Windows 桌面软件，主要功能包括："
        "工业相机采集图像并测量镯子内径（mm）、串口电子秤读取重量（g）、"
        "一键检测存库、历史记录查询与 CSV 导出。"
        "安装包已内置运行环境，工控机无需安装 Python。"
    )

    pdf.h1("2. 系统要求")
    pdf.bullet("操作系统：Windows 10 / 11，64 位")
    pdf.bullet("内存：建议 8 GB 及以上")
    pdf.bullet("硬盘：安装约 500 MB 可用空间")
    pdf.bullet("相机：大华 GigE 工业相机（可选模拟模式调试）")
    pdf.bullet("电子秤：RS232 或 USB 转 RS232，支持 YAML 配置协议")

    pdf.h1("3. 软件下载与安装")
    pdf.h2("3.1 下载 GoldenV（必装）")
    pdf.body("请从 GitHub Releases 下载最新安装包或绿色版：")
    pdf.link_line("GoldenV 最新 Release 下载页", RELEASE_URL)
    pdf.bullet("GoldenV_Setup.exe — 推荐，双击安装向导")
    pdf.bullet("GoldenV-portable-win64.zip — 免安装，解压后运行 GoldenV.exe")
    pdf.h2("3.2 安装步骤")
    pdf.numbered(1, "下载 GoldenV_Setup.exe")
    pdf.numbered(2, "右键「以管理员身份运行」安装程序")
    pdf.numbered(3, "按向导完成安装，桌面或开始菜单会出现「黄金镯子检测系统」")
    pdf.numbered(4, "首次运行后，配置保存在：C:\\ProgramData\\GoldenV\\")

    pdf.h1("4. 需自行下载安装的组件")
    pdf.body("以下组件不包含在 GoldenV 安装包内，请按现场设备按需安装：")
    pdf.h2("4.1 大华 MV Viewer（使用大华 GigE 相机时必装）")
    pdf.body(
        "商业软件，需从大华官方或随相机光盘获取。安装时请勾选 GigE 网卡过滤驱动。"
        "安装完成后 GoldenV 会自动识别 SDK；未安装时将降级为模拟相机。"
    )
    pdf.link_line("大华机器视觉 — 下载中心", HUARAY_DOWNLOAD)
    pdf.body("常见安装路径：C:\\Program Files\\HuarayTech\\MV Viewer")
    pdf.h2("4.2 Visual C++ 运行库 x64（多数电脑已自带）")
    pdf.body("若启动提示缺少 VCRUNTIME 等 DLL，请安装微软官方运行库：")
    pdf.link_line("Microsoft Visual C++ 可再发行组件", VC_REDIST_URL)
    pdf.h2("4.3 USB 转串口驱动（电子秤走 USB 转 RS232 时）")
    pdf.body("安装后在「设备管理器 → 端口」中应出现 COM 口：")
    pdf.link_line("CH340 / CH341 驱动（沁恒 WCH）", CH340_DRIVER)
    pdf.link_line("FTDI VCP 驱动", FTDI_DRIVER)

    pdf.add_page()
    pdf.h1("5. 推荐部署顺序")
    pdf.numbered(1, "安装 GoldenV")
    pdf.numbered(2, "安装大华 MV Viewer，并用 MV Viewer 确认相机可发现、可预览")
    pdf.numbered(3, "配置工控机网口与相机同网段（GigE 相机）")
    pdf.numbered(4, "安装 USB 转串口驱动（如需要），确认 COM 口号")
    pdf.numbered(5, "启动 GoldenV → 设置 → 连接设备 → 标定 → 正式检测")

    pdf.h1("6. 首次使用")
    pdf.h2("6.1 连接设备")
    pdf.bullet("点击主界面「连接设备」")
    pdf.bullet("相机预览区应显示实时画面（模拟模式下为合成环规图）")
    pdf.bullet("重量区会周期性刷新读数")
    pdf.h2("6.2 工位设置")
    pdf.bullet("菜单：打开设置 → 相机：类型 / IP / 曝光 / 增益")
    pdf.bullet("电子秤：协议、COM 口、波特率、校验位、轮询命令")
    pdf.bullet("支持导入/导出电子秤协议 YAML")
    pdf.body("配置文件路径：C:\\ProgramData\\GoldenV\\configs\\station.yaml")

    pdf.h1("7. 内径标定")
    pdf.body("首次上线或更换镜头/工位高度后，建议使用标准环规标定：")
    pdf.numbered(1, "连接设备，放入已知内径的标准环规")
    pdf.numbered(2, "打开「标定向导」→ 环规标定")
    pdf.numbered(3, "输入标准内径（mm），点击「测量预览」再「执行标定」")
    pdf.numbered(4, "也可在「手动调整」页直接修改 mm/像素 或启用 X/Y 分向标定")
    pdf.body("标定结果自动保存到 station.yaml，重启后仍有效。")

    pdf.h1("8. 日常检测流程")
    pdf.h2("8.1 一键检测（推荐）")
    pdf.body("点击「一键检测」：自动完成内径测量 → 读取重量 → 保存记录。")
    pdf.h2("8.2 分步操作")
    pdf.bullet("测量内径：单独触发视觉测量并显示结果")
    pdf.bullet("读取重量：手动刷新电子秤读数")
    pdf.bullet("保存记录：将当前内径、重量、图像写入数据库")
    pdf.bullet("导出 CSV：导出历史检测记录")
    pdf.body("数据目录：C:\\ProgramData\\GoldenV\\data\\")

    pdf.h1("9. 串口调试")
    pdf.body("「串口调试」窗口可实时查看 RX 原始数据、解析成功/失败信息，便于排查秤协议问题。")

    pdf.h1("10. 常见问题")
    pdf.h2("Q：相机连接失败？")
    pdf.bullet("确认已安装 MV Viewer 及 GigE 驱动")
    pdf.bullet("用 MV Viewer 先验证相机 IP 与取流")
    pdf.bullet("检查 station.yaml 中 kind: dahua 与 ip 是否正确")
    pdf.h2("Q：电子秤无读数？")
    pdf.bullet("设备管理器确认 COM 口存在")
    pdf.bullet("设置中选择正确协议与波特率")
    pdf.bullet("使用串口调试查看是否有 RX 数据")
    pdf.h2("Q：内径偏差大？")
    pdf.bullet("重新执行标定向导")
    pdf.bullet("检查光照、ROI 与环规是否居中")

    pdf.h1("11. 参考链接")
    pdf.link_line("GoldenV 项目主页", REPO_URL)
    pdf.link_line("最新版本下载", RELEASE_URL)
    pdf.link_line("大华 SDK 下载", HUARAY_DOWNLOAD)
    pdf.link_line("VC++ 运行库", VC_REDIST_URL)

    DOCS.mkdir(parents=True, exist_ok=True)
    out = DOCS / "GoldenV_安装使用手册.pdf"
    pdf.output(str(out))
    return out


if __name__ == "__main__":
    path = build_manual()
    print(f"已生成: {path}")
