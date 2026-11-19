"""Streamlit dashboard for exploring the batch distillation dataset (Task 1).

Run: streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import data_utils as du
from diagram import STEPS, process_svg
from icons import icon
from data_utils import SENSORS, SENSOR_ORDER, OPS, fmt_hms, fmt_dur

# Page setup and styling
st.set_page_config(page_title="Understanding Anomalies in Chemical Processes", layout="wide",
                   initial_sidebar_state="expanded")

APP_DIR = Path(__file__).parent
DATA_ROOT = APP_DIR / "batch_distillation_dataset"

C_NORMAL = "#2f6fb0"      # normal run
C_ANOM = "#c0392b"        # anomalous run
C_CONF = "#c0392b"        # confirmed anomaly interval
C_UNCONF = "#e0a030"      # unconfirmed observation
C_RECUR = "#7b4fb8"       # recurrent / permanent intervals
C_INTERP = "#8d99ae"      # interpolated data
TEMPLATE = "plotly_white"
TEMP_COLORS = {"T703": "#b2182b", "T709": "#e66101", "T711": "#d9a400", "T712": "#4daf4a", "T705": "#2166ac"}

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1500px;}
.header {border-bottom: 3px solid #16324f; padding-bottom: 10px; margin-bottom: 18px; display:flex; align-items:center; gap:14px;}
.header .ic {background:#eaf0f8; border-radius:10px; padding:9px; display:flex;}
.sec {display:flex; align-items:center; gap:10px; margin:22px 0 8px 0;}
.sec h3 {margin:0; padding:0; font-size:1.3rem; color:#16324f;}
.kpi .top {display:flex; align-items:center; gap:10px;}
.kpi .ic {background:#eaf0f8; border-radius:8px; padding:6px; display:flex;}
.note {display:flex; gap:10px; align-items:flex-start;}
.header h1 {margin: 0; font-size: 2.0rem; color: #16324f;}
.header p {margin: 4px 0 0 0; color: #5b6474; font-size: 1.0rem;}
.kpi {background:#fff; border:1px solid #e1e5ec; border-radius:8px; padding:14px 16px; height: 100%;}
.kpi .v {font-size:1.6rem; font-weight:700; color:#16324f; line-height:1.15;}
.kpi .l {font-size:.85rem; color:#5b6474; margin-top:4px;}
.note {border-radius:6px; padding:12px 16px; margin:6px 0 12px 0; font-size:.95rem;
       background:#f4f6fa; border-left:4px solid #2f6fb0;}
.note.caution {border-left-color:#c0392b; background:#fbf1f0;}
.small {font-size:.85rem; color:#5b6474;}
</style>
""", unsafe_allow_html=True)


def header(title, subtitle=None, ic=None):
    ic_html = f'<div class="ic">{icon(ic, 30)}</div>' if ic else ""
    st.markdown(f'<div class="header">{ic_html}<div><h1>{title}</h1>' + (f"<p>{subtitle}</p>" if subtitle else "")
                + "</div></div>", unsafe_allow_html=True)


def section(title, ic):
    st.markdown(f'<div class="sec">{icon(ic, 24)}<h3>{title}</h3></div>', unsafe_allow_html=True)


def note(text, title=None, caution=False):
    head = f"<b>{title}</b><br>" if title else ""
    ic = icon("alert", 20, "#c0392b") if caution else icon("info", 20, "#2f6fb0")
    st.markdown(f'<div class="note{" caution" if caution else ""}">{ic}<div>{head}{text}</div></div>', unsafe_allow_html=True)


def kpi(col, value, label, ic=None):
    top = (f'<div class="top"><div class="ic">{icon(ic, 20)}</div><div class="v">{value}</div></div>' if ic
           else f'<div class="v">{value}</div>')
    col.markdown(f'<div class="kpi">{top}<div class="l">{label}</div></div>', unsafe_allow_html=True)


def show(fig, key=None):
    st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False})


def table(df, **kw):
    st.dataframe(df, width="stretch", hide_index=True, **kw)


def color_key(items):
    html = "".join(f'<span style="display:inline-flex;align-items:center;margin-right:18px;font-size:.88rem">'
                   f'<span style="width:22px;height:12px;border-radius:2px;background:{c};opacity:{o};margin-right:6px;'
                   f'display:inline-block"></span>{t}</span>' for c, o, t in items)
    st.markdown(f'<div style="padding:4px 0 2px 0">{html}</div>', unsafe_allow_html=True)


# Data loading (cached: files are read once)
@st.cache_data(show_spinner="Loading the 13 recordings…")
def load_all(root: str):
    runs = du.discover_runs(root)
    data = {r.run_id: du.load_run(r.path) for _, r in runs.iterrows()}
    ann = du.load_annotations(root, runs)
    events = du.event_table(ann)
    summary = du.run_summary(runs, data)
    return runs, data, ann, events, summary


if not (DATA_ROOT / "OP10").exists():
    st.error("Dataset not found. Place the folder `batch_distillation_dataset` next to app.py.")
    st.stop()
runs, data, ann, events, summary = load_all(str(DATA_ROOT))

PAGES = ["Overview", "Dataset structure", "Time series", "Annotated anomalies", "Data quality"]
with st.sidebar:
    st.markdown("### Batch Distillation Dataset")
    st.caption("Understanding Anomalies in Chemical Processes · Task 1: Dataset exploration")
    MENU_ICONS = {"Overview": ":material/dashboard:", "Dataset structure": ":material/database:",
                  "Time series": ":material/show_chart:", "Annotated anomalies": ":material/warning:",
                  "Data quality": ":material/verified:"}
    page = st.radio("Section", PAGES, label_visibility="collapsed", format_func=lambda p: f"{MENU_ICONS[p]} {p}")

# Text shown on the pages (based on the README, the CSV/YAML files and the project brief)
SENSOR_INFO = {  # what it measures, behaviour in normal runs, annotated disturbances that affect it
    "T703": ("Temperature of the liquid in reboiler V001.",
             "Increases gradually during a run as the more volatile component is depleted.",
             "Decreases during the combined set-point changes with reduced heat input (OP29)."),
    "T709": ("Temperature below column section C001, i.e. at the bottom of the column.",
             "Highest temperature in the column; follows the reboiler temperature.",
             "Nitrogen injection at the connection below C001 (OP18)."),
    "T711": ("Temperature between column sections C001 and C002.", "Drifts slowly; lies between bottom and top values.",
             "Short decreases during nitrogen injection (OP18)."),
    "T712": ("Temperature between column sections C002 and C003.", "Nearly constant for long periods, rises late in a run.",
             "Small decrease during nitrogen injection (OP10, OP18)."),
    "T705": ("Temperature at the top of column section C003.", "Nearly constant until the volatile component is depleted, then rises. At OP17, OP18 and OP22 it reads about 0.3 °C above T712.",
             "Decreases during nitrogen injection (OP10, OP18) and during the combined set-point changes (OP29)."),
    "FT703": ("Flow in the top product (distillate) stream.", "Fluctuates around a constant level.",
              "Spikes caused by an improperly sealed sample valve (OP17, OP18, OP22); drops to near zero when pump P702 is switched off (OP29)."),
    "FT704": ("Flow in the reflux stream, i.e. liquid returned to the column.", "Fluctuates around a constant level.",
              "Decreases during sample withdrawal from the reflux line (OP17, OP22); spikes from the improperly sealed valve."),
    "FYI702": ("Cooling-water flow signal of the condensers HE001/HE002.", "Changes in discrete steps between a few levels.",
               "Drops to zero when thermostat TCU1 is switched off (OP31)."),
    "PY23": ("Pressure in top vessel G001, controlled via valve TV1.", "Nearly constant at the set-point of the operating point.",
             "Decreases when the pressure set-point is lowered (OP29), followed by overshoots."),
    "PDI701": ("Pressure difference along the column.", "Fluctuates around a small value (median between about −0.15 and 1.0 depending on the OP).",
               "Changes when the vapour load changes, e.g. reduced heat input (OP29)."),
    "PDI702": ("Pressure difference associated with buffer vessel V002 (liquid level). Controlled at 2 mbar by pumps P701/P702.",
               "Fluctuates around 2 mbar.", "Air ingress (OP22); set-point lowered to 1 mbar (OP29)."),
}

OP_DISTURBANCES = {  # summary of the YAML files
    "OP10": "Nitrogen injection into reboiler V001 (1 event)",
    "OP17": "Sample withdrawal from the reflux line (4 events); improperly sealed sample valves throughout the run",
    "OP18": "Nitrogen injection below column section C001 (3 events); improperly sealed sample valves throughout the run",
    "OP22": "Sample withdrawal (2 events), air ingress (1 event); improperly sealed sample valves during the entire run",
    "OP29": "Combined set-point changes (heat input, pressure, pumps; 1 event); several unconfirmed observations",
    "OP31": "Cooling-water supply switched off (2 events)",
}


def unit_txt(s):
    return du.unit(s) or "unit not stated"


def sname(s):
    return f"{s} – {SENSORS[s][0]}"


def event_label(op, event_id, status, mode, category, effect):
    # short label derived from the PerturbationMode label in the YAML file
    if status not in ("ConfirmedAnomaly", "Confirmed"):
        return "Unconfirmed: pressure overshoot" if "pressure" in str(effect).lower() else "Unconfirmed: heater power fluctuation"
    if op == "OP29" and event_id.endswith("A001"):
        return "Combined set-point changes"
    m = str(mode).lower()
    if "inert gas" in m:
        return "Nitrogen injection"
    if "egress" in m:
        return "Sample withdrawal (reflux line)"
    if "air ingress" in m:
        return "Air ingress" if category == "transient" else "Air ingress (improperly sealed valve)"
    if "cooling" in m:
        return "Cooling-water supply off"
    return str(mode)


# Chart helpers
def xval(sec_of_day, start_s, mode):
    if mode == "clock":
        return pd.Timestamp("2000-01-01") + pd.to_timedelta(sec_of_day, unit="s")
    return (sec_of_day - start_s) / 60.0


def merge_intervals(iv):
    iv = sorted((a, b) for a, b in iv if b >= a)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def run_events(rid: str) -> pd.DataFrame:
    a = ann[(ann.run_id == rid) & ann.valid]
    rows = []
    for eid, g in a.groupby("event_id", sort=False):
        f = g.iloc[0]
        sensors = sorted(set(g.sensor))
        rows.append(dict(event_id=eid, short=eid[-4:], status=f.status, category=f.category,
                         label=event_label(f.op, eid, f.status, f.mode_label, f.category, f.effect),
                         begin_s=g.begin_s.min(), end_s=g.end_s.max(),
                         periods=merge_intervals(zip(g.begin_s, g.end_s)), sensors=sensors,
                         visible=any(s in SENSORS for s in sensors)))
    return pd.DataFrame(rows)


def series_chart(d, cols, rid, title, ytitle, xrange=None, height=300, recurrent=False, colors=None, yclip=False):
    fig = go.Figure()
    for s in cols:
        c = (colors or {}).get(s, C_ANOM if "Anomalous" in rid else C_NORMAL)
        fig.add_trace(go.Scattergl(x=d.clock, y=d[s], mode="lines", name=sname(s), line=dict(color=c, width=1.5),
                                   hovertemplate=f"{s}: %{{y:.3f}} {du.unit(s)}<extra></extra>"))
    ev = run_events(rid) if "Anomalous" in rid else pd.DataFrame()
    lane = 0
    for _, e in (ev.iterrows() if len(ev) else []):
        if not e.visible:
            continue
        if e.category in ("recurrent", "permanent"):
            if recurrent:
                for b, en in e.periods:
                    fig.add_vrect(x0=xval(b, 0, "clock"), x1=xval(max(en, b + 5), 0, "clock"), fillcolor=C_RECUR,
                                  opacity=0.18, line_width=0, layer="below")
            continue
        col = C_CONF if e.status == "ConfirmedAnomaly" else C_UNCONF
        for b, en in e.periods:
            fig.add_vrect(x0=xval(b, 0, "clock"), x1=xval(en, 0, "clock"), fillcolor=col, opacity=0.15,
                          line_width=0, layer="below")
        fig.add_annotation(x=xval(e.periods[0][0], 0, "clock"), y=1.0, yref="paper", yanchor="bottom", xanchor="left",
                           text=f"<b>{e.short}</b> {e.label}", showarrow=False, font=dict(size=10, color=col),
                           yshift=2 + 13 * (lane % 2))
        lane += 1
    for b, en in du.segments(d.interpolated, d.clock_s):
        fig.add_vrect(x0=xval(b, 0, "clock"), x1=xval(en, 0, "clock"), fillcolor=C_INTERP, opacity=0.35, line_width=0,
                      annotation_text="interpolated data", annotation_position="top left", annotation_font_size=10)
    if yclip:
        lo = min(d[s].quantile(0.002) for s in cols)
        hi = max(d[s].quantile(0.995) for s in cols)
        pad = (hi - lo) * 0.25 or 0.1
        fig.update_yaxes(range=[max(lo - pad, 0) if lo >= 0 else lo - pad, hi + pad])
    fig.update_layout(template=TEMPLATE, height=height, title=dict(text=title, font=dict(size=15), y=0.98),
                      margin=dict(l=10, r=10, t=70, b=30), hovermode="x unified", yaxis_title=ytitle,
                      legend=dict(orientation="h", y=-0.18, x=0), showlegend=len(cols) > 1)
    fig.update_xaxes(tickformat="%H:%M", range=xrange)
    return fig


def glossary(words):
    with st.expander("Terminology"):
        st.markdown("\n".join(f"- **{w}**: {t}" for w, t in words))


# Page: Overview
if page == PAGES[0]:
    header("Understanding Anomalies in Chemical Processes", "Batch distillation dataset: overview", "overview")
    n_conf = events[events.status == "Confirmed"].event_id.nunique()
    n_unconf = events[events.status != "Confirmed"].event_id.nunique()
    c = st.columns(5)
    kpi(c[0], "6", "operating points (OP10, OP17, OP18, OP22, OP29, OP31)", "gauge")
    kpi(c[1], "13", "runs: 7 normal, 6 anomalous", "file")
    kpi(c[2], "11", "sensors: temperatures, flows, pressures", "sensor")
    kpi(c[3], f"{summary.duration_min.sum() / 60:.1f} h", f"of recordings at 1 Hz ({int(summary.rows.sum()):,} time steps)", "clock")
    kpi(c[4], f"{n_conf} + {n_unconf}", "confirmed anomaly events + unconfirmed observations", "flag")
    st.write("")

    section("The process", "plant")
    st.markdown("Select a unit of the plant to highlight it and display its sensors. "
                "Enable *Show disturbance locations* to see where the disturbances of each operating point were applied "
                "(hover over a marker for details).")
    keys = ["ALL"] + list(STEPS)
    cc1, cc2 = st.columns([5, 1.3])
    active = cc1.radio("Plant unit", keys, horizontal=True, label_visibility="collapsed",
                       format_func=lambda k: "Entire plant" if k == "ALL" else STEPS[k][0])
    disturb = cc2.toggle("Show disturbance locations", value=False)
    active = None if active == "ALL" else active
    c1, c2 = st.columns([2.1, 1])
    with c1:
        st.markdown(process_svg(active, disturb), unsafe_allow_html=True)
    with c2:
        if active is None:
            st.markdown("""
**Batch distillation** separates a liquid mixture by heating it and cooling the resulting vapour (README).

1. The mixture is heated in reboiler **V001** and partially evaporates.
2. The vapour rises through the column (**C001–C003**) and is enriched in the more volatile component.
3. It is condensed in **HE001/HE002** and collected in buffer vessel **V002**.
4. Pump **P701** returns part of the liquid to the column as **reflux**; pump **P702** withdraws the rest as **distillate**.
5. The plant operates below atmospheric pressure; the pressure in **G001** is controlled via valve **TV1**.

**Mixture:** butan-1-ol, propan-2-ol and water.

**Batch operation:** the mixture is not replenished, so its composition changes over time and
temperatures rise gradually even under normal operation.
""")
        else:
            code, title, desc, sens = STEPS[active]
            st.markdown(f"#### {code}")
            st.markdown(f"*{title}*")
            st.markdown(desc, unsafe_allow_html=True)
            st.markdown("**Sensors at this unit**")
            table(pd.DataFrame([dict(Sensor=s, Measurement=SENSORS[s][0], Unit=unit_txt(s)) for s in sens]))

    with st.expander("Example: temperature development during a normal run (OP31)"):
        d = data["OP31 | Normal #1"]
        sm = d[["T703", "T705"]].rolling(30, center=True, min_periods=1).mean()
        brk = float(d.elapsed_min[(d.T705 > d.T705.iloc[:600].median() + 2).idxmax()])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d.elapsed_min, y=sm.T703, name=sname("T703"), line=dict(color=TEMP_COLORS["T703"], width=2.5)))
        fig.add_trace(go.Scatter(x=d.elapsed_min, y=sm.T705, name=sname("T705"), line=dict(color=TEMP_COLORS["T705"], width=2.5)))
        fig.add_vline(x=brk, line=dict(color="#555", dash="dot"))
        fig.add_annotation(x=brk / 2, y=106, showarrow=False,
                           text="Top temperature constant, reboiler temperature rising")
        fig.add_annotation(x=brk, y=76, xanchor="left", xshift=6, showarrow=False,
                           text=f"≈ {brk:.0f} min: top temperature starts to rise")
        fig.update_layout(template=TEMPLATE, height=360, xaxis_title="Time since start of run (min)", yaxis_title="°C",
                          legend=dict(orientation="h", y=1.12), margin=dict(t=30))
        show(fig, "batch")
        st.caption("30-second moving average. The gradual increase is part of normal batch operation and must not be confused "
                   "with an anomaly. The marked point is where T705 first exceeds its initial level by 2 °C.")

# Page: Dataset structure
elif page == PAGES[1]:
    header("Dataset structure", "Files, operating points, sensors and annotations", "database")

    section("1. Organisation", "folder")
    c = st.columns(3)
    kpi(c[0], "6 operating points", "Each operating point (OP) is a different combination of process settings, such as pressure "
               "and heat input (README).", "gauge")
    kpi(c[1], "13 runs (CSV)", "Per OP one normal run (<code>train_normal_…</code>) and one anomalous run "
               "(<code>test_anormal_…</code>); OP31 has a second normal run.", "file")
    kpi(c[2], "6 annotation files (YAML)", "One per anomalous run, describing each disturbance, its timing and the affected sensors.", "code")
    st.write("")

    section("2. Content of one operating point", "gauge")
    op = st.radio("Operating point", OPS, index=OPS.index("OP31"), horizontal=True, key="ds_op")
    s_op = summary[summary.op == op]
    ev_op = run_events(runs[(runs.op == op) & (runs.kind == "Anomalous")].run_id.iloc[0])
    rows = []
    for r in s_op.itertuples():
        rows.append(dict(File=r.file.split("/")[-1], Type="Normal run" if r.kind == "Normal" else "Anomalous run",
                         Start=r.start, End=r.end, Duration=f"{r.duration_min:.1f} min", Rows=r.rows))
    yaml_name = Path(runs[(runs.op == op) & (runs.kind == "Anomalous")].annotation.iloc[0]).name
    rows.append(dict(File=yaml_name, Type="Annotation of the anomalous run", Start="", End="", Duration="",
                     Rows=None))
    table(pd.DataFrame(rows), column_config={"Rows": st.column_config.NumberColumn("Rows (= seconds)", format="%d")})
    st.markdown("**Annotated events in the anomalous run:** " +
                "; ".join(f"{e.short} {e.label}" + (f" ({len(e.periods)} intervals)" if len(e.periods) > 1 else "")
                          for e in ev_op.itertuples()) + ".")
    st.caption(f"Typical pressure (median of PY23): {s_op.pressure_mbar.median():.0f} mbar · typical reflux ratio "
               f"(median FT704 ÷ median FT703): {s_op.reflux_ratio.median():.1f}. The dataset does not list the settings of an OP; "
               "both values are computed from the recordings. The unit mbar is stated in the OP29 annotation "
               "(“pressure setpoint 550 mbar”, sensor PY23).")
    st.caption("Normal vs anomalous: the README lists “seven normal and six anomalous runs”; the project brief describes "
               "“experiments with deliberately introduced disturbances”. The YAML field *Perturbation* describes each action "
               "(e.g. “Injection of nitrogen at 5 NL/h via valve (HV009)”). Not all entries are planned actions: the improperly "
               "sealed sample valve and the unconfirmed observations in OP29 are not.")

    section("3. Content of a measurement file (CSV)", "table")
    st.markdown(f"First six rows of the anomalous run of {op}, restricted to the 11 project sensors. "
                "**One row corresponds to one second; one column to one sensor.** Hover over a column header for its description.")
    raw = pd.read_csv(runs[(runs.op == op) & (runs.kind == "Anomalous")].path.iloc[0], nrows=6)
    table(raw[["Time"] + SENSOR_ORDER],
          column_config={"Time": st.column_config.TextColumn("Time", help="Clock time HH:MM:SS (no date is stored)"),
                         **{s: st.column_config.NumberColumn(s, help=f"{SENSORS[s][0]}; unit: {unit_txt(s)}", format="%.3f")
                            for s in SENSOR_ORDER}})
    st.caption("Each file has 19 columns: Time and 18 sensors. The README specifies the 11 sensors used in this project; "
               "the remaining 7 (LS701, LS702, T701, T702, T704, T706, T708) are not used. "
               "All 13 files were checked: no empty cells, no duplicate or missing time steps.")

    section("4. Content of an annotation file (YAML)", "code")
    ev_list = events[events.op == op].reset_index(drop=True)
    ev_list["pick"] = [f"{e.event_id} – " + event_label(op, e.event_id, "ConfirmedAnomaly" if e.status == "Confirmed" else "Anomaly",
                                                        e["mode"], e.category, e.effect) + f" – sensor {e.sensor}"
                       for _, e in ev_list.iterrows()]
    pick = st.selectbox("Annotation entry", ev_list.pick.tolist(), key="ds_ev")
    e0 = ev_list[ev_list.pick == pick].iloc[0]
    iv0 = ann[(ann.op == op) & (ann.event_id == e0.event_id) & (ann.entry == e0.entry)]
    times = (f"{iv0.begin.iloc[0]} → {iv0.end.iloc[0]}" if len(iv0) == 1
             else f"{len(iv0)} intervals; first {iv0.begin.iloc[0]} → {iv0.end.iloc[0]}")
    pm = f"{e0.pm_begin} → {e0.pm_end}" if pd.notna(e0.pm_begin) else "00:00:00 → 00:00:00 (placeholder)"
    cat_txt = {"transient": "occurs once and the process recovers", "recurrent": "occurs repeatedly during the run",
               "permanent": "persists for the entire run", "not given": "not specified (unconfirmed observation)"}[e0.category]
    rows = [
        ("id", e0.event_id, f"Event identifier: {op}, test run 001, anomaly {e0.event_id[-3:]}"),
        ("class", "ConfirmedAnomaly" if e0.status == "Confirmed" else "Anomaly",
         "Confirmed anomaly" if e0.status == "Confirmed" else "Observed deviation; cause not confirmed"),
        ("hasBeginning / hasEnd", times, "Annotated interval in which the process behaved anomalously"),
        ("hasCategory", e0.category if e0.category != "not given" else "null", cat_txt.capitalize()),
        ("Perturbation", e0.perturbation, "Description of the disturbance"),
        ("PerturbationMode → label", e0["mode"], "Type of disturbance"),
        ("PerturbationMode → hasBeginning / hasEnd", pm, "Time at which the disturbance was applied (may differ from the annotated interval)"),
        ("happenedAt → System", e0.system, "Affected equipment"),
        ("hasLocalEffect → label", e0.effect, "Observed effect"),
        ("madeBySensor", e0.sensor, f"Sensor showing the effect: {SENSORS[e0.sensor][0]}" if e0.sensor in SENSORS
         else "Heater sensor, not among the 11 project sensors"),
    ]
    table(pd.DataFrame(rows, columns=["Field", "Value", "Meaning"]),
          column_config={"Value": st.column_config.TextColumn(width="large"), "Meaning": st.column_config.TextColumn(width="large")})
    with st.expander("Raw YAML file"):
        st.code(Path(runs[(runs.op == op) & (runs.kind == "Anomalous")].annotation.iloc[0]).read_text(encoding="utf-8"),
                language="yaml")

    section("5. The 11 sensors", "sensor")
    groups = {"T703": "Temperature", "T709": "Temperature", "T711": "Temperature", "T712": "Temperature", "T705": "Temperature",
              "FT703": "Flow", "FT704": "Flow", "FYI702": "Flow", "PY23": "Pressure", "PDI701": "Pressure difference",
              "PDI702": "Pressure difference"}
    table(pd.DataFrame([dict(Sensor=s, Type=groups[s], Measurement=SENSOR_INFO[s][0], Unit=unit_txt(s)) for s in SENSOR_ORDER]),
          column_config={"Measurement": st.column_config.TextColumn(width="large")})
    st.caption("Descriptions follow the README. Units: the README gives none; the YAML files state mbar for PY23 and PDI702 "
               "and use °C for temperatures. PDI701 is assumed to be in mbar like PDI702. Flow units are not stated. "
               "Temperatures are ordered from the bottom of the column (T703) to the top (T705).")

    section("6. Summary of the operating points", "list")
    fig = go.Figure()
    for label, kind, num, col in [("Normal run", "Normal", 1, C_NORMAL), ("Normal run 2 (OP31 only)", "Normal", 2, "#76b7e8"),
                                  ("Anomalous run", "Anomalous", 1, C_ANOM)]:
        sub = summary.merge(runs[["run_id", "number"]], on="run_id")
        sub = sub[(sub.kind == kind) & (sub.number == num)]
        fig.add_trace(go.Bar(x=sub.op, y=sub.duration_min, name=label, marker_color=col,
                             text=sub.duration_min.round(0).astype(int).astype(str) + " min", textposition="outside",
                             hovertemplate="%{x}: %{y:.1f} min<extra>" + label + "</extra>"))
    fig.update_layout(template=TEMPLATE, barmode="group", height=360, title="Length of each run per operating point",
                      yaxis_title="Duration (min)", xaxis=dict(categoryorder="array", categoryarray=OPS),
                      legend=dict(orientation="h", y=1.12), margin=dict(t=80, b=30))
    show(fig, "run_lengths")
    st.caption("Normal and anomalous runs of the same operating point differ in length (e.g. OP17: 41 min vs 175 min) "
               "and therefore cover different parts of the batch.")
    rows = []
    for op_ in OPS:
        s_ = summary[summary.op == op_]
        rows.append(dict(OP=op_, Pressure=s_.pressure_mbar.median(), RR=s_.reflux_ratio.median(),
                         Normal=s_[s_.kind == "Normal"].duration_min.sum(), Anomalous=s_[s_.kind == "Anomalous"].duration_min.iloc[0],
                         Disturbances=OP_DISTURBANCES[op_]))
    table(pd.DataFrame(rows), column_config={
        "OP": "Operating point", "Pressure": st.column_config.NumberColumn("Pressure PY23 (mbar, median)", format="%d"),
        "RR": st.column_config.NumberColumn("Reflux ratio (median)", format="%.1f"),
        "Normal": st.column_config.NumberColumn("Normal run(s) (min)", format="%.0f"),
        "Anomalous": st.column_config.NumberColumn("Anomalous run (min)", format="%.0f"),
        "Disturbances": st.column_config.TextColumn("Annotated disturbances", width="large")})
    st.caption("Pressure and reflux ratio are computed from the recordings. All pressures are below atmospheric pressure "
               "(about 1013 mbar).")

    glossary([("Operating point (OP)", "a fixed combination of process settings."),
              ("Normal / anomalous run", "recording without / with annotated disturbances."),
              ("Reflux", "condensed liquid returned to the column. Distillate: condensed liquid withdrawn as product."),
              ("Reflux ratio", "reflux flow divided by distillate flow (FT704 ÷ FT703)."),
              ("Transient / recurrent / permanent", "anomaly categories used in the YAML files: once / repeatedly / for the entire run."),
              ("NL/h", "normal litres per hour (gas volume at 0 °C, 1.013 bar), as defined in the YAML files.")])

# Page: Time series
elif page == PAGES[2]:
    header("Time series", "Sensor readings of a single run, with annotated intervals", "chart")
    t1, t2 = st.tabs(["Single run", "Normal vs anomalous run"])
    with t1:
        c1, c2, c3 = st.columns([1.1, 1.3, 1.4])
        op = c1.selectbox("Operating point", OPS, index=OPS.index("OP31"), key="ex_op")
        kinds = runs[runs.op == op].run_id.tolist()
        run_name = {r: ("Anomalous run" if "Anomalous" in r else "Normal run" + (" 2" if r.endswith("#2") else "")) for r in kinds}
        rid = c2.radio("Run", kinds, index=next(i for i, r in enumerate(kinds) if "Anomalous" in r), horizontal=True,
                       format_func=lambda r: run_name[r])
        view = c3.radio("Display", ["groups", "one"], horizontal=True,
                        format_func=lambda v: "Sensor groups" if v == "groups" else "Single sensor")
        d = data[rid]
        ev = run_events(rid) if "Anomalous" in rid else pd.DataFrame()

        if len(ev):
            st.markdown("**Annotated events in this run**")
            rows = []
            for e in ev.itertuples():
                if e.category in ("recurrent", "permanent"):
                    when = f"{len(e.periods)} intervals throughout the run" if e.category == "recurrent" else "entire run"
                else:
                    when = f"{fmt_hms(e.begin_s)} – {fmt_hms(e.end_s)} ({fmt_dur(e.end_s - e.begin_s)})"
                rows.append(dict(ID=e.short, Event=e.label, Status="confirmed" if e.status == "ConfirmedAnomaly" else "unconfirmed",
                                 Category=e.category, Interval=when,
                                 Sensors=", ".join(x if x in SENSORS else f"{x} (not among the 11)" for x in e.sensors)))
            table(pd.DataFrame(rows))
            targets = ["Entire run"] + [f"{e.short} – {e.label}" for e in ev.itertuples()
                                        if e.category not in ("recurrent", "permanent") and e.visible]
            zoom = st.selectbox("Zoom to", targets)
        else:
            note("Normal run: there is no annotation file, i.e. no disturbances are annotated for this run. "
                 "Use it as reference for normal behaviour at this operating point.")
            zoom = "Entire run"
        xr = None
        if zoom != "Entire run":
            e = ev[(ev.short + " – " + ev.label) == zoom].iloc[0]
            xr = [xval(max(e.begin_s - 600, d.clock_s.iloc[0]), 0, "clock"),
                  xval(min(e.end_s + 600, d.clock_s.iloc[-1]), 0, "clock")]

        keys = [(C_CONF, .35, "confirmed anomaly interval (label above)"), (C_UNCONF, .45, "unconfirmed observation"),
                (C_RECUR, .35, "recurrent/permanent intervals (flow chart only)"), (C_INTERP, .5, "interpolated data")]
        color_key(keys if "Anomalous" in rid else keys[3:])

        if view == "groups":
            show(series_chart(d, ["T703", "T709", "T711", "T712", "T705"], rid,
                              "Temperatures from reboiler (T703, bottom) to column top (T705)", "°C", xr, 360,
                              colors=TEMP_COLORS), "c_temp")
            show(series_chart(d, ["FT704", "FT703"], rid, "Reflux flow (FT704) and distillate flow (FT703)",
                              "flow (unit not stated)", xr, 330, recurrent=True,
                              colors={"FT704": "#2a9d5c", "FT703": "#7b4fb8"}, yclip=True), "c_flow")
            st.caption("The y-axis is limited to the 99.5th percentile so that the normal level remains readable; "
                       "isolated spikes may extend beyond the plot area.")
            c1, c2 = st.columns(2)
            with c1:
                show(series_chart(d, ["FYI702"], rid, "Cooling-water flow signal (FYI702)", "unit not stated", xr, 300,
                                  colors={"FYI702": "#2a78b5"}), "c_cool")
            with c2:
                show(series_chart(d, ["PY23"], rid, "Pressure in top vessel G001 (PY23)", "mbar", xr, 300,
                                  colors={"PY23": "#7b4fb8"}), "c_pres")
            st.caption("PDI701 and PDI702 are available under *Single sensor*.")
        else:
            s = st.selectbox("Sensor", SENSOR_ORDER, format_func=sname, index=SENSOR_ORDER.index("FT704"))
            c1, c2 = st.columns([2.3, 1])
            with c1:
                show(series_chart(d, [s], rid, sname(s), unit_txt(s), xr, 440,
                                  recurrent=s in ("FT703", "FT704"), yclip=s in ("FT703", "FT704", "PDI702")), "c_one")
            with c2:
                what, normal, dist = SENSOR_INFO[s]
                st.markdown(f"**Measurement**  \n{what}")
                st.markdown(f"**Behaviour in normal runs**  \n{normal}")
                st.markdown(f"**Annotated disturbances affecting this sensor**  \n{dist}")
                st.caption(f"This run: median {d[s].median():.3g}, minimum {d[s].min():.3g}, maximum {d[s].max():.3g} "
                           f"({unit_txt(s)}).")
        st.caption("Hover for exact values; drag to zoom; double-click to reset the view.")

    with t2:
        st.markdown("The normal and anomalous runs of one operating point were recorded on different days. "
                    "They are therefore aligned by **time since the start of the run**.")
        c1, c2 = st.columns([1, 2])
        op2 = c1.selectbox("Operating point", OPS, index=OPS.index("OP31"), key="nva_op")
        s = c2.selectbox("Sensor", SENSOR_ORDER, format_func=sname, index=SENSOR_ORDER.index("FYI702"), key="nva_s")
        fig = go.Figure()
        for r in runs[runs.op == op2].run_id:
            dd = data[r]
            col = C_ANOM if "Anomalous" in r else (C_NORMAL if r.endswith("#1") else "#76b7e8")
            name = "Anomalous run" if "Anomalous" in r else ("Normal run" + (" 2" if r.endswith("#2") else ""))
            fig.add_trace(go.Scattergl(x=dd.elapsed_min, y=dd[s].rolling(10, center=True, min_periods=1).mean(),
                                       mode="lines", name=name, line=dict(color=col, width=1.5)))
        a = ann[(ann.op == op2) & ann.valid & (ann.status == "ConfirmedAnomaly") & (ann.category == "transient")]
        for b, e in merge_intervals(zip(a.begin_elapsed_min * 60, a.end_elapsed_min * 60)):
            fig.add_vrect(x0=b / 60, x1=e / 60, fillcolor=C_CONF, opacity=0.12, line_width=0, layer="below")
        fig.update_layout(template=TEMPLATE, height=430, yaxis_title=unit_txt(s), xaxis_title="Time since start of run (min)",
                          title=sname(s), legend=dict(orientation="h", y=1.12), margin=dict(t=70))
        color_key([(C_NORMAL, 1, "normal run"), (C_ANOM, 1, "anomalous run"), (C_CONF, .2, "transient anomaly interval")])
        show(fig, "nva")
        st.caption("10-second moving average.")
        note("A difference in <b>level</b> between the two runs is not necessarily an anomaly: the runs can cover different stages "
             "of the batch, and some pairs differ in their settings (e.g. in OP10 the cooling-water signal of the anomalous run is "
             "about twice as high). Changes in <b>shape</b> within the shaded intervals (drops, steps, spikes, increased "
             "fluctuation) are more informative.", "Interpretation")

    glossary([("Annotated interval", "time span given by hasBeginning/hasEnd in the YAML file."),
              ("Interpolated data", "a gap in the recording that was filled with a straight line."),
              ("Moving average", "average over a sliding time window, used to reduce noise.")])

# Page: Annotated anomalies
elif page == PAGES[3]:
    header("Annotated anomalies", "Summary of the six YAML annotation files", "alert")
    conf_ev = events[events.status == "Confirmed"].drop_duplicates(["op", "event_id"])
    c = st.columns(4)
    kpi(c[0], conf_ev.event_id.nunique(), "confirmed anomaly events", "flag")
    kpi(c[1], int((conf_ev.category == "transient").sum()), "transient (single occurrence, followed by recovery)", "clock")
    kpi(c[2], int((conf_ev.category != "transient").sum()), "recurrent or permanent", "timeline")
    kpi(c[3], events[events.status != "Confirmed"].event_id.nunique(), "unconfirmed observations (OP29 only)", "search")
    st.write("")

    ev_ids = events.drop_duplicates(["op", "event_id"])
    cnt = pd.DataFrame({
        "Transient (occurs once)": ev_ids[(ev_ids.status == "Confirmed") & (ev_ids.category == "transient")].groupby("op").size(),
        "Recurrent or permanent": ev_ids[(ev_ids.status == "Confirmed") & (ev_ids.category != "transient")].groupby("op").size(),
        "Unconfirmed observation": ev_ids[ev_ids.status != "Confirmed"].groupby("op").size(),
    }).reindex(OPS).fillna(0).astype(int)
    fig = go.Figure()
    for colname, col in [("Transient (occurs once)", C_CONF), ("Recurrent or permanent", C_RECUR),
                         ("Unconfirmed observation", C_UNCONF)]:
        fig.add_trace(go.Bar(x=cnt.index, y=cnt[colname], name=colname, marker_color=col,
                             hovertemplate="%{x}: %{y}<extra>" + colname + "</extra>"))
    totals = cnt.sum(axis=1)
    fig.add_trace(go.Scatter(x=cnt.index, y=totals, mode="text", text=totals.astype(str), textposition="top center",
                             showlegend=False, hoverinfo="skip"))
    fig.update_layout(template=TEMPLATE, barmode="stack", height=340, title="Number of annotated events per operating point",
                      yaxis=dict(title="Number of events", dtick=1, range=[0, totals.max() + 1.5]),
                      legend=dict(orientation="h", y=1.14), margin=dict(t=80, b=30))
    show(fig, "events_per_op")
    st.caption("Each event ID is counted once, even if the YAML file lists it for several sensors.")

    op = st.radio("Operating point", OPS, index=OPS.index("OP17"), horizontal=True)
    st.markdown(f"**{op}:** {OP_DISTURBANCES[op]}.")
    rid_a = runs[(runs.op == op) & (runs.kind == "Anomalous")].run_id.iloc[0]
    ev = run_events(rid_a)
    t0 = data[rid_a].clock_s.iloc[0]
    dur = summary[(summary.op == op) & (summary.kind == "Anomalous")].duration_min.iloc[0]
    CAT = {"transient": ("Transient (occurs once)", C_CONF), "recurrent": ("Recurrent (occurs repeatedly)", C_RECUR),
           "permanent": ("Permanent (entire run)", "#16324f"), "not given": ("Unconfirmed observation", C_UNCONF)}

    section("When did the anomalies occur?", "timeline")
    fig = go.Figure()
    shown = set()
    order = []
    for e in ev.itertuples():
        row = f"{e.short} – {e.label}"
        order.append(row)
        cat = e.category if e.status == "ConfirmedAnomaly" else "not given"
        name, col = CAT[cat]
        for b_, e_ in e.periods:
            fig.add_trace(go.Bar(y=[row], x=[max((e_ - b_) / 60, 0.3)], base=[(b_ - t0) / 60], orientation="h",
                                 marker_color=col, name=name, showlegend=name not in shown, legendgroup=name,
                                 hovertemplate=f"{row}<br>{fmt_hms(b_)} – {fmt_hms(e_)}<extra></extra>"))
            shown.add(name)
    fig.update_layout(template=TEMPLATE, barmode="overlay", height=140 + 42 * len(order),
                      xaxis=dict(range=[0, dur], title=f"Minutes since the start of the anomalous run (run length {dur:.0f} min)"),
                      yaxis=dict(categoryorder="array", categoryarray=order[::-1], title=None),
                      legend=dict(orientation="h", y=1.12), margin=dict(t=40, b=40, l=10, r=10))
    show(fig, "anom_tl")
    st.caption("How to read it: each row is one annotated event. Each bar shows when it occurred during the run; "
               "a longer bar means a longer anomaly. Recurrent events consist of many short bars. Hover for exact times.")

    section("What happened in each event?", "list")
    rows = []
    for e in ev.itertuples():
        f = events[(events.op == op) & (events.event_id == e.event_id)].iloc[0]
        cat = e.category if e.status == "ConfirmedAnomaly" else "not given"
        if e.category in ("recurrent", "permanent"):
            when = f"{len(e.periods)} intervals" if e.category == "recurrent" else "entire run"
        else:
            when = f"{fmt_hms(e.begin_s)} – {fmt_hms(e.end_s)}"
        rows.append({"Event": f"{e.short} – {e.label}", "Type": CAT[cat][0], "When": when,
                     "Sensor(s) named": ", ".join(e.sensors), "Description in the YAML file": f.perturbation})
    table(pd.DataFrame(rows), column_config={"Description in the YAML file": st.column_config.TextColumn(width="large")})
    note("The same event ID can occur several times when one disturbance affects several sensors "
         "(e.g. OP29 A001 appears seven times). For the transient events, the annotated interval begins within one minute of the "
         "start of the disturbance and ends about 1–10 minutes after it has been removed, reflecting the delayed response and "
         "recovery of the process.")

# Page: Data quality
elif page == PAGES[4]:
    header("Data quality", "Observations from checking all files that are relevant for later modelling and evaluation", "check")

    section("1. Interpolated segment in the normal run of OP18", "chart")
    d = data["OP18 | Normal #1"]
    b, e = du.segments(d.interpolated, d.clock_s)[0]
    w = d[(d.clock_s > b - 1200) & (d.clock_s < e + 1800)]
    fig = make_subplots(rows=1, cols=2, subplot_titles=["PY23 – pressure in G001 (mbar)", "T705 – top temperature (°C)"])
    for i, s in enumerate(["PY23", "T705"], 1):
        fig.add_trace(go.Scattergl(x=w.clock, y=w[s], mode="lines", line=dict(color=C_NORMAL), showlegend=False), 1, i)
    fig.add_vrect(x0=xval(b, 0, "clock"), x1=xval(e, 0, "clock"), fillcolor=C_INTERP, opacity=.35, line_width=0,
                  row="all", col="all")
    fig.update_xaxes(tickformat="%H:%M")
    fig.update_layout(template=TEMPLATE, height=300, margin=dict(t=40, b=30))
    show(fig, "f1")
    note(f"From {fmt_hms(b)} to {fmt_hms(e)} ({fmt_dur(e - b)}) all 11 sensors follow an exact straight line, i.e. the values were "
         "interpolated over a gap. Immediately afterwards the pressure is about 979 mbar instead of about 400 mbar, indicating an "
         "unrecorded interruption of operation. This segment should be excluded from the training data.", caution=True)

    section("2. Invalid intervals in the annotation files", "code")
    table(ann[~ann.valid][["op", "event_id", "sensor", "begin", "end", "issue"]],
          column_config={"op": "OP", "event_id": "Event ID", "sensor": "Sensor", "begin": "Begin", "end": "End", "issue": "Issue"})
    note("In three intervals the end time precedes the start time (probably typing errors, e.g. 10:20:37 instead of 11:20:37). "
         "They are excluded from all charts and counts rather than corrected by assumption. "
         "In addition, the begin times of OP18 A004 (FT704) are not in chronological order.")

    section("3. Spikes in normal runs", "sensor")
    sp = du.spike_counts(data, runs, "FT703")
    sp = sp[sp.kind == "Normal"]
    table(pd.DataFrame({"Normal run": sp.run_id.str.replace(" | Normal #1", "").str.replace(" | Normal #2", " (run 2)"),
                        "Number of spikes in FT703": sp.spike_events.values}))
    st.caption("Spike = a reading more than 0.3 above the median of the run.")
    note("In OP17, OP18 and OP22 an improperly sealed sample valve is annotated as a recurrent or permanent anomaly that causes "
         "spikes in the flow signals. The normal runs of these three operating points also contain such spikes, whereas OP10, "
         "OP29 and OP31 contain none. The normal training data may therefore already contain this behaviour.")

    section("4. Further observations", "list")
    st.markdown("""
- **OP22 is annotated as anomalous for 100 % of its duration** (permanent event A004). A per-time-step evaluation is therefore not meaningful for this run; an event-based evaluation is more suitable.
- **Normal and anomalous runs often cover different stages of the batch** (e.g. the normal run of OP17 lasts 41 min, the anomalous run 175 min). Temperature levels in an anomalous run can lie outside the range of the corresponding normal run without any disturbance.
- **The two runs of OP10 differ in their settings:** median cooling-water signal ≈ 3.3 vs ≈ 7.1, reflux ratio ≈ 0.7 vs ≈ 1.1.
- **The OP29 annotations refer to heater temperatures** (T701, T702, T704, T706, T708) that are not among the 11 project sensors, and include unconfirmed entries with placeholder times (00:00:00).
- **Annotation text and data can differ:** OP18 A001 states a lower temperature at T709, but T709 increases (≈ 60.9 → 63–64 °C); the decrease is visible in T711 and T712.
- **Sensor characteristics:** FYI702 changes in discrete steps; PDI702 is controlled at 2 mbar; PDI701 is slightly negative at OP17 (median ≈ −0.15).
""")
    with st.expander("Complete dataset guide"):
        guide = APP_DIR / "DATASET_GUIDE.md"
        st.markdown(guide.read_text(encoding="utf-8") if guide.exists() else "DATASET_GUIDE.md not found.")
