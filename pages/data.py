import datetime as dt

import streamlit as st
import streamlit.components.v1 as components

from src import ui
from src.data_parts import FLOW

ui.apply_style()
ui.header("2 · The dataset")
recs, frames, ann, events = ui.require_data()
D = ui.data_dir()
n_norm = sum(r.run_type == "normal" for r in recs)
hours = sum(len(f) for f in frames.values()) / 3600


def clock(sec: int) -> dt.time:
    return dt.time(sec // 3600, sec % 3600 // 60, sec % 60)


def secs(t: dt.time) -> int:
    return t.hour * 3600 + t.minute * 60 + t.second


st.markdown(f"The dataset contains **{len(recs)} recordings** of the plant ({n_norm} normal, {len(recs) - n_norm} "
            f"anomalous) at **6 operating points**, {hours:.1f} hours in total. Each recording is a CSV file in which "
            "**every row is one second** and every column one sensor.")

# ------------------------------------------------------------------------------------------ 1
st.markdown("### From the plant to numbers")
st.markdown("Choose a recording and where to start. The plant then replays that part of the file second by second: "
            "the clock is the file's Time column, the tags show the values of that row, and the box below the "
            "drawing shows the same rows as they appear in the file.")
labels, moments, spans = ui.replay_choices(D)
keys = [r.key for r in recs]
default = next(r.key for r in recs if r.op == "OP31" and r.run_type == "anomalous")
c1, c2 = st.columns([1, 1.3])
key = c1.selectbox("Recording", keys, index=keys.index(default), format_func=labels.get)
ms = moments[key]
mi = c2.selectbox("Start at", range(len(ms)), index=1 if len(ms) > 1 and key == default else 0,
                  format_func=lambda i: ms[i]["label"], key=f"start_{key}")
m = ms[mi]
t0, t1 = spans[key]
rng = st.slider("From – To (at most 30 minutes)", min_value=clock(t0), max_value=clock(t1),
                value=(clock(m["a"]), clock(m["b"])), step=dt.timedelta(seconds=30), format="HH:mm:ss",
                key=f"range_{key}_{mi}")
a, b = secs(rng[0]), secs(rng[1])
if b - a > 1800:
    b = a + 1800
    st.caption(f"Shortened to 30 minutes: {clock(a)} – {clock(b)}.")
if b - a < 30:
    b = min(t1, a + 60)
components.html(ui.dataset_plant(D, key, a, b, m["focus"]), height=880, scrolling=False)

# ------------------------------------------------------------------------------------------ 2
st.markdown("### What is in the dataset")
st.markdown("Every operating point has one **normal** recording (OP31 has two) and one **anomalous** recording. "
            "The files contain clock times but no dates.")
st.markdown(ui.ds_part(D, "files"), unsafe_allow_html=True)
st.caption("Operating points are ordered by pressure. Anomalies = number of annotated anomalies in the recording's "
           "annotation file.")

# ------------------------------------------------------------------------------------------ 3
st.markdown("### Operating points: why the recordings differ")
st.markdown("An operating point is one combination of plant settings, *such as pressure and heat input* (README). The "
            "plant was run at six of them. The clearest difference is the pressure: the lower the pressure, the lower "
            "the boiling temperatures, so the whole column runs cooler. A value that is normal at one operating point "
            "can be unusual at another, so every recording must be compared with normal data **from the same "
            "operating point**; that is why each one has its own normal recording.")
html, h = ui.ds_part(D, "ops")
components.html(html, height=h)
st.caption("Typical (median) values of the normal recordings. OP18 and OP22 have the same pressure, so they must "
           "differ in another setting that the dataset does not name. Only OP29 has its settings written out (in its "
           "annotation file): heater H701 at 60 % (210 W), pressure setpoint 550 mbar, PDI702 setpoint 2 mbar.")

# ------------------------------------------------------------------------------------------ 4
st.markdown("### What each value means")
st.markdown("Each file has a time column and 18 sensor columns; the project uses the 11 below.")
st.markdown(ui.ds_part(D, "sensors"), unsafe_allow_html=True)
st.caption("Units as given in the README and the annotation files; for the flows and PDI701 the dataset states no "
           "unit. 'Background physics' marks general knowledge that the dataset itself does not state.")

# ------------------------------------------------------------------------------------------ 5
st.markdown("### Normal, anomalous, and the answer key")
c = st.columns(2)
with c[0].container(border=True):
    st.markdown(f"**Normal recordings ({n_norm})**  \nThe plant ran as planned. The detection models learn from these "
                "what normal behaviour looks like.")
with c[1].container(border=True):
    st.markdown(f"**Anomalous recordings ({len(recs) - n_norm})**  \nThe operators disturbed the plant on purpose. "
                "Each comes with an **annotation file**, the *answer key*: for every anomaly it says what was done, "
                "where, and when the process counts as anomalous.")
opts = ui.anomaly_choices(D)
okeys = [k for k, _ in opts]
olab = dict(opts)
pick = st.selectbox("Example", okeys, index=okeys.index("OP31OP031TA001A001"), format_func=olab.get,
                    help="All 23 annotated anomalies")
ex = ui.example(D, pick)
components.html(ex["chart"], height=ex["height"])
st.markdown(f"- **What was done:** {ex['what']}\n- **When:** {ex['when']} {ex['how']}\n- **{ex['seen']}** "
            "Other sensors may react too: page 3 shows which.")
st.caption("Orange = disturbance applied by the operators; light red = marked anomalous by the experts; purple = "
           "short marked spikes. In total the six annotation files describe 23 anomalies: 17 caused on purpose and "
           "6 side effects observed afterwards (all in OP29).")

# ------------------------------------------------------------------------------------------ 6
st.markdown("### How the project uses the data")
st.markdown(FLOW, unsafe_allow_html=True)

# ------------------------------------------------------------------------------------------ 7
st.markdown("### Two things that look odd but are normal")
st.markdown("A detection model must not mistake these for anomalies.")
n1, n2 = ui.ds_part(D, "normal")
c = st.columns(2)
with c[0]:
    st.markdown("**Temperatures rise slowly during every batch.** The light components boil away first, so the "
                "remaining liquid gets heavier and hotter (OP10 normal run: 72.5 → 104.0 °C).")
    components.html(n1, height=232)
with c[1]:
    st.markdown("**The pressure moves in a regular saw-tooth.** The pressure controller keeps pulling it back to its "
                "setpoint (OP17 normal run, 10 minutes shown).")
    components.html(n2, height=232)

# ------------------------------------------------------------------------------------------ 8
st.markdown("### Things to keep in mind")
st.markdown("The files are clean at first sight: one row every second, no missing values, no repeated time stamps. "
            "Four details matter for the rest of the project.")
fill = ui.fill_info(D)
t = st.tabs(["A filled gap", "Errors in the answer key", "One run anomalous throughout", "Normal runs do not cover everything"])
with t[0]:
    st.markdown(f"In the OP18 normal recording, from {fill['start']} to {fill['end']}, all sensors follow perfectly "
                f"straight lines for {fill['length'] / 60:.1f} minutes: these values were filled in, not measured. "
                "This part should not be used as normal data.")
    html, h = ui.ds_part(D, "fill"); components.html(html, height=h)
with t[1]:
    st.markdown("In the long lists of short spikes (OP17 and OP18), three periods end before they begin and one is "
                "listed out of time order. They must be removed or corrected before results are evaluated.")
    st.markdown(ui.ds_part(D, "invalid"), unsafe_allow_html=True)
with t[2]:
    st.markdown("In OP22 the leaking sample valves (A004) are marked anomalous for every second of the recording, so "
                "this recording has no normal stretch to compare with.")
    html, h = ui.ds_part(D, "whole"); components.html(html, height=h)
with t[3]:
    st.markdown("The cooling-water flow at OP10 stays around 3.3 in the normal recording (blue) and around 7.1 in the "
                "anomalous one (red): no value of the anomalous run lies in the range of the normal run (blue band). "
                "A model trained on the normal run may raise alarms here although nothing is marked.")
    html, h = ui.ds_part(D, "cover"); components.html(html, height=h)
