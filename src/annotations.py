"""
Turning the nested YAML annotation files into flat tables.

Important structure facts (checked on all six YAML files):
* One anomaly 'id' can appear several times. Each repeat describes a
  different affected piece of equipment and/or a different sensor in which
  the effect was observed. Counting YAML entries therefore over-counts events.
* hasBeginning / hasEnd are either one time or a LIST of times. A list means
  the event consists of several separate intervals (recurrent anomalies).
* class 'ConfirmedAnomaly' entries describe a deliberately applied
  disturbance (Perturbation + PerturbationMode).
  class 'Anomaly' entries (OP29 only) have no perturbation; their
  PerturbationMode times are the placeholder 00:00:00 and the observation is
  stored under 'wasOriginatedBy' instead of 'hasLocalEffect'.
* A few intervals end before they begin (data-entry errors). They are kept
  in the tables, flagged, and excluded from shading and analysis.
"""
from __future__ import annotations

import pandas as pd

from .data_loader import load_yaml, seconds_to_time, time_to_seconds
from .metadata import SENSORS


def has_time(v) -> bool:
    """True if v is a usable 'HH:MM:SS' value (not None/NaN/placeholder)."""
    return isinstance(v, str) and v not in ("", "00:00:00")


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _state_text(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    return str(v)


def flatten_annotations(op: str, file_name: str, yaml_path: str,
                        rec_start_s: int, rec_end_s: int) -> pd.DataFrame:
    """One row per (YAML entry, interval)."""
    doc = load_yaml(yaml_path)
    rows = []
    for entry_no, a in enumerate(doc.get("anomalies", []), start=1):
        pm = a.get("PerturbationMode") or {}
        system = ((pm.get("happenedAt") or {}).get("System")) or {}
        local = ((pm.get("hasLocalEffect") or {}).get("LocalEffect")) or {}
        observation = ((a.get("wasOriginatedBy") or {}).get("Observation")) or {}
        effect = local or observation
        sensor = (((effect.get("madeBySensor") or {}).get("Sensor")) or {}).get("id")
        prop = ((effect.get("observedProperty") or {}).get("ObservableProperty"))
        feature = ((effect.get("hasFeatureOfInterest") or {}).get("FeatureOfInterest"))

        pm_b, pm_e = pm.get("hasBeginning"), pm.get("hasEnd")
        pm_valid = pm_b is not None and str(pm_b) not in ("00:00:00", "0")
        begins, ends = _as_list(a.get("hasBeginning")), _as_list(a.get("hasEnd"))
        if len(begins) != len(ends):
            raise ValueError(f"{yaml_path}: entry {entry_no} has {len(begins)} begins and {len(ends)} ends")

        for k, (b, e) in enumerate(zip(begins, ends), start=1):
            bs, es = time_to_seconds(b), time_to_seconds(e)
            issues = []
            if es < bs:
                issues.append("end is before beginning")
            if k > 1 and bs < time_to_seconds(begins[k - 2]):
                issues.append("listed out of chronological order")
            if bs < rec_start_s or es > rec_end_s:
                issues.append("outside recording time range")
            rows.append({
                "OP": op, "File": file_name, "Entry": entry_no, "Interval no.": k,
                "Intervals in entry": len(begins),
                "ID": a.get("id"), "Class": a.get("class"), "Category": a.get("hasCategory"),
                "Recovery action": a.get("hasRecoveryAction"),
                "Perturbation": " ".join(str(a.get("Perturbation")).split()) if a.get("Perturbation") else None,
                "Perturbation mode": pm.get("label"),
                "Perturbation begin": str(pm_b) if pm_valid else None,
                "Perturbation end": str(pm_e) if pm_valid else None,
                "Equipment ID": system.get("id"), "Equipment": system.get("label"),
                "Equipment function": " ".join(str(system.get("hasFunction", "")).split()) or None,
                "Normal state": _state_text(system.get("hasNormalState")),
                "Anomalous state": _state_text(system.get("hasAnomalousState")),
                "Observed effect": effect.get("label"),
                "Sensor": sensor,
                "Sensor in project's 11": sensor in SENSORS,
                "Observed property": prop, "Feature of interest": feature,
                "Begin": str(b), "End": str(e), "begin_s": bs, "end_s": es,
                "Duration (s)": es - bs + 1 if es >= bs else None,
                "Valid interval": es >= bs,
                "Issue": "; ".join(issues) if issues else "",
            })
    return pd.DataFrame(rows)


def build_annotation_table(recordings, frames) -> pd.DataFrame:
    parts = []
    for r in recordings:
        if r.yaml_path is None:
            continue
        df = frames[r.key]
        parts.append(flatten_annotations(r.op, r.file_name, r.yaml_path,
                                         int(df["seconds_of_day"].iloc[0]),
                                         int(df["seconds_of_day"].iloc[-1])))
    return pd.concat(parts, ignore_index=True)


def build_event_table(ann: pd.DataFrame) -> pd.DataFrame:
    """
    One row per anomaly ID (per OP). Merges the repeated YAML entries.
    For an ID with several intervals, the begin/end shown are the first
    begin and last end of its valid intervals.
    """
    rows = []
    for (op, aid), g in ann.groupby(["OP", "ID"], sort=False):
        v = g[g["Valid interval"]]
        intervals = v.drop_duplicates(["begin_s", "end_s"])
        pm_b = g["Perturbation begin"].dropna()
        pm_e = g["Perturbation end"].dropna()
        first = g.iloc[0]
        sensors = list(dict.fromkeys(g["Sensor"].dropna()))
        rows.append({
            "OP": op, "ID": aid, "Class": first["Class"], "Category": first["Category"],
            "YAML entries": int(g["Entry"].nunique()),
            "Distinct intervals": len(intervals),
            "Invalid intervals": int((~g["Valid interval"]).sum()),
            "First begin": seconds_to_time(v["begin_s"].min()) if len(v) else None,
            "Last end": seconds_to_time(v["end_s"].max()) if len(v) else None,
            "begin_s": int(v["begin_s"].min()) if len(v) else None,
            "end_s": int(v["end_s"].max()) if len(v) else None,
            "Perturbation begin": pm_b.iloc[0] if len(pm_b) else None,
            "Perturbation end": pm_e.iloc[0] if len(pm_e) else None,
            "Perturbation": first["Perturbation"],
            "Perturbation mode(s)": "; ".join(dict.fromkeys(g["Perturbation mode"].dropna())),
            "Equipment": ", ".join(dict.fromkeys(g["Equipment ID"].dropna())),
            "Observed effect(s)": "; ".join(dict.fromkeys(g["Observed effect"].dropna())),
            "Annotated sensors": ", ".join(sensors),
            "Annotated sensors in the 11": ", ".join(s for s in sensors if s in SENSORS) or "none",
            "Recovery action": first["Recovery action"],
        })
    ev = pd.DataFrame(rows)
    # timing differences between labelled event and applied perturbation
    def _diff(r, ev_col, pm_col):
        if has_time(r[pm_col]) and r["Distinct intervals"] == 1:
            return int(r[ev_col] - time_to_seconds(r[pm_col]))
        return None
    ev["Event start minus perturbation start (s)"] = ev.apply(
        lambda r: _diff(r, "begin_s", "Perturbation begin"), axis=1).astype("Int64")
    ev["Event end minus perturbation end (s)"] = ev.apply(
        lambda r: _diff(r, "end_s", "Perturbation end"), axis=1).astype("Int64")
    return ev


def label_mask(df_seconds: pd.Series, ann_op_file: pd.DataFrame) -> pd.Series:
    """True for every second that falls in at least one valid annotated interval."""
    mask = pd.Series(False, index=df_seconds.index)
    for _, r in ann_op_file[ann_op_file["Valid interval"]].iterrows():
        mask |= (df_seconds >= r["begin_s"]) & (df_seconds <= r["end_s"])
    return mask
