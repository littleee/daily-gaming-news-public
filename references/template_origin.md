# Template Origin

当前模板来自这篇历史公众号文章的版式抽取：

- https://mp.weixin.qq.com/s/yVzcXGxtycxZGYlyMtD4kA

保留了这些核心视觉特征：

- 金色纹理标题条
- 居中的彩色分隔条
- 密集但可读的正文节奏
- 带二维码与装饰图的结尾区域

当前正式模板文件：

- `templates/tgdog_roundup_template.html.j2`

如果后续想换成别的历史文章风格，可以再次运行：

```bash
python3 scripts/extract_wechat_template.py --url '历史文章链接' --name new-style
```

当前主流程已经固定为“3DM 采集 -> payload -> 渲染 -> 草稿箱”，不再依赖旧的中间版本工作流。
