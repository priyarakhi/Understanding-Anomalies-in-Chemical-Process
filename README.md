# Understanding Anomalies in Chemical Processes – Task 1

Interactive Streamlit dashboard for exploring the batch distillation dataset
(butan-1-ol, propan-2-ol and water; 6 operating points, 13 runs, 11 sensors).

## Contents

The dashboard has five pages:

- **Overview** – key figures and a diagram of the plant with the sensor locations
- **Dataset structure** – file organisation, example CSV rows, annotation fields, sensors and operating points
- **Time series** – sensor readings of each run with the annotated anomaly intervals, and normal vs. anomalous runs
- **Annotated anomalies** – timeline and table of the annotated events per operating point
- **Data quality** – issues found in the data that are relevant for the next tasks

## Running locally

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
app.py                       Streamlit app (pages, charts, tables)
data_utils.py                loading the CSV/YAML files, summaries, data checks
diagram.py                   plant diagram (SVG)
icons.py                     small icons used in the layout
DATASET_GUIDE.md             written description of the dataset
batch_distillation_dataset/  the provided dataset
```

## Notes

- Only the provided files are used (README, measurement CSVs, YAML annotations).
- Units: the README does not state any. The YAML annotations use mbar for PY23 and PDI702 and °C for temperatures; flow units are not given.
- Operating-point settings (pressure, reflux ratio) are not listed in the dataset and are computed from the recordings as medians.
- Three annotation intervals have an end time before their start time; they are excluded.
- Each event ID is counted once, even if the YAML file lists it for several sensors.

## Data

Batch Distillation Dataset (subset provided for the course).
Full dataset: https://doi.org/10.5281/zenodo.17395544
