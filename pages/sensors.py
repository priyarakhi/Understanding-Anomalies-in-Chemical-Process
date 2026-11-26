import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from src import ui

ui.apply_style()
ui.header("3 · The sensors (Question 1)")
recs, frames, ann, events = ui.require_data()
D = ui.data_dir()
R = ui.q1_results(D)
A = [r for r in R if not r.get("special")]
react = {r["key"]: [s for s, x in r["sensors"].items() if x["kind"] not in ("none", "n/a")] for r in A}
avg = np.mean([len(v) for v in react.values()])
cells = [x for r in A for x in r["sensors"].values() if x["kind"] not in ("none", "n/a")]
n_yes = sum(x.get("recovery") == "yes" for x in cells)
n_no = sum(x.get("recovery") == "no" for x in cells)

st.markdown("Question 1 asks three things about every anomaly: **which sensors react, what changes, and do they "
            "recover?** The experts' annotation files name the sensor where they saw each anomaly. Here we look at "
            "**all 11 sensors** and compare each one with its own values just before the anomaly started.")

# ------------------------------------------------------------------------------------------ short answers
c = st.columns(3)
with c[0].container(border=True):
    st.markdown(f"**Which sensors?**  \nOn average **{avg:.0f} of the 11 sensors** react to an anomaly, while the "
                "experts usually named only one.")
with c[1].container(border=True):
    st.markdown("**What changes?**  \nTemperatures mostly **fall or rise**; flows and the buffer-vessel signal "
                "mostly **swing up and down**.")
with c[2].container(border=True):
    st.markdown(f"**Do they recover?**  \n**{n_yes} of {len(cells)}** reactions come back to normal; **{n_no}** "
                "stay different for more than 10 minutes.")
st.caption(f"Based on the {len(A)} anomalies that can be judged with the method at the bottom of the page "
           f"(of 23 in total).")

# ------------------------------------------------------------------------------------------ explore
st.markdown("### Explore the anomalies")
st.markdown("Pick a kind of disturbance and one anomaly. The anomaly plays out from **before** through **during** to "
            "**after**; each sensor's sentence appears when it starts to react. Hover a chart to read the values.")
components.html(ui.q1_page(D), height=1900, scrolling=False)

# ------------------------------------------------------------------------------------------ what we learn
st.markdown("### What we learn")
d_flow = [x["delay"] for r in A for s, x in r["sensors"].items() if s in ("FT704", "FT703", "PDI702") and x.get("delay") is not None]
d_temp = [x["delay"] for r in A for s, x in r["sensors"].items() if s[0] == "T" and x.get("delay") is not None]
not_back = [f"{s} in {r['op']} {r['id'][-4:]}" for r in A for s, x in r["sensors"].items() if x.get("recovery") == "no" and x["kind"] != "none"]
st.markdown(f"""
- **The annotation is a hint, not the full picture.** It names where the experts saw the anomaly; usually several more
  sensors react.
- **Flows react first, temperatures later:** typically about {np.median(d_flow) / 60:.1f} min after the onset for the
  flows, about {np.median(d_temp) / 60:.1f} min for the temperatures. After liquid is withdrawn (OP17, OP22) the
  column temperatures react only after about 2 to 5 minutes.
- **The same kind of disturbance gives the same pattern**, e.g. nitrogen below the column makes all column
  temperatures fall within about half a minute (OP18 A002, A003).
- **Most reactions recover.** Not back within 10 minutes: {", ".join(not_back)}.
- **Some reactions come after the disturbance:** when the cooling is switched off (OP31), the pressure, flows and
  column temperatures react only after the cooling returns.
""")

with st.expander("How 'react', 'change' and 'recover' are decided"):
    st.markdown("""
- **Onset** = when the disturbance was applied (side effects: when the marked period starts). **End** = end of the
  marked period.
- **Before** = the 5 minutes before the onset. The slow, normal drift of a batch (temperatures rising) is carried
  forward as a straight line fitted to the 10 minutes before the onset, if it is clearly larger than the noise;
  otherwise the level of the 5 minutes before is used.
- Values are smoothed with a 15-second median. **Tolerance** = 4 × the spread of the sensor in the "before" window, at
  least 3 measurement steps.
- **Reacts**: away from the carried-forward level by more than the tolerance for at least 30 s between onset and end
  (at least 3 minutes are looked at), and reached quickly (the deviation changes by more than twice the tolerance
  within one minute), so that slow batch drift is not counted. **Falls / rises**: direction of the largest
  deviation; **swings**: clearly above and clearly below; **short spikes**: no lasting change but short jumps at
  least 3 × as often as before.
- **Back to normal**: after the largest deviation, the value stays within the tolerance for at least 60 s, at the
  latest 10 minutes after the end. **Part of the way**: it comes back at least half way.
- **Checked by eye**: all anomalies were checked in plots. In 17 cases the simple line cannot follow the batch (late,
  fast-changing phases) or a regular pattern changes; these were corrected and the sentence says what is seen.
- **Not judged**: leaking valves (spikes over almost the whole run, no clean "before"), four OP29 side effects seen
  only in heater temperatures outside the 11 sensors, and OP29 A003 (the last 11 seconds of the recording).
""")
