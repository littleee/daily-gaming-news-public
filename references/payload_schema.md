# Payload Schema

使用 UTF-8 JSON。

这个文件描述的是 `build_payload_from_news.py` 生成并交给渲染器使用的结构，不再包含旧的 workspace bridge 流程。

## 推荐结构

```json
{
  "title": "《艾恩葛朗特 回荡新声》两分钟实机宣传片 ｜ 《匹诺曹的谎言》全球销量已超400万套",
  "author": "狗子",
  "digest": "今日 6 条 3DM 主机与 PC 游戏资讯整理。",
  "publish_time": "2026-03-22",
  "source_url": "https://www.3dmgame.com/news/game/",
  "cover_image": "https://img.3dmgame.com/uploads/images/news/20260322/3940270_001.jpg",
  "intro_paragraphs": [],
  "sections": [
    {
      "heading": "《红色沙漠》又遭批评 隐瞒使用AI创作画作",
      "paragraphs": [
        "正文段落 1。",
        "正文段落 2。"
      ],
      "image": "https://img.3dmgame.com/uploads/images/news/20260322/3940270_001.jpg",
      "gallery": [
        "https://img.3dmgame.com/uploads/images/news/20260322/3940270_002.jpg"
      ]
    }
  ],
  "closing_paragraphs": [],
  "footer_note": "更多资讯，关注狗子"
}
```

## 字段说明

- `title`：公众号草稿标题。当前默认由前两条新闻标题拼接，使用 `｜` 分隔。
- `author`：作者名。若未显式设置，推草稿时可由环境变量覆盖。
- `digest`：公众号摘要。
- `publish_time`：文章日期。
- `source_url`：新闻来源页或聚合来源页。
- `cover_image`：封面图路径或 URL。
- `intro_paragraphs`：正文开篇段落。当前主流程通常留空。
- `sections`：新闻正文段落列表。
- `sections[*].heading`：每条新闻的小标题。
- `sections[*].paragraphs`：正文段落数组。
- `sections[*].image`：主图，可省略。
- `sections[*].gallery`：组图，可省略。
- `closing_paragraphs`：结尾段落。
- `footer_note`：底部提示文案。

## 兼容的自由格式

如果上游已经生成了完整内容，也可以传：

- `body_markdown`
- `body_html`

渲染器优先级为：

1. `body_html`
2. `body_markdown`
3. 结构化 schema

## 当前正式输入来源

当前正式链路读取的是：

- `news/YYYY-MM-DD.json`
- `news/latest.json`

推荐直接运行：

```bash
python3 scripts/run_daily_news_pipeline.py
```

这会自动完成：

1. 从 `news/` 目录定位输入文件
2. 构建 payload
3. 渲染公众号 HTML
4. 在需要时推送到草稿箱
