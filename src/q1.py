"""Question 1: which sensors change during an anomaly, how, and do they recover?

Method (applied to every annotated anomaly and every one of the 11 sensors)
---------------------------------------------------------------------------
* Onset = the time the disturbance was applied (or, without a documented disturbance, the start of the marked
  period). End = the end of the marked (annotated) period.
* "Before" = the 5 minutes before the onset. The slow, normal drift of a batch (e.g. temperatures rising) is carried
  forward as a straight line fitted to the 10 minutes before the onset, if that drift is clearly larger than the
  noise; otherwise the level of the 5 minutes before is used.
* Every value is smoothed with a 15-second rolling median, then compared with that line. The tolerance is the
  larger of (a) 4 x the robust spread of the sensor around the line in the "before" window and (b) 3 x its
  measurement step.
* Clear change: the smoothed value stays beyond the tolerance for at least 30 s between onset and end (at least
  3 minutes are looked at), and it got there quickly: within some 1-minute span the deviation changed by more than
  twice the tolerance. This keeps slow changes of the batch drift from being counted.
  Direction: rise or fall (sign of the largest deviation); "swings" when it is clearly above and clearly below.
  Spikes: no lasting change, but at least 3 short (< 30 s) jumps of the raw value away from its 15-s median, at
  least 3 times as often as in the "before" window.
* Recovered: after the largest deviation, the value stays within the tolerance for at least 60 s, at the latest
  10 minutes after the end of the marked period. Partly: it comes back at least half way. Otherwise: not recovered.

The line carried forward is only an approximation of the batch drift. All results were checked against plots of
every anomaly; 17 cells where the simple rule cannot follow the batch or where a regular pattern changes were
corrected by eye (REVIEWED, each with its reason). The results remain an analysis, not ground truth.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .analysis import resolution_step
from .data_loader import time_to_seconds

SENSORS11 = ["T703", "T709", "T711", "T712", "T705", "PDI701", "PY23", "FYI702", "PDI702", "FT704", "FT703"]
BEFORE, SMOOTH, MIN_RUN, HOLD, AFTER = 300, 15, 30, 60, 600


def _t(x):
    return time_to_seconds(x) if isinstance(x, str) and x.count(":") == 2 else None


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Start/end index pairs of consecutive True values."""
    out, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            out.append((start, i - 1)); start = None
    if start is not None:
        out.append((start, len(mask) - 1))
    return out


def analyse_one(df: pd.DataFrame, s: str, t_on: int, t_end: int, res: float) -> dict:
    sec = df["seconds_of_day"].to_numpy()
    y = df[s].to_numpy(dtype=float)
    sm = pd.Series(y).rolling(SMOOTH, center=True, min_periods=1).median().to_numpy()
    b = (sec >= t_on - BEFORE) & (sec < t_on)
    if b.sum() < 120:
        return dict(kind="n/a", why="less than 2 minutes of data before the onset")
    # slow drift: a line fitted to the 10 minutes before the onset, kept only if the drift is clearly larger than
    # the noise; otherwise the level of the 5 minutes before is used (flat line)
    lw = (sec >= t_on - 2 * BEFORE) & (sec < t_on)
    k, c = np.polyfit(sec[lw] - t_on, y[lw], 1)
    r0 = sm[b] - (c + k * (sec[b] - t_on))
    spread0 = 1.4826 * np.median(np.abs(r0 - np.median(r0)))
    tol = max(4 * spread0, 3 * res, 1e-9)
    if abs(k) * 2 * BEFORE < 2 * tol:
        k, c = 0.0, float(np.median(y[b]))
    line = lambda t: c + k * (t - t_on)
    t_end = max(t_end, t_on + 180)          # very short marked periods: look at least 3 minutes
    if sec[-1] < t_on + 60:
        return dict(kind="n/a", why="the recording ends right after the onset")
    w = (sec >= t_on) & (sec <= t_end)
    dev = sm[w] - line(sec[w])
    # a change must also be fast: within some 1-minute span the deviation changes by more than 2 x the tolerance
    wx = (sec >= t_on - 120) & (sec <= t_end)
    devx = sm[wx] - line(sec[wx])
    lag = np.concatenate([np.full(60, devx[0]), devx[:-60]])[:len(devx)]
    fast = (np.abs(devx - lag) > 2 * tol)[-len(dev):]
    def keep(r):
        return r[1] - r[0] + 1 >= MIN_RUN and fast[max(0, r[0] - 60):r[1] + 1].any()
    up = [r for r in _runs(dev > tol) if keep(r)]
    dn = [r for r in _runs(dev < -tol) if keep(r)]
    # spikes: short jumps of the raw value away from its own 15-s median, clearly more often than before
    jump = np.abs(y - sm)
    jb = jump[b]
    thr = max(6 * 1.4826 * np.median(np.abs(jb - np.median(jb))) + np.median(jb), 3 * res, 1e-9)
    n_dur = len([q for q in _runs(jump[w] > thr) if q[1] - q[0] + 1 < MIN_RUN])
    n_bef = len([q for q in _runs(jb > thr) if q[1] - q[0] + 1 < MIN_RUN])
    rate_dur, rate_bef = n_dur / max(1, w.sum()) * 60, n_bef / max(1, b.sum()) * 60
    out = dict(tol=float(tol), line=[float(c), float(k)], t_on=int(t_on), t_end=int(t_end))
    if not up and not dn:
        if n_dur >= 3 and rate_dur >= 3 * max(rate_bef, 1e-9):
            return dict(out, kind="spikes", n_spikes=n_dur, size=float(np.max(jump[w])), recovery="n/a")
        return dict(out, kind="none")
    i_ext = int(np.argmax(np.abs(dev) * ((dev > tol) | (dev < -tol))))
    ext = float(dev[i_ext])
    kind = "swing" if up and dn else ("rise" if ext > 0 else "fall")
    first = min([r[0] for r in up + dn])
    onset_delay = int(sec[w][first] - t_on)
    # recovery: from the largest deviation until 10 minutes after the end of the marked period
    t_ext = int(sec[w][i_ext])
    r = (sec >= t_ext) & (sec <= t_end + AFTER)
    devr = sm[r] - line(sec[r])
    back = [q for q in _runs(np.abs(devr) <= tol) if q[1] - q[0] + 1 >= HOLD]
    if back:
        rec, t_back = "yes", int(sec[r][back[0][0]])
    else:
        half = np.abs(devr[np.sign(devr) == np.sign(ext)]) if len(devr) else np.array([])
        rec = "partly" if len(devr) and np.min(np.abs(devr)) <= 0.5 * abs(ext) else "no"
        t_back = None
    ends_early = sec[-1] < t_end + AFTER and rec != "yes"
    return dict(out, kind=kind, size=ext, delay=onset_delay, recovery=rec, t_back=t_back, t_ext=t_ext,
                ends_early=bool(ends_early))


# Cells corrected after looking at the plots, where the simple line cannot follow the batch (late, fast-changing
# phases) or a regular pattern changes rather than the level. Each correction keeps its reason; the page marks them.
_BATCH = "dips, then follows the normal batch rise again"
REVIEWED = {
    ("OP10OP010TA001A001", "PY23"): dict(kind="pattern", recovery="yes",
        note="its regular saw-tooth becomes faster during the injection (about 36 instead of 22-23 cycles per 10 min)"),
    ("OP31OP031TA001A001", "T703"): dict(kind="fall", recovery="yes", note="small dip after the cooling returns; " + _BATCH),
    ("OP31OP031TA001A001", "FT704"): dict(kind="swing", recovery="yes", note="surges, then dips after the cooling returns"),
    ("OP31OP031TA001A001", "FT703"): dict(kind="swing", recovery="yes", note="surges, then dips after the cooling returns"),
    ("OP31OP031TA001A001", "PDI702"): dict(kind="swing", recovery="yes", note="swings after the cooling returns"),
    ("OP31OP031TA001A002", "T703"): dict(kind="fall", recovery="yes", note="small dip after the cooling returns; " + _BATCH),
    ("OP31OP031TA001A002", "T709"): dict(kind="swing", recovery="yes", note="a bump after the cooling returns; " + _BATCH),
    ("OP31OP031TA001A002", "T712"): dict(kind="fall", recovery="yes", note="dips after the cooling returns"),
    ("OP31OP031TA001A002", "FT703"): dict(kind="swing", recovery="yes", note="surges, then dips after the cooling returns"),
    ("OP31OP031TA001A002", "PDI702"): dict(kind="swing", recovery="yes", note="swings after the cooling returns"),
    ("OP29OP029TA001A002", "T703"): dict(kind="fall", recovery="partly", note="dips with each pressure drop; the pattern repeats"),
    ("OP29OP029TA001A002", "T709"): dict(kind="fall", recovery="partly", note="dips with each pressure drop; the pattern repeats"),
    ("OP29OP029TA001A002", "T711"): dict(kind="none", recovery="", delay=None, note="its large rise is the late phase of the batch (seen in the normal run too), not a reaction"),
    ("OP29OP029TA001A002", "T712"): dict(kind="none", recovery="", delay=None, note="its large rise is the late phase of the batch (seen in the normal run too), not a reaction"),
    ("OP29OP029TA001A002", "PDI702"): dict(kind="swing", recovery="partly", note="swings with each pressure drop; the pattern repeats"),
    ("OP29OP029TA001A002", "FT704"): dict(kind="swing", recovery="partly", note="surges with each pressure drop; the pattern repeats"),
    ("OP29OP029TA001A002", "FT703"): dict(kind="swing", recovery="partly", note="surges with each pressure drop; the pattern repeats"),
}


def analyse(recs, frames, events) -> list[dict]:
    """One result per annotated anomaly: its times and the reaction of each of the 11 sensors."""
    res = {s: float(np.median([resolution_step(frames[r.key][s]) for r in recs])) for s in SENSORS11}
    rows = []
    for _, e in events.iterrows():
        r = next(x for x in recs if x.op == e["OP"] and x.run_type == "anomalous")
        df = frames[r.key]
        cat = e["Category"] if isinstance(e["Category"], str) else None
        pb, pe = _t(e["Perturbation begin"]), _t(e["Perturbation end"])
        b, en = int(e["begin_s"]), int(e["end_s"])
        annotated = [x.strip() for x in str(e["Annotated sensors"]).split(",")]
        row = dict(op=e["OP"], id=e["ID"], key=e["OP"] + e["ID"], cls=e["Class"], cat=cat or "none", run=r.key,
                   annotated=annotated, first=e["First begin"], last=e["Last end"], b=b, e=en,
                   pb=pb if cat == "transient" else None, pe=pe if cat == "transient" else None, sensors={})
        if cat in ("recurrent", "permanent"):
            row["special"] = ("Leaking valve: many short spikes over (almost) the whole run, so there is no clean "
                              "'before' period. Shown: the sensors the experts annotated.")
            for s in SENSORS11:
                row["sensors"][s] = dict(kind="spikes", recovery="n/a") if s in annotated else dict(kind="n/a")
        elif e["OP"] == "OP29" and e["ID"].endswith("A003"):
            row["special"] = "Only 11 seconds at the very end of the recording: there is no 'after' to judge."
            for s in SENSORS11:
                row["sensors"][s] = dict(kind="n/a")
        elif not any(s in SENSORS11 for s in annotated) and e["Class"] == "Anomaly":
            row["special"] = (f"Seen only in {', '.join(annotated)}, a heater temperature that is not among the 11 "
                              "sensors; this side effect overlaps with A001.")
            for s in SENSORS11:
                row["sensors"][s] = dict(kind="n/a")
        else:
            t_on = pb if (cat == "transient" and pb is not None) else b
            for s in SENSORS11:
                row["sensors"][s] = analyse_one(df, s, t_on, en, res[s])
                fix = REVIEWED.get((row["key"], s))
                if fix:   # the automatic size and timing may describe something else, so they are dropped
                    base = {k: v for k, v in row["sensors"][s].items() if k not in ("size", "delay", "t_back", "t_ext")}
                    row["sensors"][s] = dict(base, **fix, reviewed=True)
        rows.append(row)
    return rows
