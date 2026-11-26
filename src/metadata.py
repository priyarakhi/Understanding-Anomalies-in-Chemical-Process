"""
Static descriptions of the dataset.

Every description here comes from one of three sources that ship with the
project: the dataset README.md, the professor's introduction slides, or the
YAML annotation files. Where a fact is NOT stated in those sources (for
example the unit of a flow sensor), we say so explicitly instead of guessing.
"""

OPERATING_POINTS = ["OP10", "OP17", "OP18", "OP22", "OP29", "OP31"]

# The 11 sensors the README tells us to use for this project.
SENSORS = ["FT703", "FT704", "FYI702", "PDI701", "PDI702", "PY23",
           "T703", "T705", "T709", "T711", "T712"]

# Columns present in every CSV but NOT part of the 11 project sensors.
EXTRA_COLUMNS = ["LS701", "LS702", "T701", "T702", "T704", "T706", "T708"]

# Order used when sensors are listed physically from bottom to top of the plant
SENSOR_ORDER_PHYSICAL = ["T703", "T709", "T711", "T712", "T705", "PDI701",
                         "PY23", "FYI702", "PDI702", "FT704", "FT703"]

GROUP_COLORS = {
    "Mass flow": "#1f77b4",
    "Pressure difference": "#9467bd",
    "Pressure": "#2ca02c",
    "Temperature": "#d62728",
}

SENSOR_INFO = {
    "FT703": dict(
        group="Mass flow", unit="not stated in dataset",
        readme="Flow in the top product stream",
        plain="How much finished product (distillate) leaves the plant per unit of time. "
              "This liquid is sent to the distillate receiver by the distillate pump P702.",
        location="Distillate (top product) line after pump P702"),
    "FT704": dict(
        group="Mass flow", unit="not stated in dataset",
        readme="Flow in the reflux stream: liquid returned to the column",
        plain="How much condensed liquid is pumped back into the top of the column (reflux) "
              "by the reflux pump P701. Reflux is needed for a good separation.",
        location="Reflux line from buffer vessel V002 back to the column top"),
    "FYI702": dict(
        group="Mass flow", unit="not stated in dataset",
        readme="Cooling-water flow signal",
        plain="How much cooling water flows through the condensers that turn the vapour back "
              "into liquid. The cooling water is supplied by the thermostat TCU1.",
        location="Cooling-water loop of the condensers HE001/HE002"),
    "PDI701": dict(
        group="Pressure difference", unit="not stated (PDI702 is given in mbar in the YAML)",
        readme="Pressure difference along the column",
        plain="Difference in pressure between the bottom and the top of the column. Vapour must "
              "push its way up through the column, so this value reflects how much vapour and "
              "liquid are travelling through it.",
        location="Across the column sections C001-C003"),
    "PDI702": dict(
        group="Pressure difference", unit="mbar (setpoint 2 mbar given in OP29 YAML)",
        readme="Pressure-difference measurement associated with buffer vessel V002",
        plain="A signal from the buffer vessel V002 where condensed liquid is collected. The YAML "
              "files link a lower value with a lower liquid level. The two pumps (P701, P702) "
              "are controlled to keep this value at its setpoint.",
        location="Buffer vessel V002 (after the condensers)"),
    "PY23": dict(
        group="Pressure", unit="mbar (setpoints 550/500 mbar given in OP29 YAML)",
        readme="Pressure in the top vessel G001",
        plain="The absolute pressure of the plant. The plant runs under vacuum (below "
              "atmospheric pressure), controlled by a vacuum pump and throttle valve TV1. "
              "The pressure level is one of the settings that defines an operating point.",
        location="Top vessel G001 (vacuum system)"),
    "T703": dict(
        group="Temperature", unit="°C",
        readme="Liquid temperature in the reboiler vessel V001",
        plain="Temperature of the boiling liquid mixture at the bottom of the plant (the 'pot' "
              "that is heated). It rises slowly during a batch as the lighter components "
              "leave.",
        location="Reboiler vessel V001 (bottom)"),
    "T705": dict(
        group="Temperature", unit="°C",
        readme="Temperature at the top of column section C003",
        plain="Temperature at the very top of the column, where the vapour leaves towards "
              "the condensers.",
        location="Top of column section C003"),
    "T709": dict(
        group="Temperature", unit="°C",
        readme="Temperature below column section C001",
        plain="Temperature just above the reboiler, where vapour enters the column.",
        location="Below column section C001"),
    "T711": dict(
        group="Temperature", unit="°C",
        readme="Temperature between column sections C001 and C002",
        plain="Temperature in the lower-middle part of the column.",
        location="Between C001 and C002"),
    "T712": dict(
        group="Temperature", unit="°C",
        readme="Temperature between column sections C002 and C003",
        plain="Temperature in the upper-middle part of the column.",
        location="Between C002 and C003"),
}

EXTRA_INFO = {
    "LS701": "Not described in the README. Values are only 0 or 1.",
    "LS702": "Not described in the README. Value is always 1 in all 13 files.",
    "T701": "Named in OP29 YAML as the temperature of main reboiler heater H701 (typically several hundred °C; range 73-439 °C over all files).",
    "T702": "Named in OP29 YAML as the sensor of heater H702 (upper section of reboiler V001).",
    "T704": "Named in OP29 YAML as the sensor of heater H704 (column section C002).",
    "T706": "Named in OP29 YAML as the sensor of heater H706 (column section C001).",
    "T708": "Named in OP29 YAML as the sensor of heater H708 (column section C003).",
}

# Equipment names that appear in the README and YAML files.
EQUIPMENT = {
    "V001": "Reboiler vessel: the heated 'pot' at the bottom that holds the liquid mixture",
    "V002": "Buffer vessel: collects the condensed liquid after the condensers",
    "C001": "Column section 1 (bottom section of the column)",
    "C002": "Column section 2 (middle section)",
    "C003": "Column section 3 (top section)",
    "G001": "Top vessel where the plant pressure PY23 is measured",
    "H701": "Main electric heater of the reboiler V001",
    "H702": "Heater of the upper section of V001 (prevents condensation on the wall)",
    "H704 / H706 / H708": "Column wall heaters (C002 / C001 / C003) that prevent wall condensation",
    "HE001, HE002": "Condensers: cool the vapour so it becomes liquid again",
    "TCU1": "Circulating thermostat that pumps cooling water through the condensers",
    "P701": "Reflux pump: sends liquid from V002 back to the column top",
    "P702": "Distillate pump: sends liquid from V002 to the distillate receiver",
    "P301 / TV1": "Vacuum pump and vacuum throttle valve that set the plant pressure",
    "HV001": "Side-draw valve between reboiler V001 and column section C001",
    "HV004": "Manual sample valve on the reflux line (behind reflux pump P701)",
    "HV005": "Manual sample valve (YAML links it to the distillate stream)",
    "HV009": "Manual valve at the reboiler vessel V001",
}

CATEGORY_TEXT = {
    "transient": "Temporary: a disturbance is applied for a limited time and the normal state is restored afterwards.",
    "recurrent": "Repeating: the same kind of short disturbance happens again and again during the run.",
    "permanent": "Lasting: the disturbance is present for the whole annotated period (here: the whole run).",
    None: "No category given (these entries have class 'Anomaly', not 'ConfirmedAnomaly').",
}

GLOSSARY = {
    "Batch distillation": "A process that separates a liquid mixture by heating it in a vessel. "
                          "Components that boil more easily evaporate first, rise through a column, are cooled "
                          "back into liquid and collected. 'Batch' means one filling is processed at a time, so "
                          "the conditions change slowly during a run.",
    "Operating point (OP)": "One fixed combination of plant settings, such as pressure and heat input (README).",
    "Run / recording / experiment": "One CSV file: one continuous series of sensor readings, one row per second.",
    "Normal run": "A recording without deliberately introduced disturbances. Used to learn normal behaviour (file prefix 'train_normal').",
    "Anomalous run": "A recording in which disturbances happened. Used for testing (file prefix 'test_anormal').",
    "Anomaly": "A period in which the process behaves differently from normal operation.",
    "Annotation": "Expert description (YAML file) of when an anomaly happened, what caused it and which sensor showed it.",
    "Event interval": "hasBeginning/hasEnd at the top level of an annotation: the period labelled as anomalous.",
    "Perturbation interval": "hasBeginning/hasEnd inside PerturbationMode: when the disturbance was actually applied.",
    "Reflux": "Condensed liquid returned to the top of the column. More reflux usually means a cleaner separation.",
    "Distillate": "The top product that is taken out of the plant.",
    "Vacuum": "Pressure below atmospheric pressure (about 1013 mbar). Lower pressure lowers boiling temperatures.",
    "Setpoint": "The target value that a controller tries to keep (e.g. pressure 550 mbar).",
    "Time series": "A sequence of measurements ordered in time.",
    "Residual": "Observed value minus predicted (forecast) value. Large residuals suggest unusual behaviour.",
    "Ground truth": "The reference labels (here: the annotated intervals) used to judge a model's detections.",
}
