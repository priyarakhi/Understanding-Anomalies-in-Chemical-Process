"""
Loading the measurement CSV files and the YAML annotation files.

Nothing in this module changes the data values. Each recording is returned
exactly as stored in the CSV, with three helper columns added:
    seconds_of_day : clock time converted to seconds after midnight
    elapsed_s      : seconds since the first row of that recording
    timestamp      : clock time as a datetime on a dummy date (for plotting)
The dataset gives clock times only (HH:MM:SS) and no calendar dates, so the
dummy date 2000-01-01 is used purely so that plotting libraries can draw a
time axis. It carries no meaning.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from .metadata import OPERATING_POINTS, SENSORS

DUMMY_DATE = "2000-01-01"


def default_data_dir() -> Path:
    """Where the app looks for the dataset unless BATCH_DATA_DIR is set."""
    env = os.environ.get("BATCH_DATA_DIR")
    if env:
        return Path(env)
    root = Path(__file__).resolve().parent.parent
    for d in (root / "batch_distillation_dataset", root / "data" / "batch_distillation_dataset"):
        if d.is_dir():
            return d
    return root / "batch_distillation_dataset"


def time_to_seconds(t) -> int:
    """'16:20:44' -> 58844. Accepts strings like H:MM:SS or HH:MM:SS."""
    h, m, s = (int(x) for x in str(t).strip().split(":"))
    return h * 3600 + m * 60 + s


def seconds_to_time(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


@dataclass(frozen=True)
class RecordingInfo:
    op: str
    file_name: str          # e.g. 'train_normal_experiment_001.csv'
    run_type: str           # 'normal' or 'anomalous'
    run_number: str         # '001' / '002'
    csv_path: str
    yaml_path: str | None   # only anomalous runs have annotations

    @property
    def key(self) -> str:
        return f"{self.op} | {self.label}"

    @property
    def label(self) -> str:
        kind = "Normal" if self.run_type == "normal" else "Anomalous"
        return f"{kind} run {self.run_number}"


def discover_recordings(data_dir: Path) -> list[RecordingInfo]:
    """Find every measurement CSV following the README folder structure."""
    pattern = re.compile(r"^(train_normal|test_anormal)_experiment_(\d{3})\.csv$")
    found = []
    for op in OPERATING_POINTS:
        mdir = Path(data_dir) / op / "measurements"
        if not mdir.is_dir():
            continue
        for f in sorted(mdir.iterdir()):
            m = pattern.match(f.name)
            if not m:
                continue  # ignores e.g. macOS '._' resource files
            run_type = "normal" if m.group(1) == "train_normal" else "anomalous"
            yaml_path = Path(data_dir) / op / "annotations" / f.name.replace(".csv", ".yaml")
            found.append(RecordingInfo(
                op=op, file_name=f.name, run_type=run_type, run_number=m.group(2),
                csv_path=str(f),
                yaml_path=str(yaml_path) if yaml_path.exists() else None))
    # normal runs first, then anomalous, within each OP
    found.sort(key=lambda r: (r.op, r.run_type != "normal", r.run_number))
    return found


def load_recording(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["Time"] = df["Time"].astype(str)
    df["seconds_of_day"] = df["Time"].map(time_to_seconds)
    df["elapsed_s"] = df["seconds_of_day"] - df["seconds_of_day"].iloc[0]
    df["timestamp"] = pd.to_datetime(DUMMY_DATE + " " + df["Time"])
    return df


def load_yaml(yaml_path: str) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def recording_summary(recs: list[RecordingInfo], frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for r in recs:
        df = frames[r.key]
        dt = df["seconds_of_day"].diff().dropna()
        rows.append({
            "Operating point": r.op,
            "Run": r.label,
            "Type": r.run_type,
            "File": r.file_name,
            "Start": df["Time"].iloc[0],
            "End": df["Time"].iloc[-1],
            "Rows": len(df),
            "Duration (min)": round((df["seconds_of_day"].iloc[-1] - df["seconds_of_day"].iloc[0]) / 60, 1),
            "Time step (s)": ", ".join(str(int(v)) for v in sorted(dt.unique())),
            "Missing values (11 sensors)": int(df[SENSORS].isna().sum().sum()),
            "Has annotation file": r.yaml_path is not None,
        })
    return pd.DataFrame(rows)
