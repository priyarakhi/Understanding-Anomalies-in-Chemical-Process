"""
Analysis functions used by the dashboard (no Streamlit code in here, so
everything can be tested on its own).

Contents
1. Data-quality checks
2. Normal-vs-anomalous comparison (coverage of value ranges)
3. Question 1: how each of the 11 sensors responds to an annotated event
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data_loader import seconds_to_time
from .metadata import SENSORS


# ---------------------------------------------------------------------------
# 1. Data-quality checks
# ---------------------------------------------------------------------------
def resolution_step(x: pd.Series) -> float:
    """
    Typical step size of a sensor = median of the non-zero changes between
    consecutive readings. For the temperature sensors this is 0.021 °C in
    every file, i.e. the sensor's resolution. (The smallest gap between
    distinct values is NOT used, because some files contain values halfway
    between two readings, e.g. 72.4595, which would give a misleadingly tiny
    step.)
    """
    d = np.abs(np.diff(x.dropna().to_numpy(dtype=float)))
    d = d[d > 1e-9]
    return float(np.median(d)) if len(d) else 0.0


def find_straight_line_segments(df: pd.DataFrame, min_len: int = 10, cols=SENSORS) -> list[dict]:
    """
    Find stretches in which ALL given sensors change by exactly the same amount
    every second (second difference ~ 0). Real noisy measurements never do this
    for minutes, so such stretches are most likely filled-in (interpolated) data.
    """
    X = df[cols].to_numpy(dtype=float)
    if len(X) < 3:
        return []
    dd = np.abs(np.diff(X, n=2, axis=0))
    tol = 1e-6 * np.maximum(1.0, np.abs(X[1:-1]))
    lin = (dd <= tol).all(axis=1)
    out, start = [], None
    for i, v in enumerate(np.append(lin, False)):
        if v and start is None:
            start = i
        elif not v and start is not None:
            a, b = start, i + 1          # rows a .. b (inclusive) lie on one line
            if b - a + 1 >= min_len:
                out.append({"start_row": a, "end_row": b,
                            "Start": df["Time"].iloc[a], "End": df["Time"].iloc[b],
                            "Length (s)": b - a + 1})
            start = None
    return out


def quality_table(recordings, frames) -> pd.DataFrame:
    rows = []
    for r in recordings:
        df = frames[r.key]
        dt = df["seconds_of_day"].diff().dropna()
        segs = find_straight_line_segments(df)
        rows.append({
            "OP": r.op, "Run": r.label, "Rows": len(df),
            "Regular 1-s steps": bool((dt == 1).all()),
            "Duplicate timestamps": int(df["Time"].duplicated().sum()),
            "Missing values": int(df[SENSORS].isna().sum().sum()),
            "Straight-line (filled) seconds": int(sum(s["Length (s)"] for s in segs)),
            "Filled stretch": "; ".join(f'{s["Start"]}-{s["End"]}' for s in segs) or "none",
            "Negative PDI701 values": int((df["PDI701"] < 0).sum()),
            "Negative PDI702 values": int((df["PDI702"] < 0).sum()),
            "FYI702 exactly 0 (s)": int((df["FYI702"] == 0).sum()),
        })
    return pd.DataFrame(rows)


def sensor_stats(df: pd.DataFrame, cols=SENSORS) -> pd.DataFrame:
    rows = []
    for s in cols:
        x = df[s]
        rows.append({"Sensor": s, "Min": x.min(), "1st pct": x.quantile(.01), "Median": x.median(),
                     "Mean": x.mean(), "99th pct": x.quantile(.99), "Max": x.max(),
                     "Std. dev.": x.std(), "Distinct values": x.nunique(),
                     "Typical step": resolution_step(x)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. Normal vs anomalous: does the normal data cover the anomalous data?
# ---------------------------------------------------------------------------
def coverage_table(recordings, frames, exclude_mask=None) -> pd.DataFrame:
    """
    Per OP and sensor: % of anomalous-run samples whose value lies inside the
    [min, max] range seen in that OP's normal run(s).
    A low value means the anomalous run visits values the normal data never
    shows - a model trained on normal data has never seen such values.
    """
    rows = []
    ops = sorted({r.op for r in recordings})
    for op in ops:
        normals = [frames[r.key] for r in recordings if r.op == op and r.run_type == "normal"]
        anomal = [frames[r.key] for r in recordings if r.op == op and r.run_type == "anomalous"]
        if not normals or not anomal:
            continue
        N = pd.concat(normals)
        A = anomal[0]
        row = {"OP": op}
        for s in SENSORS:
            lo, hi = N[s].min(), N[s].max()
            row[s] = round(100 * ((A[s] >= lo) & (A[s] <= hi)).mean(), 1)
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Question 1 - sensor response to an event
# ---------------------------------------------------------------------------
Q1_PARAMS = dict(
    baseline_s=600,      # reference window before the onset (10 min)
    min_baseline_s=120,  # skip a sensor-event pair if less baseline is available
    smooth_s=31,         # centred rolling median (s): removes noise and very short spikes
    after_s=600,         # how long after the annotated end we look for a return to normal
    hold_s=60,           # a return to normal must last this long to count
    ref_step_s=30,       # spacing of the reference windows
    ref_margin_s=600,    # reference windows keep this distance from annotated events
    clear_pct=99,        # 'clear change'  : peak larger than 99 % of reference peaks
    weak_pct=95,         # 'possible change': peak larger than 95 % of reference peaks
    min_clear_z=5.0,     # lower limits for the thresholds
    min_weak_z=3.0,
    stage_tol_c=2.5,     # reference windows: T703 within +/- this of the event's T703
    fast_lag_s=120,      # 'fast change' = change of the smoothed signal within 2 min
    fast_min_steps=5,    # a fast change must be at least 5 resolution steps
    min_ref=20,          # fewer reference windows -> fixed fallback thresholds
    fallback_clear_z=10.0,
    fallback_weak_z=6.0,
    filled_after_s=1800, # ignore 30 min after a filled (straight-line) stretch
)


def _smooth(y: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(y).rolling(n, center=True, min_periods=1).median().to_numpy()


def _z_path(y_raw, y_s, step, i, n_after, p):
    """
    Level deviation from the expected path, in units of the noise level.
    Expected path = straight line fitted through the `baseline_s` raw samples
    before index i (the onset). Noise level sigma = spread of the baseline
    around that line (at least the sensor's resolution step).
    Returns (z, expected, sigma, slope) or None if not enough baseline.
    """
    b0 = max(0, i - p["baseline_s"])
    if i - b0 < p["min_baseline_s"]:
        return None
    yb = y_raw[b0:i]
    t = np.arange(b0 - i, 0, dtype=float)
    if np.ptp(yb) == 0:
        slope, icpt = 0.0, float(yb[0])
    else:
        slope, icpt = np.polyfit(t, yb, 1)
    sigma = max(float(np.std(yb - (slope * t + icpt))), step, 1e-9)
    j = min(len(y_s), i + n_after)
    tt = np.arange(0, j - i, dtype=float)
    expected = slope * tt + icpt
    return (y_s[i:j] - expected) / sigma, expected, sigma, slope


def _fast_change(y_s, i, dur, lag):
    """Signed change of the smoothed signal over `lag` seconds, for t = i .. i+dur."""
    j = min(len(y_s), i + dur + 1)
    if i - lag < 0:
        return None
    return y_s[i:j] - y_s[i - lag:j - lag]


def reference_thresholds(series_list, step, duration_s, p=Q1_PARAMS):
    """
    'How large do the two scores get when nothing is annotated?'
    series_list: list of (y_raw, y_s, allowed_onset_mask) for reference data.
    Every `ref_step_s` seconds an imaginary event of the same duration is
    placed and scored with exactly the same method. The thresholds are high
    percentiles of these reference scores.
    """
    peaks, fasts = [], []
    for y_raw, y_s, allowed in series_list:
        allowed = np.asarray(allowed, dtype=bool)
        n = len(y_raw)
        for i in range(p["baseline_s"], n - duration_s - 1, p["ref_step_s"]):
            if not allowed[i]:
                continue
            res = _z_path(y_raw, y_s, step, i, duration_s + 1, p)
            fc = _fast_change(y_s, i, duration_s, p["fast_lag_s"])
            if res is None or fc is None:
                continue
            peaks.append(np.abs(res[0]).max())
            fasts.append(np.abs(fc).max())
    if len(peaks) < p["min_ref"]:
        return dict(clear=p["fallback_clear_z"], weak=p["fallback_weak_z"],
                    fast_clear=np.inf, fast_weak=np.inf, n_ref=len(peaks), fallback=True)
    return dict(
        clear=max(float(np.percentile(peaks, p["clear_pct"])), p["min_clear_z"]),
        weak=max(float(np.percentile(peaks, p["weak_pct"])), p["min_weak_z"]),
        fast_clear=max(float(np.percentile(fasts, p["clear_pct"])), p["fast_min_steps"] * step, 1e-9),
        fast_weak=max(float(np.percentile(fasts, p["weak_pct"])), p["fast_min_steps"] * step, 1e-9),
        n_ref=len(peaks), fallback=False)


def sensor_response(df, sensor, onset_s, end_s, thr, p=Q1_PARAMS, y_s=None):
    """
    Score one sensor for one event. Two questions are asked:
      A) Level shift: how far does the (smoothed) signal move away from the
         straight line that continues its behaviour of the 10 min before the
         onset? Measured as z = deviation / noise level.
      B) Fast change: what is the largest change within 2 minutes? Slow batch
         drift hardly contributes here, so short steps become visible.
    Each score is compared with the same score computed on reference windows
    (moments without annotated events at a similar batch stage):
      'clear'    = larger than 99 % of the reference values
      'possible' = larger than 95 % of the reference values
    Return to normal: after the largest level deviation, the deviation falls
    to at most 25 % of that peak (or below 3 noise levels) and stays there for
    60 s, searched until 10 min after the annotated end.
    """
    sod = df["seconds_of_day"].to_numpy()
    y_raw = df[sensor].to_numpy(dtype=float)
    if y_s is None:
        y_s = _smooth(y_raw, p["smooth_s"])
    i = int(np.searchsorted(sod, onset_s))
    dur = int(end_s - onset_s)
    res = _z_path(y_raw, y_s, resolution_step(df[sensor]), i, dur + 1 + p["after_s"], p)
    fc = _fast_change(y_s, i, dur, p["fast_lag_s"])
    if res is None or fc is None:
        return None
    z, expected, sigma, slope = res
    zd = z[:dur + 1]
    k = int(np.argmax(np.abs(zd)))
    peak = float(zd[k])
    kf = int(np.argmax(np.abs(fc)))
    fpeak = float(fc[kf])

    def grade(v, clear, weak):
        return 2 if v >= clear else 1 if v >= weak else 0
    g_level = grade(abs(peak), thr["clear"], thr["weak"])
    g_fast = grade(abs(fpeak), thr["fast_clear"], thr["fast_weak"])
    g = max(g_level, g_fast)
    level = {2: "clear", 1: "possible", 0: "no clear change"}[g]
    changed = g > 0
    basis = " + ".join(n for n, gg in (("level shift", g_level), ("fast change", g_fast)) if gg == g and g > 0)

    delay, direction = None, ""
    if changed:
        hit_l = np.where(np.abs(zd) >= thr["weak"])[0]
        hit_f = np.where(np.abs(fc) >= thr["fast_weak"])[0]
        cands = [(int(hit_l[0]), np.sign(zd[hit_l[0]])) if len(hit_l) else None,
                 (int(hit_f[0]), np.sign(fc[hit_f[0]])) if len(hit_f) else None]
        cands = [c for c in cands if c is not None]
        if cands:
            first = min(cands, key=lambda c: c[0])
            delay = first[0]
            direction = "up" if first[1] > 0 else "down"

    recovered, rec_at = "", None
    if changed:
        target = max(0.25 * abs(peak), 3.0)
        run = 0
        for j in range(k, len(z)):
            run = run + 1 if abs(z[j]) <= target else 0
            if run >= p["hold_s"]:
                rec_at = int(sod[i + j - p["hold_s"] + 1])
                break
        if rec_at is not None:
            recovered = "yes"
        elif len(z) < dur + 1 + p["after_s"]:
            recovered = "recording ends too early"
        else:
            recovered = "no (not within 10 min after end)"

    return {
        "Sensor": sensor,
        "Change": level,
        "Detected by": basis,
        "Direction (first movement)": direction,
        "Peak level shift (z)": round(peak, 1),
        "Peak level shift (sensor units)": float(y_s[i + k] - expected[k]),
        "Largest 2-min change (sensor units)": fpeak,
        "Time of peak level shift": seconds_to_time(sod[i + k]),
        "Reaction delay (s)": delay,
        "Returned to normal": recovered,
        "Back to normal at": seconds_to_time(rec_at) if rec_at else "",
        "Back to normal vs annotated end (s)": (rec_at - end_s) if rec_at else None,
        "Noise level": sigma,
        "Level threshold clear (z)": round(thr["clear"], 1),
        "Fast-change threshold clear": thr["fast_clear"],
        "Reference windows": thr["n_ref"],
        "Few reference windows": thr.get("fallback", False),
    }


def event_onset_end(ev_row) -> tuple[int, int]:
    """Onset = earlier of annotated begin and perturbation begin; end = annotated end."""
    from .data_loader import time_to_seconds
    from .annotations import has_time
    onset = int(ev_row["begin_s"])
    if has_time(ev_row.get("Perturbation begin")):
        onset = min(onset, time_to_seconds(ev_row["Perturbation begin"]))
    return onset, int(ev_row["end_s"])


def q1_units(ann: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """
    Units analysed for Question 1: every distinct interval of every event
    that is NOT recurrent or permanent (those cover almost the whole run and
    are studied separately with spike_ratio_table).
    """
    rows = []
    keep = events[~events["Category"].isin(["recurrent", "permanent"])]
    for _, ev in keep.iterrows():
        sub = ann[(ann["OP"] == ev["OP"]) & (ann["ID"] == ev["ID"]) & ann["Valid interval"]]
        iv = sub.drop_duplicates(["begin_s", "end_s"]).sort_values("begin_s")
        for n, (_, r) in enumerate(iv.iterrows(), start=1):
            u = ev.to_dict()
            u["begin_s"], u["end_s"] = int(r["begin_s"]), int(r["end_s"])
            u["Distinct intervals"] = 1
            u["Unit"] = ev["ID"] if len(iv) == 1 else f'{ev["ID"]} ({n}/{len(iv)})'
            u["Begin"], u["End"] = r["Begin"], r["End"]
            rows.append(u)
    U = pd.DataFrame(rows)
    on_end = U.apply(lambda r: event_onset_end(r), axis=1)
    U["onset_s"] = [a for a, _ in on_end]
    U["Onset"] = U["onset_s"].map(seconds_to_time)
    U["Duration (s)"] = U["end_s"] - U["onset_s"] + 1
    return U


def _allowed_mask(sod: np.ndarray, blocked: list[tuple[int, int]], dur: int, p) -> np.ndarray:
    """Onsets whose [onset-baseline, onset+dur+after] window keeps the margin from all blocked intervals."""
    ok = np.ones(len(sod), dtype=bool)
    for b, e in blocked:
        lo = b - p["ref_margin_s"] - dur - p["after_s"]
        hi = e + p["ref_margin_s"] + p["baseline_s"]
        ok &= ~((sod >= lo) & (sod <= hi))
    return ok


def _stage_ok(df: pd.DataFrame, stage_value: float, p) -> np.ndarray:
    """Onsets where the median T703 of the preceding baseline is close to stage_value."""
    med = df["T703"].rolling(p["baseline_s"], min_periods=p["min_baseline_s"]).median().shift(1)
    return (med - stage_value).abs().le(p["stage_tol_c"]).to_numpy()


def _not_filled(df: pd.DataFrame, p) -> np.ndarray:
    """False around filled (straight-line) stretches: from baseline before them
    until `filled_after_s` after them."""
    ok = np.ones(len(df), dtype=bool)
    for seg in find_straight_line_segments(df):
        a = max(0, seg["start_row"])
        b = min(len(df), seg["end_row"] + p["filled_after_s"])
        ok[a:b] = False
    return ok


def q1_response_matrix(units: pd.DataFrame, recordings, frames, p=Q1_PARAMS) -> pd.DataFrame:
    """
    Score every Q1 unit x sensor.
    Reference ('normal behaviour') windows come first from the anomalous run
    itself, away from every analysed event (with margin): same day, same
    cooling water, same batch. Only if that gives fewer than `min_ref`
    windows are the normal run(s) of the same OP added. In both cases only
    moments at a similar batch stage (T703 close to its value before the
    event) are used, and filled stretches plus their aftermath are excluded.
    Because a filled stretch lies on a perfect line, any window overlapping it
    would have zero noise and absurdly large scores.
    """
    rows = []
    smooth_cache, filled_cache = {}, {}

    def sm(key, s):
        if (key, s) not in smooth_cache:
            smooth_cache[(key, s)] = _smooth(frames[key][s].to_numpy(dtype=float), p["smooth_s"])
        return smooth_cache[(key, s)]

    def nf(key):
        if key not in filled_cache:
            filled_cache[key] = _not_filled(frames[key], p)
        return filled_cache[key]

    for op, U in units.groupby("OP", sort=False):
        anom = [r for r in recordings if r.op == op and r.run_type == "anomalous"][0]
        norms = [r for r in recordings if r.op == op and r.run_type == "normal"]
        dfa = frames[anom.key]
        sod_a = dfa["seconds_of_day"].to_numpy()
        blocked = list(zip(U["onset_s"], U["end_s"]))
        for _, u in U.iterrows():
            dur = int(u["end_s"] - u["onset_s"])
            onset = int(u["onset_s"])
            bmask = (sod_a >= onset - p["baseline_s"]) & (sod_a < onset)
            stage = float(np.median(dfa.loc[bmask, "T703"])) if bmask.any() else float(dfa["T703"].iloc[0])
            own_mask = (_stage_ok(dfa, stage, p) & nf(anom.key)
                        & _allowed_mask(sod_a, blocked, dur, p))
            norm_masks = {r.key: _stage_ok(frames[r.key], stage, p) & nf(r.key) for r in norms}
            for s in SENSORS:
                step = max(resolution_step(frames[r.key][s]) for r in norms + [anom])
                own = [(dfa[s].to_numpy(dtype=float), sm(anom.key, s), own_mask)]
                thr = reference_thresholds(own, step, dur, p)
                source = "quiet parts of the same anomalous run"
                if thr.get("fallback"):
                    ref = own + [(frames[r.key][s].to_numpy(dtype=float), sm(r.key, s), norm_masks[r.key])
                                 for r in norms]
                    thr = reference_thresholds(ref, step, dur, p)
                    source = "same anomalous run + normal run(s) of this OP"
                res = sensor_response(dfa, s, onset, int(u["end_s"]), thr, p, y_s=sm(anom.key, s))
                if res is None:
                    continue
                annotated = [x.strip() for x in str(u["Annotated sensors"]).split(",")]
                res.update({"OP": op, "Unit": u["Unit"], "ID": u["ID"], "Class": u["Class"],
                            "Onset": u["Onset"], "End": u["End"],
                            "Batch stage T703 (°C)": round(stage, 1),
                            "Reference source": source,
                            "Annotated sensors": u["Annotated sensors"],
                            "Annotated for this sensor": s in annotated})
                rows.append(res)
    return pd.DataFrame(rows)


def spike_ratio_table(frames_by_op_anom: dict, ann: pd.DataFrame, events: pd.DataFrame,
                      window_s: int = 61) -> pd.DataFrame:
    """
    For recurrent events (many short intervals): how much 'jumpier' is each
    sensor inside the annotated spike intervals than outside them?
    Jumpiness = average absolute distance from a 61-s rolling median
    (the average, not the median, is used because spikes are short and rare).
    Ratio > 1 means the sensor is more disturbed inside the intervals.
    """
    rows = []
    rec = events[events["Category"] == "recurrent"]
    for _, ev in rec.iterrows():
        df = frames_by_op_anom[ev["OP"]]
        sub = ann[(ann["OP"] == ev["OP"]) & (ann["ID"] == ev["ID"]) & ann["Valid interval"]]
        sod = df["seconds_of_day"]
        for sensor_ann, g in sub.groupby("Sensor"):
            inside = pd.Series(False, index=df.index)
            for _, r in g.iterrows():
                inside |= (sod >= r["begin_s"]) & (sod <= r["end_s"])
            row = {"OP": ev["OP"], "ID": ev["ID"], "Intervals annotated on": sensor_ann,
                   "Number of intervals": len(g), "Seconds inside": int(inside.sum())}
            for s in SENSORS:
                med = df[s].rolling(window_s, center=True, min_periods=1).median()
                dev = (df[s] - med).abs()
                a, b = dev[inside].mean(), dev[~inside].mean()
                row[s] = round(a / b, 2) if b > 0 else np.nan
            rows.append(row)
    return pd.DataFrame(rows)
