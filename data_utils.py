"""Loading and preprocessing of the batch distillation dataset (CSV measurements and YAML annotations).

No Streamlit code here; `python data_utils.py` prints a short summary for checking.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import yaml

# Sensor metadata. Units: the README gives none; the YAML files use mbar for PY23/PDI702
# and degC for temperatures. Flow units are not stated, so they are left empty.
OPS = ["OP10", "OP17", "OP18", "OP22", "OP29", "OP31"]

SENSORS = {
    # id: (friendly name, group, unit, where, plain-language meaning)
    "FT703": ("Distillate (top product) flow", "Flow", "",
              "Line from buffer vessel V002 to the product receiver (pump P702)",
              "How much purified liquid is being taken out as product."),
    "FT704": ("Reflux flow", "Flow", "",
              "Line from buffer vessel V002 back to the column top (pump P701)",
              "How much condensed liquid is sent back down the column to improve separation."),
    "FYI702": ("Cooling-water flow signal", "Flow", "",
               "Cooling-water loop of the condensers HE001/HE002 (thermostat TCU1)",
               "How strongly the condensers are being cooled. It moves in steps, not smoothly."),
    "PDI701": ("Pressure difference along the column", "Pressure", "mbar (assumed)",
               "Along the column",
               "How hard the vapour has to push to get through the column; rises with vapour load."),
    "PDI702": ("Buffer-vessel pressure difference", "Pressure", "mbar",
               "Buffer vessel V002 (collects condensed liquid)",
               "A proxy for the liquid level in the buffer vessel. The pumps are controlled to keep it at about 2 mbar."),
    "PY23": ("System pressure", "Pressure", "mbar",
             "Top vessel G001 (controlled by vacuum throttle valve TV1)",
             "The operating pressure of the whole plant. Each operating point runs at its own pressure."),
    "T703": ("Reboiler liquid temperature", "Temperature", "°C",
             "Liquid inside the reboiler vessel V001 (bottom)",
             "Temperature of the boiling mixture. Rises slowly as the light component boils away."),
    "T709": ("Temperature below section C001", "Temperature", "°C",
             "Bottom of the column, just above the reboiler",
             "Highest temperature inside the column."),
    "T711": ("Temperature between C001 and C002", "Temperature", "°C",
             "Lower-middle of the column", "Column temperature, lower middle."),
    "T712": ("Temperature between C002 and C003", "Temperature", "°C",
             "Upper-middle of the column", "Column temperature, upper middle."),
    "T705": ("Temperature at top of section C003", "Temperature", "°C",
             "Top of the column (where vapour leaves)",
             "Temperature where the vapour leaves the column."),
}
SENSOR_ORDER = ["FT703", "FT704", "FYI702", "PDI701", "PDI702", "PY23",
                "T703", "T709", "T711", "T712", "T705"]   # temps bottom -> top
GROUP_COLORS = {"Flow": "#2a78b5", "Pressure": "#7b4fb8", "Temperature": "#c8553d"}

EXTRA_SENSORS = {
    "LS701": "Not described in the dataset; only takes the values 0 and 1",
    "LS702": "Not described in the dataset; always 1",
    "T701": "Temperature of the main reboiler heater H701 (named in the OP29 YAML), ~340-440",
    "T702": "Temperature of heater H702, upper part of reboiler V001 (°C)",
    "T704": "Temperature of heater H704, column section C002 (°C)",
    "T706": "Temperature of heater H706, column section C001 (°C)",
    "T708": "Temperature of heater H708, column section C003 (°C)",
}


def sensor_label(s: str, with_unit: bool = True) -> str:
    name, _, unit, _, _ = SENSORS[s]
    return f"{s} · {name}" + (f" [{unit}]" if with_unit else "")


def unit(s: str) -> str:
    return SENSORS[s][2] if s in SENSORS else ""


# Time helpers
def to_seconds(t) -> float | None:
    """'HH:MM:SS' (or int seconds) -> seconds since midnight. None stays None."""
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    h, m, s = str(t).strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def fmt_hms(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


def fmt_dur(sec: float) -> str:
    sec = int(round(sec))
    if sec < 60:
        return f"{sec} s"
    if sec < 3600:
        return f"{sec // 60} min {sec % 60:02d} s"
    return f"{sec // 3600} h {(sec % 3600) // 60:02d} min"


# Loading the runs
def discover_runs(root: str | Path) -> pd.DataFrame:
    root = Path(root)
    rows = []
    for op in OPS:
        for f in sorted((root / op / "measurements").glob("*.csv")):
            stem = f.stem
            kind = "Normal" if stem.startswith("train_normal") else "Anomalous"
            num = int(stem.split("_")[-1])
            ann = root / op / "annotations" / f"{stem}.yaml"
            rows.append(dict(run_id=f"{op} | {kind} #{num}", op=op, kind=kind, number=num,
                             split="train" if kind == "Normal" else "test",
                             file=f"{op}/measurements/{f.name}", path=str(f),
                             annotation=str(ann) if ann.exists() else None))
    return pd.DataFrame(rows)


def load_run(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["clock_s"] = df["Time"].map(to_seconds)
    df["elapsed_s"] = df["clock_s"] - df["clock_s"].iloc[0]
    df["elapsed_min"] = df["elapsed_s"] / 60.0
    # A real datetime (dummy date) so Plotly shows a proper clock axis
    df["clock"] = pd.Timestamp("2000-01-01") + pd.to_timedelta(df["clock_s"], unit="s")
    df["RR"] = df["FT704"] / df["FT703"].where(df["FT703"] > 0.02)  # reflux ratio, undefined at ~zero flow
    df["interpolated"] = flag_interpolated(df)
    return df


def flag_interpolated(df: pd.DataFrame, min_len: int = 30) -> pd.Series:
    """Rows where ALL 11 sensors follow a perfect straight line for >= min_len seconds.
    These are long gaps that were filled in (interpolated)."""
    x = df[SENSOR_ORDER].to_numpy(dtype=float)
    d2 = np.abs(np.diff(x, n=2, axis=0))
    scale = np.maximum(np.abs(x[1:-1]), 1.0)
    straight = np.zeros(len(df), dtype=bool)
    straight[1:-1] = (d2 / scale < 1e-7).all(axis=1)
    # also require some change (not just a frozen signal)
    s = pd.Series(straight)
    grp = (s != s.shift()).cumsum()
    sizes = s.groupby(grp).transform("size")
    long = s & (sizes >= min_len)
    # extend by one row on each side (the anchor points)
    long = long | long.shift(1, fill_value=False) | long.shift(-1, fill_value=False)
    return long.to_numpy()


def segments(mask, clock_s) -> list[tuple[float, float]]:
    """Contiguous True stretches -> list of (start_s, end_s)."""
    m = pd.Series(np.asarray(mask, dtype=bool))
    if not m.any():
        return []
    g = (m != m.shift()).cumsum()
    out = []
    cs = np.asarray(clock_s)
    for _, idx in m[m].groupby(g[m]).groups.items():
        out.append((float(cs[idx[0]]), float(cs[idx[-1]])))
    return out


# Annotations (YAML) -> tables
def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def load_annotations(root: str | Path, runs: pd.DataFrame) -> pd.DataFrame:
    """One row per annotated *interval* (recurrent events have many intervals).
    Adds a data-quality check for every interval."""
    rows = []
    for _, r in runs[runs.annotation.notna()].iterrows():
        csv_t = pd.read_csv(r.path, usecols=["Time"])["Time"]
        f0, f1 = to_seconds(csv_t.iloc[0]), to_seconds(csv_t.iloc[-1])
        doc = yaml.safe_load(open(r.annotation, encoding="utf-8"))
        for k, a in enumerate(doc.get("anomalies", [])):
            pm = a.get("PerturbationMode") or {}
            system = ((pm.get("happenedAt") or {}).get("System") or {})
            lf = ((pm.get("hasLocalEffect") or {}).get("LocalEffect") or {})
            obs_src = "LocalEffect"
            if not lf:  # unconfirmed 'Anomaly' entries describe an Observation instead
                lf = ((a.get("wasOriginatedBy") or {}).get("Observation") or {})
                obs_src = "Observation"
            sensor = ((lf.get("madeBySensor") or {}).get("Sensor") or {}).get("id")
            begins, ends = _as_list(a.get("hasBeginning")), _as_list(a.get("hasEnd"))
            pm_b, pm_e = to_seconds(pm.get("hasBeginning")), to_seconds(pm.get("hasEnd"))
            pm_placeholder = (pm_b == 0 and pm_e == 0)
            anom_state = system.get("hasAnomalousState")
            if isinstance(anom_state, list):
                anom_state = "; ".join(map(str, anom_state))
            normal_state = system.get("hasNormalState")
            if isinstance(normal_state, list):
                normal_state = "; ".join(map(str, normal_state))
            for i, (b, e) in enumerate(zip(begins, ends)):
                bs, es = to_seconds(b), to_seconds(e)
                issues = []
                if es < bs:
                    issues.append(f"end ({e}) is before start ({b})")
                if bs < f0 or es > f1:
                    issues.append("outside the recording")
                rows.append(dict(
                    op=r.op, run_id=r.run_id, entry=k, event_id=a.get("id"),
                    status=a.get("class"), category=a.get("hasCategory") or "not given",
                    recovery=a.get("hasRecoveryAction"),
                    perturbation=(a.get("Perturbation") or "—"),
                    mode_label=(pm.get("label") or "—"),
                    system_id=system.get("id") or "—", system_label=system.get("label") or "—",
                    normal_state=normal_state or "—", anomalous_state=anom_state or "—",
                    effect=lf.get("label") or "—", effect_source=obs_src,
                    sensor=sensor or "—", sensor_in_11=sensor in SENSORS,
                    feature=((lf.get("hasFeatureOfInterest") or {}).get("FeatureOfInterest")) or "—",
                    n_intervals=len(begins), interval_no=i + 1,
                    begin=str(b), end=str(e), begin_s=bs, end_s=es,
                    duration_s=(es - bs) if es >= bs else np.nan,
                    begin_elapsed_min=(bs - f0) / 60, end_elapsed_min=(es - f0) / 60,
                    pm_begin=None if pm_placeholder else pm.get("hasBeginning"),
                    pm_end=None if pm_placeholder else pm.get("hasEnd"),
                    pm_begin_s=None if pm_placeholder else pm_b,
                    pm_end_s=None if pm_placeholder else pm_e,
                    valid=len(issues) == 0, issue="; ".join(issues) or "OK",
                ))
    df = pd.DataFrame(rows)
    df["status_simple"] = df.status.map({"ConfirmedAnomaly": "Confirmed",
                                         "Anomaly": "Unconfirmed observation"}).fillna(df.status)
    return df


def event_table(ann: pd.DataFrame) -> pd.DataFrame:
    """One row per (event id, sensor/system observation) – a readable catalogue."""
    g = ann.groupby(["op", "event_id", "entry"], sort=False)
    out = g.agg(status=("status_simple", "first"), category=("category", "first"),
                perturbation=("perturbation", "first"), mode=("mode_label", "first"),
                system=("system_id", "first"), effect=("effect", "first"),
                sensor=("sensor", "first"), sensor_in_11=("sensor_in_11", "first"),
                intervals=("interval_no", "size"), first_begin=("begin_s", "min"),
                last_end=("end_s", "max"), total_s=("duration_s", "sum"),
                invalid=("valid", lambda v: int((~v).sum())),
                pm_begin=("pm_begin", "first"), pm_end=("pm_end", "first"),
                pm_begin_s=("pm_begin_s", "first"), pm_end_s=("pm_end_s", "first")).reset_index()
    out["first_begin_hms"] = out.first_begin.map(fmt_hms)
    out["last_end_hms"] = out.last_end.map(fmt_hms)
    out["onset_delay_s"] = out.first_begin - out.pm_begin_s       # event start minus disturbance start
    out["tail_s"] = out.last_end - out.pm_end_s                    # how long effects outlast it
    return out


# Summary tables
def run_summary(runs: pd.DataFrame, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for _, r in runs.iterrows():
        d = data[r.run_id]
        rows.append(dict(
            run_id=r.run_id, op=r.op, kind=r.kind, file=r.file, rows=len(d),
            start=d.Time.iloc[0], end=d.Time.iloc[-1],
            duration_min=round(d.elapsed_s.iloc[-1] / 60, 1),
            missing_values=int(d[SENSOR_ORDER].isna().sum().sum()),
            gaps=int((d.clock_s.diff().dropna() != 1).sum()),
            interpolated_s=int(d.interpolated.sum()),
            pressure_mbar=round(d.PY23.median(), 0),
            reflux_ratio=round(d.FT704.median() / d.FT703.median(), 2),
            T703_start=round(d.T703.iloc[:60].mean(), 1), T703_end=round(d.T703.iloc[-60:].mean(), 1),
            windows_210s=max(len(d) - 210 + 1, 0),
        ))
    return pd.DataFrame(rows)


def sensor_stats(data: dict[str, pd.DataFrame], runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in runs.iterrows():
        d = data[r.run_id]
        for s in SENSOR_ORDER:
            x = d[s]
            rows.append(dict(run_id=r.run_id, op=r.op, kind=r.kind, sensor=s, unit=unit(s),
                             mean=x.mean(), std=x.std(), min=x.min(), p01=x.quantile(.01),
                             median=x.median(), p99=x.quantile(.99), max=x.max(),
                             first=x.iloc[0], last=x.iloc[-1]))
    return pd.DataFrame(rows)


def coverage_table(data, runs) -> pd.DataFrame:
    """% of anomalous-run samples that fall OUTSIDE the min..max seen in the normal run(s) of the same OP."""
    out = {}
    for op in OPS:
        norm = pd.concat([data[i] for i in runs[(runs.op == op) & (runs.kind == "Normal")].run_id])
        an = pd.concat([data[i] for i in runs[(runs.op == op) & (runs.kind == "Anomalous")].run_id])
        out[op] = {s: 100 * ((an[s] < norm[s].min()) | (an[s] > norm[s].max())).mean() for s in SENSOR_ORDER}
    return pd.DataFrame(out)


def spike_counts(data, runs, sensor="FT703", jump=0.3) -> pd.DataFrame:
    """Count short spikes: readings more than `jump` (sensor units) above the run's median."""
    rows = []
    for _, r in runs.iterrows():
        s = data[r.run_id][sensor]
        x = s > s.median() + jump
        rows.append(dict(run_id=r.run_id, op=r.op, kind=r.kind,
                         spike_events=int((x & ~x.shift(1, fill_value=False)).sum()),
                         seconds_above=int(x.sum())))
    return pd.DataFrame(rows)


def label_mask(d: pd.DataFrame, ann_run: pd.DataFrame, confirmed_only=True) -> np.ndarray:
    """Per-second 0/1 'is inside an annotated interval' for one run (valid intervals only)."""
    a = ann_run[ann_run.valid]
    if confirmed_only:
        a = a[a.status == "ConfirmedAnomaly"]
    m = np.zeros(len(d), dtype=bool)
    cs = d.clock_s.to_numpy()
    for b, e in zip(a.begin_s, a.end_s):
        m |= (cs >= b) & (cs <= e)
    return m


# Self-test
if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "batch_distillation_dataset")
    runs = discover_runs(root)
    data = {r.run_id: load_run(r.path) for _, r in runs.iterrows()}
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(run_summary(runs, data).to_string())
    ann = load_annotations(root, runs)
    print(len(ann), "intervals;", (~ann.valid).sum(), "invalid")
    print(ann[~ann.valid][["op", "event_id", "sensor", "begin", "end", "issue"]].to_string())
    ev = event_table(ann)
    print(ev[["op", "event_id", "status", "category", "sensor", "intervals", "first_begin_hms",
              "last_end_hms", "onset_delay_s", "tail_s"]].to_string())
    for rid, d in data.items():
        for a, b in segments(d.interpolated, d.clock_s):
            print("interpolated:", rid, fmt_hms(a), "-", fmt_hms(b), fmt_dur(b - a))
    print(coverage_table(data, runs).round(1).to_string())
    print(spike_counts(data, runs).to_string())
