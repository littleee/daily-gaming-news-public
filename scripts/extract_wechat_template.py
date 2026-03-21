#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}


def sanitize_fragment(fragment: Tag) -> str:
    for tag in fragment.find_all(["script", "iframe", "style"]):
        tag.decompose()

    for node in fragment.find_all(True):
        for attr in list(node.attrs):
            if attr.startswith("on"):
                del node.attrs[attr]
        if node.name == "img":
            data_src = node.get("data-src")
            if data_src and not node.get("src"):
                node["src"] = data_src
            node.attrs = {k: v for k, v in node.attrs.items() if k in {"src", "data-src", "style", "alt", "title", "width", "height"}}
        else:
            node.attrs = {k: v for k, v in node.attrs.items() if k in {"style", "href", "target"}}

    html = fragment.decode_contents(formatter="html")
    return re.sub(r"\n{3,}", "\n\n", html).strip()


def fetch_article(url: str) -> tuple[str, str, str]:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")

    content = soup.select_one("#js_content")
    if content is None:
        raise RuntimeError("未找到 #js_content，请确认文章链接可以公开访问。")

    title = soup.select_one("#activity-name")
    author = soup.select_one("#js_name")
    return (
        title.get_text(" ", strip=True) if title else "未命名文章",
        author.get_text(" ", strip=True) if author else "公众号",
        sanitize_fragment(content),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="提取历史公众号文章的正文 HTML 片段。")
    parser.add_argument("--url", required=True)
    parser.add_argument("--name", default="history-seed")
    parser.add_argument("--output-root", default="output/extracted")
    args = parser.parse_args()

    title, author, fragment = fetch_article(args.url)
    out_dir = Path(args.output_root) / args.name
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "raw_fragment.html").write_text(fragment, encoding="utf-8")
    (out_dir / "seed_template.html.j2").write_text(
        "{% set title = title or '未命名文章' %}\n"
        "{% set author = author or '公众号' %}\n"
        f"{fragment}\n",
        encoding="utf-8",
    )
    (out_dir / "metadata.json").write_text(
        json.dumps({"source_url": args.url, "title": title, "author": author}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"提取完成: {out_dir}")
    print(f"标题: {title}")
    print(f"作者: {author}")


if __name__ == "__main__":
    main()
