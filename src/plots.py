"""Plotly figure builders used by the pages."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .data_loader import DUMMY_DATE, seconds_to_time
from .metadata import GROUP_COLORS, SENSOR_INFO, SENSORS

C_NORMAL = "#2b6cb0"
C_ANOM = "#c0392b"
C_EVENT = "rgba(192, 57, 43, 0.16)"
C_PERT = "rgba(230, 126, 34, 0.30)"
C_SPIKE = "rgba(142, 68, 173, 0.22)"
C_BASE = "rgba(120, 120, 120, 0.12)"
FONT = dict(family="Inter, Helvetica Neue, Arial, sans-serif", size=13, color="#1b1f24")


def _layout(fig, height, **kw):
    base = dict(template="plotly_white", font=FONT, height=height,
                margin=dict(l=70, r=30, t=50, b=40), hovermode="x unified")
    base.update(kw)
    fig.update_layout(**base)
    return fig


def shade(fig, x0, x1, color):
    """One full-height shaded band across all stacked panels (they share one x range)."""
    fig.add_shape(type="rect", xref="x", yref="paper", x0=x0, x1=x1, y0=0, y1=1,
                  fillcolor=color, line_width=0, layer="below")


def _ts(sec):
    """seconds-of-day -> timestamp on the dummy date (for a clock-time axis)."""
    return pd.Timestamp(DUMMY_DATE) + pd.to_timedelta(int(sec), unit="s")


# ------------------------------------------------------------------ time series
def stacked_timeseries(df, sensors, x_mode="clock", smooth_s=1, ann=None,
                       show_event=True, show_pert=True, show_spikes=True,
                       normalize=False, title=""):
    """One row per sensor, shared time axis, annotated intervals shaded."""
    n = len(sensors)
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.012 if n > 6 else 0.03,
                        subplot_titles=None)
    if x_mode == "clock":
        x = df["timestamp"]
        xconv = _ts
    else:
        x = df["elapsed_s"] / 60.0
        start = int(df["seconds_of_day"].iloc[0])
        xconv = lambda s: (s - start) / 60.0  # noqa: E731

    for i, s in enumerate(sensors, start=1):
        y = df[s].astype(float)
        if normalize:
            y = (y - y.mean()) / (y.std() if y.std() > 0 else 1)
        color = GROUP_COLORS[SENSOR_INFO[s]["group"]] if s in SENSOR_INFO else "#555"
        fig.add_trace(go.Scattergl(x=x, y=y, mode="lines", name=s, line=dict(width=1, color=color),
                                   opacity=0.45 if smooth_s > 1 else 1.0, showlegend=False,
                                   hovertemplate=f"{s}: %{{y:.3f}}<extra></extra>"), row=i, col=1)
        if smooth_s > 1:
            ys = y.rolling(smooth_s, center=True, min_periods=1).median()
            fig.add_trace(go.Scattergl(x=x, y=ys, mode="lines", name=f"{s} (smoothed)",
                                       line=dict(width=1.6, color=color), showlegend=False,
                                       hovertemplate=f"{s} smoothed: %{{y:.3f}}<extra></extra>"), row=i, col=1)
        unit = SENSOR_INFO.get(s, {}).get("unit", "")
        short = "°C" if unit == "°C" else ("mbar" if unit.startswith("mbar") else "")
        fig.update_yaxes(title_text=f"<b>{s}</b><br><span style='font-size:10px'>{short if not normalize else 'z-score'}</span>",
                         row=i, col=1, title_standoff=4)

    if ann is not None and len(ann):
        valid = ann[ann["Valid interval"]]
        if show_spikes:
            for _, r in valid[valid["Intervals in entry"] > 1].drop_duplicates(["begin_s", "end_s"]).iterrows():
                shade(fig, xconv(r["begin_s"]), xconv(r["end_s"] + 1), C_SPIKE)
        if show_event:
            for _, r in valid[valid["Intervals in entry"] == 1].drop_duplicates(["begin_s", "end_s"]).iterrows():
                shade(fig, xconv(r["begin_s"]), xconv(r["end_s"] + 1), C_EVENT)
        if show_pert:
            pm = ann.dropna(subset=["Perturbation begin"]).drop_duplicates(["Perturbation begin", "Perturbation end"])
            for _, r in pm.iterrows():
                from .data_loader import time_to_seconds
                b, e = time_to_seconds(r["Perturbation begin"]), time_to_seconds(r["Perturbation end"])
                # skip perturbations that span the whole run (recurrent/permanent)
                if e - b > 0.8 * (df["seconds_of_day"].iloc[-1] - df["seconds_of_day"].iloc[0]):
                    continue
                shade(fig, xconv(b), xconv(e + 1), C_PERT)

    fig.update_xaxes(showgrid=True, gridcolor="#eceff3")
    fig.update_yaxes(showgrid=True, gridcolor="#eceff3", zeroline=False)
    if x_mode == "clock":
        fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M:%S", row=n, col=1, title_text="Clock time (HH:MM)")
    else:
        fig.update_xaxes(title_text="Minutes since start of recording", row=n, col=1)
    return _layout(fig, height=max(320, 135 * n + 90), title=title, hovermode="x")


def legend_html():
    return (f"<span style='background:{C_PERT};padding:2px 8px;border-radius:3px'>disturbance applied "
            f"(PerturbationMode)</span>&nbsp; <span style='background:{C_EVENT};padding:2px 8px;border-radius:3px'>"
            f"annotated anomaly interval</span>&nbsp; <span style='background:{C_SPIKE};padding:2px 8px;"
            f"border-radius:3px'>recurrent short intervals (spikes)</span>")


# ------------------------------------------------------------------ overview charts
def recordings_timeline(summary: pd.DataFrame, events: pd.DataFrame):
    """Horizontal bars on a clock-time axis: when each recording ran (no dates in the data)."""
    fig = go.Figure()
    s = summary.copy()
    s["y"] = s["Operating point"] + " - " + s["Run"]
    order = list(s["y"])[::-1]
    for typ, color, name in (("normal", C_NORMAL, "Normal run"), ("anomalous", C_ANOM, "Anomalous run")):
        d = s[s["Type"] == typ]
        b = pd.to_datetime(DUMMY_DATE + " " + d["Start"])
        e = pd.to_datetime(DUMMY_DATE + " " + d["End"])
        fig.add_trace(go.Bar(base=b, x=(e - b).dt.total_seconds() * 1000, y=d["y"], orientation="h",
                             marker_color=color, opacity=0.85, name=name,
                             customdata=np.stack([d["Start"], d["End"], d["Duration (min)"], d["Rows"]], axis=1),
                             hovertemplate="%{y}<br>%{customdata[0]} - %{customdata[1]}<br>"
                                           "%{customdata[2]} min, %{customdata[3]} rows<extra></extra>"))
    ev = events.dropna(subset=["begin_s"])
    ys, bs, xs, txt = [], [], [], []
    for _, r in ev.iterrows():
        y = s[(s["Operating point"] == r["OP"]) & (s["Type"] == "anomalous")]["y"]
        if len(y):
            ys.append(y.iloc[0]); bs.append(_ts(r["begin_s"])); xs.append((r["end_s"] - r["begin_s"] + 1) * 1000)
            txt.append(f'{r["ID"]} ({r["Category"] if isinstance(r["Category"], str) else r["Class"]})'
                       f'<br>{r["First begin"]} - {r["Last end"]}')
    fig.add_trace(go.Bar(base=bs, x=xs, y=ys, orientation="h", width=0.35, marker_color="#f1c40f",
                         marker_line=dict(color="#7d6608", width=0.6), name="Annotated event span",
                         hovertext=txt, hoverinfo="text"))
    fig.update_xaxes(type="date", tickformat="%H:%M", title_text="Clock time of day (the dataset contains no dates)")
    fig.update_yaxes(categoryorder="array", categoryarray=order)
    return _layout(fig, 520, barmode="overlay", hovermode="closest",
                   legend=dict(orientation="h", y=1.08, x=0))


def op_boxplots(recs, frames, sensor, only_normal=True):
    fig = go.Figure()
    for r in recs:
        if only_normal and r.run_type != "normal":
            continue
        y = frames[r.key][sensor]
        fig.add_trace(go.Box(y=y, name=f"{r.op}<br>{r.label.replace(' run', '')}", boxpoints=False,
                             marker_color=C_NORMAL if r.run_type == "normal" else C_ANOM, showlegend=False))
    fig.update_yaxes(title_text=f"{sensor} ({SENSOR_INFO[sensor]['unit']})")
    return _layout(fig, 430, hovermode="closest")


def heatmap(df: pd.DataFrame, title="", zmin=None, zmax=None, colorscale="RdBu", fmt=".0f",
            colorbar_title="", text=None, height=None):
    z = df.to_numpy(dtype=float)
    t = text if text is not None else np.vectorize(lambda v: "" if np.isnan(v) else format(v, fmt))(z)
    fig = go.Figure(go.Heatmap(z=z, x=list(df.columns), y=list(df.index), zmin=zmin, zmax=zmax,
                               colorscale=colorscale, text=t, texttemplate="%{text}", textfont=dict(size=11),
                               colorbar=dict(title=colorbar_title), hovertemplate="%{y} | %{x}: %{text}<extra></extra>",
                               xgap=2, ygap=2))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(side="top")
    return _layout(fig, height or max(260, 38 * len(df) + 120), title=title, hovermode="closest")


def overlay_runs(runs: list[tuple[str, pd.DataFrame, str]], sensor: str, smooth_s=31):
    fig = go.Figure()
    for name, df, color in runs:
        y = df[sensor].rolling(smooth_s, center=True, min_periods=1).median() if smooth_s > 1 else df[sensor]
        fig.add_trace(go.Scattergl(x=df["elapsed_s"] / 60, y=y, mode="lines", name=name,
                                   line=dict(color=color, width=1.4)))
    fig.update_xaxes(title_text="Minutes since start of each recording")
    fig.update_yaxes(title_text=f"{sensor} ({SENSOR_INFO[sensor]['unit']})")
    return _layout(fig, 380, legend=dict(orientation="h", y=1.12, x=0))


def distribution_compare(runs, sensor, bins=80):
    fig = go.Figure()
    for name, df, color in runs:
        fig.add_trace(go.Histogram(x=df[sensor], name=name, marker_color=color, opacity=0.55,
                                   nbinsx=bins, histnorm="percent"))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text=f"{sensor} ({SENSOR_INFO[sensor]['unit']})")
    fig.update_yaxes(title_text="% of readings")
    return _layout(fig, 330, hovermode="closest", legend=dict(orientation="h", y=1.15, x=0))


# ------------------------------------------------------------------ event view (Q1)
def event_multiples(df, onset_s, end_s, pert=None, sensors=SENSORS, before_s=600, after_s=600,
                    smooth_s=31, deviation=False, baseline_s=600):
    sod = df["seconds_of_day"]
    w = df[(sod >= onset_s - before_s) & (sod <= end_s + after_s)]
    x = (w["seconds_of_day"] - onset_s) / 60.0
    n = len(sensors)
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.01)
    base = df[(sod >= onset_s - baseline_s) & (sod < onset_s)]
    for i, s in enumerate(sensors, start=1):
        y = w[s].astype(float)
        ys = y.rolling(smooth_s, center=True, min_periods=1).median()
        if deviation:
            ref = base[s].median()
            y, ys = y - ref, ys - ref
        color = GROUP_COLORS[SENSOR_INFO[s]["group"]]
        fig.add_trace(go.Scattergl(x=x, y=y, mode="lines", line=dict(width=0.8, color=color), opacity=0.35,
                                   showlegend=False, hovertemplate=f"{s}: %{{y:.3f}}<extra></extra>"), row=i, col=1)
        fig.add_trace(go.Scattergl(x=x, y=ys, mode="lines", line=dict(width=1.7, color=color),
                                   showlegend=False, hovertemplate=f"{s} smoothed: %{{y:.3f}}<extra></extra>"),
                      row=i, col=1)
        fig.update_yaxes(title_text=f"<b>{s}</b>", row=i, col=1, title_standoff=2)
    shade(fig, -baseline_s / 60, 0, C_BASE)
    shade(fig, 0, (end_s - onset_s + 1) / 60, C_EVENT)
    if pert is not None:
        shade(fig, (pert[0] - onset_s) / 60, (pert[1] - onset_s + 1) / 60, C_PERT)
    fig.add_shape(type="line", xref="x", yref="paper", x0=0, x1=0, y0=0, y1=1,
                  line=dict(color="#333", dash="dot", width=1))
    fig.update_xaxes(title_text="Minutes relative to the onset (0 = start of the disturbance / event)", row=n, col=1)
    fig.update_xaxes(showgrid=True, gridcolor="#eceff3")
    fig.update_yaxes(showgrid=True, gridcolor="#eceff3", zeroline=deviation, zerolinecolor="#999")
    return _layout(fig, 118 * n + 90, hovermode="x")


# ------------------------------------------------------------------ plant sketch
def plant_sketch(highlight: list[str] | None = None):
    """
    Simplified sketch of the plant built ONLY from the README and YAML texts.
    Not to scale and not the official piping diagram.
    """
    hl = set(highlight or [])
    fig = go.Figure()
    shapes, ann = [], []

    def box(x0, y0, x1, y1, label, fill="#f4f6f9", line="#4a5563"):
        shapes.append(dict(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=line, width=1.6),
                           fillcolor=fill, layer="below"))
        ann.append(dict(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=label, showarrow=False, font=dict(size=11)))

    def line(pts, color="#4a5563", dash=None, width=2):
        path = "M " + " L ".join(f"{x},{y}" for x, y in pts)
        shapes.append(dict(type="path", path=path, line=dict(color=color, width=width, dash=dash)))

    def arrow(x, y, ax, ay, color="#4a5563"):
        ann.append(dict(x=x, y=y, ax=ax, ay=ay, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                        arrowhead=3, arrowsize=1.2, arrowwidth=1.6, arrowcolor=color, text=""))

    # reboiler and column
    box(1.0, 0.3, 3.4, 1.9, "<b>Reboiler V001</b><br>heated by H701 (+H702)", fill="#fbeee6")
    box(1.6, 2.3, 2.8, 3.7, "<b>C001</b><br>section 1")
    box(1.6, 3.9, 2.8, 5.3, "<b>C002</b><br>section 2")
    box(1.6, 5.5, 2.8, 6.9, "<b>C003</b><br>section 3")
    line([(2.2, 1.9), (2.2, 2.3)]); line([(2.2, 3.7), (2.2, 3.9)]); line([(2.2, 5.3), (2.2, 5.5)])
    # vapour to condenser
    line([(2.2, 6.9), (2.2, 7.6), (5.2, 7.6), (5.2, 7.2)], color="#c0392b")
    arrow(5.2, 7.15, 5.2, 7.6, "#c0392b")
    box(4.4, 5.9, 6.0, 7.15, "<b>Condensers</b><br>HE001, HE002", fill="#e8f1fb")
    # cooling water
    line([(6.0, 6.2), (7.3, 6.2)], color="#2b6cb0", dash="dot")
    line([(6.0, 6.9), (7.3, 6.9)], color="#2b6cb0", dash="dot")
    box(7.3, 6.0, 8.6, 7.1, "<b>TCU1</b><br>cooling water", fill="#e8f1fb")
    # buffer vessel
    line([(5.2, 5.9), (5.2, 5.2)])
    arrow(5.2, 5.15, 5.2, 5.6)
    box(4.5, 4.1, 5.9, 5.15, "<b>Buffer vessel</b><br>V002")
    # pumps
    line([(4.8, 4.1), (4.8, 3.3)]); line([(5.6, 4.1), (5.6, 3.3)])
    shapes.append(dict(type="circle", x0=4.55, y0=2.8, x1=5.05, y1=3.3, line=dict(color="#4a5563", width=1.6), fillcolor="white"))
    shapes.append(dict(type="circle", x0=5.35, y0=2.8, x1=5.85, y1=3.3, line=dict(color="#4a5563", width=1.6), fillcolor="white"))
    ann += [dict(x=4.8, y=3.05, text="P701", showarrow=False, font=dict(size=9)),
            dict(x=5.6, y=3.05, text="P702", showarrow=False, font=dict(size=9))]
    # reflux back to column top
    line([(4.8, 2.8), (4.8, 2.4), (3.6, 2.4), (3.6, 6.6), (2.8, 6.6)], color="#16a085")
    arrow(2.85, 6.6, 3.4, 6.6, "#16a085")
    ann.append(dict(x=3.85, y=4.6, text="reflux", textangle=-90, showarrow=False, font=dict(size=10, color="#16a085")))
    # distillate to receiver
    line([(5.6, 2.8), (5.6, 1.6), (6.6, 1.6)], color="#8e44ad")
    arrow(6.65, 1.6, 6.1, 1.6, "#8e44ad")
    box(6.7, 1.1, 8.3, 2.1, "Distillate<br>receiver", fill="#f5eef8")
    # vacuum
    line([(6.0, 7.4), (7.0, 7.9)], color="#7f8c8d", dash="dash")
    box(7.0, 7.6, 8.6, 8.5, "<b>G001</b> top vessel<br>vacuum: TV1, P301", fill="#eef2f0")

    # sensors: (x, y, tag)
    sensors = {
        "T703": (1.45, 0.75), "T709": (1.25, 2.1), "T711": (1.25, 3.8), "T712": (1.25, 5.4),
        "T705": (1.25, 7.0), "PDI701": (0.55, 4.6), "FYI702": (6.65, 6.55), "PDI702": (6.35, 4.6),
        "FT704": (4.15, 2.4), "FT703": (6.15, 1.95), "PY23": (7.8, 8.75),
    }
    for tag, (x, y) in sensors.items():
        grp = SENSOR_INFO[tag]["group"]
        big = tag in hl
        fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text", text=[f"<b>{tag}</b>"],
                                 textposition="middle right" if x < 6 else "middle left" if x > 7.5 else "top center",
                                 marker=dict(size=22 if big else 15, color=GROUP_COLORS[grp],
                                             line=dict(color="#111" if big else "white", width=2)),
                                 hovertext=f"{tag}: {SENSOR_INFO[tag]['readme']}<br>{SENSOR_INFO[tag]['location']}",
                                 hoverinfo="text", showlegend=False))
    line([(0.75, 2.4), (0.75, 6.8)], color="#9467bd", width=1.5)  # PDI701 span along column
    # valves where disturbances were applied (from the YAML files)
    valves = {"HV009": (3.55, 1.1), "HV001": (3.0, 2.1), "HV004": (4.55, 2.6), "HV005": (5.85, 2.2)}
    for tag, (x, y) in valves.items():
        fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text", text=[tag], textposition="middle right",
                                 textfont=dict(size=9, color="#6b7280"),
                                 marker=dict(symbol="diamond", size=10, color="#d1d5db", line=dict(color="#6b7280", width=1)),
                                 hovertext=f"{tag}: valve used in the anomalous runs (see Annotations page)",
                                 hoverinfo="text", showlegend=False))
    for grp, col in GROUP_COLORS.items():
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=12, color=col), name=grp))
    fig.update_layout(shapes=shapes, annotations=ann)
    fig.update_xaxes(visible=False, range=[0, 9.2])
    fig.update_yaxes(visible=False, range=[0, 9.1], scaleanchor="x", scaleratio=1)
    return _layout(fig, 640, hovermode="closest", legend=dict(orientation="h", y=-0.02, x=0.05),
                   margin=dict(l=10, r=10, t=10, b=10))
