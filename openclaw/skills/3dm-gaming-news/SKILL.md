---
name: 3dm-gaming-news
description: |
  Collect the latest console and PC gaming news from 3DM and save it as the standard daily_gaming_news JSON input. Use when asked to scrape 3DM game news, refresh news/latest.json, or prepare the upstream source file for the TGDOG WeChat publishing pipeline. This skill only handles collection and normalization, not HTML rendering or WeChat draft publishing.
---

# 3DM 主机游戏资讯采集

## 任务目标
从 3DM 游戏网获取当天最新的 **6 条主机游戏相关资讯**，输出为标准 JSON 格式，供下游 `daily-gaming-news-pipeline` 使用。

## 执行步骤

### 1. 访问 3DM 新闻页面
打开以下页面查看最新游戏资讯：
- https://www.3dmgame.com/news/game/ （游戏新闻首页）
- https://www.3dmgame.com/news/game/2/ （第2页）
- https://www.3dmgame.com/news_32_1/ （单机资讯）

### 2. 人工挑选新闻
从页面中挑选 **当天的最新新闻**，按以下规则筛选：

**优先级排序（优先选热度高、知名IP）：**
1. **知名IP大作**（优先级最高）
   - 任天堂第一方：《塞尔达》《马里奥》《宝可梦》《火焰纹章》等
   - PlayStation独占：《战神》《最后生还者》《对马岛》《蜘蛛侠》等
   - Xbox大作：《光环》《极限竞速》《星空》《上古卷轴》等
   - 第三方大作：《GTA》《生化危机》《最终幻想》《刺客信条》《黑神话》等
   - 热门独立游戏：《空洞骑士》《哈迪斯》《死亡细胞》等

2. **热门话题**
   - 发售首日/首周销量数据
   - 媒体评分解禁（IGN、GS等权威评分）
   - 重大更新/DLC发布
   - 主机硬件性能测试

3. **其他主机游戏资讯**

**✅ 保留内容：**
- PS5 / PlayStation 游戏
- Xbox Series / Xbox One 游戏
- Switch / Switch 2 / 任天堂游戏
- Steam / PC 主机游戏
- 主机硬件、性能、画质相关
- 游戏发售、更新、DLC 消息
- 游戏预告片、实机演示
- 主机游戏销量数据

**❌ 排除内容：**
- 手游 / 手机游戏 / iOS / 安卓
- 页游 / WebGame / H5游戏
- 电竞赛事 / 职业比赛
- 电影 / 电视剧 / 动漫 / 综艺
- 单纯硬件评测（显卡、CPU评测）
- 厂商裁员 / 财报 / 收购等商业新闻

### 3. 提取信息
对每条选中的新闻提取：
- **title**: 新闻标题（清理"游戏新闻"等前缀）
- **url**: 3DM 文章页完整链接（如 https://www.3dmgame.com/news/202603/3940125.html）
- **summary**: 中文摘要（100字以内，简洁概括核心内容）
- **tags**: 自动标签（PS5/Xbox/Switch/Steam/任天堂/新游发售/游戏更新/预告片）

### 4. 生成 JSON 文件

**输出路径：**
```
~/.openclaw/workspace/output/daily_gaming_news/news/YYYY-MM-DD.json
```

并同时覆盖：

```
~/.openclaw/workspace/output/daily_gaming_news/news/latest.json
```

**JSON 结构：**
```json
{
  "date": "2026-03-20",
  "timezone": "Asia/Shanghai",
  "topic": "daily-gaming-news",
  "source_job_id": "uuid",
  "generated_at": "2026-03-20T12:00:00+08:00",
  "count": 6,
  "items": [
    {
      "rank": 1,
      "title": "新闻标题",
      "summary": "中文摘要",
      "url": "https://www.3dmgame.com/news/...",
      "source": "3DM",
      "language": "zh-CN",
      "tags": ["PS5", "新游发售"]
    }
  ]
}
```

**格式要求：**
- `date`: 当天日期（YYYY-MM-DD）
- `timezone`: 固定 "Asia/Shanghai"
- `topic`: 固定 "daily-gaming-news"
- `source_job_id`: 优先写真实 cron job id；如果当前上下文已给出任务 id，就直接复用
- `generated_at`: ISO 8601 格式带时区
- `count`: 必须为 6
- `source`: 固定 "3DM"
- `language`: 固定 "zh-CN"
- `tags`: 根据内容自动添加（最多3个）

### 5. 验证输出
生成后检查：
- [ ] 恰好 6 条新闻
- [ ] 所有 URL 都是 3DM 真实文章页
- [ ] 每条都有标题、摘要、URL
- [ ] JSON 格式合法（无 Markdown 包裹）
- [ ] 所有内容符合主机游戏筛选规则
- [ ] 同时写入 `YYYY-MM-DD.json` 和 `latest.json`

## 标签规则
根据标题内容自动添加标签：
- PS5 / PlayStation → `"PS5"`
- Xbox → `"Xbox"`
- Switch 2 / NS2 → `"Switch 2"`
- Switch / NS → `"Switch"`
- Steam → `"Steam"`
- 任天堂 → `"任天堂"`
- 发售/上市/推出 → `"新游发售"`
- 更新/补丁/DLC → `"游戏更新"`
- 预告/宣传片 → `"预告片"`

## 示例

**输入（3DM 页面内容）：**
```
《艾恩葛朗特 回荡新声》两分钟实机宣传片
万代和开发商Game Studio发布了...登陆PC Steam，PS5和Xbox...
```

**输出 JSON 条目：**
```json
{
  "rank": 1,
  "title": "《艾恩葛朗特 回荡新声》两分钟实机宣传片",
  "summary": "万代公布了《刀剑神域》系列新作的两分钟实机宣传片，游戏将于7月9日发售，登陆PC Steam、PS5和Xbox Series平台。",
  "url": "https://www.3dmgame.com/news/202603/3940125.html",
  "source": "3DM",
  "language": "zh-CN",
  "tags": ["Steam", "PS5", "Xbox"]
}
```

## 注意事项

1. **只使用 3DM 来源**，不发散到其他网站
2. **必须 6 条**，不够时从更多页面获取
3. **必须当天新闻**，检查发布日期
4. **摘要要简洁**，不要复制整段内容
5. **不要包含 Markdown 代码块**，输出纯 JSON
6. **这个 skill 只负责采集**，不要在这里渲染 HTML 或推公众号草稿
7. **不需要额外过滤 `webp` 图片**，下游发布脚本会在推送到微信前自动转换成 `jpg`
