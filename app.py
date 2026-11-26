import streamlit as st

st.set_page_config(page_title="Understanding Anomalies in Chemical Processes", layout="wide",
                   initial_sidebar_state="expanded")
st.navigation([
    st.Page("pages/plant.py", title="1 · The plant in motion", default=True),
    st.Page("pages/data.py", title="2 · The dataset"),
    st.Page("pages/sensors.py", title="3 · The sensors (Question 1)"),
]).run()
