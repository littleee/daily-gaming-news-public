#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import markdown
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "templates" / "tgdog_roundup_template.html.j2"


def load_payload(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("输入 JSON 顶层必须是对象。")
    return payload


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "iframe"]):
        tag.decompose()
    return str(soup)


def normalize_payload(payload: dict) -> dict:
    if payload.get("body_html"):
        payload["body_html"] = clean_html(payload["body_html"])
        return payload

    if payload.get("body_markdown"):
        payload["body_html"] = clean_html(
            markdown.markdown(payload["body_markdown"], extensions=["extra", "sane_lists", "tables"], output_format="html5")
        )
        return payload

    payload.setdefault("intro_paragraphs", [])
    payload.setdefault("sections", [])
    payload.setdefault("closing_paragraphs", [])
    payload.setdefault("footer_note", "更多资讯，关注狗子")
    return payload


def render(payload: dict, template_path: Path) -> str:
    env = Environment(loader=FileSystemLoader(str(template_path.parent)), autoescape=True)
    template = env.get_template(template_path.name)
    return template.render(**normalize_payload(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description="将 OpenClaw 采集结果渲染成历史公众号风格 HTML。")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    args = parser.parse_args()

    payload = load_payload(Path(args.input))
    html = render(payload, Path(args.template))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"渲染完成: {output_path}")


if __name__ == "__main__":
    main()
