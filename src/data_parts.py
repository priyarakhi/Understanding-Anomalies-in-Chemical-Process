"""More content for page 2: the replay of any recording, operating points, examples for all 23 anomalies,
how the project uses the data, and two things that look odd but are normal. All numbers come from the dataset files."""
from __future__ import annotations

import pandas as pd

from .data_loader import time_to_seconds
from .data_view import NAMES, ORDER, _key, _ser, chart_html, colour, op_order
from .plant_view import ANOMALY_GROUPS, replay_events


def _t(x):
    return time_to_seconds(x) if isinstance(x, str) and x.count(":") == 2 else None


def hhmm(sec):
    return f"{int(sec) // 3600:02d}:{int(sec) % 3600 // 60:02d}"


def plain_names(events) -> dict:
    """OP+ID -> plain name of the kind of anomaly."""
    out = {}
    for g in ANOMALY_GROUPS:
        for op, short in g["items"]:
            e = events[(events["OP"] == op) & events["ID"].str.endswith(short)].iloc[0]
            out[op + e["ID"]] = g["title"]
    for _, e in events.iterrows():
        out.setdefault(e["OP"] + e["ID"], "Side effect after the settings change")
    return out


# ---------------------------------------------------------------------------------------------- replay of any recording
def recording_label(r, frames) -> str:
    kind = ("normal run" + (f" {r.label[-3:]}" if r.op == "OP31" else "")) if r.run_type == "normal" else "anomalous run"
    return f"{r.op} · {kind} · {(len(frames[r.key]) - 1) / 60:.0f} min"


def moments(r, frames, events) -> list[dict]:
    """Where a replay can start: the beginning of the recording, or one annotated anomaly."""
    df = frames[r.key]
    t0, t1 = int(df["seconds_of_day"].iloc[0]), int(df["seconds_of_day"].iloc[-1])
    out = [dict(label="Beginning of the recording", a=t0, b=min(t1, t0 + 900), focus=None)]
    if r.run_type != "anomalous":
        return out
    plain = plain_names(events)
    for _, e in events[events["OP"] == r.op].iterrows():
        pb, pe = _t(e["Perturbation begin"]), _t(e["Perturbation end"])
        b, en = int(e["begin_s"]), int(e["end_s"])
        cat = e["Category"] if isinstance(e["Category"], str) else None
        if cat in ("recurrent", "permanent"):
            pb = pe = None
        start = min(b, pb or b) - 300
        stop = start + 1200 if cat in ("recurrent", "permanent") else max(en, pe or en) + 300
        start = max(t0, start)
        stop = min(t1, stop, start + 1800)
        s11 = [x.strip() for x in str(e["Annotated sensors"]).split(",") if x.strip() in ORDER]
        out.append(dict(label=f"{e['ID'][-4:]} · {plain[e['OP'] + e['ID']]} ({hhmm(pb or b)})", a=start, b=stop,
                        focus=s11[0] if s11 else None))
    return out


def rowdata(r, frames, ann, events, a: int, b: int, focus) -> dict:
    df = frames[r.key]
    w = df[(df["seconds_of_day"] >= a) & (df["seconds_of_day"] <= b)]
    evs = []
    if r.run_type == "anomalous":
        for e in replay_events(ann, events, r.op, r.file_name):
            hit = e["e"] >= a and e["b"] <= b
            if e["pb"] is not None:
                hit = hit or (e["pe"] >= a and e["pb"] <= b)
            if hit:
                evs.append(dict(k=e["kind"], b=e["b"], e=e["e"], pb=e["pb"], pe=e["pe"], what=e["what"], id=e["short"][:4]))
    return dict(order=ORDER, names=NAMES, time=w["Time"].tolist(), v={s: [round(float(x), 3) for x in w[s]] for s in ORDER},
                t0=int(w["seconds_of_day"].iloc[0]), first_line=int(w.index[0]) + 2, rows=len(df),
                file=f"{r.op}/measurements/{r.file_name}", op=r.op, kind=r.run_type, events=evs, focus=focus,
                med={s: float(df[s].median()) for s in ("FT704", "FT703", "FYI702")})


# ---------------------------------------------------------------------------------------------- operating points
def op_bars(recs, frames) -> tuple[str, int]:
    """Two linked charts: pressure vs. column-top temperature, and the temperature profile up the column."""
    order, _ = op_order(recs, frames)
    ops = []
    for o in order:
        m = pd.concat([frames[r.key] for r in recs if r.op == o and r.run_type == "normal"])[
            ["PY23", "T703", "T709", "T711", "T712", "T705"]].median()
        ops.append(dict(op=o, p=round(float(m["PY23"]), 1), t={s: round(float(m[s]), 2) for s in ["T703", "T709", "T711", "T712", "T705"]}))
    return chart_html(dict(type="ops", ops=ops, names={s: NAMES[s] for s in ["T703", "T709", "T711", "T712", "T705"]})), 360


FLOW = """<div class='flow3'>
<div><b>1 · Normal recordings</b><span>The models learn what normal behaviour looks like: from the last minutes of
data they forecast the next values.</span></div><i>&rarr;</i>
<div><b>2 · Anomalous recordings</b><span>The models raise an alarm where the measured values differ too much from
their forecast.</span></div><i>&rarr;</i>
<div><b>3 · Annotation files</b><span>The alarms are compared with the periods the experts marked as anomalous:
which anomalies were found, how many alarms were false, and how late they came.</span></div></div>"""


# ---------------------------------------------------------------------------------------------- examples (all anomalies)
def anomaly_options(events) -> list[tuple[str, str]]:
    plain = plain_names(events)
    return [(e["OP"] + e["ID"], f"{e['OP']} · {e['ID'][-4:]} · {plain[e['OP'] + e['ID']]}") for _, e in events.iterrows()]


def example(recs, frames, ann, events, key) -> dict:
    e = next(row for _, row in events.iterrows() if row["OP"] + row["ID"] == key)
    r = next(x for x in recs if x.op == e["OP"] and x.run_type == "anomalous")
    df = frames[r.key]
    cat = e["Category"] if isinstance(e["Category"], str) else None
    deliberate = e["Class"] == "ConfirmedAnomaly"
    pb, pe = (_t(e["Perturbation begin"]), _t(e["Perturbation end"])) if cat in ("transient", None) else (None, None)
    b, en = int(e["begin_s"]), int(e["end_s"])
    sens = [x.strip() for x in str(e["Annotated sensors"]).split(",")]
    shown = [x for x in sens if x in ORDER] or [next(x for x in sens if x in df.columns)]
    s = shown[0]
    in11 = s in ORDER
    t0, t1 = int(df["seconds_of_day"].iloc[0]), int(df["seconds_of_day"].iloc[-1])
    if cat == "permanent":
        a, z = t0, t1
    elif cat == "recurrent":
        a, z = max(t0, b - 60), min(t1, b + 2400)
    else:
        a, z = max(t0, min(b, pb or b) - 480), min(t1, max(en, pe or en) + 480)
    w = df[(df["seconds_of_day"] >= a) & (df["seconds_of_day"] <= z)]
    step = max(1, len(w) // 1500)
    iv = ann[(ann["OP"] == e["OP"]) & (ann["ID"] == e["ID"]) & ann["Valid interval"]].drop_duplicates(["begin_s", "end_s"])
    shade = []
    if pb is not None:
        shade.append(dict(a=pb, b=pe, fill="rgba(230,126,34,.25)"))
    for x, y in zip(iv["begin_s"], iv["end_s"]):
        shade.append(dict(a=int(x), b=int(y), fill="rgba(142,68,173,.28)" if cat == "recurrent" else "rgba(192,57,43,.14)"))
    notes = []
    if pb is not None:
        notes += [dict(x=pb, ty=-38, text=f"① {e['Perturbation begin']} disturbance\nstarts", color="#b35c00"),
                  dict(x=pe, ty=-38, text=f"② {e['Perturbation end']} disturbance\nends", color="#b35c00")]
        if en > pe + 120:
            notes.append(dict(x=en, ty=-38, text=f"③ marked anomalous\nuntil {e['Last end']}", color="#a32d2d"))
    elif cat == "recurrent":
        notes.append(dict(x=a, ty=-38, text=f"{int(e['Distinct intervals'])} short marked periods between {e['First begin']} "
                                              f"and {e['Last end']} (first 40 minutes shown)", color="#7d3c98"))
    elif cat == "permanent":
        notes.append(dict(x=a, ty=-38, text="marked anomalous for the whole recording", color="#a32d2d"))
    else:
        notes.append(dict(x=b, ty=-38, text=f"marked anomalous\n{e['First begin']} – {e['Last end']}", color="#a32d2d"))
    panels = []
    for k, x in enumerate(shown):
        last = k == len(shown) - 1
        h = (300 if len(shown) == 1 else 190 if k == 0 else 140) + (0 if last or len(shown) == 1 else -22)
        panels.append(dict(series=[_ser(w, x, step=step, color=colour(x) if x in ORDER else "#64748b")], shade=shade,
                           notes=notes if k == 0 else [], ylab=x, ysub=NAMES.get(x, "not one of the 11 project sensors"),
                           sensor=x, height=h, top=58 if k == 0 else 8, noX=not last))
    chart = chart_html(dict(type="single", xr=[a, z], panels=panels, left=235))
    if deliberate and isinstance(e["Perturbation"], str):
        what = e["Perturbation"]
    else:
        what = ("Nothing was done on purpose: the experts observed this side effect after the settings change "
                f"OP29 A001 ({e['Observed effect(s)']}).")
    if pb is not None:
        when = (f"Disturbance applied {e['Perturbation begin']} – {e['Perturbation end']}; "
                f"marked anomalous {e['First begin']} – {e['Last end']}.")
        ds, de = int(e["Event start minus perturbation start (s)"]), int(e["Event end minus perturbation end (s)"])
        how = (f"The marking starts {abs(ds)} s {'after' if ds >= 0 else 'before'} the disturbance and ends "
               f"{de / 60:.1f} min after it, because the plant needs time to recover.")
    elif cat == "recurrent":
        when = f"{int(e['Distinct intervals'])} short periods marked between {e['First begin']} and {e['Last end']}."
        how = "The improperly sealed valve leaked during almost the whole run; each spike is marked separately."
    elif cat == "permanent":
        when = f"Marked anomalous for the whole recording ({e['First begin']} – {e['Last end']})."
        how = "Every second of this recording counts as anomalous."
    else:
        n = int(e["Distinct intervals"])
        when = f"Marked anomalous {e['First begin']} – {e['Last end']}" + (f" ({n} periods)." if n > 1 else ".")
        how = "No disturbance time is given, because nothing was done on purpose."
    seen = f"Annotated in {e['Annotated sensors']}" + (
        "" if in11 else f"; {s} is a column of the file but not one of the 11 project sensors") + "."
    return dict(chart=chart, height=sum(p["height"] for p in panels) + 4, what=what, when=when, how=how, seen=seen)


# ---------------------------------------------------------------------------------------------- odd but normal
def normal_charts(recs, frames) -> tuple[str, str]:
    d10 = frames[_key(recs, "OP10", "normal")]
    p1 = dict(series=[_ser(d10, "T703", step=4)], ylab="T703", ysub=NAMES["T703"], height=230, top=10)
    c1 = chart_html(dict(type="single", xr=[int(d10["seconds_of_day"].iloc[0]), int(d10["seconds_of_day"].iloc[-1])],
                         panels=[p1], left=140))
    d17 = frames[_key(recs, "OP17", "normal")]
    t = int(d17["seconds_of_day"].iloc[0]) + 1200
    w = d17[(d17["seconds_of_day"] >= t) & (d17["seconds_of_day"] <= t + 600)]
    p2 = dict(series=[_ser(w, "PY23", step=1)], ylab="PY23", ysub=NAMES["PY23"], height=230, top=10)
    c2 = chart_html(dict(type="single", xr=[t, t + 600], panels=[p2], left=140))
    return c1, c2
