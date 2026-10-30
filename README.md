# wall-downloader

Przeglądarka i pobieranie **animowanych tapet z [MoeWalls](https://moewalls.com/)**. Aplikacja GTK3 w tym samym terminalowym stylu co [command-center](https://github.com/K-u-r-c/command-center): czarne, półprzezroczyste tło, ramki 1px, czcionka Nerd Font.

- wklejasz link do kategorii lub filtra MoeWalls albo do pojedynczej tapety, ewentualnie wpisujesz frazę do wyszukania,
- filtry: kategorie (ANIME, GAMES, PIXEL-ART, SCI-FI…), rozdzielczości (3440x1440 UW, 1920x1080, 2560x1440, 4K…) i sortowanie,
- **podgląd na żywo** (`mpv`) przed pobraniem,
- **Download & Set**: pobiera do `~/Pictures/wallpapers` i od razu ustawia tapetę na wybranym monitorze albo na wszystkich (lista monitorów z `hyprctl`).

> Część zestawu **[linux-tools](https://github.com/K-u-r-c/linux-tools)**.

## Instalacja

```bash
sudo pacman -S --needed python-gobject gtk3 mpv ffmpeg

git clone https://github.com/K-u-r-c/wall-downloader ~/.local/share/wall-downloader
mkdir -p ~/.local/bin && ln -sfn ~/.local/share/wall-downloader/wall_downloader.py ~/.local/bin/wall-downloader
```

Aktualizacja: `git -C ~/.local/share/wall-downloader pull`.

## Użycie

```bash
wall-downloader                                   # GUI (domyślnie: Anime, 3440x1440)
wall-downloader "https://moewalls.com/category/anime/page/6/?filter-by-taxonomies=resolutions&resolutions-terms=142"
wall-downloader --cli "https://moewalls.com/anime/rappa-honkai-star-rail-live-wallpaper/"   # bez GUI
```

## Współpraca

| Z czym | Jak |
|---|---|
| [hypr](https://github.com/K-u-r-c/hypr): `wallpaper.sh`, `primary-monitor.sh` | „Set wallpaper” woła `wallpaper.sh set <monitor> <plik>` (wideo przez mpvpaper); bez niego tapeta tylko się pobiera |
| [command-center](https://github.com/K-u-r-c/command-center) | pobrane tapety od razu widać w jego kafelku tapet: tapety 21:9 dostają prefiks `uw-`, a miniatura trafia do wspólnego `~/.cache/wallpaper-thumbs/` (generuje ją `ffmpeg`) |
