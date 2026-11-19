"""Plant diagram for the Overview page, drawn as an SVG string.

Equipment codes are taken from the dataset README and the YAML annotations.
"""
from __future__ import annotations

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
VAP, LIQ, COOL, REF, DIST, GREY = "#e8833a", "#2f6fb0", "#36a3d9", "#2a9d5c", "#7b4fb8", "#6b7280"

# step key -> (code shown on the button, title, plain explanation, sensors)
STEPS = {
    "V001": ("V001 – Reboiler", "Heating and evaporation",
             "The mixture is heated in reboiler vessel <b>V001</b> by heater <b>H701</b> and partially evaporates. "
             "The more volatile components evaporate preferentially.",
             ["T703"]),
    "C001": ("C001–C003 – Column", "Separation",
             "The vapour rises through column sections <b>C001</b>, <b>C002</b> and <b>C003</b> and is in contact with the "
             "liquid flowing downwards. The vapour is enriched in the more volatile component towards the top; "
             "temperatures generally decrease from bottom to top.",
             ["T709", "T711", "T712", "T705", "PDI701"]),
    "G001": ("G001 – Pressure control", "Operation below atmospheric pressure",
             "The top vessel <b>G001</b> is connected to vacuum pump <b>P301</b>. Throttle valve <b>TV1</b> controls the "
             "pressure to the set-point of the operating point (about 300–700 mbar). A lower pressure lowers the boiling temperatures.",
             ["PY23"]),
    "HE001": ("HE001/HE002 – Condensers", "Condensation",
              "The vapour is condensed in <b>HE001/HE002</b>, which are supplied with cooling water by thermostat <b>TCU1</b>.",
              ["FYI702"]),
    "V002": ("V002 – Buffer vessel", "Collection of the condensate",
             "The condensate is collected in buffer vessel <b>V002</b>. Pumps P701 and P702 are controlled to keep the pressure "
             "difference PDI702 (liquid level) at its set-point of 2 mbar.",
             ["PDI702"]),
    "P701": ("P701/P702 – Pumps", "Reflux and distillate withdrawal",
             "Pump <b>P701</b> returns part of the condensate to the column as <b>reflux</b>; pump <b>P702</b> withdraws the "
             "remainder as <b>distillate</b> into the distillate receiver.",
             ["FT704", "FT703"]),
}

DISTURB = [  # x, y, label, tooltip, label side (tooltips follow the YAML annotations)
    (168, 598, "OP10", "OP10: nitrogen injection at 5 NL/h into reboiler V001 via valve HV009", "left"),
    (395, 572, "OP18", "OP18: nitrogen injection at 30-50 NL/h below column section C001 via valve HV001", "right"),
    (540, 262, "OP17 · OP22", "OP17/OP22: sample withdrawal from the reflux line at valve HV004; air ingress at improperly "
                              "sealed sample valves HV004/HV005 (spikes in FT703/FT704)", "above"),
    (840, 128, "OP31", "OP31: thermostat TCU1 switched off, reducing the cooling-water supply", "below"),
    (150, 62, "OP29", "OP29: combined set-point changes: heater H701 power 210 to 157.5 W, pressure set-point 550 to 500 mbar (TV1), "
                       "distillate pump P702 off, PDI702 set-point 2 to 1 mbar", "below"),
]
SENSOR_POS = {  # where each sensor tag is drawn: x, y, side of the label
    "T703": (300, 690, "right"), "T709": (300, 575, "left"), "T711": (300, 420, "left"), "T712": (300, 270, "left"),
    "T705": (300, 122, "left"), "PDI701": (110, 340, "right"), "PY23": (350, 50, "pyright"),
    "FYI702": (800, 58, "below"), "PDI702": (680, 255, "right"), "FT704": (470, 196, "right"), "FT703": (680, 380, "right"),
}
SENSOR_COLOR = {"T": "#c8553d", "F": "#2a78b5", "P": "#7b4fb8"}


def _t(x, y, s, size=14, color="#1f2933", anchor="middle", weight="normal", opacity=1.0):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}" opacity="{opacity}">{s}</text>')


def _arrow_defs():
    out = "<defs>"
    for name, col in [("vap", VAP), ("liq", LIQ), ("ref", REF), ("dist", DIST), ("grey", GREY)]:
        out += (f'<marker id="ah_{name}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
                f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{col}"/></marker>')
    return out + "</defs>"


def process_svg(active: str | None = None, show_disturbances: bool = False) -> str:
    def op(key):  # opacity of a part of the plant
        return 1.0 if active in (None, key) else 0.3

    def stroke(key):
        return ("#16324f", 3.5) if active == key else ("#4a5568", 2)

    p = [f'<svg viewBox="0 0 1000 800" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;'
         f'background:#ffffff;border:1px solid #e6e9ef;border-radius:12px">', _arrow_defs(),
         '<rect x="0" y="0" width="1000" height="800" fill="#ffffff"/>']

    # ---------- V001 reboiler ----------
    c, w = stroke("V001")
    p.append(f'<g opacity="{op("V001")}"><title>Reboiler V001 with heater H701</title>'
             f'<ellipse cx="300" cy="660" rx="150" ry="72" fill="#fde2cf" stroke="{c}" stroke-width="{w}"/>'
             f'<path d="M 205 742 q 15 -14 30 0 q 15 14 30 0 q 15 -14 30 0 q 15 14 30 0 q 15 -14 30 0 q 15 14 30 0" '
             f'fill="none" stroke="#c0392b" stroke-width="3"/>'
             + _t(300, 650, "V001", 20, "#16324f", weight="bold") + _t(300, 672, "Reboiler", 14)
             + _t(300, 772, "heater H701", 13, "#c0392b") + "</g>")

    # ---------- C001-C003 column ----------
    c, w = stroke("C001")
    g = [f'<g opacity="{op("C001")}"><title>Column sections C001-C003</title>']
    for y0, y1, nm in [(430, 560, "C001"), (285, 410, "C002"), (140, 265, "C003")]:
        g.append(f'<rect x="262" y="{y0}" width="76" height="{y1 - y0}" rx="6" fill="#e3ebf6" stroke="{c}" stroke-width="{w}"/>')
        for yy in range(y0 + 14, y1 - 8, 16):
            g.append(f'<line x1="268" y1="{yy}" x2="332" y2="{yy + 9}" stroke="#b6c4d8" stroke-width="1.2"/>')
        g.append(_t(300, (y0 + y1) / 2 + 6, nm, 16, "#16324f", weight="bold"))
    for y0, y1 in [(560, 588), (410, 430), (265, 285), (100, 140)]:
        g.append(f'<line x1="300" y1="{y0}" x2="300" y2="{y1}" stroke="#4a5568" stroke-width="3"/>')
    for y in (535, 385, 250):
        g.append(f'<line x1="362" y1="{y}" x2="362" y2="{y - 72}" stroke="{VAP}" stroke-width="4" marker-end="url(#ah_vap)"/>')
        g.append(f'<line x1="238" y1="{y - 72}" x2="238" y2="{y}" stroke="{LIQ}" stroke-width="4" marker-end="url(#ah_liq)"/>')
    g.append(_t(378, 470, "vapour", 14, VAP, "start", "bold") + _t(378, 488, "rises", 14, VAP, "start"))
    g.append(_t(222, 470, "liquid", 14, LIQ, "end", "bold") + _t(222, 488, "falls", 14, LIQ, "end"))
    g.append("</g>")
    p.append("".join(g))

    # ---------- G001 + vacuum ----------
    c, w = stroke("G001")
    p.append(f'<g opacity="{op("G001")}"><title>Top vessel G001, vacuum pump P301 via throttle valve TV1</title>'
             f'<rect x="250" y="50" width="100" height="50" rx="6" fill="#eceff3" stroke="{c}" stroke-width="{w}"/>'
             + _t(300, 81, "G001", 16, "#16324f", weight="bold") +
             f'<line x1="250" y1="62" x2="60" y2="62" stroke="{GREY}" stroke-width="3" stroke-dasharray="8 6" marker-end="url(#ah_grey)"/>'
             + _t(60, 40, "to vacuum pump P301 via valve TV1", 13, GREY, "start") + "</g>")

    # ---------- HE001/HE002 condensers + cooling ----------
    c, w = stroke("HE001")
    p.append(f'<g opacity="{op("HE001")}"><title>Condensers HE001/HE002, cooling water from thermostat TCU1</title>'
             f'<line x1="350" y1="88" x2="555" y2="88" stroke="{VAP}" stroke-width="5" marker-end="url(#ah_vap)"/>'
             + _t(452, 78, "vapour", 13, VAP) +
             f'<rect x="560" y="40" width="180" height="80" rx="10" fill="#d6eef8" stroke="{c}" stroke-width="{w}"/>'
             + _t(650, 75, "HE001 / HE002", 16, "#16324f", weight="bold") + _t(650, 97, "Condensers", 14) +
             f'<line x1="740" y1="58" x2="930" y2="58" stroke="{COOL}" stroke-width="4" stroke-dasharray="3 6"/>'
             f'<line x1="740" y1="102" x2="930" y2="102" stroke="{COOL}" stroke-width="4" stroke-dasharray="3 6"/>'
             + _t(935, 36, "cooling water from TCU1", 13, "#1d6fa5", "end", "bold") + "</g>")

    # ---------- V002 buffer vessel ----------
    c, w = stroke("V002")
    p.append(f'<g opacity="{op("V002")}"><title>Buffer vessel V002</title>'
             f'<line x1="650" y1="120" x2="650" y2="196" stroke="{LIQ}" stroke-width="5" marker-end="url(#ah_liq)"/>'
             + _t(662, 165, "liquid", 13, LIQ, "start") +
             f'<rect x="610" y="200" width="80" height="100" rx="8" fill="#dcefdf" stroke="{c}" stroke-width="{w}"/>'
             f'<rect x="613" y="262" width="74" height="35" rx="5" fill="{LIQ}" opacity="0.18"/>'
             + _t(650, 236, "V002", 16, "#16324f", weight="bold") + _t(705, 222, "Buffer vessel", 14, "#1f2933", "start") + "</g>")

    # ---------- P701 / P702 split ----------
    c, w = stroke("P701")
    p.append(f'<g opacity="{op("P701")}"><title>Reflux pump P701 and distillate pump P702</title>'
             f'<polyline points="610,280 470,280 470,152 344,152" fill="none" stroke="{REF}" stroke-width="5" marker-end="url(#ah_ref)"/>'
             + _t(470, 306, "P701 – reflux", 14, REF, "middle", "bold") +
             f'<line x1="650" y1="300" x2="650" y2="476" stroke="{DIST}" stroke-width="5" marker-end="url(#ah_dist)"/>'
             + _t(662, 420, "P702 – distillate", 14, DIST, "start", "bold") +
             f'<rect x="600" y="480" width="100" height="80" rx="8" fill="#ece3f8" stroke="{c}" stroke-width="{w}"/>'
             + _t(650, 516, "Distillate", 14, "#16324f", weight="bold") + _t(650, 536, "receiver", 13) + "</g>")

    # ---------- sensors of the active step ----------
    if active:
        for s in STEPS[active][3]:
            x, y, side = SENSOR_POS[s]
            col = SENSOR_COLOR[s[0]]
            if s == "PDI701":
                p.append(f'<line x1="110" y1="565" x2="110" y2="100" stroke="{col}" stroke-width="2" stroke-dasharray="4 4"/>')
            p.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{col}" stroke="white" stroke-width="2.5"/>')
            dx, anchor, dy = {"left": (-16, "end", 5), "right": (16, "start", 5), "below": (0, "middle", 28),
                              "pyright": (14, "start", -10)}[side]
            if s in ("T709", "T711", "T712", "T705"):  # tags left of the column, clear of the arrows
                dx = -78
            p.append(_t(x + dx, y + dy, s, 15, col, anchor, "bold"))

    # ---------- disturbances ----------
    if show_disturbances:
        for x, y, lab, tip, side in DISTURB:
            star = " ".join(f"{x + r * __import__('math').cos(a):.1f},{y + r * __import__('math').sin(a):.1f}"
                            for i in range(10)
                            for a, r in [(-1.5708 + i * 0.6283, 15 if i % 2 == 0 else 6.5)])
            dx, dy, anchor = {"left": (-22, 6, "end"), "right": (22, 6, "start"), "above": (0, -22, "middle"),
                              "below": (0, 34, "middle")}[side]
            p.append(f'<g><title>{tip}</title><polygon points="{star}" fill="#d1495b" stroke="white" stroke-width="1.5"/>'
                     + _t(x + dx, y + dy, lab, 14, "#d1495b", anchor, "bold") + "</g>")

    # ---------- legend ----------
    items = [("vapour", VAP, ""), ("liquid", LIQ, ""), ("reflux", REF, ""), ("distillate", DIST, ""),
             ("cooling water", COOL, "3 6"), ("vacuum line", GREY, "8 6")]
    x = 40
    for name, col, dash in items:
        p.append(f'<line x1="{x}" y1="790" x2="{x + 30}" y2="790" stroke="{col}" stroke-width="5" stroke-dasharray="{dash}"/>')
        p.append(_t(x + 38, 795, name, 13, "#1f2933", "start"))
        x += 48 + 8.0 * len(name)
    p.append("</svg>")
    return "".join(p)


if __name__ == "__main__":  # write preview files
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for key in [None] + list(STEPS):
        for dist in (False, True):
            open(f"{out}/diag_{key}_{int(dist)}.svg", "w").write(process_svg(key, dist))
