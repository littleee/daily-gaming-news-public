# daily_gaming_news

这是脱敏后的公开版本，用于给其他开发者复用整套 `3DM -> OpenClaw -> 微信草稿箱` 工作流。

用于把 OpenClaw 采集到的 3DM 游戏新闻，自动整理成 TGDOG 风格的微信公众号草稿。

## 当前正式链路

1. `3dm-gaming-news` skill 采集新闻，写入 `news/YYYY-MM-DD.json` 和 `news/latest.json`
2. `run_daily_news_pipeline.py` 读取新闻 JSON，构建 payload 并渲染 HTML
3. `push_wechat_draft.py` 可选将文章推送到微信公众号草稿箱
4. 公众号卡片在微信后台手工补充

## 仓库包含

- `scripts/build_payload_from_news.py`：抓取 3DM 正文并构建公众号 payload
- `scripts/render_wechat_roundup.py`：渲染公众号 HTML
- `scripts/push_wechat_draft.py`：上传图片并推草稿箱
- `scripts/run_daily_news_pipeline.py`：一键运行完整流水线
- `scripts/daily_news_mcp_server.py`：MCP server，供 OpenClaw 调用
- `templates/tgdog_roundup_template.html.j2`：当前正式模板
- `openclaw/skills/`：当前在用的 OpenClaw skill 副本
- `openclaw/examples/`：OpenClaw MCP 和 cron 示例配置
- `docs/使用说明.md`：中文使用说明

## 公开仓库说明

- 当前仓库已去掉真实公众号凭证、飞书频道 ID 和本机专用配置
- `openclaw/examples/` 中的路径均为占位符，需要替换成你自己的实际仓库路径
- 真实的 `openclaw.json`、`jobs.json`、环境变量和 1Password 条目不会进入仓库

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

仅生成 payload 和 HTML：

```bash
python3 scripts/run_daily_news_pipeline.py \
  --input news/2026-03-22.json
```

生成并推送草稿：

```bash
python3 scripts/run_daily_news_pipeline.py \
  --push-draft \
  --thumb /绝对路径/封面图.jpg
```

## 微信环境变量

- `WECHAT_APPID`
- `WECHAT_APPSECRET`
- `WECHAT_AUTHOR`
- `WECHAT_THUMB_PATH`

## 说明

- `payload.title` 保留逻辑完整标题，通常由前两条新闻标题组成
- 推草稿时会先尝试完整标题，若微信接口返回 `45003` 再自动降级
- 推草稿时会自动把 `webp` 图片转换为 `jpg` 后再上传，避免微信图片接口报格式错误
- 公众号账号名片无法通过公开 API 稳定插入，建议在公众号后台手工补
- 更多使用细节见：[docs/使用说明.md](docs/使用说明.md)
