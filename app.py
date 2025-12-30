import os
import fastf1
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings

warnings.filterwarnings("ignore")

os.makedirs(".fastf1_cache", exist_ok=True)
fastf1.Cache.enable_cache(".fastf1_cache")

st.set_page_config(
    page_title="F1 Telemetry Analytics",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    font-weight: bold;
    color: #E10600;
    text-align: center;
}
.stSelectbox label, .stTextInput label {
    font-weight: bold;
    color: #05f2db;
}
</style>
""", unsafe_allow_html=True)

if "race_data" not in st.session_state:
    st.session_state.race_data = None
if "qualifying_data" not in st.session_state:
    st.session_state.qualifying_data = None


def get_years():
    return list(range(2018, pd.Timestamp.now().year + 1))


def get_schedule(year):
    try:
        return fastf1.get_event_schedule(year)
    except:
        return None


def load_session(year, rnd, s_type):
    try:
        session = fastf1.get_session(year, rnd, s_type)
        session.load()
        return session
    except:
        return None


def get_telemetry(session, driver):
    try:
        laps = session.laps.pick_driver(driver)
        if laps.empty:
            return None
        lap = laps.pick_fastest()
        tel = lap.get_telemetry()
        if "Brake" in tel and tel["Brake"].max() <= 1:
            tel["Brake"] *= 100
        if "Distance" in tel:
            tel = tel.sort_values("Distance")
        return tel
    except:
        return None


def racing_line(tel, title, color_col):
    if tel is None or "X" not in tel or "Y" not in tel:
        return None

    color_map = {
        "Speed": ("Speed", "Speed (km/h)", "Viridis"),
        "Throttle": ("Throttle", "Throttle (%)", "Greens"),
        "Brake": ("Brake", "Brake (%)", "Reds"),
        "Gear": ("nGear", "Gear", "Plasma"),
        "DRS": ("DRS", "DRS", "Blues")
    }

    col, label, scale = color_map[color_col]
    if col not in tel:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=tel["X"],
        y=tel["Y"],
        mode="lines+markers",
        marker=dict(
            size=6,
            color=tel[col],
            colorscale=scale,
            showscale=True,
            colorbar=dict(title=label)
        ),
        line=dict(width=3),
        name="Racing Line"
    ))

    fig.update_layout(
        title=title,
        height=700,
        template="plotly_white"
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def compare_drivers(session, drivers):
    fig = go.Figure()
    colors = ["red", "blue", "green", "orange", "purple"]

    for i, d in enumerate(drivers):
        tel = get_telemetry(session, d)
        if tel is not None:
            fig.add_trace(go.Scatter(
                x=tel["X"],
                y=tel["Y"],
                mode="lines",
                name=d,
                line=dict(width=4, color=colors[i % len(colors)])
            ))

    fig.update_layout(
        title="Driver Comparison",
        height=800,
        template="plotly_white"
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def sector_delta(session, driver):
    laps = session.laps.pick_driver(driver)
    data = laps[["LapNumber", "Sector1Time", "Sector2Time", "Sector3Time"]].dropna()
    if data.empty:
        return None

    for s in ["Sector1Time", "Sector2Time", "Sector3Time"]:
        data[s] = data[s].dt.total_seconds()

    fig = make_subplots(rows=3, cols=1)

    fig.add_trace(go.Scatter(x=data["LapNumber"], y=data["Sector1Time"]), 1, 1)
    fig.add_trace(go.Scatter(x=data["LapNumber"], y=data["Sector2Time"]), 2, 1)
    fig.add_trace(go.Scatter(x=data["LapNumber"], y=data["Sector3Time"]), 3, 1)

    fig.update_layout(height=800, title="Sector Delta")
    return fig


def main():
    st.markdown('<div class="main-header">F1 Telemetry Analytics Dashboard</div>', unsafe_allow_html=True)

    with st.sidebar:
        year = st.selectbox("Year", get_years())
        schedule = get_schedule(year)

        if schedule is None:
            st.stop()

        race_names = [f"Round {r.RoundNumber}: {r.EventName}" for _, r in schedule.iterrows()]
        race_choice = st.selectbox("Race", race_names)
        round_no = schedule.iloc[race_names.index(race_choice)]["RoundNumber"]

        drivers = st.text_input("Driver Codes", "VER").upper().split(",")

        load = st.button("Load Data")

        show_throttle = st.checkbox("Throttle")
        show_brake = st.checkbox("Brake")
        show_gear = st.checkbox("Gear")
        show_drs = st.checkbox("DRS")
        show_compare = st.checkbox("Compare Drivers")
        show_sector = st.checkbox("Sector Delta")

    if load:
        race = load_session(year, round_no, "R")
        st.session_state.race_data = race

    race = st.session_state.race_data
    if race is None:
        st.info("Load race data to begin")
        return

    driver = drivers[0]
    tel = get_telemetry(race, driver)

    if tel is None:
        st.error("No telemetry found")
        return

    st.plotly_chart(racing_line(tel, f"Speed - {driver}", "Speed"), True)

    if show_throttle:
        st.plotly_chart(racing_line(tel, f"Throttle - {driver}", "Throttle"), True)
    if show_brake:
        st.plotly_chart(racing_line(tel, f"Brake - {driver}", "Brake"), True)
    if show_gear:
        st.plotly_chart(racing_line(tel, f"Gear - {driver}", "Gear"), True)
    if show_drs:
        st.plotly_chart(racing_line(tel, f"DRS - {driver}", "DRS"), True)

    if show_compare and len(drivers) > 1:
        st.plotly_chart(compare_drivers(race, drivers), True)

    if show_sector:
        fig = sector_delta(race, driver)
        if fig:
            st.plotly_chart(fig, True)


if __name__ == "__main__":
    main()
