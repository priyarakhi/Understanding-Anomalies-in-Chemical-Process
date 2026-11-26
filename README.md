# Understanding Anomalies in Chemical Processes

Interactive Streamlit dashboard for the master project *Understanding Anomalies in Chemical Processes*.
It covers Task 1: the plant (1.a), the dataset (1.b) and Question 1, what changes in the sensors (1.c).

## 1. Run it (Mac, VS Code)

1. Open this folder in VS Code (*File > Open Folder...*), then open a terminal (*Terminal > New Terminal*).
2. Check Python (3.10 or newer is needed):
   ```bash
   python3 --version
   ```
3. Create a virtual environment and install the packages (only once):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Start the dashboard:
   ```bash
   streamlit run app.py
   ```
   Your browser opens at http://localhost:8501. Stop it with `Ctrl + C` in the terminal.
   Next time you only need `source .venv/bin/activate` and `streamlit run app.py`.

The dataset is already included in `batch_distillation_dataset/`. If you move it, start with `BATCH_DATA_DIR=/path/to/batch_distillation_dataset streamlit run app.py`.

## 2. Pages (sidebar)

1. **The plant in motion** - the animated plant: how it works (step by step), the six operating points, where
   anomalies happened (with a replay of the measured data), and a replay of any recording. Every part and sensor
   can be clicked.
2. **The dataset** - from the plant to numbers (choose any of the 13 recordings and a time range: the plant replays
   the file row by row while the CSV rows appear below; restart and progress bar), what is in the dataset, operating
   points, what each value means, the answer key with an example for each of the 23 anomalies, how the project uses
   the data, two things that look odd but are normal, and four things to keep in mind.
3. **The sensors (Question 1)** - which sensors react to each anomaly, how, and whether they recover: three
   short answers; pick a kind of disturbance and an anomaly to see it play out before / during / after, with
   one chart and one sentence per sensor; a bar chart of how often each sensor reacts (click a bar for the list);
   five findings, and the method (src/q1.py).

## 3. Code structure

```
app.py                 entry point and page navigation
pages/                 plant.py, data.py and sensors.py, one file per sidebar page
src/metadata.py        sensor and equipment descriptions (from README, slides, YAML)
src/data_loader.py     reading CSV and YAML files, time handling
src/annotations.py     flattening and checking the YAML annotations
src/analysis.py        data-quality checks, coverage, Question 1 screening
src/q1_findings.py     reviewed findings for Question 1 (written after inspecting the plots)
src/plots.py           Plotly figures (used by later tasks)
src/plant_view.py      interactive plant drawing (texts + data); drawing, styles and script in src/assets/
src/dataset_view.py    reads the YAML annotation text for display
src/data_view.py       tables and charts for page 2 (charts drawn by src/assets/charts.*)
src/data_parts.py      page 2: replay of any recording, operating points, examples for all anomalies
src/q1.py              Question 1 analysis: change and recovery of every sensor for every anomaly
src/q1_view.py         page 3: data for the anomaly view and the bar chart
src/ui.py              cached data access and shared page elements
.streamlit/config.toml colour theme
batch_distillation_dataset/  the provided dataset
DATASET_GUIDE.md       written description of the dataset
```

The analysis code in `src/` does not depend on Streamlit and can be imported in a notebook:

```python
from src.data_loader import default_data_dir, discover_recordings, load_recording
recs = discover_recordings(default_data_dir())
df = load_recording(recs[0].csv_path)
```

## 4. Data sources

Only the files provided for the project are used: the measurement CSVs, the YAML annotations, the dataset
README and the introduction slides. Dataset reference (from the slides): Arweiler, J., Jungjohann, I.,
Muraleedharan, A. et al. *Batch Distillation Data for Developing Machine Learning Anomaly Detection Methods.*
Sci Data 13, 513 (2026). Full dataset: https://doi.org/10.5281/zenodo.17395544
