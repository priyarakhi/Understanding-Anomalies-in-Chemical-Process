"""Shared Streamlit helpers: cached data access, page header, explanation boxes."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from . import analysis as an
from .annotations import build_annotation_table, build_event_table
from .data_loader import default_data_dir, discover_recordings, load_recording, recording_summary
from .metadata import SENSORS


# ---------------------------------------------------------------- data access
@st.cache_data(show_spinner="Loading the 13 recordings and 6 annotation files ...")
def load_all(data_dir: str):
    recs = discover_recordings(Path(data_dir))
    frames = {r.key: load_recording(r.csv_path) for r in recs}
    ann = build_annotation_table(recs, frames)
    events = build_event_table(ann)
    return recs, frames, ann, events


@st.cache_data(show_spinner="Computing data-quality checks ...")
def quality(data_dir: str):
    recs, frames, _, _ = load_all(data_dir)
    return an.quality_table(recs, frames), recording_summary(recs, frames), an.coverage_table(recs, frames)


@st.cache_data(show_spinner="Scoring every sensor for every event (takes a few seconds once) ...")
def q1_results(data_dir: str):
    recs, frames, ann, events = load_all(data_dir)
    units = an.q1_units(ann, events)
    matrix = an.q1_response_matrix(units, recs, frames)
    anom = {r.op: frames[r.key] for r in recs if r.run_type == "anomalous"}
    spikes = an.spike_ratio_table(anom, ann, events)
    return units, matrix, spikes


@st.cache_data(show_spinner="Preparing the interactive plant (all 13 recordings) ...")
def _plant_payload(data_dir: str) -> dict:
    from .plant_view import build_payload
    return build_payload(*load_all(data_dir))


@st.cache_data(show_spinner=False)
def plant_page(data_dir: str) -> str:
    from .plant_view import page_html
    return page_html(_plant_payload(data_dir))


# ---------------------------------------------------------------- page 2 "The dataset"
@st.cache_data(show_spinner="Loading this part of the recording ...", max_entries=30)
def dataset_plant(data_dir: str, key: str, a: int, b: int, focus: str | None) -> str:
    from .data_parts import rowdata
    from .plant_view import page_html
    recs, frames, ann, events = load_all(data_dir)
    r = next(x for x in recs if x.key == key)
    return page_html(dict(_plant_payload(data_dir), rowdemo=rowdata(r, frames, ann, events, a, b, focus)), start_view="row")


@st.cache_data(show_spinner=False)
def replay_choices(data_dir: str):
    """Recording labels and, per recording, the moments where a replay can start."""
    from .data_parts import moments, recording_label
    recs, frames, _, events = load_all(data_dir)
    return ({r.key: recording_label(r, frames) for r in recs}, {r.key: moments(r, frames, events) for r in recs},
            {r.key: (int(frames[r.key]["seconds_of_day"].iloc[0]), int(frames[r.key]["seconds_of_day"].iloc[-1])) for r in recs})


@st.cache_data(show_spinner=False)
def anomaly_choices(data_dir: str):
    from .data_parts import anomaly_options
    return anomaly_options(load_all(data_dir)[3])


@st.cache_data(show_spinner=False, max_entries=30)
def example(data_dir: str, key: str) -> dict:
    from .data_parts import example as f
    return f(*load_all(data_dir), key)


@st.cache_data(show_spinner=False)
def ds_part(data_dir: str, part: str):
    from . import data_view as dv
    recs, frames, ann, events = load_all(data_dir)
    if part == "files":
        return dv.files_table(recs, frames, events)
    if part == "sensors":
        return dv.sensor_table()
    if part == "ops":
        from .data_parts import op_bars
        return op_bars(recs, frames)
    if part == "normal":
        from .data_parts import normal_charts
        return normal_charts(recs, frames)
    if part == "fill":
        return dv.fill_chart(recs, frames, fill_info(data_dir))
    if part == "whole":
        return dv.whole_run_chart(recs, frames, ann, events)
    if part == "cover":
        return dv.coverage_chart(recs, frames)
    if part == "invalid":
        return dv.invalid_table(ann)
    raise ValueError(part)


# ---------------------------------------------------------------- page 3 "The sensors (Question 1)"
@st.cache_data(show_spinner="Analysing all anomalies (once) ...")
def q1_results(data_dir: str) -> list:
    from .q1 import analyse
    recs, frames, _, events = load_all(data_dir)
    return analyse(recs, frames, events)


@st.cache_data(show_spinner=False)
def q1_page(data_dir: str) -> str:
    from .q1_view import build, page_html
    return page_html(build(*load_all(data_dir)))


@st.cache_data(show_spinner=False)
def q1_replay_options(data_dir: str):
    from .q1_view import replay_options
    recs, frames, _, events = load_all(data_dir)
    return replay_options(recs, frames, events)


@st.cache_data(show_spinner="Loading this anomaly ...", max_entries=20)
def q1_replay(data_dir: str, key: str) -> str:
    from .plant_view import page_html
    from .q1_view import replay_marks
    d, _ = replay_marks(*load_all(data_dir), key)
    return page_html(dict(_plant_payload(data_dir), rowdemo=d), start_view="row")


@st.cache_data(show_spinner=False)
def fill_info(data_dir: str) -> dict:
    from .analysis import find_straight_line_segments
    recs, frames, _, _ = load_all(data_dir)
    k = next(r.key for r in recs if r.op == "OP18" and r.run_type == "normal")
    d, seg = frames[k], find_straight_line_segments(frames[k])[0]
    return dict(b=int(d["seconds_of_day"].iloc[seg["start_row"]]), e=int(d["seconds_of_day"].iloc[seg["end_row"]]),
                start=seg["Start"], end=seg["End"], length=int(seg["Length (s)"]))


@st.cache_data(show_spinner=False)
def plant_sensor_stats(data_dir: str):
    from .plant_view import sensor_info
    recs, frames, _, _ = load_all(data_dir)
    return sensor_info(recs, frames)


def data_dir() -> str:
    return st.session_state.get("data_dir", str(default_data_dir()))


def require_data():
    """Stop the page with a helpful message if the dataset is not found."""
    d = Path(data_dir())
    if not (d / "OP10" / "measurements").is_dir():
        st.error(
            f"The dataset was not found at `{d}`.\n\n"
            "Unzip `batch_distillation_dataset.zip` so that the folder "
            "`batch_distillation_dataset/OP10/...` exists next to `app.py`.")
        st.stop()
    return load_all(str(d))


# ---------------------------------------------------------------- page parts
def header(page_title: str):
    """Project title on every page, then the title of the page."""
    st.title("Understanding Anomalies in Chemical Processes")
    st.markdown("<p class='subtitle'>Master Project: Visualization and Artificial Intelligence</p>"
                f"<div class='page-h'>{page_title}</div>", unsafe_allow_html=True)


def explain(text: str, title: str = "How to read this"):
    with st.expander(title, expanded=False):
        st.markdown(text)


def key_point(text: str):
    st.markdown(f"<div class='keypoint'>{text}</div>", unsafe_allow_html=True)


def caution(text: str):
    st.markdown(f"<div class='caution'>{text}</div>", unsafe_allow_html=True)


def recording_picker(recs, key: str, only_anomalous: bool = False, default_op: str = "OP31"):
    ops = sorted({r.op for r in recs})
    c1, c2 = st.columns([1, 2])
    op = c1.selectbox("Operating point", ops, index=ops.index(default_op) if default_op in ops else 0,
                      key=f"{key}_op")
    options = [r for r in recs if r.op == op and (r.run_type == "anomalous" or not only_anomalous)]
    labels = [r.label for r in options]
    default = next((i for i, r in enumerate(options) if r.run_type == "anomalous"), 0)
    lab = c2.selectbox("Recording", labels, index=default, key=f"{key}_rec")
    return options[labels.index(lab)]


def sensor_label(s: str) -> str:
    from .metadata import SENSOR_INFO
    return f"{s} - {SENSOR_INFO[s]['readme']}"


def df_download(df: pd.DataFrame, name: str, label: str = "Download table as CSV"):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=name, mime="text/csv")


CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1300px;}
iframe {border: none;}
h1 {font-weight: 700; letter-spacing: -0.01em; margin-bottom: 0;}
.subtitle {color: #5b6472; font-size: 1.02rem; margin: -0.3rem 0 0.2rem 0;}
.page-h {font-size: 1.55rem; font-weight: 700; margin: 1.1rem 0 0.1rem 0; padding-top: 0.9rem; border-top: 1px solid #e3e8ef;}
table.ds {border-collapse: collapse; width: 100%; font-size: 0.92rem; margin: 0.3rem 0 0.6rem 0;}
table.ds th {text-align: left; font-weight: 700; color: #5b6472; border-bottom: 2px solid #e3e8ef; padding: 7px 10px; font-size: 0.85rem;}
table.ds td {border-bottom: 1px solid #eef1f5; padding: 7px 10px; vertical-align: top;}
table.ds tr.first td {border-top: 1px solid #dfe4ea;}
table.ds td.op {background: #f7f9fc; width: 120px;} table.ds td.op span {color: #5b6472; font-size: 0.85rem;}
table.ds .num {text-align: right; font-variant-numeric: tabular-nums;}
table.ds .mono {font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.82rem; color: #475569;}
table.ds .dot {display: inline-block; width: 9px; height: 9px; border-radius: 5px; margin-right: 7px;}
table.ds .dot.n {background: #2b6cb0;} table.ds .dot.a {background: #c0392b;}
table.ds .hb {display: inline-block; height: 10px; border-radius: 5px; margin-right: 8px; vertical-align: 0; opacity: .8;}
table.ds td.note {color: #5b6472; font-size: 0.85rem;}
.flow3 {display: flex; align-items: stretch; gap: 10px; margin: 0.4rem 0 0.8rem 0;}
.flow3 div {flex: 1; border: 1px solid #e3e8ef; border-radius: 12px; padding: 10px 14px; background: #f7f9fc;}
.flow3 b {display: block; color: #1f4e79; margin-bottom: 3px;} .flow3 span {font-size: 0.92rem; color: #334155;}
.flow3 i {align-self: center; font-style: normal; color: #94a3b8; font-size: 1.4rem;}
table.ds .bar {display: inline-block; width: 4px; height: 14px; border-radius: 2px; margin-right: 8px; vertical-align: -2px;}
</style>
"""


def apply_style():
    st.markdown(CSS, unsafe_allow_html=True)
