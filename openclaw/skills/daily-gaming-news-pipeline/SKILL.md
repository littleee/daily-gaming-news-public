---
name: daily-gaming-news-pipeline
description: |
  Build the full TGDOG daily gaming news workflow from local news JSON into a WeChat-ready article. Use when asked to turn daily_gaming_news/news/*.json into a payload, render the WeChat HTML, save artifacts, or optionally push the result to the WeChat draft box. This skill is the fixed publishing pipeline that works with the 3dm-gaming-news collector skill and the daily OpenClaw cron job.
---

# Daily Gaming News Pipeline

Use this skill after `3dm-gaming-news` has produced a standard news JSON file under:

- `~/.openclaw/workspace/output/daily_gaming_news/news/YYYY-MM-DD.json`
- or `~/.openclaw/workspace/output/daily_gaming_news/news/latest.json`

The canonical project root for this workflow is:

- `/path/to/daily_gaming_news`

## What This Skill Does

1. Read a collected news JSON file
2. Build a WeChat payload with full article text and images
3. Render the TGDOG-style HTML template
4. Optionally push the final article to the WeChat draft box
5. Save all artifacts into `artifacts/runs/YYYY-MM-DD/`

## Default Command

Run:

```bash
python3 /path/to/daily_gaming_news/scripts/run_daily_news_pipeline.py
```

This resolves input automatically in this order:

1. `news/latest.json`
2. `news/<today>.json`
3. the newest JSON file in `news/`

## Push To Draft

If the user explicitly wants a real draft push, run:

```bash
python3 /path/to/daily_gaming_news/scripts/run_daily_news_pipeline.py \
  --push-draft \
  --thumb '封面图路径或URL'
```

### Required Environment Variables

推送草稿到微信公众号需要以下环境变量：

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `WECHAT_APPID` | ✅ | 微信公众号 AppID |
| `WECHAT_APPSECRET` | ✅ | 微信公众号 AppSecret |
| `WECHAT_AUTHOR` | ❌ | 文章作者（可选） |
| `WECHAT_THUMB_PATH` | ❌ | 封面图路径/URL（可选，默认使用文章首图） |

**如何获取凭证：**
1. 登录[微信公众平台](https://mp.weixin.qq.com/)
2. 进入「开发 > 基本配置」
3. 获取 AppID 和 AppSecret

**配置方式：**
```bash
# 方式1：临时设置（当前会话）
export WECHAT_APPID="wx..."
export WECHAT_APPSECRET="..."

# 方式2：使用 1Password CLI（推荐）
eval $(op signin)
export WECHAT_APPID=$(op item get "微信公众号" --field appid)
export WECHAT_APPSECRET=$(op item get "微信公众号" --field appsecret)
```

## Important Behavior

- Keep `payload.title` as the logical full title built from the first two article titles.
- The push script will attempt the full title first and only fall back to a shorter title if the WeChat API rejects it with `45003`.
- WebP images from 3DM are handled automatically. The push script converts `webp` images to `jpg` before uploading them to WeChat.
- Do not use `mp-common-profile` or other editor-only WeChat components in API-pushed drafts.
- The account card should be added manually in the WeChat backend after the draft is created.

## Output Files

The pipeline writes:

- `artifacts/runs/YYYY-MM-DD/payload.json`
- `artifacts/runs/YYYY-MM-DD/rendered_article.html`
- `artifacts/runs/YYYY-MM-DD/run_summary.json`

If draft push succeeds, `run_summary.json` includes the final `media_id` and the actual title used.

## When To Use Which Skill

- Use `3dm-gaming-news` to collect and normalize source news into JSON
- Use `daily-gaming-news-pipeline` to turn that JSON into a WeChat draft-ready article
