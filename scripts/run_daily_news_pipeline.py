#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS_DIR = ROOT / "news"
ARTIFACTS_DIR = ROOT / "artifacts"


def run_command(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def resolve_input(input_arg: str | None) -> Path:
    if input_arg:
        path = Path(input_arg).expanduser()
        if path.exists():
            return path
        raise FileNotFoundError(f"找不到输入文件: {path}")

    latest = NEWS_DIR / "latest.json"
    if latest.exists():
        return latest

    today = datetime.now().strftime("%Y-%m-%d")
    dated = NEWS_DIR / f"{today}.json"
    if dated.exists():
        return dated

    candidates = sorted(NEWS_DIR.glob("*.json"))
    if candidates:
        return candidates[-1]
    raise FileNotFoundError("news 目录下没有可用的 JSON 输入文件。")


def main() -> None:
    parser = argparse.ArgumentParser(description="一键执行 daily_gaming_news 的构建、渲染与可选草稿投递。")
    parser.add_argument("--input", help="新闻 JSON 路径。默认优先读取 news/latest.json。")
    parser.add_argument("--output-dir", help="产物输出目录。默认按日期写入 artifacts/runs/YYYY-MM-DD/")
    parser.add_argument("--push-draft", action="store_true", help="渲染完成后继续推送到微信公众号草稿箱。")
    parser.add_argument("--thumb", help="推草稿时使用的封面图路径或 URL。")
    args = parser.parse_args()

    news_path = resolve_input(args.input)
    news = json.loads(news_path.read_text(encoding="utf-8"))
    date_label = news.get("date") or datetime.now().strftime("%Y-%m-%d")

    run_dir = Path(args.output_dir).expanduser() if args.output_dir else ARTIFACTS_DIR / "runs" / date_label
    run_dir.mkdir(parents=True, exist_ok=True)

    payload_path = run_dir / "payload.json"
    html_path = run_dir / "rendered_article.html"
    summary_path = run_dir / "run_summary.json"

    build_stdout = run_command(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_payload_from_news.py"),
            "--input",
            str(news_path),
            "--output",
            str(payload_path),
        ]
    )
    render_stdout = run_command(
        [
            sys.executable,
            str(ROOT / "scripts" / "render_wechat_roundup.py"),
            "--input",
            str(payload_path),
            "--output",
            str(html_path),
        ]
    )

    summary: dict[str, object] = {
        "date": date_label,
        "input_news": str(news_path),
        "payload": str(payload_path),
        "rendered_html": str(html_path),
        "build_stdout": build_stdout,
        "render_stdout": render_stdout,
        "pushed_to_draft": False,
    }

    if args.push_draft:
        push_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "push_wechat_draft.py"),
            "--input",
            str(payload_path),
            "--rendered-html",
            str(html_path),
        ]
        if args.thumb:
            push_cmd.extend(["--thumb", args.thumb])
        push_stdout = run_command(push_cmd)
        summary["pushed_to_draft"] = True
        summary["draft_response"] = json.loads(push_stdout)

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
