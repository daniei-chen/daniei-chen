# -*- coding: utf-8 -*-
"""从 data/profile.json 生成 README.md。

为什么 README 也要生成而不是手写：
项目卡是按仓库逐个生成的素材，手写 README 意味着每加一个仓库
都要手动补一段 <picture> 块（漏了就会出现"有素材但主页不显示"）。
生成之后，新增仓库会被每天定时运行的 Action 自动带进主页。

静态文案（关于我、技术栈徽章等）集中在本文件的常量里，改内容改这里。
"""
from __future__ import annotations

import json
import os

from make_assets import (CFG, SECTIONS, DATA, ROOT, display_name, project_repos, slug, REPO_META, esc)

OUT = os.path.join(ROOT, "README.md")

BULLETS = [
    "🛠 **独立开发者** —— 习惯一个人把一个想法从原型推到能上线的产品",
    "📱 主力技术栈 **Flutter / Dart**，以 Android 端为主，必要时下沉到原生；"
    "服务端写 **Go / Python**",
    "🧩 最近在做 **DSH 插件与本地优先的 AI 工具**：使用统计、安卓远控、模型网关",
    "🔒 相信工具该在**本地**解决问题：小鲸鱼的解析全程跑在手机上，链接不经过任何第三方服务器",
    "🧪 喜欢把踩过的坑沉淀成能复用的方案，而不是一次性脚本",
    "🚀 信奉「**先做出来，再做好**」",
    "📫 交流走 Issue 就行，每个仓库都开着",
]

# (标题, 徽章 markdown 列表)
STACK_GROUPS = [
    ("框架与运行时", [
        "![Flutter](https://img.shields.io/badge/Flutter-02569B?style=flat-square&logo=flutter&logoColor=white)",
        "![Android](https://img.shields.io/badge/Android-3DDC84?style=flat-square&logo=android&logoColor=white)",
        "![WebView](https://img.shields.io/badge/WebView-4285F4?style=flat-square&logo=googlechrome&logoColor=white)",
        "![Kotlin](https://img.shields.io/badge/Kotlin-7F52FF?style=flat-square&logo=kotlin&logoColor=white)",
        "![PowerShell](https://img.shields.io/badge/PowerShell-5391FE?style=flat-square&logo=powershell&logoColor=white)",
    ]),
    ("服务端与工程", [
        "![Go](https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white)",
        "![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)",
        "![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)",
        "![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)",
        "![Node.js](https://img.shields.io/badge/Node.js-339933?style=flat-square&logo=nodedotjs&logoColor=white)",
        "![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)",
        "![Git](https://img.shields.io/badge/Git-F05032?style=flat-square&logo=git&logoColor=white)",
        "![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)",
    ]),
]

TOP_BADGES = [
    "![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)",
    "![Dart](https://img.shields.io/badge/Dart-0175C2?style=for-the-badge&logo=dart&logoColor=white)",
    "![Go](https://img.shields.io/badge/Go-00ADD8?style=for-the-badge&logo=go&logoColor=white)",
    "![Android](https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white)",
    "![DSH](https://img.shields.io/badge/DSH-Plugin-4C8DFF?style=for-the-badge&labelColor=0E1A33)",
    "![独立开发者](https://img.shields.io/badge/独立开发者-22D3EE?style=for-the-badge&labelColor=0E1A33)",
]

FOOT_BADGES = [
    "![Status](https://img.shields.io/badge/status-building-22D3EE?style=flat-square&labelColor=0E1A33)",
    "![PRs](https://img.shields.io/badge/PRs-welcome-A78BFA?style=flat-square&labelColor=0E1A33)",
    "![Made with](https://img.shields.io/badge/自绘_SVG-无第三方图床-F472B6?style=flat-square&labelColor=0E1A33)",
]

# 全部仓库索引。项目卡只放当前主项目，这里保证每个公开仓库都有入口。
REPO_GROUPS = [
    ("DSH / AI 工具", [
        "dsh-token-insight",
        "DeepSeek-Harness-APP",
        "WorkBuddy-API",
        "Qoder-API",
        "Trae-API",
        "dsh-purge",
    ]),
    ("移动端 / Flutter", [
        "ZCode-App",
        "Little-Whale",
        "Pdd-Shopping",
    ]),
    ("3D / 视觉实验", [
        "Forbidden-City",
        "solar-system",
    ]),
    ("工具 / 其他", [
        "QQ-Space-Nostalgia",
    ]),
    ("Fork / 实验", [
        "deepseek-harness",
        "deepseek-harness-phone",
    ]),
]


def _md_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def _repo_desc(r: dict) -> str:
    """优先用 REPO_META 的中文简介，避免主页表格里出现英文截断。"""
    desc = _md_cell(REPO_META.get(r["name"], {}).get("blurb") or r.get("desc") or "等待补充简介")
    return desc[:57] + "…" if len(desc) > 58 else desc


def repo_index(data: dict) -> str:
    """生成按方向分组的全部仓库表格；新增仓库会自动落到“其他”。"""
    login = data["user"]["login"].lower()
    by_name = {
        r["name"]: r
        for r in data.get("repos", [])
        if r["name"].lower() != login
    }
    used: set[str] = set()
    chunks: list[str] = []

    for title, names in REPO_GROUPS:
        rows = [by_name[n] for n in names if n in by_name]
        used.update(r["name"] for r in rows)
        if not rows:
            continue
        chunks.append(f"### {title}")
        chunks.append("")
        chunks.append("| 仓库 | 语言 | ★ | 最近更新 | 说明 |")
        chunks.append("| --- | --- | ---: | --- | --- |")
        for r in rows:
            name = _md_cell(display_name(r))
            url = r["url"]
            tag = " · fork" if r.get("fork") else ""
            empty = " · 空仓库" if r.get("empty") else ""
            desc = _repo_desc(r)
            chunks.append(
                f"| [{name}]({url}){tag} | `{r.get('lang') or '-'}` | "
                f"{r.get('stars', 0)} | {r['pushed_at'][:10]} | {desc}{empty} |"
            )
        chunks.append("")

    rest = [r for r in data.get("repos", [])
            if r["name"] not in used and r["name"].lower() != login]
    if rest:
        chunks.append("### 其他")
        chunks.append("")
        chunks.append("| 仓库 | 语言 | ★ | 最近更新 | 说明 |")
        chunks.append("| --- | --- | ---: | --- | --- |")
        for r in rest:
            name = _md_cell(display_name(r))
            tag = " · fork" if r.get("fork") else ""
            empty = " · 空仓库" if r.get("empty") else ""
            desc = _repo_desc(r)
            chunks.append(
                f"| [{name}]({r['url']}){tag} | `{r.get('lang') or '-'}` | "
                f"{r.get('stars', 0)} | {r['pushed_at'][:10]} | {desc}{empty} |"
            )
        chunks.append("")

    return "\n".join(chunks).strip()


def pic(name: str, alt: str, width: str = "100%") -> str:
    return (f'<picture>\n'
            f'  <source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">\n'
            f'  <source media="(prefers-color-scheme: light)" srcset="assets/{name}-light.svg">\n'
            f'  <img src="assets/{name}-dark.svg" alt="{alt}" width="{width}">\n'
            f'</picture>')


def linked_pic(name: str, href: str, alt: str, title: str = "") -> str:
    """整张图可点击的项目卡；title 提供浏览器原生悬浮提示。"""
    return (f'<p align="center">\n  <a href="{href}" title="{esc(title or alt)}">\n'
            f'    <picture>\n'
            f'      <source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">\n'
            f'      <source media="(prefers-color-scheme: light)" srcset="assets/{name}-light.svg">\n'
            f'      <img src="assets/{name}-dark.svg" alt="{alt}" width="100%">\n'
            f'    </picture>\n  </a>\n</p>')


def hdr(slugname: str, alt: str) -> str:
    return pic(f"hdr-{slugname}", alt)


def build(data: dict) -> str:
    repos = project_repos(data)
    parts: list[str] = []

    parts.append('<div align="center">\n')
    parts.append(pic("banner", f'{CFG["name_zh"]} · {CFG["name_en"]}'))
    parts.append("\n")
    parts.append(pic("typing", "正在做的事"))
    parts.append("\n<br>\n")
    parts.append("\n".join(TOP_BADGES))
    parts.append("\n</div>\n")

    parts.append(pic("divider", ""))
    parts.append("\n")
    parts.append(hdr("about", "关于我"))
    parts.append("\n")
    parts.append("\n".join(f"- {b}" for b in BULLETS))
    parts.append("\n")
    parts.append(pic("terminal", "终端名片"))

    parts.append(hdr("dsh", "DSH 生态"))
    parts.append("\n")
    parts.append(pic("dsh", "DSH 生态"))
    parts.append("\n")
    parts.append("> 统计、远控、插件、中继——都围绕同一个本地 DSH host；数据不离开自己的机器。")
    parts.append("\n")

    parts.append(hdr("stack", "技术栈"))
    parts.append("\n")
    parts.append(pic("lang", "代码语言构成"))
    parts.append("\n")
    parts.append("<table>\n<tr>")
    for title, badges in STACK_GROUPS:
        parts.append(f'\n<td valign="top" width="{100 // len(STACK_GROUPS)}%">\n')
        parts.append(f"**{title}**\n\n")
        parts.append("\n".join(badges))
        parts.append("\n</td>")
    parts.append("\n</tr>\n</table>")

    parts.append(hdr("projects", "在做的东西"))
    parts.append("\n")
    for r in repos:
        blurb = REPO_META.get(r["name"], {}).get("blurb") or r.get("desc") or ""
        parts.append(linked_pic(
            f"proj-{slug(r['name'])}", r["url"], display_name(r),
            f"{display_name(r)} — {blurb}" if blurb else display_name(r),
        ))
        parts.append("\n")

    parts.append(hdr("repos", "全部仓库"))
    parts.append("\n")
    parts.append("> 上面是当前主项目；这里是全部公开仓库，按方向分组，Fork 和空仓库也保留入口。\n")
    parts.append(repo_index(data))
    parts.append("\n")

    parts.append(hdr("stats", "数据与轨迹"))
    parts.append("\n")
    parts.append(pic("stats", "数据概览"))
    parts.append("\n")
    parts.append(pic("activity", "加入以来的每日提交"))
    parts.append("\n")
    parts.append("> 上面的图**不是第三方图床的静态卡片**：数据由本仓库的 GitHub Action "
                 f"每天重新抓取并重绘（最近更新 `{data.get('generated_at', '')[:10]}`），\n"
                 "> 素材全部自绘，深浅色模式各一套。")

    parts.append(hdr("focus", "方向与投入"))
    parts.append("\n")
    parts.append(pic("focus", "方向与投入"))
    parts.append("\n")
    parts.append("> 占比是自评，不是考试成绩，会随手上在做的东西变。")

    parts.append(pic("divider", ""))
    parts.append("\n<div align=\"center\">\n")
    parts.append("**如果哪个仓库对你有用，点个 ⭐ 就是最好的鼓励。**\n")
    parts.append("\n".join(FOOT_BADGES))
    parts.append("\n</div>")

    return "\n".join(parts) + "\n"


def main() -> None:
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    md = build(data)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(md)

    repos = project_repos(data)
    print(f"wrote {OUT}  {len(md.encode('utf-8'))} bytes")
    print(f"  项目卡 {len(repos)} 个: {', '.join(display_name(r) for r in repos)}")

    # 生成期校验：README 引用的每个素材都必须真实存在，
    # 否则线上就是破图（这个坑踩过一次：相对路径写错，整页 SVG 全挂）
    import re
    refs = sorted(set(re.findall(r'src(?:set)?="assets/([^"]+\.svg)"', md)))
    missing = [r for r in refs if not os.path.exists(os.path.join(ROOT, "assets", r))]
    print(f"  引用素材 {len(refs)} 个，缺失 {len(missing)} 个")
    for m in missing:
        print(f"    MISSING: {m}")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
