#!/usr/bin/env python3
"""
MOEWALLS DOWNLOADER // HUD TERMINAL EDITION
Stylized after Hyprland Command Center & Alacritty (black translucent HUD, sharp borders, JetBrainsMono Nerd Font).
Downloads animated wallpapers directly into ~/Pictures/wallpapers and generates thumbnails for Command Center.
"""

import html
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango

HOME = Path.home()
WALL_DIR = HOME / "Pictures/wallpapers"
THUMB_DIR = HOME / ".cache/wallpaper-thumbs"
REMOTE_THUMB_CACHE = HOME / ".cache/moewalls-thumbs"
WALL_SCRIPT = HOME / ".config/hypr/wallpaper.sh"
PRIMARY_MON_SCRIPT = HOME / ".config/hypr/primary-monitor.sh"

WALL_DIR.mkdir(parents=True, exist_ok=True)
THUMB_DIR.mkdir(parents=True, exist_ok=True)
REMOTE_THUMB_CACHE.mkdir(parents=True, exist_ok=True)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)
BASE_URL = "https://moewalls.com"
DOWNLOAD_ENDPOINT = "https://go.moewalls.com/download.php?video="

CATEGORIES: List[Tuple[str, str]] = [
    ("ALL", ""),
    ("ANIME", "anime"),
    ("GAMES", "games"),
    ("PIXEL-ART", "pixel-art"),
    ("SCI-FI", "sci-fi"),
    ("LANDSCAPE", "landscape"),
    ("FANTASY", "fantasy"),
    ("LIFESTYLE", "lifestyle"),
    ("MOVIES", "movies"),
    ("ABSTRACT", "abstract"),
    ("OTHERS", "others"),
]

# MoeWalls taxonomy term IDs for resolutions
RESOLUTIONS: List[Tuple[str, str, str]] = [
    ("3440x1440 [UW]", "3440x1440", "142"),
    ("1920x1080 [FHD]", "1920x1080", "33"),
    ("2560x1440 [QHD]", "2560x1440", "310"),
    ("3840x2160 [4K]", "3840x2160", "192"),
    ("2560x1080 [UW]", "2560x1080", "759"),
    ("5120x1440 [UW]", "5120x1440", "7085"),
    ("ALL RES", "", ""),
]

ORDERS: List[Tuple[str, str]] = [
    ("LATEST", "newest"),
    ("MOST UPVOTED", "most_upvotes"),
    ("MOST DISCUSSED", "most_commented"),
    ("OLDEST", "oldest"),
]

CSS = b"""
* {
    font-family: "JetBrainsMono Nerd Font", monospace;
    border-radius: 0;
    box-shadow: none;
    outline: none;
    text-shadow: none;
    -gtk-icon-shadow: none;
}

button {
    background-image: none;
}

selection,
entry selection,
label selection {
    background-color: #3a3a3a;
    color: #ffffff;
}

window#main-win {
    background-color: rgba(0, 0, 0, 0.94);
    color: #d8d8d8;
}

.root-frame {
    background-color: rgba(0, 0, 0, 0.94);
    border: 1px solid #444444;
    padding: 12px;
}

.hud-box {
    background-color: rgba(8, 8, 8, 0.96);
    border: 1px solid #333333;
    padding: 8px 12px;
}

.hud-title {
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
}

.hud-sub {
    color: #777777;
    font-size: 11px;
}

.hud-status {
    color: #ffffff;
    background-color: #121212;
    border: 1px solid #444444;
    padding: 4px 10px;
    font-size: 11px;
}

.tile-card {
    background-color: rgba(5, 5, 5, 0.95);
    border: 1px solid #333333;
}

.tile-header {
    background-color: #0d0d0d;
    border-bottom: 1px solid #333333;
    padding: 8px 12px;
}

.tile-title {
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
}

.tile-sub {
    color: #666666;
    font-size: 11px;
}

.section-label {
    color: #888888;
    font-size: 11px;
    font-weight: bold;
}

.mono-btn {
    background-image: none;
    background-color: #0d0d0d;
    color: #cccccc;
    border: 1px solid #3a3a3a;
    padding: 4px 9px;
    font-size: 11px;
}

.mono-btn label {
    color: #cccccc;
}

.mono-btn:hover {
    background-image: none;
    background-color: #222222;
    color: #ffffff;
    border: 1px solid #888888;
}

.mono-btn:hover label {
    color: #ffffff;
}

.mono-btn:disabled {
    background-image: none;
    background-color: #080808;
    color: #444444;
    border: 1px solid #222222;
}

.mono-btn:disabled label {
    color: #444444;
}

.mono-btn-active {
    background-image: none;
    background-color: #242424;
    color: #ffffff;
    border: 1px solid #ffffff;
    font-weight: bold;
    padding: 4px 9px;
    font-size: 11px;
}

.mono-btn-active label {
    color: #ffffff;
    font-weight: bold;
}

.action-btn-primary {
    background-image: none;
    background-color: #1f1f1f;
    color: #ffffff;
    border: 1px solid #ffffff;
    font-weight: bold;
    padding: 8px 12px;
    font-size: 12px;
}

.action-btn-primary label {
    color: #ffffff;
    font-weight: bold;
}

.action-btn-primary:hover {
    background-image: none;
    background-color: #303030;
    color: #ffffff;
    border: 1px solid #ffffff;
}

.action-btn-primary:disabled {
    background-image: none;
    background-color: #121212;
    color: #555555;
    border: 1px solid #333333;
}

.action-btn-primary:disabled label {
    color: #555555;
}

.item-row {
    background-color: transparent;
    border-left: 2px solid transparent;
    border-bottom: 1px solid #161616;
    padding: 6px 10px;
}

.item-row:hover {
    background-color: rgba(255, 255, 255, 0.04);
}

.item-row-selected {
    background-color: rgba(255, 255, 255, 0.12);
    border-left: 2px solid #ffffff;
    border-bottom: 1px solid #2a2a2a;
    padding: 6px 10px;
}

.item-row-selected .row-title {
    color: #ffffff;
}

.row-title {
    color: #e6e6e6;
    font-size: 12px;
    font-weight: bold;
}

.row-sub {
    color: #777777;
    font-size: 11px;
}

.badge-installed {
    color: #ffffff;
    background-color: #262626;
    border: 1px solid #ffffff;
    padding: 1px 5px;
    font-size: 10px;
    font-weight: bold;
}

.badge-uw {
    color: #ffffff;
    border: 1px solid #666666;
    padding: 1px 5px;
    font-size: 10px;
}

.preview-box {
    border: 1px solid #333333;
    background-color: #050505;
}

entry {
    background-color: #0a0a0a;
    color: #ffffff;
    caret-color: #ffffff;
    border: 1px solid #3a3a3a;
    padding: 5px 10px;
    font-size: 12px;
}

entry:focus {
    border: 1px solid #ffffff;
    background-color: #111111;
}

progressbar trough {
    background-color: #0d0d0d;
    border: 1px solid #333333;
    min-height: 10px;
}

progressbar progress {
    background-color: #ffffff;
    min-height: 10px;
}

scrollbar {
    background-color: #080808;
    border: none;
}

scrollbar slider {
    background-color: #333333;
    min-width: 6px;
    min-height: 24px;
}

scrollbar slider:hover {
    background-color: #666666;
}
"""


@dataclass
class MoeWallpaperItem:
    post_id: str
    title: str
    page_url: str
    thumb_url: str
    resolution: str = "1920x1080"
    category: str = "Anime"
    votes: str = "0"
    slug: str = ""
    preview_webm_url: str = ""
    data_url_token: str = ""

    @property
    def is_ultrawide(self) -> bool:
        m = re.match(r"^(\d+)x(\d+)$", self.resolution.strip())
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            return h > 0 and (w / h) >= 2.0
        return False

    @property
    def ratio_tag(self) -> str:
        return "21:9" if self.is_ultrawide else "16:9"

    def target_filename(self, force_uw_prefix: Optional[bool] = None) -> str:
        base = self.slug or self.page_url.rstrip("/").split("/")[-1]
        base = re.sub(r"-live-wallpaper$", "", base)
        base = re.sub(r"-moewalls-com$", "", base)
        base = re.sub(r"^uw-", "", base)
        use_uw = self.is_ultrawide if force_uw_prefix is None else force_uw_prefix
        prefix = "uw-" if use_uw else ""
        return f"{prefix}{base}.mp4"

    def installed_path(self) -> Optional[Path]:
        p1 = WALL_DIR / self.target_filename(True)
        p2 = WALL_DIR / self.target_filename(False)
        if p1.exists():
            return p1
        if p2.exists():
            return p2
        return None


def http_get(url: str, referer: str = BASE_URL, timeout: int = 20) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": referer,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def detect_monitors() -> List[Tuple[str, int, int]]:
    try:
        out = subprocess.check_output(["hyprctl", "monitors", "-j"], text=True, stderr=subprocess.DEVNULL)
        data = json.loads(out)
        mons = [(m["name"], int(m.get("width", 1920)), int(m.get("height", 1080))) for m in data if "name" in m]
        if PRIMARY_MON_SCRIPT.exists():
            prim = subprocess.check_output([str(PRIMARY_MON_SCRIPT)], text=True, stderr=subprocess.DEVNULL).strip()
            mons.sort(key=lambda x: 0 if x[0] == prim else 1)
        if mons:
            return mons
    except Exception:
        pass
    return [("DP-1", 3440, 1440), ("HDMI-A-1", 1920, 1080)]


def ensure_wallpaper_thumb(wp_path: Path) -> Optional[Path]:
    thumb = THUMB_DIR / f"{wp_path.name}.png"
    if not thumb.exists() or wp_path.stat().st_mtime > thumb.stat().st_mtime:
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-i",
                    str(wp_path),
                    "-vf",
                    "scale=160:90:force_original_aspect_ratio=increase,crop=160:90",
                    "-frames:v",
                    "1",
                    str(thumb),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                timeout=15,
            )
        except Exception:
            return None
    return thumb if thumb.exists() else None


def parse_moewalls_listing(html_text: str) -> Tuple[List[MoeWallpaperItem], int]:
    items: List[MoeWallpaperItem] = []
    articles = re.findall(r"<article\b.*?</article>", html_text, re.S | re.I)

    for art in articles:
        post_m = re.search(r"\bpost-(\d+)\b", art)
        post_id = post_m.group(1) if post_m else "0"

        link_m = re.search(
            r'<a[^>]+title=["\']([^"\']+)["\'][^>]+href=["\'](https://moewalls\.com/[^"\']+)["\']',
            art,
            re.I,
        )
        if not link_m:
            link_m = re.search(
                r'<h3[^>]*>\s*<a[^>]+href=["\'](https://moewalls\.com/[^"\']+)["\'][^>]*>(.*?)</a>',
                art,
                re.I | re.S,
            )
            if not link_m:
                continue
            page_url = link_m.group(1).strip()
            raw_title = re.sub(r"<[^>]+>", "", link_m.group(2)).strip()
        else:
            raw_title = link_m.group(1).strip()
            page_url = link_m.group(2).strip()

        title = html.unescape(raw_title)
        title = re.sub(r"\s+Live Wallpaper$", "", title, flags=re.I)

        img_m = re.search(r'<img[^>]+src=["\'](https://moewalls\.com/wp-content/uploads/[^"\']+)["\']', art, re.I)
        thumb_url = img_m.group(1).strip() if img_m else ""

        res_m = re.search(r'resolutions-(\d+x\d+)', art)
        if not res_m:
            res_m = re.search(r'/resolution/(\d+x\d+)/', art)
        resolution = res_m.group(1) if res_m else "1920x1080"

        cat_m = re.search(r'class=["\'][^"\']*entry-category[^"\']*["\'][^>]*>([^<]+)<', art)
        category = html.unescape(cat_m.group(1).strip()) if cat_m else "Anime"

        votes_m = re.search(r'class=["\'][^"\']*entry-votes[^"\']*["\'][^>]*>\s*<strong>(\d+)</strong>', art, re.S)
        votes = votes_m.group(1) if votes_m else "0"

        slug = page_url.rstrip("/").split("/")[-1]
        items.append(
            MoeWallpaperItem(
                post_id=post_id,
                title=title,
                page_url=page_url,
                thumb_url=thumb_url,
                resolution=resolution,
                category=category,
                votes=votes,
                slug=slug,
            )
        )

    # Extract max page number
    page_nums = [int(x) for x in re.findall(r'class=["\'][^"\']*page-numbers[^"\']*["\'][^>]*>(\d+)<', html_text)]
    max_page = max(page_nums) if page_nums else 1
    return items, max_page


def parse_moewalls_single_page(html_text: str, page_url: str) -> MoeWallpaperItem:
    title_m = re.search(r'<meta property="og:title" content="([^"]+)"', html_text)
    raw_title = html.unescape(title_m.group(1)) if title_m else page_url.rstrip("/").split("/")[-1]
    raw_title = re.sub(r"\s*-\s*MoeWalls.*$", "", raw_title, flags=re.I)
    raw_title = re.sub(r"\s+Live Wallpaper$", "", raw_title, flags=re.I)

    thumb_m = re.search(r'<meta property="og:image" content="([^"]+)"', html_text)
    thumb_url = thumb_m.group(1) if thumb_m else ""

    res_m = re.search(r'<div class="entry-resolutions">.*?/resolution/(\d+x\d+)/', html_text, re.S)
    if not res_m:
        res_m = re.search(r'resolutions-(\d+x\d+)', html_text)
    resolution = res_m.group(1) if res_m else "1920x1080"

    dl_m = re.search(
        r'id=["\']moe-download["\'][^>]*data-id\s*=\s*["\'](\d+)["\'][^>]*data-url=["\']([^"\']+)["\']',
        html_text,
        re.I,
    )
    if not dl_m:
        dl_m = re.search(r'data-url=["\']([^"\']+)["\']', html_text, re.I)
        post_id = "0"
        data_url = dl_m.group(1) if dl_m else ""
    else:
        post_id = dl_m.group(1)
        data_url = dl_m.group(2)

    webm_m = re.search(r'(/wp-content/uploads/preview/[^"\']+\.webm)', html_text, re.I)
    preview_webm = (BASE_URL + webm_m.group(1)) if webm_m else ""

    slug = page_url.rstrip("/").split("/")[-1]
    return MoeWallpaperItem(
        post_id=post_id,
        title=raw_title,
        page_url=page_url,
        thumb_url=thumb_url,
        resolution=resolution,
        slug=slug,
        preview_webm_url=preview_webm,
        data_url_token=data_url,
    )


class MoeWallsDownloaderApp(Gtk.Window):
    def __init__(self, initial_url: Optional[str] = None):
        super().__init__(title="MOEWALLS // WALLPAPER DOWNLOADER")
        self.set_name("main-win")
        self.set_default_size(1180, 780)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Enable RGBA visual for Alacritty / Command Center translucent background
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # State
        self.category_slug = "anime"
        self.res_slug = "3440x1440"
        self.res_term_id = "142"
        self.order_val = "newest"
        self.search_query = ""
        self.current_page = 1
        self.max_page = 1

        self.items: List[MoeWallpaperItem] = []
        self.selected_idx = 0
        self.is_loading = False
        self.is_downloading = False
        self.auto_uw_prefix = True

        self.monitors = detect_monitors()
        self.mon_names = [m[0] for m in self.monitors] + (["ALL"] if len(self.monitors) > 1 else [])
        self.selected_mon_idx = 0

        self.cat_btns: List[Tuple[str, Gtk.Button]] = []
        self.res_btns: List[Tuple[str, str, Gtk.Button]] = []
        self.order_btns: List[Tuple[str, Gtk.Button]] = []
        self.mon_btns: List[Gtk.Button] = []

        self._build_ui()
        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", Gtk.main_quit)

        if initial_url:
            self.url_entry.set_text(initial_url)
            self.handle_url_or_search(initial_url)
        else:
            self.sync_filter_buttons()
            self.fetch_listing()

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.get_style_context().add_class("root-frame")
        self.add(root)

        # 1. TOP HUD BAR
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top_bar.get_style_context().add_class("hud-box")

        title_lbl = Gtk.Label(label="MOEWALLS // TERMINAL DOWNLOADER")
        title_lbl.get_style_context().add_class("hud-title")
        top_bar.pack_start(title_lbl, False, False, 0)

        target_lbl = Gtk.Label(label=f"TARGET: {WALL_DIR}")
        target_lbl.get_style_context().add_class("hud-sub")
        top_bar.pack_start(target_lbl, False, False, 6)

        self.status_lbl = Gtk.Label(label="READY")
        self.status_lbl.get_style_context().add_class("hud-status")
        top_bar.pack_end(self.status_lbl, False, False, 0)

        help_lbl = Gtk.Label(label="[j/k] NAV  [Enter] DOWNLOAD  [p] PREVIEW  [h/l] PAGE  [/] URL/SEARCH  [q] QUIT")
        help_lbl.get_style_context().add_class("hud-sub")
        top_bar.pack_end(help_lbl, False, False, 8)

        root.pack_start(top_bar, False, False, 0)

        # 2. URL / SEARCH & FILTER BAR
        filter_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        filter_card.get_style_context().add_class("hud-box")

        # Row A: Search / Direct MoeWalls URL input
        url_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        url_tag = Gtk.Label(label="URL / SEARCH:")
        url_tag.get_style_context().add_class("section-label")
        url_row.pack_start(url_tag, False, False, 0)

        self.url_entry = Gtk.Entry()
        self.url_entry.set_placeholder_text(
            "Paste moewalls.com URL (e.g. .../category/anime/page/6/?...&resolutions-terms=142) or type search query..."
        )
        self.url_entry.connect("activate", lambda e: self.handle_url_or_search(e.get_text().strip()))
        url_row.pack_start(self.url_entry, True, True, 0)

        go_btn = Gtk.Button(label="LOAD / SEARCH")
        go_btn.get_style_context().add_class("mono-btn-active")
        go_btn.connect("clicked", lambda _: self.handle_url_or_search(self.url_entry.get_text().strip()))
        url_row.pack_start(go_btn, False, False, 0)

        clear_btn = Gtk.Button(label="RESET")
        clear_btn.get_style_context().add_class("mono-btn")
        clear_btn.connect("clicked", self.on_reset_filters)
        url_row.pack_start(clear_btn, False, False, 0)

        filter_card.pack_start(url_row, False, False, 0)

        # Row B: Categories
        cat_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        cat_lbl = Gtk.Label(label="CATEGORY:  ")
        cat_lbl.get_style_context().add_class("section-label")
        cat_row.pack_start(cat_lbl, False, False, 0)

        for label, slug in CATEGORIES:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("mono-btn")
            btn.connect("clicked", self.on_category_clicked, slug)
            cat_row.pack_start(btn, False, False, 0)
            self.cat_btns.append((slug, btn))

        filter_card.pack_start(cat_row, False, False, 0)

        # Row C: Resolutions + Sort Order
        res_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        res_lbl = Gtk.Label(label="RESOLUTION:")
        res_lbl.get_style_context().add_class("section-label")
        res_row.pack_start(res_lbl, False, False, 0)

        for label, r_slug, term_id in RESOLUTIONS:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("mono-btn")
            btn.connect("clicked", self.on_resolution_clicked, r_slug, term_id)
            res_row.pack_start(btn, False, False, 0)
            self.res_btns.append((r_slug, term_id, btn))

        # Order buttons on the right of Row C
        for label, ord_val in reversed(ORDERS):
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("mono-btn")
            btn.connect("clicked", self.on_order_clicked, ord_val)
            res_row.pack_end(btn, False, False, 0)
            self.order_btns.append((ord_val, btn))

        ord_lbl = Gtk.Label(label="SORT:")
        ord_lbl.get_style_context().add_class("section-label")
        res_row.pack_end(ord_lbl, False, False, 6)

        filter_card.pack_start(res_row, False, False, 0)
        root.pack_start(filter_card, False, False, 0)

        # 3. MAIN CONTENT SPLIT: LEFT LIST + RIGHT INSPECTOR
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # LEFT TILE: WALLPAPER LIST
        left_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left_card.get_style_context().add_class("tile-card")
        left_card.set_size_request(640, -1)

        left_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        left_hdr.get_style_context().add_class("tile-header")
        self.list_title_lbl = Gtk.Label(label="WALLPAPERS")
        self.list_title_lbl.get_style_context().add_class("tile-title")
        left_hdr.pack_start(self.list_title_lbl, False, False, 0)

        # Pagination controls in header
        self.next_btn = Gtk.Button(label="NEXT >>")
        self.next_btn.get_style_context().add_class("mono-btn")
        self.next_btn.connect("clicked", lambda _: self.change_page(self.current_page + 1))
        left_hdr.pack_end(self.next_btn, False, False, 0)

        self.page_entry = Gtk.Entry()
        self.page_entry.set_width_chars(4)
        self.page_entry.set_alignment(0.5)
        self.page_entry.set_text("1")
        self.page_entry.connect("activate", self.on_page_entry_activate)
        left_hdr.pack_end(self.page_entry, False, False, 0)

        self.page_total_lbl = Gtk.Label(label="/ 1")
        self.page_total_lbl.get_style_context().add_class("tile-sub")
        left_hdr.pack_end(self.page_total_lbl, False, False, 4)

        self.prev_btn = Gtk.Button(label="<< PREV")
        self.prev_btn.get_style_context().add_class("mono-btn")
        self.prev_btn.connect("clicked", lambda _: self.change_page(self.current_page - 1))
        left_hdr.pack_end(self.prev_btn, False, False, 4)

        left_card.pack_start(left_hdr, False, False, 0)

        self.list_scroll = Gtk.ScrolledWindow()
        self.list_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.list_box.set_margin_top(6)
        self.list_box.set_margin_bottom(6)
        self.list_box.set_margin_start(6)
        self.list_box.set_margin_end(6)
        self.list_scroll.add(self.list_box)
        left_card.pack_start(self.list_scroll, True, True, 0)

        content_box.pack_start(left_card, True, True, 0)

        # RIGHT TILE: INSPECTOR & DOWNLOAD / APPLY CONTROLS
        right_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right_card.get_style_context().add_class("tile-card")
        right_card.set_size_request(480, -1)

        right_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        right_hdr.get_style_context().add_class("tile-header")
        insp_title = Gtk.Label(label="INSPECTOR // DOWNLOAD & APPLY")
        insp_title.get_style_context().add_class("tile-title")
        right_hdr.pack_start(insp_title, False, False, 0)
        right_card.pack_start(right_hdr, False, False, 0)

        insp_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        insp_body.set_margin_top(12)
        insp_body.set_margin_bottom(12)
        insp_body.set_margin_start(12)
        insp_body.set_margin_end(12)

        # Large Preview Image
        self.preview_frame = Gtk.EventBox()
        self.preview_frame.get_style_context().add_class("preview-box")
        self.preview_frame.set_size_request(440, 248)
        self.preview_img = Gtk.Image()
        self.preview_frame.add(self.preview_img)
        insp_body.pack_start(self.preview_frame, False, False, 0)

        # Selected Title & Meta
        self.sel_title_lbl = Gtk.Label(label="Select a wallpaper")
        self.sel_title_lbl.get_style_context().add_class("hud-title")
        self.sel_title_lbl.set_xalign(0)
        self.sel_title_lbl.set_line_wrap(True)
        self.sel_title_lbl.set_max_width_chars(46)
        insp_body.pack_start(self.sel_title_lbl, False, False, 0)

        self.sel_meta_lbl = Gtk.Label(label="—")
        self.sel_meta_lbl.get_style_context().add_class("row-sub")
        self.sel_meta_lbl.set_xalign(0)
        insp_body.pack_start(self.sel_meta_lbl, False, False, 0)

        # Target Filename Editor + uw- prefix toggle
        fname_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fname_lbl = Gtk.Label(label="SAVE FILENAME (in ~/Pictures/wallpapers):")
        fname_lbl.get_style_context().add_class("section-label")
        fname_lbl.set_xalign(0)
        fname_hdr.pack_start(fname_lbl, True, True, 0)

        self.uw_toggle_btn = Gtk.Button(label="[x] AUTO uw- (21:9)")
        self.uw_toggle_btn.get_style_context().add_class("mono-btn-active")
        self.uw_toggle_btn.connect("clicked", self.on_toggle_uw_prefix)
        fname_hdr.pack_end(self.uw_toggle_btn, False, False, 0)
        insp_body.pack_start(fname_hdr, False, False, 0)

        self.filename_entry = Gtk.Entry()
        insp_body.pack_start(self.filename_entry, False, False, 0)

        # Progress bar & transfer stats
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        insp_body.pack_start(self.progress_bar, False, False, 0)

        self.progress_lbl = Gtk.Label(label="IDLE")
        self.progress_lbl.get_style_context().add_class("row-sub")
        self.progress_lbl.set_xalign(0)
        insp_body.pack_start(self.progress_lbl, False, False, 0)

        # Monitor Selector for Apply
        mon_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mon_lbl = Gtk.Label(label="TARGET MONITOR:")
        mon_lbl.get_style_context().add_class("section-label")
        mon_row.pack_start(mon_lbl, False, False, 0)

        for idx, mname in enumerate(self.mon_names):
            b = Gtk.Button(label=mname)
            b.connect("clicked", self.on_select_monitor, idx)
            mon_row.pack_start(b, False, False, 0)
            self.mon_btns.append(b)
        self._sync_mon_buttons()
        insp_body.pack_start(mon_row, False, False, 0)

        # Action Buttons
        self.dl_btn = Gtk.Button(label="[ ENTER ] DOWNLOAD TO WALLPAPERS")
        self.dl_btn.get_style_context().add_class("action-btn-primary")
        self.dl_btn.connect("clicked", lambda _: self.start_download(apply_after=False))
        insp_body.pack_start(self.dl_btn, False, False, 0)

        self.dl_apply_btn = Gtk.Button(label="DOWNLOAD & SET WALLPAPER NOW")
        self.dl_apply_btn.get_style_context().add_class("mono-btn")
        self.dl_apply_btn.connect("clicked", lambda _: self.start_download(apply_after=True))
        insp_body.pack_start(self.dl_apply_btn, False, False, 0)

        sec_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.preview_mpv_btn = Gtk.Button(label="[ P ] LIVE PREVIEW (MPV)")
        self.preview_mpv_btn.get_style_context().add_class("mono-btn")
        self.preview_mpv_btn.connect("clicked", lambda _: self.preview_in_mpv())
        sec_actions.pack_start(self.preview_mpv_btn, True, True, 0)

        self.apply_existing_btn = Gtk.Button(label="APPLY INSTALLED")
        self.apply_existing_btn.get_style_context().add_class("mono-btn")
        self.apply_existing_btn.connect("clicked", lambda _: self.apply_installed_wallpaper())
        sec_actions.pack_start(self.apply_existing_btn, True, True, 0)

        self.delete_btn = Gtk.Button(label="DELETE")
        self.delete_btn.get_style_context().add_class("mono-btn")
        self.delete_btn.connect("clicked", lambda _: self.delete_installed_wallpaper())
        sec_actions.pack_start(self.delete_btn, False, False, 0)

        insp_body.pack_start(sec_actions, False, False, 0)

        right_card.pack_start(insp_body, True, True, 0)
        content_box.pack_start(right_card, False, False, 0)

        root.pack_start(content_box, True, True, 0)

    # ---------------- UI HELPERS ----------------
    def set_status(self, text: str):
        GLib.idle_add(self.status_lbl.set_text, text)

    def _sync_mon_buttons(self):
        for idx, b in enumerate(self.mon_btns):
            ctx = b.get_style_context()
            ctx.remove_class("mono-btn")
            ctx.remove_class("mono-btn-active")
            ctx.add_class("mono-btn-active" if idx == self.selected_mon_idx else "mono-btn")

    def on_select_monitor(self, _btn, idx: int):
        self.selected_mon_idx = idx % len(self.mon_names)
        self._sync_mon_buttons()

    def on_toggle_uw_prefix(self, _btn):
        self.auto_uw_prefix = not self.auto_uw_prefix
        ctx = self.uw_toggle_btn.get_style_context()
        ctx.remove_class("mono-btn")
        ctx.remove_class("mono-btn-active")
        if self.auto_uw_prefix:
            self.uw_toggle_btn.set_label("[x] AUTO uw- (21:9)")
            ctx.add_class("mono-btn-active")
        else:
            self.uw_toggle_btn.set_label("[ ] AUTO uw- (21:9)")
            ctx.add_class("mono-btn")
        self.update_inspector()

    def sync_filter_buttons(self):
        for slug, btn in self.cat_btns:
            ctx = btn.get_style_context()
            ctx.remove_class("mono-btn")
            ctx.remove_class("mono-btn-active")
            ctx.add_class("mono-btn-active" if slug == self.category_slug and not self.search_query else "mono-btn")

        for r_slug, term_id, btn in self.res_btns:
            ctx = btn.get_style_context()
            ctx.remove_class("mono-btn")
            ctx.remove_class("mono-btn-active")
            active = (r_slug == self.res_slug) or (term_id and term_id == self.res_term_id)
            ctx.add_class("mono-btn-active" if active else "mono-btn")

        for ord_val, btn in self.order_btns:
            ctx = btn.get_style_context()
            ctx.remove_class("mono-btn")
            ctx.remove_class("mono-btn-active")
            ctx.add_class("mono-btn-active" if ord_val == self.order_val else "mono-btn")

    # ---------------- URL & FILTER HANDLING ----------------
    def build_current_url(self) -> str:
        if self.search_query:
            q = urllib.parse.quote_plus(self.search_query)
            if self.current_page > 1:
                return f"{BASE_URL}/page/{self.current_page}/?s={q}"
            return f"{BASE_URL}/?s={q}"

        # Category + Resolution
        if self.category_slug:
            path = f"/category/{self.category_slug}/"
            if self.current_page > 1:
                path += f"page/{self.current_page}/"
            params = []
            if self.res_term_id:
                params.append("filter-by-taxonomies=resolutions")
                params.append(f"resolutions-terms={self.res_term_id}")
            if self.order_val and self.order_val != "newest":
                params.append(f"order={self.order_val}")
            qstr = ("?" + "&".join(params)) if params else ""
            return BASE_URL + path + qstr
        else:
            # ALL categories
            if self.res_slug:
                path = f"/resolution/{self.res_slug}/"
            else:
                path = "/"
            if self.current_page > 1:
                path += f"page/{self.current_page}/"
            params = []
            if self.order_val and self.order_val != "newest":
                params.append(f"order={self.order_val}")
            qstr = ("?" + "&".join(params)) if params else ""
            return BASE_URL + path + qstr

    def handle_url_or_search(self, text: str):
        if not text:
            self.search_query = ""
            self.current_page = 1
            self.sync_filter_buttons()
            self.fetch_listing()
            return

        if text.startswith("http://") or text.startswith("https://") or "moewalls.com" in text:
            if not text.startswith("http"):
                text = "https://" + text
            parsed = urllib.parse.urlparse(text)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            # Check if it's a listing URL or single wallpaper URL
            is_listing = (
                "/category/" in path
                or "/resolution/" in path
                or "/tag/" in path
                or path in ("/", "")
                or path.startswith("/page/")
                or "s" in qs
            )

            if is_listing:
                self.search_query = qs.get("s", [""])[0]
                m_cat = re.search(r"/category/([^/]+)", path)
                self.category_slug = m_cat.group(1) if m_cat else ""

                m_page = re.search(r"/page/(\d+)", path)
                self.current_page = int(m_page.group(1)) if m_page else 1

                m_res = re.search(r"/resolution/(\d+x\d+)", path)
                term_id = qs.get("resolutions-terms", [""])[0]
                if term_id:
                    self.res_term_id = term_id
                    self.res_slug = next((r for _, r, t in RESOLUTIONS if t == term_id), "")
                elif m_res:
                    self.res_slug = m_res.group(1)
                    self.res_term_id = next((t for _, r, t in RESOLUTIONS if r == self.res_slug), "")
                else:
                    self.res_slug = ""
                    self.res_term_id = ""

                self.order_val = qs.get("order", ["newest"])[0]
                self.sync_filter_buttons()
                self.fetch_listing(direct_url=text)
            else:
                # Single wallpaper page URL!
                self.fetch_single_wallpaper_url(text)
        else:
            # Search query
            self.search_query = text
            self.current_page = 1
            self.sync_filter_buttons()
            self.fetch_listing()

    def on_reset_filters(self, _btn):
        self.search_query = ""
        self.category_slug = "anime"
        self.res_slug = "3440x1440"
        self.res_term_id = "142"
        self.order_val = "newest"
        self.current_page = 1
        self.url_entry.set_text("")
        self.sync_filter_buttons()
        self.fetch_listing()

    def on_category_clicked(self, _btn, slug: str):
        self.search_query = ""
        self.category_slug = slug
        self.current_page = 1
        self.sync_filter_buttons()
        self.fetch_listing()

    def on_resolution_clicked(self, _btn, r_slug: str, term_id: str):
        self.res_slug = r_slug
        self.res_term_id = term_id
        self.current_page = 1
        self.sync_filter_buttons()
        self.fetch_listing()

    def on_order_clicked(self, _btn, ord_val: str):
        self.order_val = ord_val
        self.current_page = 1
        self.sync_filter_buttons()
        self.fetch_listing()

    def change_page(self, new_page: int):
        if new_page < 1 or new_page > self.max_page or self.is_loading:
            return
        self.current_page = new_page
        self.fetch_listing()

    def on_page_entry_activate(self, entry: Gtk.Entry):
        try:
            p = int(entry.get_text().strip())
            self.change_page(max(1, min(self.max_page, p)))
        except ValueError:
            entry.set_text(str(self.current_page))

    # ---------------- NETWORK FETCHING ----------------
    def fetch_listing(self, direct_url: Optional[str] = None):
        if self.is_loading:
            return
        self.is_loading = True
        url = direct_url or self.build_current_url()
        self.url_entry.set_text(url)
        self.set_status(f"FETCHING PAGE {self.current_page}...")

        def worker():
            try:
                raw = http_get(url).decode("utf-8", "ignore")
                items, max_p = parse_moewalls_listing(raw)
                # If searching with a specific resolution selected, sort matching resolutions first
                if self.search_query and self.res_slug:
                    items.sort(key=lambda x: 0 if x.resolution == self.res_slug else 1)
                GLib.idle_add(self._on_listing_loaded, items, max_p, None)
            except Exception as exc:
                GLib.idle_add(self._on_listing_loaded, [], 1, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def fetch_single_wallpaper_url(self, page_url: str):
        if self.is_loading:
            return
        self.is_loading = True
        self.set_status("FETCHING WALLPAPER PAGE...")

        def worker():
            try:
                raw = http_get(page_url).decode("utf-8", "ignore")
                item = parse_moewalls_single_page(raw, page_url)
                GLib.idle_add(self._on_listing_loaded, [item], 1, None)
            except Exception as exc:
                GLib.idle_add(self._on_listing_loaded, [], 1, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_listing_loaded(self, items: List[MoeWallpaperItem], max_p: int, err: Optional[str]):
        self.is_loading = False
        if err:
            self.set_status(f"ERROR: {err[:45]}")
            return

        self.items = items
        self.max_page = max(1, max_p)
        self.selected_idx = 0
        self.page_entry.set_text(str(self.current_page))
        self.page_total_lbl.set_text(f"/ {self.max_page}")
        self.prev_btn.set_sensitive(self.current_page > 1)
        self.next_btn.set_sensitive(self.current_page < self.max_page)

        cat_name = (self.category_slug or "ALL").upper()
        res_name = self.res_slug or "ALL-RES"
        if self.search_query:
            self.list_title_lbl.set_text(f"SEARCH: '{self.search_query.upper()}' ({len(items)})")
        else:
            self.list_title_lbl.set_text(f"{cat_name} // {res_name} ({len(items)} ITEMS)")

        self.set_status(f"LOADED {len(items)} WALLPAPERS (PAGE {self.current_page}/{self.max_page})")
        self.rebuild_list_ui()
        self.update_inspector()

    def rebuild_list_ui(self):
        for child in self.list_box.get_children():
            self.list_box.remove(child)

        for idx, item in enumerate(self.items):
            ev = Gtk.EventBox()
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.get_style_context().add_class(
                "item-row-selected" if idx == self.selected_idx else "item-row"
            )
            ev.add(row)

            # Thumbnail image widget
            img = Gtk.Image()
            img.set_size_request(128, 72)
            img.get_style_context().add_class("preview-box")
            row.pack_start(img, False, False, 0)
            self._load_thumb_async(item, img, 128, 72)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            top_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            inst_path = item.installed_path()
            if inst_path:
                b_inst = Gtk.Label(label="INSTALLED")
                b_inst.get_style_context().add_class("badge-installed")
                top_line.pack_start(b_inst, False, False, 0)

            lbl = Gtk.Label(label=item.title)
            lbl.get_style_context().add_class("row-title")
            lbl.set_xalign(0)
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            top_line.pack_start(lbl, True, True, 0)
            vbox.pack_start(top_line, False, False, 0)

            sub_text = f"[{item.resolution} • {item.ratio_tag}]  •  {item.category.upper()}  •  ▲ {item.votes}"
            if inst_path:
                sub_text += f"  •  {inst_path.name}"
            sub = Gtk.Label(label=sub_text)
            sub.get_style_context().add_class("row-sub")
            sub.set_xalign(0)
            vbox.pack_start(sub, False, False, 0)

            row.pack_start(vbox, True, True, 0)
            ev.connect("button-press-event", self.on_row_clicked, idx)
            self.list_box.pack_start(ev, False, False, 0)

        self.list_box.show_all()
        self._scroll_selected_into_view()

    def _scroll_selected_into_view(self):
        children = self.list_box.get_children()
        if not children or not (0 <= self.selected_idx < len(children)):
            return

        def _do():
            adj = self.list_scroll.get_vadjustment()
            if not adj:
                return False
            row = children[self.selected_idx]
            alloc = row.get_allocation()
            if alloc.height <= 1:
                return False
            top = alloc.y
            bot = alloc.y + alloc.height
            page = adj.get_page_size()
            cur = adj.get_value()
            if top < cur:
                adj.set_value(top)
            elif bot > cur + page:
                adj.set_value(bot - page)
            return False

        GLib.idle_add(_do)

    def _load_thumb_async(self, item: MoeWallpaperItem, img_widget: Gtk.Image, w: int, h: int):
        if not item.thumb_url:
            return
        cache_file = REMOTE_THUMB_CACHE / f"{item.slug or item.post_id}.jpg"

        def apply_pb(path: Path):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), w, h, True)
                img_widget.set_from_pixbuf(pb)
            except Exception:
                pass
            return False

        if cache_file.exists():
            apply_pb(cache_file)
            return

        def worker():
            try:
                data = http_get(item.thumb_url, timeout=15)
                cache_file.write_bytes(data)
                GLib.idle_add(apply_pb, cache_file)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def on_row_clicked(self, _widget, event, idx: int):
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            self.selected_idx = idx
            self.update_selection_styles()
            self.update_inspector()
            self.start_download(apply_after=False)
            return True
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return True
        self.selected_idx = idx
        self.update_selection_styles()
        self.update_inspector()
        return True

    def update_selection_styles(self):
        for idx, child in enumerate(self.list_box.get_children()):
            row = child.get_child()
            if not row:
                continue
            ctx = row.get_style_context()
            ctx.remove_class("item-row")
            ctx.remove_class("item-row-selected")
            ctx.add_class("item-row-selected" if idx == self.selected_idx else "item-row")
        self._scroll_selected_into_view()

    def update_inspector(self):
        if not self.items or not (0 <= self.selected_idx < len(self.items)):
            self.sel_title_lbl.set_text("No wallpaper selected")
            self.sel_meta_lbl.set_text("—")
            self.filename_entry.set_text("")
            self.apply_existing_btn.set_sensitive(False)
            self.delete_btn.set_sensitive(False)
            return

        item = self.items[self.selected_idx]
        self.sel_title_lbl.set_text(item.title)
        inst = item.installed_path()
        status_tag = f"INSTALLED ({inst.name})" if inst else "NOT INSTALLED"
        self.sel_meta_lbl.set_text(
            f"RES: {item.resolution} [{item.ratio_tag}]  •  CAT: {item.category.upper()}  •  {status_tag}"
        )

        use_uw = item.is_ultrawide if self.auto_uw_prefix else False
        self.filename_entry.set_text(item.target_filename(force_uw_prefix=use_uw))

        self.apply_existing_btn.set_sensitive(inst is not None)
        self.delete_btn.set_sensitive(inst is not None)

        self._load_thumb_async(item, self.preview_img, 440, 248)

    # ---------------- DOWNLOAD / PREVIEW / APPLY ----------------
    def resolve_item_details(self, item: MoeWallpaperItem) -> MoeWallpaperItem:
        if item.data_url_token and item.preview_webm_url:
            return item
        raw = http_get(item.page_url).decode("utf-8", "ignore")
        parsed = parse_moewalls_single_page(raw, item.page_url)
        item.data_url_token = parsed.data_url_token
        item.preview_webm_url = parsed.preview_webm_url
        if parsed.resolution:
            item.resolution = parsed.resolution
        return item

    def start_download(self, apply_after: bool = False):
        if self.is_downloading or not self.items:
            return
        item = self.items[self.selected_idx]
        fname = self.filename_entry.get_text().strip() or item.target_filename(
            force_uw_prefix=(item.is_ultrawide if self.auto_uw_prefix else False)
        )
        if not fname.lower().endswith(".mp4"):
            fname += ".mp4"
        dest_path = WALL_DIR / fname
        tmp_path = WALL_DIR / f".{fname}.part"

        self.is_downloading = True
        self.dl_btn.set_sensitive(False)
        self.dl_apply_btn.set_sensitive(False)
        self.progress_bar.set_fraction(0.0)
        self.progress_lbl.set_text(f"RESOLVING DOWNLOAD TOKEN FOR {fname}...")
        self.set_status(f"DOWNLOADING: {fname}")

        def worker():
            try:
                self.resolve_item_details(item)
                if not item.data_url_token:
                    raise RuntimeError("Could not find moe-download data-url token on page")

                dl_url = DOWNLOAD_ENDPOINT + item.data_url_token
                req = urllib.request.Request(
                    dl_url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Referer": item.page_url,
                    },
                )
                t0 = time.time()
                with urllib.request.urlopen(req, timeout=60) as resp:
                    total = int(resp.headers.get("Content-Length", "0") or 0)
                    downloaded = 0
                    with open(tmp_path, "wb") as f:
                        while True:
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            elapsed = max(0.001, time.time() - t0)
                            speed_mb = (downloaded / (1024 * 1024)) / elapsed
                            frac = (downloaded / total) if total > 0 else 0.0
                            mb_done = downloaded / (1024 * 1024)
                            mb_tot = total / (1024 * 1024)
                            GLib.idle_add(
                                self._update_dl_progress,
                                frac,
                                f"{mb_done:.1f} / {mb_tot:.1f} MB ({frac*100:.0f}%)  •  {speed_mb:.1f} MB/s",
                            )

                tmp_path.replace(dest_path)
                GLib.idle_add(
                    self._update_dl_progress,
                    1.0,
                    f"GENERATING THUMBNAIL FOR COMMAND CENTER...",
                )
                ensure_wallpaper_thumb(dest_path)
                GLib.idle_add(self._on_download_finished, dest_path, apply_after, None)
            except Exception as exc:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass
                GLib.idle_add(self._on_download_finished, dest_path, False, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _update_dl_progress(self, frac: float, text: str):
        self.progress_bar.set_fraction(max(0.0, min(1.0, frac)))
        self.progress_lbl.set_text(text)
        return False

    def _on_download_finished(self, dest_path: Path, apply_after: bool, err: Optional[str]):
        self.is_downloading = False
        self.dl_btn.set_sensitive(True)
        self.dl_apply_btn.set_sensitive(True)

        if err:
            self.progress_lbl.set_text(f"ERROR: {err}")
            self.set_status("DOWNLOAD FAILED")
            return

        self.progress_bar.set_fraction(1.0)
        self.progress_lbl.set_text(f"SAVED: {dest_path.name} (+ THUMBNAIL READY)")
        self.set_status(f"SAVED TO WALLPAPERS: {dest_path.name}")
        self.rebuild_list_ui()
        self.update_inspector()

        if apply_after:
            self.apply_wallpaper_path(dest_path)

    def apply_wallpaper_path(self, wp_path: Path):
        if not wp_path.exists():
            return
        target_mon = self.mon_names[self.selected_mon_idx]
        if WALL_SCRIPT.exists():
            subprocess.Popen([str(WALL_SCRIPT), "set", target_mon, str(wp_path)])
            self.set_status(f"APPLIED ON {target_mon}: {wp_path.name}")
        else:
            self.set_status("ERROR: ~/.config/hypr/wallpaper.sh NOT FOUND")

    def apply_installed_wallpaper(self):
        if not self.items:
            return
        inst = self.items[self.selected_idx].installed_path()
        if inst:
            ensure_wallpaper_thumb(inst)
            self.apply_wallpaper_path(inst)

    def delete_installed_wallpaper(self):
        if not self.items:
            return
        inst = self.items[self.selected_idx].installed_path()
        if inst and inst.exists():
            try:
                thumb = THUMB_DIR / f"{inst.name}.png"
                inst.unlink()
                if thumb.exists():
                    thumb.unlink()
                self.set_status(f"DELETED: {inst.name}")
                self.rebuild_list_ui()
                self.update_inspector()
            except Exception as exc:
                self.set_status(f"DELETE ERROR: {exc}")

    def preview_in_mpv(self):
        if not self.items:
            return
        item = self.items[self.selected_idx]
        inst = item.installed_path()
        if inst and inst.exists():
            subprocess.Popen(
                ["mpv", "--loop-file=inf", "--no-audio", f"--title=PREVIEW // {item.title}", str(inst)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.set_status(f"PREVIEWING LOCAL: {inst.name}")
            return

        self.set_status("RESOLVING PREVIEW STREAM...")

        def worker():
            try:
                self.resolve_item_details(item)
                if item.preview_webm_url:
                    subprocess.Popen(
                        [
                            "mpv",
                            "--loop-file=inf",
                            "--no-audio",
                            f"--user-agent={USER_AGENT}",
                            f"--referrer={item.page_url}",
                            f"--title=PREVIEW // {item.title}",
                            item.preview_webm_url,
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.set_status(f"STREAMING PREVIEW: {item.title[:30]}")
                else:
                    self.set_status("NO PREVIEW STREAM FOUND")
            except Exception as exc:
                self.set_status(f"PREVIEW ERROR: {str(exc)[:35]}")

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- KEYBOARD NAVIGATION ----------------
    def on_key_press(self, _widget, event):
        key = Gdk.keyval_name(event.keyval)
        focus = self.get_focus()
        in_entry = isinstance(focus, Gtk.Entry)

        if key == "Escape":
            if in_entry:
                self.set_focus(None)
                return True
            Gtk.main_quit()
            return True

        if in_entry:
            return False

        if key in ("q", "Q"):
            Gtk.main_quit()
            return True
        if key == "slash":
            self.url_entry.grab_focus()
            return True
        if key in ("j", "J", "Down"):
            if self.items:
                self.selected_idx = (self.selected_idx + 1) % len(self.items)
                self.update_selection_styles()
                self.update_inspector()
            return True
        if key in ("k", "K", "Up"):
            if self.items:
                self.selected_idx = (self.selected_idx - 1) % len(self.items)
                self.update_selection_styles()
                self.update_inspector()
            return True
        if key in ("h", "H", "bracketleft", "Left"):
            self.change_page(self.current_page - 1)
            return True
        if key in ("l", "L", "bracketright", "Right"):
            self.change_page(self.current_page + 1)
            return True
        if key in ("Return", "KP_Enter"):
            self.start_download(apply_after=False)
            return True
        if key in ("a", "A"):
            inst = self.items[self.selected_idx].installed_path() if self.items else None
            if inst:
                self.apply_installed_wallpaper()
            else:
                self.start_download(apply_after=True)
            return True
        if key in ("p", "P", "space"):
            self.preview_in_mpv()
            return True
        if key in ("m", "M", "Tab"):
            self.selected_mon_idx = (self.selected_mon_idx + 1) % len(self.mon_names)
            self._sync_mon_buttons()
            return True
        return False


def cli_download(url: str):
    print(f"[*] Fetching {url} ...")
    raw = http_get(url).decode("utf-8", "ignore")
    if "/category/" in url or "/resolution/" in url or "?s=" in url:
        items, max_p = parse_moewalls_listing(raw)
        print(f"[*] Found {len(items)} items on page (total pages: {max_p}):")
        for i, it in enumerate(items, 1):
            print(f"  {i:2d}. [{it.resolution}] {it.title} -> {it.page_url}")
        return

    item = parse_moewalls_single_page(raw, url)
    if not item.data_url_token:
        print("[!] Error: Could not extract download token from page.")
        sys.exit(1)

    fname = item.target_filename()
    dest = WALL_DIR / fname
    dl_url = DOWNLOAD_ENDPOINT + item.data_url_token
    print(f"[*] Downloading '{item.title}' ({item.resolution}) -> {dest}")
    req = urllib.request.Request(dl_url, headers={"User-Agent": USER_AGENT, "Referer": url})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    ensure_wallpaper_thumb(dest)
    print(f"[+] Done! Saved to {dest} and generated Command Center thumbnail.")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--cli":
        cli_download(sys.argv[2])
        sys.exit(0)

    init_url = sys.argv[1] if len(sys.argv) >= 2 else None
    app = MoeWallsDownloaderApp(initial_url=init_url)
    app.show_all()
    app.set_focus(None)
    Gtk.main()
