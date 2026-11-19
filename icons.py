"""Small inline SVG icons (24x24, stroke style) for headers and cards."""

_PATHS = {
    "overview": '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/>'
                '<rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>'
                '<path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M7 15l4-6 4 4 5-8"/>',
    "alert": '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
             '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "check": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
    "gauge": '<path d="M12 14l4-4"/><path d="M3.3 19a10 10 0 1 1 17.4 0"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>'
            '<path d="M8 13h8"/><path d="M8 17h8"/>',
    "sensor": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "flag": '<path d="M4 22V4"/><path d="M4 4h13l-2 4 2 4H4"/>',
    "plant": '<path d="M9 3h6"/><path d="M10 3v5l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3"/><path d="M7 15h10"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18"/><path d="M9 4v16"/>',
    "code": '<path d="M8 6l-6 6 6 6"/><path d="M16 6l6 6-6 6"/>',
    "list": '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    "timeline": '<path d="M3 6h10"/><path d="M7 12h12"/><path d="M5 18h8"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
}


def icon(name: str, size: int = 22, color: str = "#16324f", stroke: float = 1.9) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" '
            f'style="vertical-align:middle;flex-shrink:0">{_PATHS[name]}</svg>')


if __name__ == "__main__":  # preview sheet
    import sys
    names = list(_PATHS)
    cells = "".join(f'<g transform="translate({20 + (i % 6) * 110},{20 + (i // 6) * 90})">'
                    f'<g transform="scale(2)" fill="none" stroke="#16324f" stroke-width="1.9" stroke-linecap="round" '
                    f'stroke-linejoin="round">{_PATHS[n]}</g>'
                    f'<text x="24" y="70" font-size="12" text-anchor="middle" font-family="sans-serif">{n}</text></g>'
                    for i, n in enumerate(names))
    rows = (len(names) + 5) // 6
    open(sys.argv[1], "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="680" height="{rows * 90 + 30}">'
                                 f'<rect width="100%" height="100%" fill="white"/>{cells}</svg>')
