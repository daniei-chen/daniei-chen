# -*- coding: utf-8 -*-
"""生成 README 所需的全部自绘 SVG（深色 / 浅色两套）。

为什么自绘而不是用 github-readme-stats：
- 新账号数据稀疏，第三方数据卡会渲染出"连续贡献 0 天""活动图全空"这类难看结果；
- 自绘图不依赖第三方可用性，且深浅色模式都能精确适配；
- 图形语言统一（深空极光），比默认 tokyonight 卡片更贴主题。

所有 SVG 只使用 SMIL / 内联 CSS 动效，不引用任何外部资源
（GitHub 通过 camo 代理以 <img> 渲染，外部字体、脚本、外链都不可用）。
"""
from __future__ import annotations

import json
import os
import random
import unicodedata
import xml.sax.saxutils as sx
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 仓库根目录
DATA = os.path.join(ROOT, "data", "profile.json")
OUT = os.path.join(ROOT, "assets")

# ----------------------------------------------------------------------------
# 可编辑文案：改这里即可换名字 / 标签 / 打字内容
# ----------------------------------------------------------------------------
CFG = {
    "name_en": "DANIEI CHEN",
    "name_zh": "陈丹妮",
    "chips": ["独立开发者", "Flutter / Dart", "移动端产品"],
    "typing": [
        "把想法做成能上线的产品",
        "用 Flutter 写能解决真实问题的小工具",
        "在写代码，也在做产品",
    ],
    # 方向自评（0-100）。这组数字是主观占比，按自己的感觉改就行。
    "focus": [
        ("Flutter / Dart 客户端", 100),
        ("产品设计与交互打磨", 72),
        ("独立开发 · 从想法到上线", 80),
        ("移动端原生能力集成", 60),
        ("服务端与部署", 45),
    ],
}

FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
        "'Hiragino Sans GB','Microsoft YaHei','Helvetica Neue',Arial,sans-serif")

PAL = {
    "dark": {
        "bg1": "#070B1A", "bg2": "#0E1A33",
        "stroke": "#1E3A5F", "text": "#E6F1FF", "muted": "#8CA3C7", "dim": "#5B7093",
        "cyan": "#22D3EE", "cyan2": "#67E8F9",
        "violet": "#8B5CF6", "violet2": "#A78BFA",
        "teal": "#2DD4BF", "pink": "#F472B6",
        "star": "#EAF4FF", "grid": "#16233D",
    },
    "light": {
        "bg1": "#F8FBFF", "bg2": "#E6EFFF",
        "stroke": "#C7D8F0", "text": "#0B1229", "muted": "#4A5B7A", "dim": "#7C8CA8",
        "cyan": "#0891B2", "cyan2": "#22B8D9",
        "violet": "#7C3AED", "violet2": "#8B5CF6",
        "teal": "#0D9488", "pink": "#DB2777",
        "star": "#9FC0E8", "grid": "#D8E5F7",
    },
}

AURORA = {
    "dark": [
        (200, 60, 300, "#22D3EE", 0.55, 15),
        (790, 90, 285, "#8B5CF6", 0.55, 18),
        (520, 250, 340, "#2DD4BF", 0.32, 21),
        (60, 250, 240, "#F472B6", 0.20, 24),
    ],
    "light": [
        (200, 60, 300, "#22B8D9", 0.30, 15),
        (790, 90, 285, "#8B5CF6", 0.28, 18),
        (520, 250, 340, "#14B8A6", 0.16, 21),
        (60, 250, 240, "#EC4899", 0.12, 24),
    ],
}


def project_repos(data: dict) -> list[dict]:
    """真正要展示的项目仓库。排除两类：

    1. 与用户名同名的仓库 —— 那是主页 README 的载体，不是项目。
       不排除的话，主页上会冒出一张"关于主页仓库自己"的项目卡，
       语言构成的字节统计也会被 tools/ 里的 Python 带偏。
    2. 空仓库（一个文件都没有）—— 没内容可描述，生成出来的卡片是空壳。
    """
    login = data["user"]["login"].lower()
    return [r for r in data["repos"]
            if r["name"].lower() != login and not r.get("empty")]


def esc(s: str) -> str:
    return sx.escape(s, {'"': "&quot;"})


def text_w(s: str, size: float) -> float:
    """粗略估算渲染宽度：CJK 按 1.0em，其余按 0.55em。"""
    units = sum(1.0 if unicodedata.east_asian_width(c) in "WF" else 0.55 for c in s)
    return units * size


def svg(w: int, h: int, label: str, defs: str, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" fill="none" role="img" aria-label="{esc(label)}">'
            f'<defs>{defs}</defs>{body}</svg>')


def panel(p: dict, pid: str, w: int, h: int, rx: int = 18) -> str:
    return (f'<rect width="{w}" height="{h}" rx="{rx}" fill="url(#{pid})"/>'
            f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="{rx}" '
            f'stroke="{p["stroke"]}" stroke-opacity="0.7"/>')


def bg_grad(p: dict, pid: str) -> str:
    return (f'<linearGradient id="{pid}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{p["bg1"]}"/>'
            f'<stop offset="1" stop-color="{p["bg2"]}"/></linearGradient>')


def aurora(mode: str, seed: int = 7) -> tuple[str, str]:
    """返回 (defs, body)：极光光斑 + 星点，缓慢漂移。"""
    p, blobs = PAL[mode], AURORA[mode]
    defs, body = [], []
    for i, (cx, cy, r, color, op, dur) in enumerate(blobs):
        gid = f"ab{i}"
        defs.append(
            f'<radialGradient id="{gid}">'
            f'<stop offset="0" stop-color="{color}" stop-opacity="{op}"/>'
            f'<stop offset="0.55" stop-color="{color}" stop-opacity="{op * 0.35:.3f}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
        body.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{gid})">'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0; {18 + i * 8} {-10 - i * 3}; 0 0" dur="{dur}s" repeatCount="indefinite" '
            f'calcMode="spline" keyTimes="0;0.5;1" '
            f'keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/></circle>')
    rng = random.Random(seed)
    stars = []
    for _ in range(78):
        x, y = rng.uniform(8, 992), rng.uniform(6, 232)
        r = rng.uniform(0.6, 1.9)
        a = rng.uniform(0.25, 0.9)
        stars.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{p["star"]}">'
            f'<animate attributeName="opacity" values="{a:.2f};{min(a*1.9,1):.2f};{a:.2f}" '
            f'dur="{rng.uniform(2.4,6.2):.1f}s" begin="{rng.uniform(0,5):.1f}s" '
            f'repeatCount="indefinite"/></circle>')
    return "".join(defs), "".join(body) + "".join(stars)


def wave(w: int, y: float, fill: str, dur: float, amp: float) -> str:
    d = (f"M0 {y:.0f} C {w*0.18:.0f} {y-amp:.0f} {w*0.32:.0f} {y+amp:.0f} {w*0.5:.0f} {y:.0f} "
         f"C {w*0.68:.0f} {y-amp:.0f} {w*0.82:.0f} {y+amp:.0f} {w} {y:.0f} V 320 H 0 Z")
    return (f'<g><path d="{d}" fill="{fill}"/><path d="{d}" fill="{fill}" '
            f'transform="translate({w} 0)"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;-{w} 0" dur="{dur}s" repeatCount="indefinite"/></g>')


# ----------------------------------------------------------------------------
# 1) 头图
# ----------------------------------------------------------------------------
def banner(mode: str) -> str:
    p = PAL[mode]
    W, H = 1000, 300
    a_defs, a_body = aurora(mode)
    defs = (bg_grad(p, "bg") + a_defs
            + f'<linearGradient id="nameGrad" x1="0" y1="0" x2="1" y2="1">'
              f'<stop offset="0" stop-color="{p["cyan2"]}"/>'
              f'<stop offset="0.5" stop-color="{p["cyan"]}"/>'
              f'<stop offset="1" stop-color="{p["violet2"]}"/></linearGradient>'
            + '<linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0">'
              '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
              '<stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.5"/>'
              '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
            + f'<linearGradient id="waveA" x1="0" y1="0" x2="0" y2="1">'
              f'<stop offset="0" stop-color="{p["cyan"]}" stop-opacity="0"/>'
              f'<stop offset="1" stop-color="{p["cyan"]}" stop-opacity="0.30"/></linearGradient>'
            + f'<linearGradient id="waveB" x1="0" y1="0" x2="0" y2="1">'
              f'<stop offset="0" stop-color="{p["violet"]}" stop-opacity="0"/>'
              f'<stop offset="1" stop-color="{p["violet"]}" stop-opacity="0.24"/></linearGradient>'
            + f'<clipPath id="round"><rect width="{W}" height="{H}" rx="22"/></clipPath>'
            + '<clipPath id="nameClip">'
              f'<text x="500" y="198" text-anchor="middle" font-family="{FONT}" '
              f'font-size="80" font-weight="800" letter-spacing="2">'
              f'{esc(CFG["name_zh"])}</text></clipPath>')

    n = len(CFG["chips"])
    chip_w, gap = 126, 4
    x0 = 500 - (n * chip_w + (n - 1) * gap) / 2
    chips = []
    for i, chip in enumerate(CFG["chips"]):
        cx = x0 + i * (chip_w + gap)
        chips.append(
            f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.8s" '
            f'begin="{1.0 + i * 0.16:.2f}s" fill="freeze"/>'
            f'<rect x="{cx:.0f}" y="230" width="{chip_w}" height="32" rx="16" '
            f'fill="{p["cyan"]}" fill-opacity="0.10" stroke="{p["cyan"]}" stroke-opacity="0.45"/>'
            f'<text x="{cx + chip_w/2:.0f}" y="251" text-anchor="middle" '
            f'font-family="{FONT}" font-size="14" fill="{p["text"]}">{esc(chip)}</text></g>')

    body = (
        f'<g clip-path="url(#round)">'
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
        + a_body
        + wave(W, 252, "url(#waveA)", 20, 13)
        + wave(W, 272, "url(#waveB)", 29, 9)
        # 上：英文名
        + f'<text x="500" y="112" text-anchor="middle" font-family="{FONT}" font-size="17" '
          f'font-weight="600" letter-spacing="7" fill="{p["cyan"]}" opacity="0">'
          f'{esc(CFG["name_en"])}'
          f'<animate attributeName="opacity" values="0;1" dur="1.1s" begin="0.2s" '
          f'fill="freeze"/></text>'
        # 中：中文名（渐变 + 扫光）
        + f'<text x="500" y="198" text-anchor="middle" font-family="{FONT}" font-size="80" '
          f'font-weight="800" letter-spacing="2" fill="url(#nameGrad)" opacity="0">'
          f'{esc(CFG["name_zh"])}'
          f'<animate attributeName="opacity" values="0;1" dur="1.1s" begin="0.45s" '
          f'fill="freeze"/></text>'
        + '<g clip-path="url(#nameClip)"><rect x="-320" y="112" width="170" height="116" '
          'fill="url(#sheen)" transform="skewX(-16)">'
          '<animate attributeName="x" values="-320;1120" dur="5.5s" begin="1.8s" '
          'repeatCount="indefinite"/></rect></g>'
        # 下：标签
        + "".join(chips)
        + '</g>'
        + f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="22" '
          f'stroke="{p["stroke"]}" stroke-opacity="0.75"/>'
    )
    return svg(W, H, f'{CFG["name_zh"]} · {CFG["name_en"]}', defs, body)


# ----------------------------------------------------------------------------
# 2) 打字机
# ----------------------------------------------------------------------------
def typing(mode: str) -> str:
    p = PAL[mode]
    W, H = 1000, 96
    phrases = CFG["typing"]
    n = len(phrases)
    cycle = 3.0 * n
    x0, size = 78, 22
    defs = [bg_grad(p, "tbg"),
            f'<linearGradient id="tline" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{p["cyan"]}"/>'
            f'<stop offset="1" stop-color="{p["violet"]}"/></linearGradient>']
    body = [panel(p, "tbg", W, H, 18),
            f'<rect x="26" y="24" width="3" height="48" rx="1.5" fill="url(#tline)">'
            f'<animate attributeName="height" values="48;30;48" dur="3.2s" '
            f'repeatCount="indefinite"/><animate attributeName="y" values="24;33;24" '
            f'dur="3.2s" repeatCount="indefinite"/></rect>',
            f'<text x="46" y="60" font-family="{FONT}" font-size="22" font-weight="700" '
            f'fill="{p["cyan"]}">&#10095;</text>']
    for i, ph in enumerate(phrases):
        tw = text_w(ph, size)
        start, type_end = i / n, i / n + 0.10
        hold_end = (i + 1) / n - 0.045
        reset_end = hold_end + 0.015
        # 关键：收缩必须瞬时完成。若把收缩的 keyTime 一路拉到 1.0，
        # 收缩会横跨整个周期，导致多句文字长时间重叠。
        kt = f"0;{start:.3f};{type_end:.3f};{hold_end:.3f};{reset_end:.3f};1"
        if i == 0:  # 首句起点与 0 重合，keyTimes 必须严格递增
            kt = f"0.000;0.001;{type_end:.3f};{hold_end:.3f};{reset_end:.3f};1"
        defs.append(
            f'<clipPath id="tc{i}"><rect x="{x0}" y="18" width="0" height="60">'
            f'<animate attributeName="width" '
            f'values="0;0;{tw:.0f};{tw + 12:.0f};0;0" '
            f'keyTimes="{kt}" dur="{cycle}s" repeatCount="indefinite"/></rect></clipPath>')
        body.append(
            f'<g clip-path="url(#tc{i})">'
            f'<text x="{x0}" y="60" font-family="{FONT}" font-size="{size}" '
            f'fill="{p["text"]}">{esc(ph)}</text>'
            f'<rect x="{x0 + tw + 5:.0f}" y="36" width="2" height="26" fill="{p["cyan"]}">'
            f'<animate attributeName="opacity" values="1;0;1;0" dur="1.1s" '
            f'repeatCount="indefinite"/></rect></g>')
    return svg(W, H, "自我介绍打字动效", "".join(defs), "".join(body))


# ----------------------------------------------------------------------------
# 3) 分隔线
# ----------------------------------------------------------------------------
def divider(mode: str) -> str:
    p = PAL[mode]
    W, H = 1000, 26
    defs = (f'<linearGradient id="dline" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{p["cyan"]}" stop-opacity="0"/>'
            f'<stop offset="0.2" stop-color="{p["cyan"]}" stop-opacity="0.75"/>'
            f'<stop offset="0.5" stop-color="{p["violet"]}" stop-opacity="0.85"/>'
            f'<stop offset="0.8" stop-color="{p["teal"]}" stop-opacity="0.7"/>'
            f'<stop offset="1" stop-color="{p["violet"]}" stop-opacity="0"/></linearGradient>'
            '<linearGradient id="dglow" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
            '<stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.95"/>'
            '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>')
    body = (f'<rect x="0" y="12" width="{W}" height="2" rx="1" fill="url(#dline)"/>'
            '<rect x="-160" y="10.5" width="160" height="5" rx="2.5" fill="url(#dglow)">'
            '<animate attributeName="x" values="-160;1000" dur="4.5s" '
            'repeatCount="indefinite"/></rect>')
    return svg(W, H, "分隔线", defs, body)


# ----------------------------------------------------------------------------
# 4) 数据卡
# ----------------------------------------------------------------------------
def stats(mode: str, data: dict) -> str:
    p = PAL[mode]
    W, H = 1000, 116
    c = data["contributions"]
    stars = sum(r["stars"] for r in project_repos(data))
    days = (date.today() - date.fromisoformat(data["user"]["created_at"][:10])).days
    items = [("项目仓库", len(project_repos(data)), p["cyan"]),
             ("获得星标", stars, p["violet2"]),
             ("公开贡献", c["total"], p["teal"]),
             ("加入天数", days, p["pink"])]
    defs = bg_grad(p, "sbg")
    body = [panel(p, "sbg", W, H, 18)]
    bw = W / len(items)
    for i, (label, value, color) in enumerate(items):
        cx = bw * (i + 0.5)
        if i:
            body.append(f'<line x1="{bw*i:.0f}" y1="26" x2="{bw*i:.0f}" y2="{H-26}" '
                        f'stroke="{p["stroke"]}" stroke-opacity="0.65"/>')
        body.append(
            f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.7s" '
            f'begin="{0.15*i:.2f}s" fill="freeze"/>'
            f'<circle cx="{cx:.0f}" cy="{H/2 + 20}" r="3.5" fill="{color}"/>'
            f'<circle cx="{cx:.0f}" cy="{H/2 + 20}" r="3.5" fill="{color}" opacity="0.4">'
            f'<animate attributeName="r" values="3.5;11;3.5" dur="2.6s" begin="{i*0.3:.1f}s" '
            f'repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.4;0;0.4" dur="2.6s" '
            f'begin="{i*0.3:.1f}s" repeatCount="indefinite"/></circle>'
            f'<text x="{cx:.0f}" y="{H/2 - 2:.0f}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="30" font-weight="800" fill="{color}">{value}</text>'
            f'<text x="{cx:.0f}" y="{H/2 + 44:.0f}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="13" fill="{p["muted"]}">{esc(label)}</text></g>')
    return svg(W, H, "数据概览", defs, "".join(body))


# ----------------------------------------------------------------------------
# 4.5) 方向自评
# ----------------------------------------------------------------------------
def focus(mode: str) -> str:
    """方向占比条。之所以自绘而不是手写 ASCII：
    █ / ░ 属于东亚「歧义宽度」字符，不同字体下宽度不一致，
    用 ASCII 画的进度条在部分用户机器上会错位得很明显。"""
    p = PAL[mode]
    rows = CFG["focus"]
    W = 1000
    # 卡片内不再重复标题（README 章节已有一份），直接排条
    pad_t, row_h, pad_b = 28, 52, 26
    H = pad_t + row_h * len(rows) + pad_b
    lx, bar_x, bar_w = 40, 320, 560
    defs = (bg_grad(p, "fbg")
            + f'<linearGradient id="fbar" x1="0" y1="0" x2="1" y2="0">'
              f'<stop offset="0" stop-color="{p["cyan"]}"/>'
              f'<stop offset="1" stop-color="{p["violet2"]}"/></linearGradient>')
    body = [panel(p, "fbg", W, H, 18)]
    for i, (label, pct) in enumerate(rows):
        y = pad_t + i * row_h
        fill_w = bar_w * pct / 100
        body.append(
            f'<text x="{lx}" y="{y + 16}" font-family="{FONT}" font-size="14" '
            f'fill="{p["muted"]}">{esc(label)}</text>'
            f'<rect x="{bar_x}" y="{y + 6}" width="{bar_w}" height="10" rx="5" '
            f'fill="{p["stroke"]}" fill-opacity="0.45"/>'
            f'<rect x="{bar_x}" y="{y + 6}" width="0" height="10" rx="5" fill="url(#fbar)">'
            f'<animate attributeName="width" from="0" to="{fill_w:.1f}" dur="1.1s" '
            f'begin="{0.25 + i * 0.14:.2f}s" fill="freeze" calcMode="spline" '
            f'keySplines="0.2 0 0.2 1"/></rect>'
            f'<circle cx="{bar_x + fill_w:.1f}" cy="{y + 11}" r="4" fill="{p["cyan2"]}" '
            f'opacity="0"><animate attributeName="opacity" values="0;0.9" dur="0.4s" '
            f'begin="{1.35 + i * 0.14:.2f}s" fill="freeze"/>'
            f'<animate attributeName="r" values="4;6;4" dur="2.8s" begin="{1.6 + i * 0.14:.2f}s" '
            f'repeatCount="indefinite"/></circle>'
            f'<text x="{bar_x + bar_w + 96}" y="{y + 16}" text-anchor="end" font-family="{FONT}" '
            f'font-size="14" font-weight="700" fill="{p["cyan2"]}">{pct}%</text>'
        )
    return svg(W, H, "方向与投入", defs, "".join(body))


# ----------------------------------------------------------------------------
# 5) 加入以来的每日提交
# ----------------------------------------------------------------------------
def activity(mode: str, data: dict) -> str:
    p = PAL[mode]
    W, H = 1000, 216
    c = data["contributions"]
    created = data["user"]["created_at"][:10]
    since = [d for d in c["days"] if d["date"] >= created] or c["days"][-14:]
    n = len(since)
    maxc = max([d["count"] for d in since] + [1])
    total = sum(d["count"] for d in since)
    active = sum(1 for d in since if d["count"] > 0)
    # pt 留得比常规大：最高柱顶部的数值标签也要放得下，不能压到标题行
    pl, pr, pt, pb = 40, 40, 58, 46
    pw, ph = W - pl - pr, H - pt - pb
    step = pw / max(n, 1)
    bw = max(6.0, min(step * 0.52, 26.0))

    defs = (bg_grad(p, "abg")
            + '<linearGradient id="bar" x1="0" y1="1" x2="0" y2="0">'
              f'<stop offset="0" stop-color="{p["cyan"]}" stop-opacity="0.30"/>'
              f'<stop offset="1" stop-color="{p["cyan2"]}"/></linearGradient>'
            + '<linearGradient id="barHot" x1="0" y1="1" x2="0" y2="0">'
              f'<stop offset="0" stop-color="{p["violet"]}" stop-opacity="0.55"/>'
              f'<stop offset="1" stop-color="{p["pink"]}"/></linearGradient>')
    body = [panel(p, "abg", W, H, 18),
            f'<text x="{pl}" y="27" font-family="{FONT}" font-size="15" font-weight="700" '
            f'fill="{p["text"]}">加入以来 · 每日提交</text>',
            f'<text x="{W-pr}" y="27" text-anchor="end" font-family="{FONT}" font-size="13" '
            f'fill="{p["muted"]}">{esc(created)} → 今天 · {n} 天里 {active} 天有提交 · '
            f'合计 {total} 次</text>']
    for g in range(1, maxc + 1):
        y = pt + ph - ph * g / maxc
        body.append(f'<line x1="{pl}" y1="{y:.1f}" x2="{W-pr}" y2="{y:.1f}" '
                    f'stroke="{p["grid"]}" stroke-opacity="0.85"/>')
        body.append(f'<text x="{pl-9}" y="{y+4:.1f}" text-anchor="end" font-family="{FONT}" '
                    f'font-size="11" fill="{p["dim"]}">{g}</text>')
    body.append(f'<line x1="{pl}" y1="{pt+ph}" x2="{W-pr}" y2="{pt+ph}" stroke="{p["stroke"]}"/>')
    body.append(f'<text x="{pl-9}" y="{pt+ph+4}" text-anchor="end" font-family="{FONT}" '
                f'font-size="11" fill="{p["dim"]}">0</text>')

    for i, d in enumerate(since):
        cx = pl + step * (i + 0.5)
        cnt = d["count"]
        if cnt == 0:
            body.append(f'<rect x="{cx-bw/2:.1f}" y="{pt+ph-2:.1f}" width="{bw:.1f}" '
                        f'height="2" rx="1" fill="{p["stroke"]}" opacity="0.85"/>')
            continue
        h = max(5.0, ph * cnt / maxc)
        y = pt + ph - h
        fill = "url(#barHot)" if cnt >= maxc else "url(#bar)"
        body.append(
            f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.45s" '
            f'begin="{0.04*i:.2f}s" fill="freeze"/>'
            f'<rect x="{cx-bw/2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" '
            f'rx="{min(bw/2,4):.1f}" fill="{fill}"/>'
            f'<circle cx="{cx:.1f}" cy="{y-9:.1f}" r="3" fill="{p["cyan2"]}">'
            f'<animate attributeName="opacity" values="0.35;1;0.35" dur="2.2s" '
            f'begin="{0.3*i:.2f}s" repeatCount="indefinite"/></circle>'
            f'<text x="{cx:.1f}" y="{y-17:.1f}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="12" font-weight="700" fill="{p["text"]}">{cnt}</text></g>')
    tick = max(1, n // 7)
    last_drawn = -99
    for i in range(0, n, tick):
        cx = pl + step * (i + 0.5)
        # 与右下角"今天"标记保持距离，避免文字叠在一起
        if cx > W - pr - 46:
            continue
        body.append(f'<text x="{cx:.1f}" y="{H-20}" text-anchor="middle" font-family="{FONT}" '
                    f'font-size="11" fill="{p["dim"]}">{since[i]["date"][5:]}</text>')
        last_drawn = i
    body.append(f'<circle cx="{W-pr-6:.0f}" cy="{pt+ph:.0f}" r="3" fill="{p["cyan"]}">'
                f'<animate attributeName="opacity" values="0.4;1;0.4" dur="2s" '
                f'repeatCount="indefinite"/></circle>')
    body.append(f'<text x="{W-pr:.0f}" y="{H-20}" text-anchor="end" font-family="{FONT}" '
                f'font-size="11" fill="{p["cyan"]}">今天</text>')
    return svg(W, H, "加入以来的每日提交", defs, "".join(body))


# ----------------------------------------------------------------------------
# 6) 章节标题组件
# ----------------------------------------------------------------------------
SECTIONS = [
    ("about", "🧑‍💻", "关于我", "About"),
    ("stack", "🛠", "技术栈", "Tech Stack"),
    ("projects", "🚀", "在做的东西", "Projects"),
    ("stats", "📈", "数据与轨迹", "Stats & Activity"),
    ("focus", "🎯", "方向与投入", "Focus"),
]


def header(icon: str, zh: str, en: str, mode: str) -> str:
    p = PAL[mode]
    W, H = 1000, 92
    defs = (f'<linearGradient id="hzh" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{p["cyan2"]}"/>'
            f'<stop offset="0.55" stop-color="{p["cyan"]}"/>'
            f'<stop offset="1" stop-color="{p["violet2"]}"/></linearGradient>'
            f'<linearGradient id="hrule" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{p["cyan"]}" stop-opacity="0.85"/>'
            f'<stop offset="0.5" stop-color="{p["violet"]}" stop-opacity="0.45"/>'
            f'<stop offset="1" stop-color="{p["violet"]}" stop-opacity="0"/></linearGradient>'
            '<linearGradient id="hsweep" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
            '<stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.9"/>'
            '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="hic"><rect x="0" y="16" width="56" height="56" rx="16"/></clipPath>')
    body = [
        # 图标胶囊
        f'<rect x="0" y="16" width="56" height="56" rx="16" fill="{p["cyan"]}" fill-opacity="0.10" '
        f'stroke="{p["cyan"]}" stroke-opacity="0.38"/>'
        f'<g clip-path="url(#hic)"><rect x="-56" y="16" width="56" height="56" fill="{p["cyan"]}" '
        f'fill-opacity="0.16"><animate attributeName="x" values="-56;56" dur="3.4s" '
        f'repeatCount="indefinite"/></rect></g>'
        # 必须显式写 fill：SVG 根元素是 fill="none"，不写 fill 的文字会继承成
        # none 而完全不可见（插图图标这里已经踩过一次坑）。
        f'<text x="28" y="54" text-anchor="middle" font-family="{FONT}" font-size="27" '
        f'fill="{p["text"]}">{icon}</text>',
        # 中文大标题 + 英文小标
        f'<text x="76" y="47" font-family="{FONT}" font-size="30" font-weight="800" '
        f'fill="url(#hzh)">{esc(zh)}</text>'
        f'<text x="78" y="68" font-family="{FONT}" font-size="11" font-weight="700" '
        f'letter-spacing="3.2" fill="{p["dim"]}">{esc(en.upper())}</text>',
        # 底部分隔线 + 扫光
        f'<rect x="0" y="89" width="{W}" height="2" rx="1" fill="url(#hrule)"/>'
        '<rect x="-220" y="87.5" width="220" height="5" rx="2.5" fill="url(#hsweep)">'
        '<animate attributeName="x" values="-220;1000" dur="3.8s" repeatCount="indefinite"/></rect>',
    ]
    return svg(W, H, f'{zh} · {en}', defs, "".join(body))


# ----------------------------------------------------------------------------
# 7) 终端卡片（逐行打字）
# ----------------------------------------------------------------------------
TERM_LINES = [
    ("$ whoami", "cmd"),
    ("陈丹妮 · 独立开发者 / Indie Developer", "out"),
    ("$ cat stack.txt", "cmd"),
    ("Flutter · Dart · Android · WebView · Python", "out"),
    ("$ ls ~/repos", "cmd"),
    ("小鲸鱼/      ZCode-App/", "out"),
]


def terminal(mode: str) -> str:
    p = PAL[mode]
    W = 1000
    line_h, top = 34, 74
    H = top + line_h * len(TERM_LINES) + 22
    cycle = 13.0
    defs, body = [bg_grad(p, "tmbg")], []
    body.append(panel(p, "tmbg", W, H, 18))
    # 标题栏 + 三个圆点
    body.append(f'<rect x="0" y="0" width="{W}" height="46" rx="18" fill="{p["cyan"]}" '
                f'fill-opacity="0.05"/><rect x="0" y="30" width="{W}" height="16" '
                f'fill="{p["cyan"]}" fill-opacity="0.05"/>')
    for i, c in enumerate((p["pink"], "#FBBF24", p["teal"])):
        body.append(f'<circle cx="{34 + i*22}" cy="23" r="6" fill="{c}" opacity="0.85"/>')
    body.append(f'<text x="{W/2}" y="28" text-anchor="middle" font-family="{FONT}" '
                f'font-size="12" fill="{p["dim"]}">daniei-chen — zsh</text>')

    for i, (text, kind) in enumerate(TERM_LINES):
        y = top + i * line_h
        color = p["cyan2"] if kind == "cmd" else p["text"]
        weight = "600" if kind == "cmd" else "400"
        tw = text_w(text, 16) + 10
        t0 = 0.4 + i * 0.62
        dur = 0.34
        kt = f"0;{t0/cycle:.4f};{(t0+dur)/cycle:.4f};0.997;1"
        defs.append(
            f'<clipPath id="tm{i}"><rect x="34" y="{y-18}" width="0" height="26">'
            f'<animate attributeName="width" values="0;0;{tw:.0f};{tw:.0f};0" keyTimes="{kt}" '
            f'dur="{cycle}s" repeatCount="indefinite"/></rect></clipPath>')
        body.append(
            f'<g clip-path="url(#tm{i})"><text x="34" y="{y}" font-family="{FONT}" '
            f'font-size="16" font-weight="{weight}" fill="{color}">{esc(text)}</text></g>')
    # 末行闪烁光标
    last_y = top + (len(TERM_LINES)) * line_h - 16
    body.append(f'<rect x="34" y="{last_y}" width="9" height="18" fill="{p["cyan"]}">'
                f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.44;0.46;0.98;1" '
                f'dur="13s" repeatCount="indefinite"/></rect>')
    return svg(W, H, "终端卡片", "".join(defs), "".join(body))


# ----------------------------------------------------------------------------
# 8) 语言构成环形图
# ----------------------------------------------------------------------------
LANG_COLOR = {
    "Dart": "#0175C2", "Python": "#3776AB", "HTML": "#E34F26", "JavaScript": "#F7DF1E",
    "Kotlin": "#7F52FF", "Shell": "#4EAA25", "PowerShell": "#5391FE", "CSS": "#663399",
    "C++": "#F34B7D", "Java": "#B07219", "Swift": "#F05138", "Go": "#00ADD8",
}


def lang(mode: str, data: dict) -> str:
    p = PAL[mode]
    W, H = 1000, 230
    agg: dict[str, int] = {}
    for r in project_repos(data):
        for k, v in r["langs"].items():
            agg[k] = agg.get(k, 0) + v
    items = sorted(agg.items(), key=lambda kv: -kv[1])
    top, rest = items[:5], sum(v for _, v in items[5:])
    segs = [[n, v] for n, v in top]
    if rest:
        segs.append(["其他", rest])
    total = sum(v for _, v in segs) or 1

    cx, cy, r, sw = 132, 118, 70, 22
    circ = 2 * 3.141592653589793 * r
    defs, body = [bg_grad(p, "lgbg")], [panel(p, "lgbg", W, H, 18)]
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{p["stroke"]}" '
                f'stroke-opacity="0.35" stroke-width="{sw}"/>')
    acc = 0.0
    for i, (name, val) in enumerate(segs):
        frac = val / total
        seg_len = max(circ * frac - 3.0, 1.0)
        color = LANG_COLOR.get(name, p["violet2"] if name == "其他" else p["teal"])
        rot = -90 + 360 * acc
        acc += frac
        defs.append(f'<linearGradient id="lg{i}" x1="0" y1="0" x2="1" y2="1">'
                    f'<stop offset="0" stop-color="{color}"/>'
                    f'<stop offset="1" stop-color="{color}" stop-opacity="0.72"/></linearGradient>')
        body.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#lg{i})" '
            f'stroke-width="{sw}" stroke-dasharray="0 {circ:.1f}" '
            f'transform="rotate({rot:.2f} {cx} {cy})" stroke-linecap="butt">'
            f'<animate attributeName="stroke-dasharray" values="0 {circ:.1f};{seg_len:.1f} '
            f'{circ-seg_len:.1f}" dur="0.9s" begin="{0.15 + i*0.13:.2f}s" fill="freeze"/></circle>')
    # 圆心
    top_name, top_val = segs[0]
    body.append(f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-family="{FONT}" '
                f'font-size="30" font-weight="800" fill="{p["cyan2"]}">'
                f'{top_val*100/total:.0f}%</text>'
                f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-family="{FONT}" '
                f'font-size="12" fill="{p["muted"]}">{esc(top_name)}</text>')
    # 图例
    body.append(f'<text x="290" y="46" font-family="{FONT}" font-size="15" font-weight="700" '
                f'fill="{p["text"]}">代码语言构成</text>'
                f'<text x="{W-40}" y="46" text-anchor="end" font-family="{FONT}" font-size="12" '
                f'fill="{p["dim"]}">按仓库字节统计 · 共 {len(project_repos(data))} 个项目仓库</text>')
    for i, (name, val) in enumerate(segs):
        col = i % 2
        row = i // 2
        x = 290 + col * 350
        y = 92 + row * 44
        color = LANG_COLOR.get(name, p["violet2"] if name == "其他" else p["teal"])
        pct = val * 100 / total
        body.append(
            f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.5s" '
            f'begin="{0.3 + i*0.1:.2f}s" fill="freeze"/>'
            f'<circle cx="{x}" cy="{y-4}" r="5.5" fill="{color}"/>'
            f'<text x="{x+16}" y="{y}" font-family="{FONT}" font-size="14" '
            f'fill="{p["text"]}">{esc(name)}</text>'
            f'<text x="{x+320}" y="{y}" text-anchor="end" font-family="{FONT}" font-size="13" '
            f'font-weight="700" fill="{p["muted"]}">{pct:.1f}%</text></g>')
    return svg(W, H, "代码语言构成", "".join(defs), "".join(body))


# ----------------------------------------------------------------------------
# 9) 项目卡
# ----------------------------------------------------------------------------
REPO_META = {
    "Little-Whale": {
        "display": "小鲸鱼",
        "blurb": "粘贴链接，保存无水印原片。解析全程在手机本地完成，链接不上传、不经过任何服务器。",
    },
    "WorkBuddy-API": {
        "display": "WorkBuddy2API",
        "blurb": "自托管的 OpenAI 兼容网关：把 CodeBuddy 账号包装成统一的 /v1/chat/completions 服务，"
                 "多账号池轮转 + 会话粘性 + 额度治理。",
    },
    "solar-system": {
        "display": "太阳系 · 3D 仿真",
        "blurb": "单文件、离线可用的真渲染太阳系仿真：真实星历与 25,791 颗恒星，"
                 "从日面一路退到 30 kpc 回望银河系。",
    },
    "ZCode-App": {
        "display": "ZCode-App",
        "blurb": "在手机或平板上远程管理 ZCode 桌面任务。扫码接入，原生 Flutter 外壳 + WebView 会话。",
    },
}


def wrap(text: str, max_w: float, size: float) -> list[str]:
    out, cur = [], ""
    for ch in text:
        if text_w(cur + ch, size) > max_w and cur:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def project(mode: str, repo: dict) -> str:
    p = PAL[mode]
    topics = repo.get("topics") or []
    # 有 topic 时卡片高一点，多出一行放标签；没有就不留空白
    W, H = 1000, 214 if topics else 178
    meta = REPO_META.get(repo["name"], {})
    display = meta.get("display", repo["name"])
    blurb = meta.get("blurb") or repo["desc"] or "这个仓库还没有写简介。"
    lic = repo["license"] or "未声明许可"
    updated = repo["pushed_at"][:10]
    # 没识别出主语言时给个中性占位，否则卡片上会出现一个孤零零的色点和空文字
    lang = repo["lang"] or "未识别"
    lcolor = LANG_COLOR.get(repo["lang"], p["dim"])
    defs = (bg_grad(p, "pbg")
            + f'<linearGradient id="pav" x1="0" y1="0" x2="1" y2="1">'
              f'<stop offset="0" stop-color="{p["cyan"]}"/>'
              f'<stop offset="1" stop-color="{p["violet"]}"/></linearGradient>'
            '<linearGradient id="pshine" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
            '<stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.30"/>'
            '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="pclip"><rect width="{W}" height="{H}" rx="18"/></clipPath>')
    body = [panel(p, "pbg", W, H, 18)]
    # 扫光
    body.append(f'<g clip-path="url(#pclip)"><rect x="-260" y="-40" width="200" height="{H+80}" '
                f'fill="url(#pshine)" transform="skewX(-18)">'
                f'<animate attributeName="x" values="-260;1120" dur="6s" begin="0.6s" '
                f'repeatCount="indefinite"/></rect></g>')
    body.append(
        f'<rect x="28" y="32" width="76" height="76" rx="20" fill="url(#pav)"/>'
        f'<text x="66" y="84" text-anchor="middle" font-family="{FONT}" font-size="34" '
        f'font-weight="800" fill="#FFFFFF">{esc(display[0])}</text>')
    body.append(f'<text x="126" y="60" font-family="{FONT}" font-size="24" font-weight="800" '
                f'fill="{p["text"]}">{esc(display)}</text>')
    # 元信息行
    mx = 126
    body.append(f'<circle cx="{mx+4}" cy="82" r="5" fill="{lcolor}"/>'
                f'<text x="{mx+16}" y="87" font-family="{FONT}" font-size="13" '
                f'fill="{p["muted"]}">{esc(lang)}</text>')
    mx += 16 + text_w(lang, 13) + 26
    for ico, val in (("★", repo["stars"]), ("⑂", repo["forks"])):
        body.append(f'<text x="{mx}" y="87" font-family="{FONT}" font-size="13" '
                    f'fill="{p["muted"]}">{ico} {val}</text>')
        mx += 46
    body.append(f'<text x="{mx}" y="87" font-family="{FONT}" font-size="13" '
                f'fill="{p["muted"]}">{esc(lic)} · 更新于 {updated}</text>')
    for i, line in enumerate(wrap(blurb, 800, 14)[:2]):
        body.append(f'<text x="126" y="{120 + i*26}" font-family="{FONT}" font-size="14" '
                    f'fill="{p["muted"]}">{esc(line)}</text>')
    # topic 标签行：放不下就折叠成 +N
    if topics:
        body.extend(_chips(p, topics, 126, 166, W - 64))
    body.append(f'<text x="{W-34}" y="96" text-anchor="end" font-family="{FONT}" font-size="26" '
                f'fill="{p["cyan"]}" opacity="0.85">&#8594;</text>')
    return svg(W, H, f'{display} 项目卡', defs, "".join(body))


def _chips(p: dict, topics: list[str], x0: float, y: float, max_x: float) -> list[str]:
    """把 topic 画成一排胶囊。宽度不够时最后收一个 +N，避免溢出卡片。"""
    out: list[str] = []
    x, shown = x0, 0
    for i, t in enumerate(topics):
        w = text_w(t, 11) + 22
        # 还有剩余项时，预留出 +N 胶囊的位置
        reserve = 0 if i == len(topics) - 1 else text_w("+9", 11) + 30
        if x + w + reserve > max_x:
            break
        out.append(
            f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="24" rx="12" '
            f'fill="{p["cyan"]}" fill-opacity="0.08" stroke="{p["cyan"]}" stroke-opacity="0.28"/>'
            f'<text x="{x + w / 2:.0f}" y="{y + 16}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="11" fill="{p["muted"]}">{esc(t)}</text>')
        x += w + 8
        shown += 1
    rest = len(topics) - shown
    if rest > 0:
        label = f"+{rest}"
        w = text_w(label, 11) + 22
        out.append(
            f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="24" rx="12" '
            f'fill="{p["stroke"]}" fill-opacity="0.30" stroke="{p["stroke"]}" '
            f'stroke-opacity="0.6"/>'
            f'<text x="{x + w / 2:.0f}" y="{y + 16}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="11" fill="{p["dim"]}">{label}</text>')
    return out


def slug(s: str) -> str:
    """仓库名 -> 素材文件名用的 slug（与 make_readme.py 共用，保持唯一来源）。"""
    return s.lower().replace("-", "").replace(" ", "").replace("_", "")


def display_name(repo: dict) -> str:
    return REPO_META.get(repo["name"], {}).get("display", repo["name"])


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)

    jobs: dict = {
        "banner": lambda m: banner(m),
        "typing": lambda m: typing(m),
        "divider": lambda m: divider(m),
        "terminal": lambda m: terminal(m),
        "stats": lambda m: stats(m, data),
        "activity": lambda m: activity(m, data),
        "lang": lambda m: lang(m, data),
        "focus": lambda m: focus(m),
    }
    for s, icon, zh, en in SECTIONS:
        jobs[f"hdr-{s}"] = (lambda i, z, e: (lambda m: header(i, z, e, m)))(icon, zh, en)
    for r in project_repos(data):
        jobs[f"proj-{slug(r['name'])}"] = (lambda rr: (lambda m: project(m, rr)))(r)

    total = 0
    expected = set()
    for name, fn in jobs.items():
        for mode in ("dark", "light"):
            fname = f"{name}-{mode}.svg"
            expected.add(fname)
            path = os.path.join(OUT, fname)
            content = fn(mode)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            total += 1
    # 清掉不再生成的旧素材（比如仓库被删/改名后残留的项目卡），
    # 否则 assets/ 里会留下永远不会被引用的孤儿文件
    removed = []
    for f in sorted(os.listdir(OUT)):
        if f.endswith(".svg") and f not in expected:
            os.remove(os.path.join(OUT, f))
            removed.append(f)
    print(f"{total} files -> {OUT}")
    if removed:
        print(f"  清理孤儿素材 {len(removed)} 个: {', '.join(removed)}")


if __name__ == "__main__":
    main()
