# MOEWALLS // WALLPAPER DOWNLOADER

Terminal-styled GTK3 HUD application for browsing, previewing, downloading, and applying animated wallpapers from [moewalls.com](https://moewalls.com/) directly into `~/Pictures/wallpapers`.

## Features
- **Command Center / Alacritty HUD aesthetic**: Translucent black background (`rgba(0, 0, 0, 0.94)`), sharp `1px` borders, `JetBrainsMono Nerd Font`, monochrome active states.
- **Direct MoeWalls Integration**:
  - Paste any MoeWalls category/filter URL (e.g. `https://moewalls.com/category/anime/page/6/?filter-by-taxonomies=resolutions&resolutions-terms=142`) or single wallpaper URL, or type a search query.
  - Built-in filters for Categories (`ANIME`, `GAMES`, `PIXEL-ART`, `SCI-FI`, etc.), Resolutions (`3440x1440 [UW]`, `1920x1080 [FHD]`, `2560x1440 [QHD]`, `3840x2160 [4K]`, etc.), and Sort Order.
- **Command Center Compatibility**:
  - Automatically prefixes `21:9` (`3440x1440`, `2560x1080`, `5120x1440`) wallpapers with `uw-` so `~/.config/hypr/command_center.py` and `~/.config/hypr/wallpaper.sh` recognize them as `[21:9]` ultrawide wallpapers.
  - Automatically generates the preview thumbnail in `~/.cache/wallpaper-thumbs/<filename>.png` via `ffmpeg`.
  - One-click **Download & Set Wallpaper** on `DP-1`, `HDMI-A-1`, or `ALL`.
  - **Live Preview (`mpv`)** streams the webm preview before downloading.

## Usage
```bash
# Open GUI (defaults to Anime 3440x1440)
~/Projects/wall-downloader/wall-downloader

# Open GUI at a specific MoeWalls URL
~/Projects/wall-downloader/wall-downloader "https://moewalls.com/category/anime/page/6/?filter-by-taxonomies=resolutions&resolutions-terms=142"

# CLI mode (list page or download single wallpaper URL)
~/Projects/wall-downloader/wall-downloader --cli "https://moewalls.com/anime/rappa-honkai-star-rail-live-wallpaper/"
```
