"""Content of page 2, "The dataset": plain names, tables and small charts. All numbers come from the dataset files."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .data_loader import time_to_seconds
from .metadata import SENSOR_INFO
from .plant_view import replay_events

ASSETS = Path(__file__).resolve().parent / "assets"
ORDER = ["T703", "T709", "T711", "T712", "T705", "PDI701", "PY23", "FYI702", "PDI702", "FT704", "FT703"]

NAMES = {   # short everyday names, based on the README descriptions
    "T703": "boiler temperature", "T709": "temperature, column bottom", "T711": "temperature, lower column",
    "T712": "temperature, upper column", "T705": "temperature, column top", "PDI701": "pressure difference, column",
    "PY23": "plant pressure", "FYI702": "cooling-water flow", "PDI702": "pressure difference, collecting vessel",
    "FT704": "flow back to the column (reflux)", "FT703": "product flow (distillate)",
}
UNITS = {"T703": "°C", "T709": "°C", "T711": "°C", "T712": "°C", "T705": "°C", "PY23": "mbar", "PDI702": "mbar"}
# what each value tells us; sources: README, YAML annotations, the data itself, or (marked) background physics
MEANING = {
    "T703": "How far the batch has progressed: it rises slowly in every run as the light components boil away.",
    "T709": "Temperature of the vapour entering the column.",
    "T711": "Middle of the temperature profile up the column (hottest at the bottom, coolest at the top).",
    "T712": "Upper part of the temperature profile up the column.",
    "T705": "Temperature of what leaves the column top towards the condensers; differs clearly between operating points.",
    "PDI701": "How hard the vapour has to push through the column (background physics).",
    "PY23": "The vacuum level of the whole plant; the main difference between the operating points. Its saw-tooth "
            "comes from the pressure controller.",
    "FYI702": "Whether the condensers are being cooled; it drops to 0 when the cooling is switched off (OP31).",
    "PDI702": "Linked to the liquid level in the collecting vessel V002 (YAML); the pumps keep it near its setpoint "
              "(2 mbar in the OP29 file).",
    "FT704": "How much liquid is sent back down the column; more reflux gives a cleaner separation (background physics).",
    "FT703": "How much product leaves the plant.",
}
GC = {"T": "#c0392b", "F": "#2b6cb0", "D": "#8e44ad", "P": "#1e8449"}


def colour(s):
    return GC["T" if s[0] == "T" else "P" if s == "PY23" else "D" if s.startswith("PDI") else "F"]


def _key(recs, op, typ, num="001"):
    return next(r.key for r in recs if r.op == op and r.run_type == typ and (typ == "anomalous" or r.label.endswith(num)))


def chart_html(cd: dict) -> str:
    css = (ASSETS / "charts.css").read_text(encoding="utf-8")
    js = (ASSETS / "charts.js").read_text(encoding="utf-8")
    blob = json.dumps(cd, separators=(",", ":")).replace("</", "<\\/")
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body><div id="root"></div>'
            f"<script>window.CD = {blob};</script><script>{js}</script></body></html>")


def _ser(df, s, step=2, name=None, color=None, width=1.4, minutes=False):
    d = df.iloc[::step]
    return dict(t0=0 if minutes else int(df["seconds_of_day"].iloc[0]), step=step / 60 if minutes else step,
                y=[round(float(v), 3) for v in d[s]], color=color or colour(s), width=width, name=name or s)


# ---------------------------------------------------------------------------------------------- 2 what is in it
def op_order(recs, frames):
    med = {o: float(pd.concat([frames[r.key]["PY23"] for r in recs if r.op == o and r.run_type == "normal"]).median())
           for o in {r.op for r in recs}}
    return sorted(med, key=med.get), {o: int(round(v / 10) * 10) for o, v in med.items()}


def files_table(recs, frames, events) -> str:
    order, press = op_order(recs, frames)
    rows = []
    for op in order:
        rs = sorted([x for x in recs if x.op == op], key=lambda x: (x.run_type != "normal", x.label))
        for k, r in enumerate(rs):
            df = frames[r.key]
            n = int(events[events["OP"] == op]["ID"].nunique()) if r.run_type == "anomalous" else 0
            kind = ("Normal" + (f" ({r.label[-3:]})" if op == "OP31" else "")) if r.run_type == "normal" else "Anomalous"
            rows.append(
                f"<tr class='{'first' if k == 0 else ''}'>"
                + (f"<td rowspan='{len(rs)}' class='op'><b>{op}</b><br><span>≈ {press[op]} mbar</span></td>" if k == 0 else "")
                + f"<td><span class='dot {'n' if r.run_type == 'normal' else 'a'}'></span>{kind}</td><td class='mono'>{r.file_name}</td>"
                f"<td>{df['Time'].iloc[0][:5]} – {df['Time'].iloc[-1][:5]}</td><td class='num'>{(len(df) - 1) / 60:.1f} min</td>"
                f"<td class='num'>{len(df):,}</td><td class='num'>{n if n else '–'}</td></tr>")
    return ("<table class='ds'><thead><tr><th>Operating point</th><th>Recording</th><th>File</th><th>Clock time</th>"
            "<th class='num'>Length</th><th class='num'>Rows</th><th class='num'>Anomalies</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def sensor_table() -> str:
    rows = "".join(
        f"<tr><td style='white-space:nowrap'><span class='bar' style='background:{colour(s)}'></span><b>{s}</b></td><td>{NAMES[s]}</td>"
        f"<td>{UNITS.get(s, 'not stated')}</td><td>{SENSOR_INFO[s]['location']}</td><td>{MEANING[s]}</td></tr>" for s in ORDER)
    return ("<table class='ds'><thead><tr><th>Code</th><th>Measures</th><th>Unit</th><th>Where in the plant</th>"
            "<th>What it tells us</th></tr></thead><tbody>" + rows + "</tbody></table>")


# ---------------------------------------------------------------------------------------------- 4 keep in mind
def fill_chart(recs, frames, fill) -> tuple[str, int]:
    df = frames[_key(recs, "OP18", "normal")]
    sh = [dict(a=fill["b"], b=fill["e"], fill="rgba(100,116,139,.18)")]
    xr = [max(int(df["seconds_of_day"].iloc[0]), fill["b"] - 900), min(int(df["seconds_of_day"].iloc[-1]), fill["e"] + 1800)]
    p1 = dict(series=[_ser(df, "PY23")], shade=sh, ylab="PY23", ysub=NAMES["PY23"], height=150, noX=True,
              notes=[dict(x=fill["b"], ty=14, text="straight lines: these values were filled in", color="#475569")], top=8)
    p2 = dict(series=[_ser(df, "T705")], shade=sh, ylab="T705", ysub=NAMES["T705"], height=170)
    return chart_html(dict(type="single", xr=xr, panels=[p1, p2])), 324


def whole_run_chart(recs, frames, ann, events) -> tuple[str, int]:
    r = next(x for x in recs if x.op == "OP22" and x.run_type == "anomalous")
    df = frames[r.key]
    shade = []
    for e in replay_events(ann, events, r.op, r.file_name):
        if e["kind"] == "spike":
            continue
        if e["pb"] is not None:
            shade.append(dict(a=e["pb"], b=e["pe"], fill="rgba(230,126,34,.25)"))
        shade.append(dict(a=e["b"], b=e["e"], fill="rgba(192,57,43,.13)"))
    xr = [int(df["seconds_of_day"].iloc[0]), int(df["seconds_of_day"].iloc[-1])]
    p = dict(series=[_ser(df, "FT704", width=1)], shade=shade, ylab="FT704", ysub=NAMES["FT704"], height=260)
    return chart_html(dict(type="single", xr=xr, panels=[p])), 262


def coverage_chart(recs, frames) -> tuple[str, int]:
    n, a = frames[_key(recs, "OP10", "normal")], frames[_key(recs, "OP10", "anomalous")]
    band = dict(lo=float(n["FYI702"].min()), hi=float(n["FYI702"].max()), fill="rgba(43,108,176,.12)")
    p = dict(series=[_ser(n, "FYI702", 4, "normal run", "#2b6cb0", 1, True), _ser(a, "FYI702", 4, "anomalous run", "#c0392b", 1, True)],
             band=band, ylab="FYI702", ysub=NAMES["FYI702"], sensor="FYI702", height=260)
    return chart_html(dict(type="single", xr=[0, round(max(len(n), len(a)) / 60, 1)], minutes=True, panels=[p])), 262


def invalid_table(ann) -> str:
    t = ann[ann["Issue"] != ""]
    rows = "".join(f"<tr><td>{r['OP']}</td><td>{r['ID'][-4:]}</td><td>{r['Sensor']}</td><td class='num'>{int(r['Interval no.'])}</td>"
                   f"<td>{r['Begin']}</td><td>{r['End']}</td><td>{r['Issue']}</td></tr>" for _, r in t.iterrows())
    return ("<table class='ds'><thead><tr><th>Recording</th><th>Anomaly</th><th>Spike list</th><th class='num'>No.</th>"
            "<th>Begin</th><th>End</th><th>Problem</th></tr></thead><tbody>" + rows + "</tbody></table>")
