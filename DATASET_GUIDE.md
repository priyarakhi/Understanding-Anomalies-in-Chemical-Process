# Dataset Guide: Batch Distillation Dataset

*Based exclusively on the provided files: dataset README, 13 CSV files, 6 YAML files and the project slides/brief. All figures were computed from the files.*

---

## 1. Project context

The project evaluates anomaly detection in a batch distillation process (project brief and slides):

1. Two forecasting models are trained on **normal** runs. Each model uses the last **180 s** of the 11 sensors to predict the next **30 s**.
2. The difference between observation and forecast (**residual**) is converted into an anomaly score by a fixed scoring rule; a fixed threshold yields detections.
3. The detections are compared with the **annotated anomaly intervals** (ground truth) in an interactive dashboard.

Task 1 is the exploration of the dataset.

---

## 2. Process

Batch distillation separates a liquid mixture by heating it and cooling the resulting vapour (README). The mixture consists of **butan-1-ol, propan-2-ol and water**.

| Unit | Function | Sensors |
|---|---|---|
| **Reboiler V001** (heater H701) | Heating and partial evaporation of the mixture | T703 |
| **Column sections C001, C002, C003** | Separation; vapour rises, liquid flows downwards | T709, T711, T712, T705, PDI701 |
| **Top vessel G001** (vacuum pump P301, throttle valve TV1) | Pressure control | PY23 |
| **Condensers HE001/HE002** (cooling water from thermostat TCU1) | Condensation of the vapour | FYI702 |
| **Buffer vessel V002** | Collection of the condensate | PDI702 |
| **Reflux pump P701** | Return of condensate to the column (reflux) | FT704 |
| **Distillate pump P702** | Withdrawal of distillate to the distillate receiver | FT703 |

Because the batch is not replenished, the composition in the reboiler changes over time and temperatures rise gradually during normal operation.

---

## 3. File structure

```
batch_distillation_dataset/
  README.md
  OP10/ OP17/ OP18/ OP22/ OP29/ OP31/
     measurements/
        train_normal_experiment_001.csv     normal run
        train_normal_experiment_002.csv     second normal run (OP31 only)
        test_anormal_experiment_001.csv     anomalous run
     annotations/
        test_anormal_experiment_001.yaml    annotation of the anomalous run
```

- 6 operating points, 13 CSV files (7 normal, 6 anomalous), 6 YAML files.
- A CSV file and its annotation share the same operating point and file stem.
- The archive additionally contains macOS system files (`__MACOSX/`, `.DS_Store`) without content.

---

## 4. Measurement files (CSV)

- One row per second; `Time` is given as `HH:MM:SS` (no date).
- 19 columns: `Time` and 18 sensors. The README specifies **11** sensors for the project; the others (LS701, LS702, T701, T702, T704, T706, T708) are not used.
- Column order in the files: T705 follows T712.
- All files were checked: no empty cells, no duplicate or missing time steps, no run crosses midnight.

| Run | Start – End | Duration | Rows |
|---|---|---|---|
| OP10 normal | 09:57:19 – 12:10:56 | 133.6 min | 8,018 |
| OP10 anomalous | 15:51:11 – 17:27:12 | 96.0 min | 5,762 |
| OP17 normal | 12:47:11 – 13:27:54 | 40.7 min | 2,444 |
| OP17 anomalous | 10:13:12 – 13:08:32 | 175.3 min | 10,521 |
| OP18 normal | 10:45:09 – 13:50:48 | 185.6 min | 11,140 |
| OP18 anomalous | 10:35:09 – 13:02:47 | 147.6 min | 8,859 |
| OP22 normal | 15:19:48 – 16:51:55 | 92.1 min | 5,528 |
| OP22 anomalous | 10:24:34 – 12:52:49 | 148.2 min | 8,896 |
| OP29 normal | 09:49:43 – 11:52:56 | 123.2 min | 7,394 |
| OP29 anomalous | 13:53:01 – 16:00:58 | 128.0 min | 7,678 |
| OP31 normal 1 | 14:18:45 – 17:55:45 | 217.0 min | 13,021 |
| OP31 normal 2 | 11:14:22 – 12:08:40 | 54.3 min | 3,259 |
| OP31 anomalous | 09:24:10 – 12:55:32 | 211.4 min | 12,683 |
| **Total** | | **29.2 h** | **105,203** |

---

## 5. Sensors

Units: the README states none. The YAML files state **mbar** for PY23 (“pressure setpoint 550 mbar”) and PDI702 (“pressure-difference setpoint 2 mbar”) and use **°C** for temperatures. PDI701 is assumed to be in mbar. Flow units are not stated.

| Sensor | Measurement (README) | Unit | Observed behaviour |
|---|---|---|---|
| FT703 | Flow in the top product (distillate) stream | not stated | Approx. 0.05–0.34 depending on OP; ≈ 0.005 corresponds to no flow; short spikes in OP17/18/22 |
| FT704 | Flow in the reflux stream | not stated | Approx. 0.2–0.65 depending on OP |
| FYI702 | Cooling-water flow signal | not stated | Discrete levels (e.g. 2.93, 3.64, 3.90, 4.56); 0 when TCU1 is switched off |
| PDI701 | Pressure difference along the column | mbar (assumed) | Median ≈ −0.15 (OP17) to ≈ 1.0 (OP29) |
| PDI702 | Pressure difference, buffer vessel V002 | mbar | Mean between 1.99 and 2.05 in every run (controlled at 2 mbar) |
| PY23 | Pressure in top vessel G001 | mbar | ≈ 300 / 400 / 550 / 600 / 700 depending on OP |
| T703 | Liquid temperature in reboiler V001 | °C | Increases during a run (up to +32 °C) |
| T709 | Temperature below C001 | °C | Highest column temperature |
| T711 | Temperature between C001 and C002 | °C | |
| T712 | Temperature between C002 and C003 | °C | |
| T705 | Temperature at the top of C003 | °C | Lowest column temperature at OP10, OP29, OP31; at OP17, OP18, OP22 about 0.3 °C above T712 |

---

## 6. Operating points

The dataset does not list the settings of the operating points. The following values are medians computed from the recordings.

| OP | Pressure PY23 (mbar) | Reflux ratio FT704/FT703 |
|---|---|---|
| OP17 | ≈ 300 | ≈ 7.8 |
| OP18 | ≈ 400 | ≈ 5.7–6.5 |
| OP22 | ≈ 400 | ≈ 9.0–9.7 |
| OP29 | ≈ 550 (confirmed in the YAML file) | ≈ 2.1 |
| OP10 | ≈ 600 | ≈ 0.7 (normal) / 1.1 (anomalous) |
| OP31 | ≈ 700 | ≈ 2.2 |

---

## 7. Annotations (YAML)

| Field | Meaning |
|---|---|
| `id` | Event identifier, e.g. `OP017TA001A003` = OP17, test run 001, anomaly 003. The same ID can appear several times if one event affects several sensors. |
| `class` | `ConfirmedAnomaly` or `Anomaly` (observed deviation, cause not confirmed; OP29 only) |
| `hasBeginning` / `hasEnd` | Annotated anomaly interval; lists of times for recurrent events |
| `hasCategory` | transient, recurrent or permanent |
| `Perturbation` | Description of the disturbance |
| `PerturbationMode` | Type of disturbance, time of application, affected equipment and sensor showing the effect |

The time of application of the disturbance and the annotated interval differ: for transient events the interval begins within one minute of the disturbance and ends about 1–10 minutes after its removal.

| OP | Event | Disturbance | Category | Sensor |
|---|---|---|---|---|
| OP10 | A001 | Nitrogen injection, 5 NL/h, into V001 (HV009) | transient | T712 |
| OP17 | A001–A004 | Sample withdrawal from the reflux line (HV004): 8.3, 8.5, 31.0, 39.6 g | transient | FT704 |
| OP17 | A005 | Improperly sealed sample valves (air ingress) | recurrent (14 + 43 intervals) | FT704, FT703 |
| OP18 | A001–A003 | Nitrogen injection, 50/30/30 NL/h, below C001 (HV001) | transient | T709 |
| OP18 | A004 | Improperly sealed sample valves (air ingress) | recurrent (61 + 28 intervals) | FT704, FT703 |
| OP22 | A001, A003 | Sample withdrawal from the reflux line: 8.2, 8.0 g | transient | FT704 |
| OP22 | A002 | Air ingress via a leaking syringe connection | transient | PDI702 |
| OP22 | A004 | Improperly sealed sample valves | permanent (entire run) | FT704, FT703 |
| OP29 | A001 | Combined changes: H701 210 → 157.5 W, heater set-points −5 °C, P702 off, PY23 set-point 550 → 500 mbar, PDI702 set-point 2 → 1 mbar | transient | T701, T702, T704, PY23, FT703, PDI702 |
| OP29 | A002, A003 | Pressure-control overshoot (unconfirmed) | – | PY23 |
| OP29 | A004–A007 | Fluctuating heater power (unconfirmed) | – | T702, T706, T704, T708 |
| OP31 | A001, A002 | Thermostat TCU1 switched off (cooling-water supply reduced) | transient | FYI702 |

In total there are 177 annotated intervals, three of which are invalid (see section 8).

---

## 8. Data quality

1. **Interpolated segment:** OP18 normal run, 10:59–11:37 (≈ 38 min). All sensors follow a straight line. Afterwards PY23 is ≈ 979 mbar instead of ≈ 400 mbar, indicating an interruption of operation. To be excluded from training.
2. **Invalid annotation intervals** (end before begin): OP17 A005/FT703 `11:20:00 → 10:20:37` and `11:33:10 → 11:30:50`; OP18 A004/FT703 `12:51:25 → 12:51:15`. The begin times of OP18 A004 (FT704) are not in chronological order.
3. **Spikes in normal runs:** the normal runs of OP17, OP18 and OP22 contain flow spikes similar to the annotated air-ingress anomalies; OP10, OP29 and OP31 do not.
4. **Fully annotated run:** OP22 is annotated as anomalous for its entire duration (permanent event).
5. **Different settings within OP10:** cooling-water signal ≈ 3.3 vs ≈ 7.1, reflux ratio ≈ 0.7 vs ≈ 1.1.
6. **Different batch stages:** normal and anomalous runs of one OP often cover different parts of the batch (e.g. OP17: 41 vs 175 min).
7. **OP29 annotations** refer to heater temperatures not among the 11 sensors and contain placeholder times (`00:00:00`).
8. **Annotation vs data:** OP18 A001 states a lower temperature at T709; the data show an increase at T709 and a decrease at T711/T712.
9. **OP29 recording ends during an unconfirmed event** (A003 ends at the last time step); PDI701 rises to ≈ 5 in the final seconds.
10. **OP31 normal run 2** is stored with full floating-point precision; all other files use three decimals.
11. About 1 % of rows contain values such as `72.45949999999999` (interpolation of single time steps).

---

## 9. Terminology

- **Operating point (OP):** fixed combination of process settings.
- **Normal / anomalous run:** recording without / with annotated disturbances.
- **Reflux / distillate:** condensate returned to the column / withdrawn as product.
- **Reflux ratio:** reflux flow divided by distillate flow.
- **Transient / recurrent / permanent:** anomaly occurring once / repeatedly / during the entire run.
- **Residual:** observed value minus forecast.
- **Interpolation:** filling a gap in a time series with estimated values.
- **NL/h:** normal litres per hour (gas volume at 0 °C, 1.013 bar).
