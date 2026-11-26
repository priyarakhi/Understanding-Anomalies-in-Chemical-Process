import streamlit as st
import streamlit.components.v1 as components

from src import ui

ui.apply_style()
ui.header("1 · The plant in motion")
ui.require_data()

st.markdown("All data in this project come from one **laboratory distillation plant**. It separates a liquid mixture "
            "(butan-1-ol, propan-2-ol and water) by boiling it and cooling the vapour back into liquid. "
            "Press **Play the process** to see how it works, compare the six **operating points**, see **where "
            "anomalies happened** and replay the measured data of that moment, or replay a whole recording.")

components.html(ui.plant_page(ui.data_dir()), height=770, scrolling=False)

st.caption("Simplified sketch built from the dataset README and the annotation files; not to scale, valve positions "
           "approximate. Moving dots illustrate the process. In a replay, the temperatures and the reflux, distillate "
           "and cooling-water flows follow the measured data.")
