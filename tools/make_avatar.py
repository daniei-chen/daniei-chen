# -*- coding: utf-8 -*-
"""生成深空极光风格头像（460x460 PNG，GitHub 头像规格）。

设计要点：
- 圆形安全区：GitHub 头像按圆形裁切，所有主体内容收在inscribed circle内。
- 深空底 + 极光三色晕染（青 / 紫 / 青绿）+ 星点 + 流光弧。
- 单色缩写渐变填充 + 外发光，浅色/深色 UI 下都清晰。
"""
from __future__ import annotations

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = H = 460          # 输出尺寸
SS = 4               # 超采样倍率
w, h = W * SS, H * SS

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 头像属于账号设置而非仓库内容，产物刻意写在仓库之外
OUT_DIR = os.path.join(os.path.dirname(_REPO), "out")

BG_TOP = np.array([6, 9, 18], dtype=np.float64)
BG_BOT = np.array([11, 23, 48], dtype=np.float64)

# (cx, cy, rx, ry, color, intensity) —— 归一化坐标
BLOBS = [
    (0.28, 0.22, 0.55, 0.55, (34, 211, 238), 0.90),   # 青
    (0.82, 0.30, 0.50, 0.52, (139, 92, 246), 0.95),   # 紫
    (0.60, 0.88, 0.65, 0.42, (124, 58, 237), 0.55),   # 底部深紫（避免发绿）
    (0.08, 0.78, 0.42, 0.38, (236, 72, 153), 0.30),   # 品红点缀
]

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\seguibl.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\msyhbd.ttc",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def base_gradient() -> np.ndarray:
    t = np.linspace(0.0, 1.0, h)[:, None, None]
    img = BG_TOP[None, None, :] * (1 - t) + BG_BOT[None, None, :] * t
    return np.repeat(img, w, axis=1)


def add_blobs(img: np.ndarray) -> np.ndarray:
    xs = np.arange(w)[None, :]
    ys = np.arange(h)[:, None]
    for cx, cy, rx, ry, color, intensity in BLOBS:
        px, py = cx * w, cy * h
        rrx, rry = rx * w, ry * h
        d = ((xs - px) / rrx) ** 2 + ((ys - py) / rry) ** 2
        falloff = np.clip(1.0 - d, 0.0, 1.0) ** 2.2
        img += np.array(color, dtype=np.float64)[None, None, :] * falloff[..., None] * intensity
    return img


def add_aurora_arc(img: np.ndarray) -> np.ndarray:
    """一条横向流光弧，模拟极光地平线。"""
    x = np.linspace(0, 1, w)
    for k, (base_y, amp, freq, phase, color, strength, thick) in enumerate([
        (0.58, 0.050, 1.6, 0.35, (103, 232, 249), 0.30, 0.075),
        (0.70, 0.065, 1.1, 1.90, (167, 139, 250), 0.24, 0.090),
    ]):
        yc = (base_y + amp * np.sin(freq * np.pi * x + phase)) * h
        band = np.exp(-(((np.arange(h)[:, None] - yc[None, :]) / (thick * h)) ** 2))
        img += np.array(color, dtype=np.float64)[None, None, :] * band[..., None] * strength
    return img


def add_stars(img: np.ndarray, count: int = 150, seed: int = 20260926) -> np.ndarray:
    rng = np.random.default_rng(seed)
    star = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(star)
    for _ in range(count):
        # 偏向圆内、上密下疏
        ang = rng.uniform(0, 2 * np.pi)
        rad = np.sqrt(rng.uniform(0, 1)) * 0.47
        px = (0.5 + rad * np.cos(ang)) * w
        py = (0.5 + rad * np.sin(ang) * 0.95) * h
        r = rng.uniform(0.8, 2.2) * SS
        a = int(rng.uniform(30, 200))
        d.ellipse([px - r, py - r, px + r, py + r], fill=a)
    star = star.filter(ImageFilter.GaussianBlur(0.9 * SS))
    s = np.asarray(star, dtype=np.float64)[..., None] / 255.0
    return img + s * np.array([235, 246, 255], dtype=np.float64)[None, None, :] * 0.75


def monogram_mask(text: str) -> Image.Image:
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    font = load_font(int(h * 0.44))
    # 以实际字形包围盒居中
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text(((w - (r - l)) / 2 - l, (h - (b - t)) / 2 - t), text, font=font, fill=255)
    return mask


def gradient_fill(mask: Image.Image) -> np.ndarray:
    """给字形填充 青→紫 的对角渐变。"""
    xs = np.linspace(0, 1, w)[None, :]
    ys = np.linspace(0, 1, h)[:, None]
    t = np.clip((xs * 0.55 + ys * 0.45), 0, 1)
    c1 = np.array([103, 232, 249], dtype=np.float64)
    c2 = np.array([192, 132, 252], dtype=np.float64)
    grad = c1[None, None, :] * (1 - t)[..., None] + c2[None, None, :] * t[..., None]
    m = np.asarray(mask, dtype=np.float64)[..., None] / 255.0
    return grad * m


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    img = base_gradient()
    img = add_blobs(img)
    img = add_aurora_arc(img)
    img = add_stars(img)

    # 圆形渐隐遮罩：边缘轻微压暗，强化"星球"感
    xs = np.arange(w)[None, :]
    ys = np.arange(h)[:, None]
    rr = np.sqrt(((xs - w / 2) / (w / 2)) ** 2 + ((ys - h / 2) / (h / 2)) ** 2)
    vignette = np.clip(1.15 - 0.55 * np.clip(rr, 0, 2) ** 2, 0.35, 1.0)
    img *= vignette[..., None]

    img = np.clip(img, 0, 255)

    # 字形 + 外发光
    mask = monogram_mask("DC")
    glow = np.asarray(mask.filter(ImageFilter.GaussianBlur(8 * SS)), dtype=np.float64)[..., None] / 255.0
    img = img + glow * np.array([120, 210, 255], dtype=np.float64)[None, None, :] * 0.42
    img = np.clip(img, 0, 255)
    img = img + gradient_fill(mask)
    img = np.clip(img, 0, 255)

    out = Image.fromarray(img.astype(np.uint8), "RGB").resize((W, H), Image.LANCZOS)
    path = os.path.join(OUT_DIR, "avatar-460.png")
    out.save(path, "PNG", optimize=True)
    print("saved:", path)

    # 预览：圆形裁切 + 真实尺寸
    preview = Image.new("RGB", (620, 340), (255, 255, 255))
    d = ImageDraw.Draw(preview)
    d.rectangle([0, 170, 620, 340], fill=(13, 17, 23))
    big = out.resize((200, 200), Image.LANCZOS)
    circ = Image.new("L", (200, 200), 0)
    ImageDraw.Draw(circ).ellipse([0, 0, 199, 199], fill=255)
    preview.paste(big, (40, 70), circ)
    small = out.resize((48, 48), Image.LANCZOS)
    sc = Image.new("L", (48, 48), 0)
    ImageDraw.Draw(sc).ellipse([0, 0, 47, 47], fill=255)
    preview.paste(small, (280, 40), sc)
    preview.paste(small, (280, 240), sc)
    d.text((360, 50), "48px  light UI", fill=(60, 60, 60))
    d.text((360, 250), "48px  dark UI", fill=(200, 200, 200))
    ppath = os.path.join(OUT_DIR, "avatar-preview.png")
    preview.save(ppath, "PNG")
    print("saved:", ppath)


if __name__ == "__main__":
    main()
