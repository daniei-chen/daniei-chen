# -*- coding: utf-8 -*-
"""把 repo/README.md 渲染成本地预览页，用于推送前核对视觉效果。

刻意做成"单一事实来源"：直接读真实的 README.md，而不是另写一份 HTML，
这样 Markdown 写错（表格、picture、列表）在预览阶段就能暴露。
只支持本 README 实际用到的 Markdown 子集。
"""
from __future__ import annotations

import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 仓库根目录
SRC = os.path.join(ROOT, "README.md")
# 预览产物刻意写在仓库之外，避免被误提交
OUT = os.path.join(os.path.dirname(ROOT), "preview", "preview.html")

INLINE = [
    (re.compile(r"!\[([^\]]*)\]\(([^)]+)\)"), r'<img alt="\1" src="\2">'),
    (re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), r'<a href="\2">\1</a>'),
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
]


def inline(s: str) -> str:
    out = html.escape(s, quote=False)
    for rx, rep in INLINE:
        out = rx.sub(rep, out)
    return out


def render(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # 围栏代码块
        if stripped.startswith("```"):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            continue

        # 原始 HTML 块
        if stripped.startswith("<"):
            buf = []
            while i < n and lines[i].strip() != "":
                buf.append(lines[i])
                i += 1
            out.append("\n".join(buf))
            continue

        if not stripped:
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        if stripped.startswith("> "):
            out.append(f"<blockquote>{inline(stripped[2:])}</blockquote>")
            i += 1
            continue

        if stripped.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(f"<li>{inline(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        if stripped == "<br>":
            out.append("<br>")
            i += 1
            continue

        buf = []
        while i < n and lines[i].strip() and not lines[i].strip().startswith(("#", "- ", ">", "<", "```")):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
        else:
            # 兜底：任何未被上面分支消费的行都必须让游标前进，否则死循环
            out.append("<p>" + inline(stripped) + "</p>")
            i += 1
    return "\n".join(out)


def pick_theme(block: str, theme: str) -> str:
    """把 <picture> 按主题折叠成单个 <img>（预览页两块面板要同时显示两种模式）。"""
    def repl(m: re.Match) -> str:
        inner = m.group(1)
        src = None
        for sm in re.finditer(r'<source[^>]*media="[^"]*color-scheme:\s*(\w+)[^"]*"[^>]*srcset="([^"]+)"', inner):
            if sm.group(1) == theme:
                src = sm.group(2)
        if not src:
            im = re.search(r'<img[^>]*src="([^"]+)"', inner)
            src = im.group(1) if im else ""
        attrs = re.search(r'<img([^>]*)>', inner)
        extra = attrs.group(1) if attrs else ""
        extra = re.sub(r'\s*src="[^"]*"', "", extra)
        return f'<img src="{src}"{extra}>'
    return re.sub(r"<picture>(.*?)</picture>", repl, block, flags=re.S)


CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin:0; font-family: -apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif; }
.panel { padding: 24px 0 40px; }
.panel.dark  { background:#0d1117; color:#e6edf3; }
.panel.light { background:#ffffff; color:#1f2328; }
.tag { max-width: 1012px; margin: 0 auto 12px; font-size:13px; letter-spacing:1px;
       text-transform:uppercase; opacity:.55; font-weight:700; padding:0 24px; }
.content { max-width: 1012px; margin: 0 auto; padding: 0 32px; font-size:16px; line-height:1.6; }
.content img { max-width:100%; }
.content h2 { font-size:1.5em; font-weight:600; margin:32px 0 16px; padding-bottom:.3em;
              border-bottom:1px solid rgba(128,128,128,.25); }
.content ul { padding-left:2em; }
.content li { margin:.25em 0; }
.content blockquote { margin:0 0 16px; padding:0 1em; border-left:.25em solid rgba(128,128,128,.4); opacity:.85; }
.content pre { background: rgba(128,128,128,.12); padding:16px; border-radius:6px; overflow:auto;
               font-size:13px; line-height:1.45; }
.content code { font-family: ui-monospace,SFMono-Regular,Consolas,monospace; }
.content table { border-collapse:collapse; width:100%; }
.content td { padding: 4px 8px; vertical-align: top; }
.content a { color:#4493f8; text-decoration:none; }
.panel.light a { color:#0969da; }
.content div[align="center"] > p { margin: 8px 0; }
.badge-row img { margin: 2px; }
"""


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        md = f.read()
    body = render(md)
    # 预览页位于仓库之外，素材在仓库的 assets/ 下；真实 README 里两者同级，
    # 所以这里只是为本地预览改写相对路径。src 与 srcset 都要改，
    # 否则 pick_theme 会从 srcset 里取回未改写的旧路径。
    body = body.replace('src="assets/', 'src="../assets/')
    body = body.replace('srcset="assets/', 'srcset="../assets/')
    panels = []
    for theme, label in (("dark", "GitHub 深色模式"), ("light", "GitHub 浅色模式")):
        panels.append(f'<section class="panel {theme}">'
                      f'<div class="tag">{label}</div>'
                      f'<div class="content">{pick_theme(body, theme)}</div>'
                      f'</section>')
    doc = (f"<!doctype html><html><head><meta charset='utf-8'>"
           f"<title>README 预览 · daniei-chen</title><style>{CSS}</style></head>"
           f"<body>{''.join(panels)}</body></html>")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {OUT}  {len(doc.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
