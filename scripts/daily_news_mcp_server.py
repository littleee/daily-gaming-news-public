#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
NEWS_DIR = ROOT / "news"

mcp = FastMCP(
    name="daily-gaming-news",
    instructions=(
        "Tools for the TGDOG daily gaming news workflow. "
        "Use these tools to turn daily_gaming_news/news JSON files into WeChat payloads, "
        "render WeChat-safe HTML, or run the full publishing pipeline."
    ),
)


def run_json_command(args: list[str]) -> dict:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"命令执行失败: {' '.join(args)}")
    stdout = result.stdout.strip()
    if not stdout:
        return {"ok": True}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"ok": True, "stdout": stdout}


def run_plain_command(args: list[str]) -> dict:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"命令执行失败: {' '.join(args)}")
    return {"ok": True, "stdout": result.stdout.strip()}


def resolve_input(input_path: str | None) -> Path:
    if input_path:
        path = Path(input_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"找不到输入文件: {path}")
        return path

    latest = NEWS_DIR / "latest.json"
    if latest.exists():
        return latest

    candidates = sorted(NEWS_DIR.glob("*.json"))
    if candidates:
        return candidates[-1]
    raise FileNotFoundError("news 目录下没有可用的 JSON 文件。")


@mcp.tool(description="读取当前 daily_gaming_news 的默认输入新闻文件路径。")
def get_latest_news_file() -> dict:
    path = resolve_input(None)
    return {"path": str(path)}


@mcp.tool(description="从标准 news JSON 构建微信公众号 payload。")
def build_payload(input_path: str = "", output_path: str = "") -> dict:
    news_path = resolve_input(input_path if input_path else None)
    if output_path:
        payload_path = Path(output_path).expanduser()
    else:
        payload_path = ROOT / "artifacts" / "mcp_payload.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    result = run_plain_command(
        [
            sys.executable,
            str(SCRIPTS / "build_payload_from_news.py"),
            "--input",
            str(news_path),
            "--output",
            str(payload_path),
        ]
    )
    return {
        "input_news": str(news_path),
        "payload": str(payload_path),
        "stdout": result.get("stdout", ""),
    }


@mcp.tool(description="把 payload JSON 渲染成公众号 HTML。")
def render_article(payload_path: str, output_html: str = "") -> dict:
    payload = Path(payload_path).expanduser()
    if not payload.exists():
        raise FileNotFoundError(f"找不到 payload 文件: {payload}")
    html_path = Path(output_html).expanduser() if output_html else ROOT / "artifacts" / "mcp_rendered_article.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    result = run_plain_command(
        [
            sys.executable,
            str(SCRIPTS / "render_wechat_roundup.py"),
            "--input",
            str(payload),
            "--output",
            str(html_path),
        ]
    )
    return {
        "payload": str(payload),
        "rendered_html": str(html_path),
        "stdout": result.get("stdout", ""),
    }


@mcp.tool(description="运行完整的 daily gaming news 流水线，可选推送到微信公众号草稿箱。")
def run_daily_pipeline(
    input_path: str = "",
    output_dir: str = "",
    push_draft: bool = False,
    thumb: str = "",
) -> dict:
    cmd = [sys.executable, str(SCRIPTS / "run_daily_news_pipeline.py")]
    if input_path:
        cmd.extend(["--input", str(Path(input_path).expanduser())])
    if output_dir:
        cmd.extend(["--output-dir", str(Path(output_dir).expanduser())])
    if push_draft:
        cmd.append("--push-draft")
    if thumb:
        cmd.extend(["--thumb", thumb])
    return run_json_command(cmd)


if __name__ == "__main__":
    mcp.run("stdio")
