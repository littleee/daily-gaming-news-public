#!/usr/bin/env python3
import argparse
import difflib
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}
BLOCK_WORDS = (
    "责任编辑",
    "点击进入",
    "更多内容",
    "转载",
    "版权",
    "原标题",
    "本文来源",
    "微信扫一扫",
    "分享至",
    "扫码二维码",
    "申请入驻",
    "网易首页",
    "登录",
    "注册",
    "热门单机",
    "网页游戏",
    "游戏领域创作者",
    "发布于",
    "作者 官方",
    "来源:",
    "来源：",
    "举报",
    "特别声明",
    "相关推荐",
    "热点推荐",
    "跟贴",
    "用微信扫码",
    "好友和朋友圈",
    "上一篇",
    "下一篇",
)
BAD_PATTERNS = (
    r"^\d+\s*$",
    r"^(网易首页|Games Industry Ecosystem|网页游戏|热门单机|登录|注册|相关推荐|热点推荐)",
    r"(分享至|扫码二维码|好友和朋友圈|申请入驻|举报|特别声明)",
    r"(All Premium|User Acquisition|Company Culture|Market Overview)",
    r"(资讯\s+\d{2}/\d{2}\s+\d{2}:\d{2})",
    r"(\d+\s*跟贴)",
)
SELECTORS = [
    "article",
    "main",
    "#content",
    "#article-content",
    ".article-content",
    ".post-content",
    ".entry-content",
    ".news_content",
    ".content",
    ".article",
    ".news-text",
    ".post_text",
    ".content-main",
    ".Textarticle-content",
]
THREEDM_IMAGE_TOKEN = "img.3dmgame.com/uploads/images/news/"


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = text.replace("\u3000", " ")
    text = text.replace("]]>", "")
    return text


def bad_text(text: str) -> bool:
    if any(word in text for word in BLOCK_WORDS):
        return True
    if text.count("|") >= 5:
        return True
    if re.fullmatch(r"[A-Za-z0-9 .,:;\-_'\"/()]+", text) and len(text) > 120:
        return True
    return any(re.search(pattern, text) for pattern in BAD_PATTERNS)


def plausible_paragraph(text: str) -> bool:
    if len(text) < 32:
        return False
    if bad_text(text):
        return False
    punct = sum(text.count(ch) for ch in "，。！？；：")
    if punct < 1 and len(text) < 90:
        return False
    if len(text) > 320:
        return False
    return True


def normalize_paragraph(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"^(\d+[、.．]\s*)", "", text)
    text = re.sub(r"^(文[丨｜|].*?)", "", text)
    text = re.sub(r"^([A-Za-z]{1,12}\s*[:：])", "", text)
    return text.strip(" -|｜")


def score_container(tag) -> int:
    score = 0
    for p in tag.find_all(["p", "div"], recursive=True):
        text = normalize_paragraph(p.get_text(" ", strip=True))
        if plausible_paragraph(text):
            score += min(len(text), 180)
    return score


def first_image_from(container) -> tuple[str, list[str]]:
    gallery = []
    for image in container.find_all("img"):
        src = image.get("data-src") or image.get("src") or ""
        if not src.startswith("http"):
            continue
        if any(token in src for token in ["logo", "avatar", "icon", "wx_fmt=gif", "default", "placeholder"]):
            continue
        gallery.append(src)
    deduped = []
    for url in gallery:
        if url not in deduped:
            deduped.append(url)
    lead = deduped[0] if deduped else ""
    return lead, deduped[1:3]


def pick_best_container(soup: BeautifulSoup):
    candidates = []
    for selector in SELECTORS:
        candidates.extend(soup.select(selector))
    candidates.extend(soup.find_all(["div", "section", "article"]))
    scored = [(score_container(tag), tag) for tag in candidates]
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else soup.body or soup


def dedupe_paragraphs(paragraphs: list[str]) -> list[str]:
    deduped = []
    for text in paragraphs:
        if any(text == existing or text in existing or existing in text for existing in deduped):
            continue
        deduped.append(text)
    return deduped


def text_fingerprint(text: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text or "").lower()


def paragraphs_are_similar(left: str, right: str) -> bool:
    left_fp = text_fingerprint(left)
    right_fp = text_fingerprint(right)
    if not left_fp or not right_fp:
        return False
    if difflib.SequenceMatcher(None, left_fp, right_fp).ratio() >= 0.55:
        return True
    shorter, longer = sorted([left_fp, right_fp], key=len)
    if shorter in longer:
        return True
    overlap = sum(1 for ch in set(shorter) if ch in set(longer))
    return overlap / max(len(set(shorter)), 1) >= 0.8


def merge_lead_summary(paragraphs: list[str], fallback_summary: str) -> list[str]:
    fallback_summary = normalize_3dm_paragraph(fallback_summary) if fallback_summary else ""
    if not fallback_summary:
        return paragraphs
    if not paragraphs:
        return [fallback_summary]
    if paragraphs_are_similar(fallback_summary, paragraphs[0]):
        return paragraphs
    return [fallback_summary, *paragraphs]


def is_3dm_url(url: str) -> bool:
    return "3dmgame.com" in (url or "")


def is_3dm_bad_paragraph(text: str) -> bool:
    if not text:
        return True
    extra_block_words = (
        "您的位置：",
        "时间：",
        "来源：",
        "作者：",
        "编辑：",
        "近期热门",
        "他们都在说",
        "再看看",
        "已有",
        "您还未评分",
        "类型：",
        "发行：",
        "发售：",
        "开发：",
        "语言：",
        "标签：",
        "专区",
    )
    if any(word in text for word in extra_block_words):
        return True
    if re.match(r"^《.+》$", text):
        return True
    return bad_text(text)


def normalize_3dm_paragraph(text: str) -> str:
    text = normalize_paragraph(text)
    text = re.sub(r"^时间：\s*\d{4}-\d{2}-\d{2}.*$", "", text)
    text = re.sub(r"^来源：.*$", "", text)
    text = re.sub(r"^作者：.*$", "", text)
    text = re.sub(r"^编辑：.*$", "", text)
    text = re.sub(r"^您的位置：.*$", "", text)
    return clean_text(text)


def extract_3dm_images(container) -> tuple[str, list[str]]:
    gallery = []
    for image in container.find_all("img"):
        src = image.get("data-src") or image.get("src") or ""
        if THREEDM_IMAGE_TOKEN not in src:
            continue
        gallery.append(src)
    deduped = []
    for url in gallery:
        if url not in deduped:
            deduped.append(url)
    lead = deduped[0] if deduped else ""
    return lead, deduped[1:4]


def fetch_3dm_article_content(url: str, fallback_summary: str) -> tuple[list[str], str, list[str]]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception:
        return [fallback_summary], "", []

    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup.find_all(["script", "style", "iframe", "noscript"]):
        tag.decompose()

    container = soup.select_one(".news_warp_center")
    if not container:
        container = soup.select_one(".Content_L.dj_chinesemode")
    if not container:
        return [fallback_summary], "", []

    paragraphs = []
    for node in container.find_all(["p", "div"], recursive=True):
        if node.find(["p", "div"], recursive=False):
            continue
        text = normalize_3dm_paragraph(node.get_text(" ", strip=True))
        if not plausible_paragraph(text):
            continue
        if is_3dm_bad_paragraph(text):
            continue
        paragraphs.append(text)

    paragraphs = dedupe_paragraphs(paragraphs)

    paragraphs = merge_lead_summary(paragraphs, fallback_summary)

    lead_image, gallery = extract_3dm_images(container)
    return paragraphs[:5], lead_image, gallery


def fetch_article_content(url: str, fallback_summary: str) -> tuple[list[str], str, list[str]]:
    if is_3dm_url(url):
        return fetch_3dm_article_content(url, fallback_summary)
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception:
        return [fallback_summary], "", []

    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup.find_all(["script", "style", "iframe", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    container = pick_best_container(soup)
    paragraphs = []
    for node in container.find_all(["p", "div", "span"], recursive=True):
        text = normalize_paragraph(node.get_text(" ", strip=True))
        if not plausible_paragraph(text):
            continue
        paragraphs.append(text)

    paragraphs = dedupe_paragraphs(paragraphs)

    fallback_summary = normalize_paragraph(fallback_summary) if fallback_summary else ""
    paragraphs = merge_lead_summary(paragraphs, fallback_summary)

    cleaned = []
    for para in paragraphs:
        if bad_text(para):
            continue
        cleaned.append(para)
    paragraphs = cleaned[:4]

    lead_image, gallery = first_image_from(container)
    if not lead_image:
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og and og.get("content", "").startswith("http") and "gif" not in og.get("content", ""):
            lead_image = og["content"]

    return paragraphs, lead_image, gallery


def build_title(news: dict) -> str:
    items = news.get("items", [])
    titles = [item.get("title", "").strip() for item in items if item.get("title", "").strip()]
    if len(titles) >= 2:
        return f"{titles[0]} ｜ {titles[1]}"
    if titles:
        return titles[0]
    return "游戏资讯"


def main() -> None:
    parser = argparse.ArgumentParser(description="从 news JSON 构建更接近公众号成稿的 payload。")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--author", default="狗子")
    args = parser.parse_args()

    news = json.loads(Path(args.input).read_text(encoding="utf-8"))
    payload = {
        "title": build_title(news),
        "author": args.author,
        "digest": f"{news.get('date', '')} 主机与 PC 游戏资讯精选。",
        "publish_time": news.get("date", ""),
        "source_url": "",
        "cover_image": "",
        "intro_paragraphs": [],
        "sections": [],
        "closing_paragraphs": [],
        "footer_note": "更多资讯，关注狗子",
    }

    for item in news.get("items", []):
        paragraphs, lead_image, gallery = fetch_article_content(item["url"], item.get("summary", ""))
        payload["sections"].append(
            {
                "heading": item["title"],
                "paragraphs": paragraphs,
                "image": lead_image,
                "gallery": gallery,
                "source_url": item["url"],
                "source_name": item.get("source", ""),
            }
        )

        if not payload["cover_image"] and lead_image:
            payload["cover_image"] = lead_image

    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"payload 已生成: {args.output}")


if __name__ == "__main__":
    main()
