#!/usr/bin/env python3
import argparse
import json
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
UPLOAD_IMAGE_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
UPLOAD_THUMB_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
ADD_DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"


def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "")
    if required and not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


def get_access_token() -> str:
    response = requests.get(
        TOKEN_URL,
        params={
            "grant_type": "client_credential",
            "appid": get_env("WECHAT_APPID"),
            "secret": get_env("WECHAT_APPSECRET"),
        },
        timeout=30,
    ).json()
    if "access_token" not in response:
        raise RuntimeError(f"获取 access_token 失败: {response}")
    return response["access_token"]


def maybe_download(path_or_url: str) -> tuple[Path, bool]:
    parsed = urlparse(path_or_url)
    if parsed.scheme in {"http", "https"}:
        suffix = Path(parsed.path).suffix or ".jpg"
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        headers = {"User-Agent": "Mozilla/5.0"}
        if "3dmgame.com" in parsed.netloc:
            headers["Referer"] = "https://www.3dmgame.com/"
        with requests.get(path_or_url, timeout=60, stream=True, headers=headers) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp.write(chunk)
        temp.close()
        return Path(temp.name), True
    return Path(path_or_url), False


def normalize_image_for_wechat(image_path: Path) -> tuple[Path, bool]:
    suffix = image_path.suffix.lower()
    if suffix not in {".webp", ".jfif"}:
        return image_path, False

    with Image.open(image_path) as image:
        converted = image.convert("RGB")
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        converted.save(temp.name, format="JPEG", quality=92)
        temp.close()
    return Path(temp.name), True


def upload_image(access_token: str, image_path: Path) -> str:
    normalized_path, created_temp = normalize_image_for_wechat(image_path)
    mime = mimetypes.guess_type(normalized_path.name)[0] or "application/octet-stream"
    try:
        with normalized_path.open("rb") as file_obj:
            response = requests.post(
                UPLOAD_IMAGE_URL,
                params={"access_token": access_token},
                files={"media": (normalized_path.name, file_obj, mime)},
                timeout=60,
            ).json()
    finally:
        if created_temp:
            normalized_path.unlink(missing_ok=True)
    if "url" not in response:
        raise RuntimeError(f"上传正文图片失败: {response}")
    return response["url"]


def upload_thumb(access_token: str, image_path: Path) -> str:
    normalized_path, created_temp = normalize_image_for_wechat(image_path)
    mime = mimetypes.guess_type(normalized_path.name)[0] or "image/jpeg"
    try:
        with normalized_path.open("rb") as file_obj:
            response = requests.post(
                UPLOAD_THUMB_URL,
                params={"access_token": access_token, "type": "thumb"},
                files={"media": (normalized_path.name, file_obj, mime)},
                timeout=60,
            ).json()
    finally:
        if created_temp:
            normalized_path.unlink(missing_ok=True)
    if "media_id" not in response:
        raise RuntimeError(f"上传封面失败: {response}")
    return response["media_id"]


def replace_inline_images(access_token: str, html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    temp_files = []
    try:
        for image in soup.find_all("img"):
            src = image.get("src") or image.get("data-src")
            if not src or src.startswith(("https://mmbiz.qpic.cn", "http://mmbiz.qpic.cn")):
                continue
            image_path, is_temp = maybe_download(src)
            if is_temp:
                temp_files.append(image_path)
            image["src"] = upload_image(access_token, image_path)
            image.attrs.pop("data-src", None)
        return str(soup)
    finally:
        for temp in temp_files:
            temp.unlink(missing_ok=True)


def extract_core_piece(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    match = re.search(r"《([^》]+)》", text)
    if match:
        return match.group(1).strip()
    return text


def title_candidates(title: str) -> list[str]:
    title = re.sub(r"\s+", " ", title or "").strip()
    if not title:
        return ["游戏资讯"]

    parts = [part.strip() for part in re.split(r"[｜|]", title) if part.strip()]
    candidates = [title]

    if len(parts) >= 2:
        compact = "｜".join(parts)
        cores = [extract_core_piece(part) for part in parts[:2]]
        candidates.append(compact)
        candidates.append("｜".join(cores))
        candidates.append("｜".join(core[:6] for core in cores if core))
        candidates.append("｜".join(core[:4] for core in cores if core))

    deduped = []
    for item in candidates:
        if item and item not in deduped:
            deduped.append(item)
    return deduped or ["游戏资讯"]


def add_draft(access_token: str, article: dict) -> dict:
    return requests.post(
        ADD_DRAFT_URL,
        params={"access_token": access_token},
        data=json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=60,
    ).json()


def main() -> None:
    parser = argparse.ArgumentParser(description="把渲染后的 HTML 保存到微信公众号草稿箱。")
    parser.add_argument("--input", required=True)
    parser.add_argument("--rendered-html", required=True)
    parser.add_argument("--thumb", help="封面图路径或 URL")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    html = Path(args.rendered_html).read_text(encoding="utf-8")
    access_token = get_access_token()
    html = replace_inline_images(access_token, html)

    thumb_candidate = args.thumb or payload.get("cover_image") or get_env("WECHAT_THUMB_PATH", required=False)
    if not thumb_candidate:
        raise RuntimeError("缺少封面图，请通过 --thumb、payload.cover_image 或 WECHAT_THUMB_PATH 提供。")

    thumb_path, thumb_is_temp = maybe_download(thumb_candidate)
    try:
        thumb_media_id = upload_thumb(access_token, thumb_path)
    finally:
        if thumb_is_temp:
            thumb_path.unlink(missing_ok=True)

    article = {
        "title": payload["title"],
        "author": payload.get("author") or get_env("WECHAT_AUTHOR", required=False) or "OpenClaw",
        "digest": payload.get("digest", ""),
        "content": html,
        "content_source_url": payload.get("source_url", ""),
        "thumb_media_id": thumb_media_id,
        "need_open_comment": int(payload.get("need_open_comment", 0)),
        "only_fans_can_comment": int(payload.get("only_fans_can_comment", 0)),
    }

    last_response = None
    for candidate_title in title_candidates(article["title"]):
        article["title"] = candidate_title
        response = add_draft(access_token, article)
        last_response = response
        if response.get("errcode", 0) == 0:
            print(json.dumps({"used_title": candidate_title, **response}, ensure_ascii=False, indent=2))
            return
        if response.get("errcode") != 45003:
            raise RuntimeError(f"新增草稿失败: {response}")

    raise RuntimeError(f"新增草稿失败: {last_response}")


if __name__ == "__main__":
    main()
