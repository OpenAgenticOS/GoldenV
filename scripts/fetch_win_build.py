#!/usr/bin/env python3
"""触发 GitHub Actions Windows 构建，并将 exe 安装包下载到本地。

依赖：已安装并登录 GitHub CLI（gh auth login）

示例：
  python scripts/fetch_win_build.py
  python scripts/fetch_win_build.py --ref main --output Output/ci_build
  python scripts/fetch_win_build.py --repo owner/GoldenV --no-wait
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


WORKFLOW_FILE = "build-windows.yml"
DEFAULT_OUTPUT = "Output/ci_build"


def _run(cmd: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd))
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
    )


def _require_gh() -> None:
    if not shutil.which("gh"):
        raise SystemExit("未找到 gh 命令。请先安装 GitHub CLI：https://cli.github.com/")
    result = _run(["gh", "auth", "status"], check=False, capture=True)
    if result.returncode != 0:
        raise SystemExit("gh 未登录。请运行：gh auth login")


def _detect_repo(explicit: str | None) -> str:
    if explicit:
        return explicit
    result = _run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture=True,
    )
    repo = result.stdout.strip()
    if not repo:
        raise SystemExit("无法解析仓库名，请使用 --repo owner/name")
    return repo


def _list_latest_run(repo: str) -> dict | None:
    result = _run(
        [
            "gh",
            "run",
            "list",
            "--repo",
            repo,
            "--workflow",
            WORKFLOW_FILE,
            "--limit",
            "1",
            "--json",
            "databaseId,status,conclusion,createdAt",
        ],
        capture=True,
    )
    runs = json.loads(result.stdout)
    return runs[0] if runs else None


def _trigger_build(repo: str, ref: str) -> int:
    before = _list_latest_run(repo)
    before_id = before["databaseId"] if before else None
    _run(["gh", "workflow", "run", WORKFLOW_FILE, "--repo", repo, "--ref", ref])

    deadline = time.time() + 90
    while time.time() < deadline:
        current = _list_latest_run(repo)
        if current and current["databaseId"] != before_id:
            if current["status"] in ("queued", "in_progress", "completed"):
                return int(current["databaseId"])
        time.sleep(3)
    raise SystemExit("超时：未检测到新启动的工作流，请稍后在 Actions 页面确认")


def _wait_run(repo: str, run_id: int) -> None:
    _run(["gh", "run", "watch", str(run_id), "--repo", repo, "--exit-status"])


def _download_artifacts(repo: str, run_id: int, output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "gh",
            "run",
            "download",
            str(run_id),
            "--repo",
            repo,
            "--dir",
            str(output_dir),
        ]
    )


def _summarize(output_dir: Path) -> None:
    setup = list(output_dir.rglob("GoldenV_Setup.exe"))
    exe = list(output_dir.rglob("GoldenV.exe"))
    print("\n=== 下载完成 ===")
    print(f"目录: {output_dir.resolve()}")
    if setup:
        print(f"安装包: {setup[0]}")
    else:
        print("安装包: 未找到 GoldenV_Setup.exe（可能 Inno Setup 步骤未产出）")
    if exe:
        print(f"可执行文件: {exe[0]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="触发 GitHub Actions 打 Windows 包并拉回本地")
    parser.add_argument("--repo", help="GitHub 仓库 owner/name，默认从当前目录推断")
    parser.add_argument("--ref", default="main", help="构建分支或 tag，默认 main")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"本地输出目录，默认 {DEFAULT_OUTPUT}")
    parser.add_argument("--no-wait", action="store_true", help="触发后立即退出，不等待构建完成")
    args = parser.parse_args(argv)

    _require_gh()
    repo = _detect_repo(args.repo)
    output_dir = Path(args.output)

    print(f"仓库: {repo}")
    print(f"分支/ref: {args.ref}")
    run_id = _trigger_build(repo, args.ref)

    if args.no_wait:
        print(f"已触发构建（run {run_id}）。完成后下载：")
        print(f"  gh run download {run_id} --repo {repo} --dir {output_dir}")
        return 0

    print(f"运行 ID: {run_id}")
    print("等待 GitHub Actions 构建…（PyInstaller 通常需 10–20 分钟）")

    try:
        _wait_run(repo, run_id)
    except subprocess.CalledProcessError:
        print("构建失败。查看日志：")
        print(f"  gh run view {run_id} --repo {repo} --log")
        return 1

    _download_artifacts(repo, run_id, output_dir)
    _summarize(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
