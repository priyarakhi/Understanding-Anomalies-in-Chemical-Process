"""
Task 1.b - interactive dataset page.

Builds one self-contained HTML page (shown with components.html) from the
dataset. The page script and styles live in src/assets/dataset.js / .css.
All numbers shown on the page are computed here from the files.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import coverage_table, find_straight_line_segments, quality_table, resolution_step
from .data_loader import seconds_to_time
from .metadata import SENSOR_INFO, SENSORS
from .plant_view import replay_events

ASSETS = Path(__file__).resolve().parent / "assets"
STEP = 2   # seconds between plotted points


def _round(s, x):
    return [round(float(v), 3) for v in x]   # the CSV files have 3 decimals


# ----------------------------------------------------------------- YAML text, split per entry
def _yaml_entries(path: str) -> list[dict]:
    """
    Split the YAML text into its list entries (one per '  - class:') and tag the
    lines the page explains: event interval, disturbance interval, class, id,
    category, perturbation text, equipment id, states, observed effect, sensor.
    Long lists of interval times are shortened to their first 4 items.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    entries, cur = [], None
    for ln in lines:
        if ln.startswith("  - class:"):
            cur = []
            entries.append(cur)
        if cur is not None and ln.strip():
            cur.append(ln)
    out = []
    for ent in entries:
        tagged, ctx, last_field, n_items = [], "", "", 0
        aid = ""
        for ln in ent:
            ind = len(ln) - len(ln.lstrip())
            st = ln.strip()
            item = st.startswith("- ") and not st.startswith("- class:")
            key = "" if item else st.lstrip("- ").split(":", 1)[0] if ":" in st else ""
            if item:
                n_items += 1
                if last_field == "event" and n_items > 4:
                    if n_items == 5:
                        tagged.append([" " * ind + "- ...  (list shortened)", "event"])
                    continue
                tagged.append([ln, last_field])
                continue
            n_items = 0
            field = ""
            if not key:                                   # continuation of a long text
                field = last_field if last_field in ("what", "effect") else ""
            elif key == "class":
                field = "class"
            elif key == "id" and ind == 4:
                field, aid = "id", st.split(":", 1)[1].strip()
            elif key in ("hasBeginning", "hasEnd"):
                field = "event" if ind == 4 else "pert"
            elif key == "hasCategory":
                field = "cat"
            elif key == "Perturbation":
                field = "what"
            elif key == "PerturbationMode":
                ctx = "mode"
            elif key == "System":
                ctx = "system"
            elif key in ("LocalEffect", "Observation"):
                ctx = "effect"
            elif key == "Sensor":
                ctx = "sensor"
            elif key == "id" and ctx == "system":
                field = "equip"
            elif key == "id" and ctx == "sensor":
                field = "sensor"
            elif key in ("hasNormalState", "hasAnomalousState"):
                field = "state"
            elif key == "label" and ctx == "effect":
                field = "effect"
            tagged.append([ln, field])
            last_field = field
        out.append(dict(id=aid, lines=tagged))
    return out


def build_payload(recs, frames, ann, events) -> dict:
    qt = quality_table(recs, frames)
    cov = coverage_table(recs, frames)

    # ---------------- runs (data for charts)
    runs, files = {}, []
    for r in recs:
        df = frames[r.key]
        d = df.iloc[::STEP]
        evs = replay_events(ann, events, r.op, r.file_name) if r.run_type == "anomalous" else []
        runs[r.key] = dict(t0=int(df["seconds_of_day"].iloc[0]), step=STEP, n=len(d),
                           v={s: _round(s, d[s].to_numpy()) for s in SENSORS}, events=evs)
        thumb = df["T703"].iloc[::max(1, len(df) // 60)].round(2).tolist()
        files.append(dict(key=r.key, op=r.op, type=r.run_type, label=r.label, file=r.file_name,
                          start=df["Time"].iloc[0], end=df["Time"].iloc[-1], rows=len(df),
                          minutes=round((len(df) - 1) / 60, 1), t0=int(df["seconds_of_day"].iloc[0]),
                          t1=int(df["seconds_of_day"].iloc[-1]), thumb=thumb,
                          n_ids=int(events[events["OP"] == r.op]["ID"].nunique()) if r.run_type == "anomalous" else 0,
                          yaml=(f"{r.op}/annotations/{r.file_name.replace('.csv', '.yaml')}" if r.yaml_path else None)))
    op_med = {o: float(pd.concat([frames[r.key]["PY23"] for r in recs if r.op == o and r.run_type == "normal"]).median())
              for o in {r.op for r in recs}}
    op_order = sorted(op_med, key=op_med.get)
    op_press = {o: int(round(v / 10) * 10) for o, v in op_med.items()}

    # ---------------- annotations
    yaml_by_op = {r.op: _yaml_entries(r.yaml_path) for r in recs if r.yaml_path}
    ids = []
    for _, e in events.iterrows():
        rec = next(r for r in recs if r.op == e["OP"] and r.run_type == "anomalous")
        ents = [x for x in yaml_by_op[e["OP"]] if x["id"] == e["ID"]]
        sens = [x.strip() for x in str(e["Annotated sensors"]).split(",")]
        in11 = [x for x in sens if x in SENSORS]
        a = ann[(ann["OP"] == e["OP"]) & (ann["ID"] == e["ID"]) & ann["Valid interval"]].drop_duplicates(["begin_s", "end_s"])
        from .annotations import has_time
        from .data_loader import time_to_seconds
        pb = time_to_seconds(e["Perturbation begin"]) if has_time(e["Perturbation begin"]) else None
        pe = time_to_seconds(e["Perturbation end"]) if has_time(e["Perturbation end"]) else None
        ids.append(dict(
            op=e["OP"], id=e["ID"], short=e["ID"][-4:], cls=e["Class"],
            cat=e["Category"] if isinstance(e["Category"], str) else "none",
            what=e["Perturbation"] if isinstance(e["Perturbation"], str) else e["Observed effect(s)"],
            entries=len(ents), intervals=int(e["Distinct intervals"]), sensors=e["Annotated sensors"],
            sensor=(in11[0] if in11 else None), run=rec.key,
            iv=[[int(x), int(y)] for x, y in zip(a["begin_s"], a["end_s"])],
            pb=pb, pe=pe, equipment=e["Equipment"] or "",
            lines=(ents[0]["lines"] if ents else []),
            first=e["First begin"], last=e["Last end"]))

    invalid = ann[ann["Issue"] != ""][["OP", "ID", "Sensor", "Interval no.", "Begin", "End", "Issue"]]
    invalid = [dict(op=r["OP"], id=r["ID"][-4:], sensor=r["Sensor"], n=int(r["Interval no."]), b=r["Begin"],
                    e=r["End"], issue=r["Issue"]) for _, r in invalid.iterrows()]

    # ---------------- quality
    k18 = next(r.key for r in recs if r.op == "OP18" and r.run_type == "normal")
    seg = find_straight_line_segments(frames[k18])[0]
    d18 = frames[k18]
    k17 = next(r.key for r in recs if r.op == "OP17" and r.run_type == "normal")
    raw = frames[k17].iloc[600:1200]
    k10 = next(r.key for r in recs if r.op == "OP10" and r.run_type == "normal")
    r10 = next(r for r in recs if r.key == k10)
    with open(r10.csv_path, encoding="utf-8") as fh:
        head = [next(fh).strip().split(",") for _ in range(4)]
    half = [[row[head[0].index("Time")], row[head[0].index("T703")]] for row in head[1:]]
    per_run = [dict(run=row["OP"] + " · " + row["Run"], steps=bool(row["Regular 1-s steps"]),
                    dup=int(row["Duplicate timestamps"]), miss=int(row["Missing values"]),
                    filled=int(row["Straight-line (filled) seconds"]), neg1=int(row["Negative PDI701 values"]),
                    neg2=int(row["Negative PDI702 values"]), zero=int(row["FYI702 exactly 0 (s)"]))
               for _, row in qt.iterrows()]
    spikes = [dict(run=r.key, ft703=int((frames[r.key]["FT703"] > 0.5).sum()),
                   ft704=int((frames[r.key]["FT704"] > 1.0).sum())) for r in recs]
    steps = {s: round(float(np.median([resolution_step(frames[r.key][s]) for r in recs])), 4) for s in SENSORS}
    quality = dict(
        fill=dict(run=k18, b=int(d18["seconds_of_day"].iloc[seg["start_row"]]), e=int(d18["seconds_of_day"].iloc[seg["end_row"]]),
                  start=seg["Start"], end=seg["End"], length=int(seg["Length (s)"]),
                  py_end=round(float(d18["PY23"].iloc[seg["end_row"]]), 1),
                  t705_end=round(float(d18["T705"].iloc[seg["end_row"]]), 1)),
        res=dict(run=k17, t0=int(raw["seconds_of_day"].iloc[0]), v=[float(x) for x in raw["T705"]]),
        half=half, per_run=per_run, spikes=spikes, steps=steps, invalid=invalid,
        total_rows=int(sum(len(frames[r.key]) for r in recs)))

    return dict(sensors=SENSORS, groups={s: SENSOR_INFO[s]["group"] for s in SENSORS},
                units={s: SENSOR_INFO[s]["unit"] for s in SENSORS}, runs=runs, files=files, op_order=op_order, op_press=op_press,
                ids=ids, coverage=cov.to_dict(orient="records"), quality=quality,
                n_entries=int(ann.drop_duplicates(["OP", "Entry"]).shape[0]))
