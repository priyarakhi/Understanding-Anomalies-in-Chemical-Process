"""Page 3 (Question 1): data for the overview grid, the zoom view and the marked replay."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .data_view import ASSETS, NAMES, ORDER
from .plant_view import ANOMALY_GROUPS, replay_events
from .q1 import analyse


def _r(x, d=3):
    return [round(float(v), d) for v in x]


def build(recs, frames, ann, events) -> dict:
    res = {r["key"]: r for r in analyse(recs, frames, events)}
    groups, used = [], set()
    for g in ANOMALY_GROUPS:
        keys = []
        for op, short in g["items"]:
            e = events[(events["OP"] == op) & events["ID"].str.endswith(short)].iloc[0]
            keys.append(op + e["ID"]); used.add(op + e["ID"])
        groups.append(dict(title=g["title"], where=g["where"], keys=keys))
    side = [r for r in res if r not in used]
    groups[-1]["keys"] += side
    rows, data = {}, {}
    for key, r in res.items():
        e = next(row for _, row in events.iterrows() if row["OP"] + row["ID"] == key)
        what = e["Perturbation"] if isinstance(e["Perturbation"], str) else f"Side effect: {e['Observed effect(s)']}"
        sens = {}
        for s, x in r["sensors"].items():
            sens[s] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items() if k not in ("line",)}
            if "line" in x:
                sens[s]["line"] = [round(x["line"][0], 4), x["line"][1]]
        rows[key] = dict(key=key, op=r["op"], id=r["id"][-4:], cls=r["cls"], cat=r["cat"], what=what,
                         first=r["first"], last=r["last"], pb=r["pb"], pe=r["pe"], b=r["b"], e=r["e"],
                         annotated=r["annotated"], special=r.get("special"), sensors=sens)
        if r.get("special"):
            continue
        t_on = next(x["t_on"] for x in r["sensors"].values() if "t_on" in x)
        t_end = next(x["t_end"] for x in r["sensors"].values() if "t_end" in x)
        df = frames[r["run"]]
        w = df[(df["seconds_of_day"] >= t_on - 600) & (df["seconds_of_day"] <= t_end + 660)]
        sm = {s: _r(pd.Series(w[s].to_numpy(dtype=float)).rolling(15, center=True, min_periods=1).median().iloc[::2])
              for s in ORDER}
        s0 = next((s for s in r["annotated"] if s in ORDER), "PY23")
        strip = df.iloc[::8]
        data[key] = dict(t0=int(w["seconds_of_day"].iloc[0]), step=2, v=sm, t_on=t_on, t_end=t_end,
                         strip=dict(s=s0, t0=int(strip["seconds_of_day"].iloc[0]), step=8, y=_r(strip[s0])))
    # how often each sensor reacts (anomalies that can be judged)
    judged = [k for k, r in rows.items() if not r["special"]]
    bars = []
    for s in ORDER:
        hits = [k for k in judged if rows[k]["sensors"][s]["kind"] not in ("none", "n/a")]
        rec = {q: sum(rows[k]["sensors"][s].get("recovery") == q for k in hits) for q in ("yes", "partly", "no")}
        named = sum(s in rows[k]["annotated"] for k in judged)
        bars.append(dict(s=s, n=len(hits), keys=hits, rec=rec, named=named))
    icons = {"Nitrogen into the reboiler": "gas", "Nitrogen below the column": "gas", "Liquid withdrawn from the reflux line": "sample",
             "Air into the reflux line": "air", "Leaking sample valves": "leak", "Cooling switched off": "cool",
             "Five settings changed at once": "dial"}
    for g in groups:
        g["icon"] = icons.get(g["title"], "dial")
    return dict(order=ORDER, names=NAMES, groups=groups, rows=rows, data=data, bars=bars, judged=len(judged))


def page_html(payload: dict) -> str:
    css = (ASSETS / "charts.css").read_text(encoding="utf-8")
    js = (ASSETS / "charts.js").read_text(encoding="utf-8")
    blob = json.dumps(dict(payload, type="q1b"), separators=(",", ":")).replace("</", "<\\/")
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body><div id="root"></div>'
            f"<script>window.CD = {blob};</script><script>{js}</script></body></html>")


# ---------------------------------------------------------------------------------------------- marked replay
def replay_marks(recs, frames, ann, events, key) -> tuple[dict, str]:
    """Row data for the plant replay of one anomaly, with a mark (-1 fell, +1 rose, 0) for every sensor and second."""
    from .data_parts import rowdata
    r = next(x for x in analyse(recs, frames, events) if x["key"] == key)
    rec = next(x for x in recs if x.key == r["run"])
    t_on = next(x["t_on"] for x in r["sensors"].values() if "t_on" in x)
    t_end = next(x["t_end"] for x in r["sensors"].values() if "t_end" in x)
    a, b = t_on - 300, min(t_end + 600, t_on - 300 + 1800)
    d = rowdata(rec, frames, ann, events, a, b, next((s for s in r["annotated"] if s in ORDER), None))
    df = frames[rec.key]
    w = df[(df["seconds_of_day"] >= a) & (df["seconds_of_day"] <= b)]
    sec = w["seconds_of_day"].to_numpy()
    marks = {}
    for s in ORDER:
        x = r["sensors"][s]
        if x["kind"] in ("none", "n/a") or "line" not in x:
            marks[s] = [0] * len(w)
            continue
        c, k = x["line"]
        sm = pd.Series(w[s].to_numpy(dtype=float)).rolling(15, center=True, min_periods=1).median().to_numpy()
        dev = sm - (c + k * (sec - t_on))
        mk = np.where(dev > x["tol"], 1, np.where(dev < -x["tol"], -1, 0))
        mk[sec < t_on] = 0
        marks[s] = mk.astype(int).tolist()
    d["marks"] = marks
    d["t_on"] = int(t_on)
    d["before"] = {s: round(float(r["sensors"][s]["line"][0]), 3) for s in ORDER if "line" in r["sensors"][s]}
    label = f"{r['op']} · {r['id'][-4:]}"
    return d, label


def replay_options(recs, frames, events) -> list[tuple[str, str]]:
    from .data_parts import plain_names
    plain = plain_names(events)
    return [(r["key"], f"{r['op']} · {r['id'][-4:]} · {plain[r['key']]}") for r in analyse(recs, frames, events)
            if not r.get("special")]
