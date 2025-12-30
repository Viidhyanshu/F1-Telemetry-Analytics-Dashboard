import os
import warnings
import fastf1
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

# Enable caching to avoid re-downloading large F1 datasets every run
os.makedirs(".fastf1_cache", exist_ok=True)
fastf1.Cache.enable_cache(".fastf1_cache")

# Streamlit page setup for dashboard-style layout
st.set_page_config(
    page_title="F1 Telemetry Analytics",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Minimal styling to keep F1 branding feel without UI clutter
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

# Session state is used so data doesn't reload on every UI interaction
if "race_data" not in st.session_state:
    st.session_state.race_data = None


def available_years():
    # FastF1 reliably supports seasons from 2018 onwards
    return list(range(2018, pd.Timestamp.now().year + 1))


def load_schedule(year):
    # Centralized schedule loading to isolate API failures
    try:
        return fastf1.get_event_schedule(year)
    except:
        return None


def load_race_session(year, round_no):
    # Load once and reuse to keep UI responsive
    try:
        session = fastf1.get_session(year, round_no, "R")
        session.load()
        return session
    except:
        return None


def fastest_lap_telemetry(session, driver):
    # Using fastest lap ensures clean, comparable racing line data
    try:
        laps = session.laps.pick_driver(driver)
        if laps.empty:
            return None

        lap = laps.pick_fastest()
        tel = lap.get_telemetry()

        # Normalize brake values for consistent heatmaps
        if "Brake" in tel and tel["Brake"].max() <= 1:
            tel["Brake"] *= 100

        # Distance ordering prevents broken track lines
        if "Distance" in tel:
            tel = tel.sort_values("Distance")

        return tel
    except:
        return None


def racing_line_plot(tel, title, metric):
    # Track maps require X-Y positional data
    if tel is None or "X" not in tel or "Y" not in tel:
        return None

    # Central mapping keeps visualization logic predictable
    metric_map = {
        "Speed": ("Speed", "Speed (km/h)", "Viridis"),
        "Throttle": ("Throttle", "Throttle (%)", "Greens"),
        "Brake": ("Brake", "Brake (%)", "Reds"),
        "Gear": ("nGear", "Gear", "Plasma"),
        "DRS": ("DRS", "DRS", "Blues")
    }

    col, label, scale = metric_map[metric]
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

    # Equal axis scaling preserves real track geometry
    fig.update_layout(
        title=title,
        height=700,
        template="plotly_white"
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)

    return fig


def compare_drivers(session, drivers):
    # Overlaying racing lines highlights driving style differences
    fig = go.Figure()
    colors = ["red", "blue", "green", "orange", "purple"]

    for i, driver in enumerate(drivers):
        tel = fastest_lap_telemetry(session, driver)
        if tel is not None:
            fig.add_trace(go.Scatter(
                x=tel["X"],
                y=tel["Y"],
                mode="lines",
                name=driver,
                line=dict(width=4, color=colors[i % len(colors)])
            ))

    fig.update_layout(
        title="Driver Racing Line Comparison",
        height=800,
        template="plotly_white"
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)

    return fig


def sector_delta_plot(session, driver):
    # Sector deltas show consistency and race pace evolution
    laps = session.laps.pick_driver(driver)
    data = laps[["LapNumber", "Sector1Time", "Sector2Time", "Sector3Time"]].dropna()
    if data.empty:
        return None

    for s in ["Sector1Time", "Sector2Time", "Sector3Time"]:
        data[s] = data[s].dt.total_seconds()

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True)

    fig.add_trace(go.Scatter(x=data["LapNumber"], y=data["Sector1Time"]), 1, 1)
    fig.add_trace(go.Scatter(x=data["LapNumber"], y=data["Sector2Time"]), 2, 1)
    fig.add_trace(go.Scatter(x=data["LapNumber"], y=data["Sector3Time"]), 3, 1)

    fig.update_layout(
        title="Sector Time Trend",
        height=800,
        template="plotly_white"
    )

    return fig


def main():
    st.markdown('<div class="main-header">F1 Telemetry Analytics Dashboard</div>', unsafe_allow_html=True)

    with st.sidebar:
        year = st.selectbox("Season", available_years())
        schedule = load_schedule(year)

        if schedule is None:
            st.stop()

        races = [f"Round {r.RoundNumber}: {r.EventName}" for _, r in schedule.iterrows()]
        race_choice = st.selectbox("Race", races)
        round_no = schedule.iloc[races.index(race_choice)]["RoundNumber"]

        drivers = st.text_input("Driver Codes", "VER").upper().split(",")

        load = st.button("Load Race Data")

        show_throttle = st.checkbox("Throttle")
        show_brake = st.checkbox("Brake")
        show_gear = st.checkbox("Gear")
        show_drs = st.checkbox("DRS")
        show_compare = st.checkbox("Compare Drivers")
        show_sector = st.checkbox("Sector Delta")

    if load:
        st.session_state.race_data = load_race_session(year, round_no)

    session = st.session_state.race_data
    if session is None:
        st.info("Load race data to begin analysis")
        return

    driver = drivers[0]
    tel = fastest_lap_telemetry(session, driver)
    if tel is None:
        st.error("Telemetry not available for selected driver")
        return

    st.plotly_chart(racing_line_plot(tel, f"Speed Map — {driver}", "Speed"), True)

    if show_throttle:
        st.plotly_chart(racing_line_plot(tel, f"Throttle — {driver}", "Throttle"), True)
    if show_brake:
        st.plotly_chart(racing_line_plot(tel, f"Brake — {driver}", "Brake"), True)
    if show_gear:
        st.plotly_chart(racing_line_plot(tel, f"Gear — {driver}", "Gear"), True)
    if show_drs:
        st.plotly_chart(racing_line_plot(tel, f"DRS — {driver}", "DRS"), True)

    if show_compare and len(drivers) > 1:
        st.plotly_chart(compare_drivers(session, drivers), True)

    if show_sector:
        fig = sector_delta_plot(session, driver)
        if fig:
            st.plotly_chart(fig, True)


if __name__ == "__main__":
    main()
