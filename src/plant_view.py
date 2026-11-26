"""
Interactive plant drawing (Task 1.a).

The drawing, its styles and its behaviour live in src/assets/ (plant.svg,
plant.css, plant.js). This module adds the data and texts and returns one
self-contained HTML page that Streamlit shows with components.html.

Every statement in the texts below comes from the dataset README, the YAML
annotation files or the CSV data. General physics is marked as background.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .metadata import SENSOR_INFO, SENSORS

ASSETS = Path(__file__).resolve().parent / "assets"

# ----------------------------------------------------------------- equipment
EQUIPMENT_INFO = {
    "V001": dict(kind="Vessel", name="Reboiler V001",
                 text="The heated vessel at the bottom that holds the liquid mixture (butan-1-ol, propan-2-ol, water). "
                      "The main heater H701 supplies the heat that makes the liquid boil; heater H702 (orange band at the "
                      "top of the vessel) heats its upper section. The liquid temperature is measured by T703.",
                 sensors=["T703"]),
    "H701": dict(kind="Heater", name="Main heater H701",
                 text="Electric heater of the reboiler V001. In the normal state of OP29 it runs without feedback "
                      "control at 60 % power (210 W); the OP29 disturbance reduced it to 45 % (157.5 W) (OP29 YAML).",
                 sensors=["T703"]),
    "C001": dict(kind="Column section", name="Column section C001 (bottom)",
                 text="Vapour from the reboiler rises through the column while liquid flows down. Each contact between "
                      "them moves light components upward and heavy components downward. T709 measures the temperature "
                      "below C001, T711 the temperature between C001 and C002. Its wall heater is H706 (orange band).",
                 sensors=["T709", "T711", "PDI701"]),
    "C002": dict(kind="Column section", name="Column section C002 (middle)",
                 text="Middle section of the column. T711 is measured below it and T712 above it. Its wall heater "
                      "H704 (orange band) heats the section to prevent wall condensation (OP29 YAML).",
                 sensors=["T711", "T712", "PDI701"]),
    "C003": dict(kind="Column section", name="Column section C003 (top)",
                 text="Top section of the column. T712 is measured below it and T705 at its top, where the vapour "
                      "leaves towards the condensers. The reflux enters the column at the top. Its wall heater is "
                      "H708 (orange band).",
                 sensors=["T712", "T705", "PDI701"]),
    "H702": dict(kind="Heater", name="Heater H702 (upper part of the reboiler)",
                 text="Electric heater of the upper section of the reboiler V001, 'to prevent wall condensation' "
                      "(OP29 YAML). It is controlled automatically: in the normal state of OP29 its setpoint is the "
                      "temperature T701 + 10 °C, measured with sensor T702; the OP29 disturbance lowered it to T701 + 5 °C. "
                      "T701 and T702 are in the CSV files but are not among the 11 project sensors.",
                 sensors=[]),
    "H706": dict(kind="Heater", name="Heater H706 (column section C001)",
                 text="Wall heater at column section C001 (OP29 YAML). The dataset names it only in an observed side "
                      "effect of OP29 ('jumpy heater power', seen in its temperature sensor T706); its purpose is not "
                      "stated. T706 is in the CSV files but not among the 11 project sensors.",
                 sensors=[]),
    "H704": dict(kind="Heater", name="Heater H704 (column section C002)",
                 text="Electric heater of column section C002, 'to prevent wall condensation' (OP29 YAML). It is "
                      "controlled automatically: in the normal state of OP29 its setpoint is T701 + 5 °C, measured with "
                      "sensor T704; the OP29 disturbance lowered it to T701 + 0 °C. T704 is in the CSV files but not "
                      "among the 11 project sensors.",
                 sensors=[]),
    "H708": dict(kind="Heater", name="Heater H708 (column section C003)",
                 text="Wall heater at column section C003 (OP29 YAML). The dataset names it only in an observed side "
                      "effect of OP29 ('jumpy heater power', seen in its temperature sensor T708); its purpose is not "
                      "stated. T708 is in the CSV files but not among the 11 project sensors.",
                 sensors=[]),
    "HE": dict(kind="Heat exchangers", name="Condensers HE001, HE002",
               text="Cool the vapour coming from the column top so that it becomes liquid again (condensate). "
                    "The cooling fluid comes from the thermostat TCU1; its flow is measured by FYI702.",
               sensors=["FYI702"]),
    "TCU1": dict(kind="Thermostat", name="Circulating thermostat TCU1",
                 text="Pumps temperature-controlled fluid through the cooling loop of the condensers (YAML: 'pumping of "
                      "temperature-controlled fluid (cooling/heating) through the loop'). In the OP31 anomalous run it "
                      "was switched off twice; FYI702 then reads exactly 0.",
                 sensors=["FYI702"]),
    "V002": dict(kind="Vessel", name="Buffer vessel V002",
                 text="Collects the condensed liquid. PDI702 is measured here; the YAML links a lower PDI702 to a lower "
                      "liquid level. The reflux pump P701 and the distillate pump P702 are controlled to keep PDI702 at "
                      "its setpoint (2 mbar in OP29).",
                 sensors=["PDI702"]),
    "P701": dict(kind="Pump", name="Reflux pump P701",
                 text="Pumps condensed liquid from V002 back to the top of the column (reflux). The reflux flow is "
                      "measured by FT704.",
                 sensors=["FT704"]),
    "P702": dict(kind="Pump", name="Distillate pump P702",
                 text="Pumps condensed liquid from V002 to the distillate receiver (the product). The distillate flow "
                      "is measured by FT703. In the OP29 disturbance this pump was switched off (power 0 %).",
                 sensors=["FT703"]),
    "RECV": dict(kind="Vessel", name="Distillate receiver",
                 text="Collects the product (distillate) that leaves the plant.",
                 sensors=["FT703"]),
    "G001": dict(kind="Vacuum system", name="Top vessel G001 with vacuum pump P301 and valve TV1",
                 text="PY23 measures the pressure in G001. The vacuum pump P301 and the throttle valve TV1 hold the plant "
                      "pressure at its setpoint (550 mbar in OP29). The pressure level is the clearest difference "
                      "between the operating points.",
                 sensors=["PY23"]),
    "HV001": dict(kind="Valve (normally sealed)", name="Side-draw valve HV001",
                  text="Valve between reboiler V001 and column section C001, normally sealed. In the OP18 anomalous run "
                       "nitrogen was injected through it (50 and 30 NL/h). Position in the drawing is approximate.",
                  sensors=[]),
    "HV009": dict(kind="Valve (normally sealed)", name="Manual valve HV009",
                  text="Valve at the reboiler V001, normally sealed. In the OP10 anomalous run nitrogen was injected "
                       "through it at 5 NL/h. Position in the drawing is approximate.",
                  sensors=[]),
    "HV004": dict(kind="Valve (normally sealed)", name="Sample valve HV004",
                  text="Manual sample valve on the reflux line behind the reflux pump P701, normally sealed. Used in the "
                       "anomalous runs for syringe withdrawals (OP17, OP22), for air entering the reflux line (OP22) and, "
                       "when improperly sealed, for recurring air leaks (OP17, OP18, OP22).",
                  sensors=["FT704"]),
    "HV005": dict(kind="Valve (normally sealed)", name="Sample valve HV005",
                  text="Manual sample valve; the YAML links its leak to the distillate stream (seen in FT703). Improperly "
                       "sealed in the anomalous runs of OP17, OP18 and OP22. Position in the drawing is approximate.",
                  sensors=["FT703"]),
}

# ----------------------------------------------------------------- tour steps
TOUR_STEPS = [
    dict(short="Overview", title="A batch distillation plant in the laboratory",
         text="<p>The plant separates a liquid mixture of <b>butan-1-ol, propan-2-ol and water</b> by heating it and "
              "cooling the vapour again (README). Liquids that boil more easily leave first.</p>"
              "<p>Follow the five steps: <b>heat</b> the liquid, let the vapour <b>rise</b> through the column, "
              "<b>condense</b> it, <b>collect and split</b> it, all under <b>vacuum</b>. Click any part or sensor "
              "in the drawing for details.</p>"
              "<p class='small'>Coloured lines: red = vapour, blue = condensate and cooling water, green = reflux, "
              "purple = distillate (product), grey = vacuum line. Moving dots in the column illustrate vapour rising "
              "and liquid falling. The drawing is simplified and not to scale.</p>",
         highlight=None, flows=[], sensors=[]),
    dict(short="Heat", title="1. Heat the liquid in the reboiler",
         text="<p>The reboiler <b>V001</b> holds the liquid. The main heater <b>H701</b> brings it to the boil. The "
              "vapour that forms is richer in the components that boil more easily (background physics).</p>"
              "<p><b>T703</b> measures the liquid temperature.</p>",
         data="As the lighter components leave, the remaining liquid gets heavier and hotter: T703 rises slowly "
              "during every run, for example from 72.5 °C to 104.0 °C over the 133.6-minute normal run of OP10. "
              "This slow rise is normal behaviour, not an anomaly.",
         highlight=["eq-V001", "eq-H701", "sen-T703"], flows=["flow-column"], sensors=["T703"]),
    dict(short="Rise", title="2. Vapour rises and separates in the column",
         text="<p>The vapour rises through the three column sections <b>C001 → C002 → C003</b>, while liquid flows "
              "down. Where they meet, light components move up and heavy components move down, so the top becomes "
              "richer in light components (background physics).</p>"
              "<p>Temperatures are measured between the sections: <b>T709</b> (below C001), <b>T711</b>, <b>T712</b> "
              "and <b>T705</b> (top). <b>PDI701</b> is the pressure difference along the column. Orange bands: the "
              "wall heaters H702 (upper reboiler), H706, H704 and H708 (column sections C001 to C003); for H702 and "
              "H704 the OP29 YAML says they prevent wall condensation.</p>",
         data="The column is hottest at the bottom and coolest at the top: in the OP10 normal run the medians are "
              "T703 77.5 > T709 75.9 > T711 70.6 > T712 70.4 > T705 68.0 °C.",
         highlight=["eq-C001", "eq-C002", "eq-C003", "eq-H702", "eq-H706", "eq-H704", "eq-H708", "sen-T709", "sen-T711", "sen-T712", "sen-T705",
                    "sen-PDI701", "eq-V001"],
         flows=["flow-column", "flow-vapour"], sensors=["T709", "T711", "T712", "T705", "PDI701"]),
    dict(short="Condense", title="3. Condense the vapour",
         text="<p>At the top the vapour enters the condensers <b>HE001, HE002</b>. Cooling fluid from the thermostat "
              "<b>TCU1</b> takes heat away and the vapour becomes liquid (condensate).</p>"
              "<p><b>FYI702</b> measures the cooling-water flow.</p>",
         data="The median FYI702 of the normal runs lies between about 3.3 and 7.0 (unit not stated). In the OP31 "
              "anomalous run TCU1 was switched off twice and FYI702 dropped to exactly 0 within 2 to 4 seconds.",
         highlight=["eq-HE", "eq-TCU1", "sen-FYI702"], flows=["flow-vapour", "flow-cool-in", "flow-cool-out",
                                                             "flow-condensate"], sensors=["FYI702"]),
    dict(short="Collect & split", title="4. Collect the liquid and split it",
         text="<p>The condensate collects in the buffer vessel <b>V002</b>. Two pumps take it away:</p>"
              "<p><b>P701</b> returns part of it to the column top as <b>reflux</b> (flow <b>FT704</b>). Reflux "
              "improves the separation. <b>P702</b> sends the rest to the receiver as <b>distillate</b>, the "
              "product (flow <b>FT703</b>).</p>"
              "<p>Both pumps are controlled to keep <b>PDI702</b> at its setpoint (2 mbar in the OP29 YAML); the YAML "
              "links PDI702 to the liquid level in V002.</p>",
         data="PDI702 stays close to 2 mbar in all normal runs (medians 1.93 to 2.03). Median reflux FT704 lies "
              "between about 0.23 and 0.62 and median distillate FT703 between about 0.05 and 0.34. In OP17, OP18 "
              "and OP22 much more liquid is returned as reflux than taken out as distillate.",
         highlight=["eq-V002", "eq-P701", "eq-P702", "eq-RECV", "sen-PDI702", "sen-FT704", "sen-FT703"],
         flows=["flow-condensate", "flow-reflux", "flow-distillate"], sensors=["PDI702", "FT704", "FT703"]),
    dict(short="Vacuum", title="5. The whole plant runs under vacuum",
         text="<p>The vacuum pump <b>P301</b> and the throttle valve <b>TV1</b> hold the pressure below atmospheric "
              "pressure (about 1013 mbar). <b>PY23</b> measures it in the top vessel <b>G001</b>.</p>"
              "<p>Lower pressure means lower boiling temperatures (background physics). The pressure level is the "
              "clearest difference between the six operating points.</p>",
         data="Median PY23 in the normal runs: OP17 ≈ 299, OP18 ≈ 399, OP22 ≈ 399, OP29 ≈ 548, OP10 ≈ 599, "
              "OP31 ≈ 699 mbar. Its saw-tooth shape comes from the pressure controller repeatedly correcting the "
              "pressure.",
         highlight=["eq-G001", "sen-PY23", "eq-HE"], flows=["flow-vacuum"], sensors=["PY23"]),
]


# ----------------------------------------------------------------- operating points
OP_NOTES = {
    "OP17": "Lowest pressure (about 299 mbar), so the coolest column: the top is at about 52.6 °C.",
    "OP18": "About 399 mbar. Same pressure as OP22, so the two must differ in another setting that the dataset does "
            "not name.",
    "OP22": "About 399 mbar, like OP18. Its median temperatures are almost identical to OP18's.",
    "OP29": "About 548 mbar. The only operating point whose settings are written out in a YAML file: heater H701 at "
            "60 % (210 W), pressure setpoint 550 mbar, PDI702 setpoint 2 mbar.",
    "OP10": "About 599 mbar. The column top runs at about 68.0 °C.",
    "OP31": "Highest pressure (about 699 mbar), so the hottest column: the top is at about 71.2 °C. It has two "
            "normal runs.",
}

PROJECT = dict(
    intro="<div class='kicker'>The project in one picture</div><h3>From the plant to the three questions</h3>"
          "<p>The plant produces the data. Two models learn from the <b>normal</b> runs what normal behaviour looks "
          "like, forecast the next 30 seconds, and raise an alarm when reality differs too much from the forecast. "
          "We compare their alarms with the expert annotations.</p>"
          "<p>Click the steps in the strip under the drawing. <b>Question 1</b> is about the first two steps (what "
          "the sensors show), <b>Question 2</b> about the alarms of each model, <b>Question 3</b> about comparing "
          "the evaluations of the two models.</p><h4>Task 1 is split into three parts</h4>"
          "<p><b>1.a</b> the plant and how it works (this page) &middot; <b>1.b</b> the dataset &middot; "
          "<b>1.c</b> what changes in the sensors during anomalies.</p>",
    footer="<h4>Fixed by the course and our choices (slide 14)</h4><table class='mini'><tr><th>Fixed</th>"
           "<th>Our choice</th></tr><tr><td>Data subset and splits</td><td>Which two models to train</td></tr>"
           "<tr><td>Preprocessing and windowing</td><td>Evaluation metrics, with justification</td></tr>"
           "<tr><td>Model definitions, training settings</td><td>Dashboard design and interactions</td></tr>"
           "<tr><td>Scoring and threshold rules</td><td>Which cases to show and explain</td></tr></table>",
    boxes=[
        dict(title="Plant & sensors", sub="11 signals, 1 per second",
             text="<p>The 11 sensors measure temperatures, flows, pressure differences and the pressure once per second "
                  "(README). Click them in the drawing to see what each one measures.</p>"),
        dict(title="Recordings", sub="13 runs in 6 OPs",
             text="<p>Each run is one CSV file: 7 <b>normal</b> runs (file names start with train_normal) and 6 "
                  "<b>anomalous</b> runs (test_anormal). For each anomalous run a YAML file describes when and where the "
                  "process was disturbed: the <b>annotations</b>, our ground truth.</p>"),
        dict(title="Learn normal", sub="trained on normal runs only",
             text="<p>Each model learns from the normal runs how the 11 signals usually develop. It never sees an "
                  "anomaly while learning. This is useful because anomalies are rare and each one is different.</p>"),
        dict(title="Forecast", sub="180 s in → 30 s out",
             text="<p>At every moment the model looks at the last 180 seconds of all 11 sensors and predicts the next "
                  "30 seconds (slide 10).</p>"),
        dict(title="Residual", sub="observed − forecast",
             text="<p>The residual is the difference between what the sensors really show and what the model "
                  "predicted. Small residual: behaviour as expected. Large residual: something unexpected.</p>"),
        dict(title="Score & alarm", sub="fixed rules",
             text="<p>A fixed scoring rule turns the residuals into one anomaly score; a fixed threshold rule turns the "
                  "score into alarm or no alarm (slide 9).</p>"),
        dict(title="Evaluate", sub="vs. annotations",
             text="<p>The alarms are compared with the annotated anomaly intervals: which events were detected or "
                  "missed, how fast, and where false alarms occurred. Possible metrics are precision, recall, F1 and "
                  "detection delay; we choose and justify them (slide 11).</p>"),
    ],
    questions=[
        dict(cls="q1", title="Question 1 · Task 1", text="What changes in the sensors during an anomaly? Which sensors, "
                                                          "what kind of change, do they recover?"),
        dict(cls="q2", title="Question 2 · Task 2", text="How does each model behave: detections, misses, response "
                                                          "time, false alarms?"),
        dict(cls="q3", title="Question 3 · Task 3", text="Where is one model better than the other, and is it the same "
                                                          "at every operating point?"),
    ],
)

EQ_MAP = {"HV009": "eq-HV009", "HV001": "eq-HV001", "HV004": "eq-HV004", "HV005": "eq-HV005", "TCU1": "eq-TCU1",
          "H701": "eq-H701", "H702": "eq-H702", "H704": "eq-H704", "TV1": "eq-G001", "P702": "eq-P702",
          "P701": "eq-P701"}

ANOMALY_GROUPS = [
    dict(title="Nitrogen into the reboiler", where="Valve HV009 at V001", eq="eq-HV009",
         text="5 NL/h of nitrogen for 17 minutes.", items=[("OP10", "A001")]),
    dict(title="Nitrogen below the column", where="Valve HV001 between V001 and C001", eq="eq-HV001",
         text="50, 30 and 30 NL/h of nitrogen, 3 to 5.5 minutes each.", items=[("OP18", "A001"), ("OP18", "A002"),
                                                                               ("OP18", "A003")]),
    dict(title="Liquid withdrawn from the reflux line", where="Valve HV004 behind pump P701", eq="eq-HV004",
         text="Samples taken with a syringe: 8.3, 8.5, 31.0 and 39.6 g (OP17); 8.2 and 8.0 g (OP22).",
         items=[("OP17", "A001"), ("OP17", "A002"), ("OP17", "A003"), ("OP17", "A004"), ("OP22", "A001"),
                ("OP22", "A003")]),
    dict(title="Air into the reflux line", where="Leaking syringe connection at HV004", eq="eq-HV004",
         text="Air entered the reflux line for about 5 minutes.", items=[("OP22", "A002")]),
    dict(title="Leaking sample valves", where="Valves HV004 and HV005", eq="eq-HV005",
         text="Improperly sealed valves let air in during (almost) the whole run: short spikes in the flows FT703 and "
              "FT704. Recurrent in OP17 and OP18, permanent in OP22.",
         items=[("OP17", "A005"), ("OP18", "A004"), ("OP22", "A004")]),
    dict(title="Cooling switched off", where="Thermostat TCU1", eq="eq-TCU1",
         text="The cooling thermostat was switched off for 6 and for 10 minutes.", items=[("OP31", "A001"),
                                                                                         ("OP31", "A002")]),
    dict(title="Five settings changed at once", where="H701, wall heaters, P702, TV1, PDI702 setpoint", eq="eq-H701",
         text="Heater power 210 → 157.5 W, wall-heater setpoints −5 °C, distillate pump off, pressure setpoint "
              "550 → 500 mbar, PDI702 setpoint 2 → 1 mbar, for 11 minutes. Afterwards, side effects were annotated "
              "(pressure-control overshoots, jumpy heater power).",
         items=[("OP29", "A001"), ("OP29", "A002")]),
]


# ----------------------------------------------------------------- data for sensor cards
def sensor_info(recs, frames) -> dict:
    out = {}
    for s in SENSORS:
        i = SENSOR_INFO[s]
        ops = {}
        for op in sorted({r.op for r in recs}):
            vals = pd.concat([frames[r.key][s] for r in recs if r.op == op and r.run_type == "normal"])
            dec = 2 if s[0] == "T" or s == "PY23" else 3
            ops[op] = dict(med=round(float(vals.median()), dec), lo=round(float(vals.quantile(.01)), dec),
                           hi=round(float(vals.quantile(.99)), dec))
        out[s] = dict(group=i["group"], readme=i["readme"], plain=i["plain"], location=i["location"],
                      unit=i["unit"], ops=ops)
    return out


def replay_events(ann: pd.DataFrame, events: pd.DataFrame, op: str, file_name: str) -> list[dict]:
    """Events of one anomalous run in the form the replay script needs."""
    from .annotations import has_time
    from .data_loader import time_to_seconds
    a = ann[(ann["OP"] == op) & (ann["File"] == file_name) & ann["Valid interval"]]
    if a.empty:
        return []
    out = []
    ev = events[events["OP"] == op].set_index("ID")
    for aid, g in a.groupby("ID", sort=False):
        e = ev.loc[aid]
        cat = e["Category"] if isinstance(e["Category"], str) else None
        what = e["Perturbation"] if isinstance(e["Perturbation"], str) else e["Observed effect(s)"]
        short = f"{aid[-4:]} ({cat or e['Class']})"
        for _, r in g.drop_duplicates(["begin_s", "end_s"]).iterrows():
            if cat == "recurrent":
                out.append(dict(kind="spike", b=int(r["begin_s"]), e=int(r["end_s"]), pb=None, pe=None,
                                short=short, what=what))
                continue
            pb = time_to_seconds(e["Perturbation begin"]) if has_time(e["Perturbation begin"]) else None
            pe = time_to_seconds(e["Perturbation end"]) if has_time(e["Perturbation end"]) else None
            if cat == "permanent":
                pb = pe = None
            out.append(dict(kind="permanent" if cat == "permanent" else "event", b=int(r["begin_s"]),
                            e=int(r["end_s"]), pb=pb, pe=pe, short=short, what=what))
    return out


def _round(s: str, x: np.ndarray) -> list:
    dec = 2 if s[0] == "T" else 1 if s == "PY23" else 3
    return [round(float(v), dec) for v in x]


def build_payload(recs, frames, ann, events, step_s: int = 4) -> dict:
    from .annotations import has_time
    from .data_loader import time_to_seconds
    stats = sensor_info(recs, frames)
    runs, order = {}, []
    for r in recs:
        df = frames[r.key]
        d = df.iloc[::step_s]
        runs[r.key] = dict(
            label=f"{r.op} · {r.label}" + (" (anomalous)" if r.run_type == "anomalous" else " (normal)"),
            op=r.op, type=r.run_type, t0=int(df["seconds_of_day"].iloc[0]), step=step_s, n=len(d),
            minutes=round(len(df) / 60, 1),
            v={s: _round(s, d[s].to_numpy()) for s in SENSORS},
            st={s: dict(min=float(df[s].min()), max=float(df[s].max()), med=float(df[s].median())) for s in SENSORS},
            events=replay_events(ann, events, r.op, r.file_name) if r.run_type == "anomalous" else [])
        order.append(r.key)

    op_order = sorted({r.op for r in recs}, key=lambda o: float(pd.concat(
        [frames[r.key]["PY23"] for r in recs if r.op == o and r.run_type == "normal"]).median()))
    ops = {}
    for o in op_order:
        normal = [r for r in recs if r.op == o and r.run_type == "normal"]
        allv = pd.concat([frames[r.key] for r in normal])
        ops[o] = dict(med={s: float(allv[s].median()) for s in SENSORS}, normal_runs=[r.key for r in normal],
                      note=OP_NOTES.get(o, ""))

    # anomalies (one entry per OP and ID)
    anoms, lookup = [], {}
    for _, e in events.iterrows():
        rec = next(r for r in recs if r.op == e["OP"] and r.run_type == "anomalous")
        eqs = [EQ_MAP[x.strip()] for x in str(e["Equipment"]).split(",") if x.strip() in EQ_MAP]
        effect = str(e["Observed effect(s)"])
        if not eqs:
            if "TV1" in effect:
                eqs = ["eq-G001"]
            elif "heater" in effect.lower():
                # side effects seen in a heater temperature: T702 -> H702, T704 -> H704, T706 -> H706, T708 -> H708
                eqs = [f"eq-H70{x.strip()[-1]}" for x in str(e["Annotated sensors"]).split(",")
                       if x.strip() in ("T702", "T704", "T706", "T708")] or ["eq-H702", "eq-H706", "eq-H704", "eq-H708"]
        eqs = list(dict.fromkeys(eqs))
        pb = time_to_seconds(e["Perturbation begin"]) if has_time(e["Perturbation begin"]) else None
        pe = time_to_seconds(e["Perturbation end"]) if has_time(e["Perturbation end"]) else None
        if e["Category"] in ("recurrent", "permanent"):
            pb = pe = None
            jump = int(e["begin_s"])
        else:
            jump = int(min(e["begin_s"], pb if pb is not None else e["begin_s"]) - 120)
        cat = e["Category"] if isinstance(e["Category"], str) else str(e["Class"])
        a = dict(op=e["OP"], id=e["ID"], short=f"{e['ID'][-4:]} ({cat})", eq=eqs,
                 what=e["Perturbation"] if isinstance(e["Perturbation"], str) else effect,
                 pb=pb, pe=pe, sensors=e["Annotated sensors"],
                 sensor_list=[x.strip() for x in str(e["Annotated sensors"]).split(",")],
                 run=rec.key, jump=jump,
                 trend=next((x.strip() for x in str(e["Annotated sensors"]).split(",") if x.strip() in SENSORS), "PY23"),
                 key=e["OP"] + e["ID"], cls=e["Class"], cat=e["Category"] if isinstance(e["Category"], str) else None,
                 b=int(e["begin_s"]), e=int(e["end_s"]), first=e["First begin"], last=e["Last end"],
                 n=int(e["Distinct intervals"]), equipment=str(e["Equipment"] or ""),
                 mode=str(e["Perturbation mode(s)"]) if isinstance(e["Perturbation mode(s)"], str) else "",
                 effect=effect if effect != "nan" else "")
        anoms.append(a)
        lookup[(e["OP"], e["ID"][-4:])] = a
    groups = []
    for g in ANOMALY_GROUPS:
        items = []
        for op, short in g["items"]:
            a = lookup[(op, short)]
            items.append(dict(run=a["run"], jump=a["jump"], trend=a["trend"], label=f"{op} {short}", key=a["key"]))
        groups.append(dict(title=g["title"], where=g["where"], eq=g["eq"], text=g["text"], items=items, side=[]))
    used = {it["key"] for g in groups for it in g["items"]}
    groups[-1]["side"] = [a["key"] for a in anoms if a["key"] not in used]

    default_run = next(r.key for r in recs if r.op == "OP31" and r.run_type == "anomalous")
    return dict(info=dict(equipment=EQUIPMENT_INFO, sensors=stats), steps=TOUR_STEPS, sensors=SENSORS,
                runs=runs, run_order=order, default_run=default_run, speeds=[5, 15, 60, 150],
                ops=ops, op_order=op_order, default_op="OP31", op_scale=[50, 110],
                anomalies=anoms, anomaly_groups=groups, project=PROJECT)


def page_html(payload: dict, start_view: str = "process", start_run: str | None = None,
              start_t: int | None = None, theme: str = "light", start_anom: str | None = None) -> str:
    css = (ASSETS / "plant.css").read_text(encoding="utf-8")
    svg = (ASSETS / "plant.svg").read_text(encoding="utf-8")
    js = (ASSETS / "plant.js").read_text(encoding="utf-8")
    data = dict(payload, start_view=start_view, start_run=start_run, start_t=start_t, start_anom=start_anom)
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    modes = "".join(f'<button class="mode" data-view="{v}">{t}</button>' for v, t in
                    [("process", "&#9881; How it works"), ("ops", "&#9673; Operating points"),
                     ("anom", "&#9888; Where anomalies happened"), ("live", "&#9654; Replay a recording")])
    legend = ("<span><span class='ln' style='border-color:#c0392b'></span>vapour</span>"
              "<span><span class='ln' style='border-color:#2b6cb0'></span>condensate / cooling water</span>"
              "<span><span class='ln' style='border-color:#138a72'></span>reflux</span>"
              "<span><span class='ln' style='border-color:#8e44ad'></span>distillate (product)</span>"
              "<span><span class='ln' style='border-color:#6b7280'></span>vacuum</span>"
              "<span class='hint'>Click any part or sensor tag</span>")
    row = start_view == "row"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body class="{'rowmode' if row else ''}">
<div class="modes">{modes}</div>
<div class="wrap"><div class="stage" id="stage">{svg}<div class="caption" id="cap"></div><div class="legend">{legend}</div>
<div class="pop" id="pop"></div></div><div class="panel" id="panel"></div></div>{'<div class="filestrip" id="rows"></div>' if row else ''}
<script>window.PLANT_DATA = {blob};</script><script>{js}</script></body></html>"""
