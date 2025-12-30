"""
F1 Telemetry Analytics Dashboard
A comprehensive Streamlit application for visualizing Formula 1 telemetry data.
"""
import os
import fastf1

os.makedirs(".fastf1_cache", exist_ok=True)
fastf1.Cache.enable_cache(".fastf1_cache")

import streamlit as st
import fastf1
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Enable FastF1 caching for better performance
fastf1.Cache.enable_cache('cache')

# Page configuration
st.set_page_config(
    page_title="F1 Telemetry Analytics",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #E10600;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stSelectbox label, .stTextInput label {
        font-weight: bold;
        color: #05f2db;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'race_data' not in st.session_state:
    st.session_state.race_data = None
if 'qualifying_data' not in st.session_state:
    st.session_state.qualifying_data = None


def get_available_years():
    """Get list of available years from FastF1 (typically 2018-2024+)"""
    # FastF1 supports data from 2018 onwards
    current_year = pd.Timestamp.now().year
    return list(range(2018, current_year + 1))


def get_race_schedule(year):
    """Fetch and return the race schedule for a given year"""
    try:
        schedule = fastf1.get_event_schedule(year)
        return schedule
    except Exception as e:
        st.error(f"Error fetching schedule for {year}: {str(e)}")
        return None


def load_race_session(year, race_name_or_round, session_type='R'):
    """
    Load race session data
    
    Parameters:
    - year: Race year
    - race_name_or_round: Race name or round number
    - session_type: 'R' for race, 'Q' for qualifying
    
    Returns:
    - Session object or None if error
    """
    try:
        # Try to load by round number first
        if str(race_name_or_round).isdigit():
            round_num = int(race_name_or_round)
            session = fastf1.get_session(year, round_num, session_type)
        else:
            # Load by location name
            session = fastf1.get_session(year, race_name_or_round, session_type)
        
        session.load()
        return session
    except Exception as e:
        st.error(f"Error loading {session_type} session: {str(e)}")
        return None


def get_fastest_lap_telemetry(session, driver_code):
    """
    Extract fastest lap telemetry for a given driver
    
    Parameters:
    - session: FastF1 session object
    - driver_code: Three-letter driver code (e.g., 'VER', 'HAM')
    
    Returns:
    - Telemetry DataFrame or None
    """
    try:
        driver_laps = session.laps.pick_driver(driver_code)
        if len(driver_laps) == 0:
            return None
        
        fastest_lap = driver_laps.pick_fastest()
        telemetry = fastest_lap.get_telemetry()
        
        # Ensure telemetry has required columns
        if telemetry is None or len(telemetry) == 0:
            return None
        
        # Normalize brake data if it exists (some sessions have boolean 0/1 instead of percentage)
        if 'Brake' in telemetry.columns:
            # If brake values are only 0 and 1, convert to percentage (0-100)
            if telemetry['Brake'].max() <= 1 and telemetry['Brake'].min() >= 0:
                telemetry['Brake'] = telemetry['Brake'] * 100
        
        # Sort by distance to ensure proper line ordering
        if 'Distance' in telemetry.columns:
            telemetry = telemetry.sort_values('Distance').reset_index(drop=True)
        
        return telemetry
    except Exception as e:
        st.error(f"Error extracting telemetry for {driver_code}: {str(e)}")
        return None


def plot_racing_line_heatmap(telemetry, title="Racing Line Heatmap", color_by="Speed", height=900, width=900):
    """
    Create a racing line heatmap visualization with larger size
    
    Parameters:
    - telemetry: DataFrame with X, Y, and speed data
    - title: Plot title
    - color_by: Column to use for color mapping ('Speed', 'Throttle', 'Brake', 'nGear')
    - height: Plot height in pixels
    - width: Plot width in pixels
    
    Returns:
    - Plotly figure object
    """
    if telemetry is None or len(telemetry) == 0:
        return None
    
    # Validate required columns
    if 'X' not in telemetry.columns or 'Y' not in telemetry.columns:
        st.error("Telemetry data missing X or Y coordinates")
        return None
    
    # Determine color column with proper error handling
    color_col = None
    color_label = ""
    colorscale = 'Viridis'
    
    if color_by == "Speed":
        if 'Speed' not in telemetry.columns:
            st.error("Speed data not available in telemetry")
            return None
        color_col = telemetry['Speed']
        color_label = "Speed (km/h)"
        colorscale = 'Viridis'
    elif color_by == "Throttle":
        if 'Throttle' not in telemetry.columns:
            st.error("Throttle data not available in telemetry")
            return None
        color_col = telemetry['Throttle']
        color_label = "Throttle (%)"
        colorscale = 'Greens'
    elif color_by == "Brake":
        # Check for brake column with multiple possible names
        brake_col = None
        if 'Brake' in telemetry.columns:
            brake_col = 'Brake'
        elif 'BR' in telemetry.columns:
            brake_col = 'BR'
        else:
            # Try to find any column with 'brake' in the name (case insensitive)
            brake_cols = [col for col in telemetry.columns if 'brake' in col.lower()]
            if brake_cols:
                brake_col = brake_cols[0]
        
        if brake_col is None:
            st.error("Brake data not available in telemetry. Available columns: " + ", ".join(telemetry.columns.tolist()[:10]))
            return None
        
        color_col = telemetry[brake_col]
        color_label = "Brake (%)"
        colorscale = 'Reds'
        
        # Check if brake data is meaningful (not all zeros)
        if color_col.max() == 0:
            st.warning("Brake data appears to be all zeros. This might indicate the data source doesn't include brake telemetry for this session.")
    elif color_by == "Gear":
        if 'nGear' not in telemetry.columns:
            st.error("Gear data not available in telemetry")
            return None
        color_col = telemetry['nGear']
        color_label = "Gear"
        colorscale = 'Plasma'
    elif color_by == "DRS":
        # Check for DRS column with multiple possible names
        drs_col = None
        if 'DRS' in telemetry.columns:
            drs_col = 'DRS'
        elif 'drs' in telemetry.columns:
            drs_col = 'drs'
        else:
            # Try to find any column with 'drs' in the name (case insensitive)
            drs_cols = [col for col in telemetry.columns if 'drs' in col.lower()]
            if drs_cols:
                drs_col = drs_cols[0]
        
        if drs_col is None:
            st.error("DRS data not available in telemetry. Available columns: " + ", ".join(telemetry.columns.tolist()[:10]))
            return None
        
        color_col = telemetry[drs_col]
        color_label = "DRS"
        colorscale = 'Blues'
        
        # Normalize DRS data if it's boolean (0/1) to percentage (0-100)
        if color_col.max() <= 1 and color_col.min() >= 0:
            color_col = color_col * 100
        
        # Check if DRS data is meaningful (not all zeros)
        if color_col.max() == 0:
            st.warning("DRS data appears to be all zeros. This might indicate the data source doesn't include DRS telemetry for this session.")
    else:
        if 'Speed' not in telemetry.columns:
            st.error("Speed data not available in telemetry")
            return None
        color_col = telemetry['Speed']
        color_label = "Speed (km/h)"
        colorscale = 'Viridis'
    
    # Remove NaN values that could break the visualization
    valid_mask = ~(pd.isna(telemetry['X']) | pd.isna(telemetry['Y']) | pd.isna(color_col))
    if not valid_mask.any():
        st.error(f"No valid data points available for {color_by} visualization")
        return None
    
    # Filter and create clean dataframes
    telemetry_clean = telemetry[valid_mask].copy()
    color_col_clean = color_col[valid_mask].copy()
    
    # Ensure data is sorted by distance for proper line connection
    if 'Distance' in telemetry_clean.columns:
        sort_idx = telemetry_clean['Distance'].argsort()
        telemetry_clean = telemetry_clean.iloc[sort_idx].reset_index(drop=True)
        color_col_clean = color_col_clean.iloc[sort_idx].reset_index(drop=True)
    else:
        # Reset index if no distance column
        telemetry_clean = telemetry_clean.reset_index(drop=True)
        color_col_clean = color_col_clean.reset_index(drop=True)
    
    # Create the plot
    fig = go.Figure()
    
    # Add racing line with color mapping - use larger markers and thicker lines
    fig.add_trace(go.Scatter(
        x=telemetry_clean['X'],
        y=telemetry_clean['Y'],
        mode='markers+lines',
        marker=dict(
            size=8,  # Increased from 5 to 8
            color=color_col_clean,
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(
                title=dict(
                    text=color_label,
                    font=dict(size=14)
                ),
                len=0.7,  # Increased colorbar length
                thickness=25,  # Thicker colorbar
                tickfont=dict(size=12)
            ),
            line=dict(width=0.5, color='rgba(0,0,0,0.3)'),
            cmin=color_col_clean.min(),
            cmax=color_col_clean.max()
        ),
        line=dict(
            width=4,  # Increased from 3 to 4
            color='rgba(128,128,128,0.3)'
        ),
        name='Racing Line',
        hovertemplate='<b>Position</b><br>' +
                      'X: %{x:.1f}m<br>' +
                      'Y: %{y:.1f}m<br>' +
                      f'{color_label}: %{{marker.color:.1f}}<extra></extra>',
        connectgaps=False
    ))
    
    # Add start/finish line marker - larger
    if len(telemetry_clean) > 0:
        track_x = telemetry_clean['X'].values
        track_y = telemetry_clean['Y'].values
        
        fig.add_trace(go.Scatter(
            x=[track_x[0]],
            y=[track_y[0]],
            mode='markers',
            marker=dict(size=30, symbol='star', color='red', line=dict(width=3, color='white')),  # Increased size
            name='Start/Finish',
            showlegend=True,
            hovertemplate='<b>Start/Finish Line</b><br>' +
                         'X: %{x:.1f}m<br>' +
                         'Y: %{y:.1f}m<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20),  # Increased title size
            x=0.5,
            xanchor='center',
            y=0.98,  # Move title up
            yanchor='top'
        ),
        xaxis_title=dict(text="X Position (m)", font=dict(size=14)),
        yaxis_title=dict(text="Y Position (m)", font=dict(size=14)),
        template='plotly_white',
        showlegend=True,
        hovermode='closest',
        height=height,  # Use parameter
        width=width,    # Use parameter
        margin=dict(l=80, r=150, t=120, b=80),  # Increased right margin for colorbar
        legend=dict(
            font=dict(size=14),
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.3)",
            borderwidth=2
        )
    )
    
    # Set equal aspect ratio for proper track shape
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    
    return fig


def plot_driver_comparison(session, driver_codes, height=1000, width=1200):
    """
    Compare multiple drivers on the same track - FIXED VERSION
    
    Parameters:
    - session: FastF1 session object
    - driver_codes: List of driver codes to compare
    - height: Plot height
    - width: Plot width
    
    Returns:
    - Plotly figure object
    """
    if not driver_codes or len(driver_codes) < 2:
        st.warning("Please enter at least 2 driver codes for comparison (comma-separated)")
        return None
    
    fig = go.Figure()
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2']
    
    drivers_found = 0
    for idx, driver_code in enumerate(driver_codes):
        telemetry = get_fastest_lap_telemetry(session, driver_code)
        if telemetry is not None and len(telemetry) > 0:
            # Validate X and Y columns exist
            if 'X' in telemetry.columns and 'Y' in telemetry.columns:
                drivers_found += 1
                fig.add_trace(go.Scatter(
                    x=telemetry['X'],
                    y=telemetry['Y'],
                    mode='lines+markers',
                    name=f"{driver_code}",
                    line=dict(width=5, color=colors[idx % len(colors)]),  # Thicker lines
                    marker=dict(size=6, color=colors[idx % len(colors)]),
                    hovertemplate=f'<b>{driver_code}</b><br>' +
                                 'X: %{x:.1f}m<br>' +
                                 'Y: %{y:.1f}m<extra></extra>'
                ))
            else:
                st.warning(f"No position data available for {driver_code}")
        else:
            st.warning(f"Could not load telemetry for {driver_code}. Check if the driver participated in this session.")
    
    if drivers_found == 0:
        st.error("No valid telemetry data found for any of the selected drivers")
        return None
    
    fig.update_layout(
        title=dict(
            text="Driver Comparison - Racing Lines",
            font=dict(size=22),
            x=0.5,
            xanchor='center'
        ),
        xaxis_title=dict(text="X Position (m)", font=dict(size=16)),
        yaxis_title=dict(text="Y Position (m)", font=dict(size=16)),
        width=width,
        height=height,
        template='plotly_white',
        showlegend=True,
        hovermode='closest',
        legend=dict(
            font=dict(size=16),
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.3)",
            borderwidth=2
        ),
        margin=dict(l=80, r=80, t=120, b=80)
    )
    
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    
    return fig


def plot_sector_delta(session, driver_code):
    """
    Visualize sector-wise lap delta
    
    Parameters:
    - session: FastF1 session object
    - driver_code: Driver code
    
    Returns:
    - Plotly figure object
    """
    try:
        driver_laps = session.laps.pick_driver(driver_code)
        if len(driver_laps) == 0:
            return None
        
        # Get sector times
        sector_times = driver_laps[['LapNumber', 'Sector1Time', 'Sector2Time', 'Sector3Time']].copy()
        sector_times = sector_times.dropna()
        
        if len(sector_times) == 0:
            return None
        
        # Convert sector times to seconds for easier comparison
        def time_to_seconds(time_val):
            if pd.isna(time_val):
                return np.nan
            return time_val.total_seconds()
        
        sector_times['S1_sec'] = sector_times['Sector1Time'].apply(time_to_seconds)
        sector_times['S2_sec'] = sector_times['Sector2Time'].apply(time_to_seconds)
        sector_times['S3_sec'] = sector_times['Sector3Time'].apply(time_to_seconds)
        
        # Calculate deltas from best sector time
        best_s1 = sector_times['S1_sec'].min()
        best_s2 = sector_times['S2_sec'].min()
        best_s3 = sector_times['S3_sec'].min()
        
        sector_times['S1_delta'] = sector_times['S1_sec'] - best_s1
        sector_times['S2_delta'] = sector_times['S2_sec'] - best_s2
        sector_times['S3_delta'] = sector_times['S3_sec'] - best_s3
        
        # Create subplot
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Sector 1 Delta', 'Sector 2 Delta', 'Sector 3 Delta'),
            vertical_spacing=0.1
        )
        
        # Plot each sector
        fig.add_trace(
            go.Scatter(
                x=sector_times['LapNumber'],
                y=sector_times['S1_delta'],
                mode='lines+markers',
                name='Sector 1',
                line=dict(color='red', width=2),
                marker=dict(size=6)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=sector_times['LapNumber'],
                y=sector_times['S2_delta'],
                mode='lines+markers',
                name='Sector 2',
                line=dict(color='blue', width=2),
                marker=dict(size=6)
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=sector_times['LapNumber'],
                y=sector_times['S3_delta'],
                mode='lines+markers',
                name='Sector 3',
                line=dict(color='green', width=2),
                marker=dict(size=6)
            ),
            row=3, col=1
        )
        
        fig.update_xaxes(title_text="Lap Number", row=3, col=1)
        fig.update_yaxes(title_text="Delta (seconds)", row=1, col=1)
        fig.update_yaxes(title_text="Delta (seconds)", row=2, col=1)
        fig.update_yaxes(title_text="Delta (seconds)", row=3, col=1)
        
        fig.update_layout(
            title=f"Sector-wise Lap Delta - {driver_code}",
            height=800,
            template='plotly_white',
            showlegend=False
        )
        
        return fig
    except Exception as e:
        st.error(f"Error creating sector delta plot: {str(e)}")
        return None


def plot_qualifying_vs_race(session_qualifying, session_race, driver_code, height=600, width=700):
    """
    Compare qualifying vs race lap - FIXED VERSION
    
    Parameters:
    - session_qualifying: Qualifying session object
    - session_race: Race session object
    - driver_code: Driver code
    - height: Plot height
    - width: Plot width
    
    Returns:
    - Plotly figure object
    """
    if session_qualifying is None:
        st.error("Qualifying session data not available")
        return None
    
    if session_race is None:
        st.error("Race session data not available")
        return None
    
    fig = go.Figure()
    
    has_data = False
    
    # Get qualifying telemetry
    qual_telemetry = get_fastest_lap_telemetry(session_qualifying, driver_code)
    if qual_telemetry is not None and len(qual_telemetry) > 0:
        if 'X' in qual_telemetry.columns and 'Y' in qual_telemetry.columns:
            has_data = True
            fig.add_trace(go.Scatter(
                x=qual_telemetry['X'],
                y=qual_telemetry['Y'],
                mode='lines+markers',
                name=f"{driver_code} - Qualifying",
                line=dict(width=5, color='#9B59B6', dash='dash'),  # Purple, thicker
                marker=dict(size=6, color='#9B59B6'),
                hovertemplate='<b>Qualifying</b><br>' +
                             'X: %{x:.1f}m<br>' +
                             'Y: %{y:.1f}m<extra></extra>'
            ))
        else:
            st.warning(f"No position data in qualifying telemetry for {driver_code}")
    else:
        st.warning(f"Could not load qualifying telemetry for {driver_code}")
    
    # Get race telemetry
    race_telemetry = get_fastest_lap_telemetry(session_race, driver_code)
    if race_telemetry is not None and len(race_telemetry) > 0:
        if 'X' in race_telemetry.columns and 'Y' in race_telemetry.columns:
            has_data = True
            fig.add_trace(go.Scatter(
                x=race_telemetry['X'],
                y=race_telemetry['Y'],
                mode='lines+markers',
                name=f"{driver_code} - Race",
                line=dict(width=5, color='#E67E22'),  # Orange, thicker
                marker=dict(size=6, color='#E67E22'),
                hovertemplate='<b>Race</b><br>' +
                             'X: %{x:.1f}m<br>' +
                             'Y: %{y:.1f}m<extra></extra>'
            ))
        else:
            st.warning(f"No position data in race telemetry for {driver_code}")
    else:
        st.warning(f"Could not load race telemetry for {driver_code}")
    
    if not has_data:
        st.error(f"No valid telemetry data found for {driver_code} in qualifying or race sessions")
        return None
    
    fig.update_layout(
        title=dict(
            text=f"Qualifying vs Race Comparison - {driver_code}",
            font=dict(size=22),
            x=0.5,
            xanchor='center'
        ),
        xaxis_title=dict(text="X Position (m)", font=dict(size=16)),
        yaxis_title=dict(text="Y Position (m)", font=dict(size=16)),
        width=width,
        height=height,
        template='plotly_white',
        showlegend=True,
        hovermode='closest',
        legend=dict(
            font=dict(size=16),
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.3)",
            borderwidth=2
        ),
        margin=dict(l=80, r=80, t=120, b=80)
    )
    
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    
    return fig


# Main App
def main():
    st.markdown('<h1 class="main-header">F1 Telemetry Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("Race Selection")
        
        # Year selection
        available_years = get_available_years()
        selected_year = st.selectbox(
            "Select Year",
            options=available_years,
            index=len(available_years) - 1  # Default to most recent year
        )
        
        # Race selection
        schedule = get_race_schedule(selected_year)
        if schedule is not None and len(schedule) > 0:
            race_options = []
            for idx, row in schedule.iterrows():
                race_display = f"Round {row['RoundNumber']}: {row['Location']} ({row['EventName']})"
                race_options.append((race_display, row['RoundNumber']))
            
            race_display_names = [opt[0] for opt in race_options]
            selected_race_display = st.selectbox(
                "Select Race",
                options=race_display_names,
                index=0
            )
            selected_round = [opt[1] for opt in race_options if opt[0] == selected_race_display][0]
        else:
            st.error("Could not load race schedule. Please check your internet connection.")
            st.stop()
        
        # Driver selection
        st.header("Driver Selection")
        driver_code_input = st.text_input(
            "Driver Code(s)",
            value="VER",
            help="Enter driver code(s) separated by commas (e.g., VER, HAM, LEC)"
        )
        
        # Parse driver codes
        driver_codes = [code.strip().upper() for code in driver_code_input.split(',') if code.strip()]
        
        # Load button
        load_button = st.button("Load Race Data", type="primary", use_container_width=True)
        
        # Visualization options
        st.header("Visualization Options")
        show_throttle = st.checkbox("Show Throttle Heatmap", value=False)
        show_brake = st.checkbox("Show Brake Zones", value=False)
        show_gear = st.checkbox("Show Gear Usage", value=False)
        show_drs = st.checkbox("Show DRS Map", value=False)
        show_comparison = st.checkbox("Driver Comparison", value=False)
        show_sector_delta = st.checkbox("Sector-wise Delta", value=False)
        show_qual_vs_race = st.checkbox("Qualifying vs Race", value=False)
    
    # Main content area
    if load_button or st.session_state.race_data is not None:
        if load_button:
            with st.spinner("⏳ Loading race data... This may take a moment."):
                # Load race session
                race_session = load_race_session(selected_year, selected_round, 'R')
                if race_session is None:
                    st.error("Failed to load race session.")
                    st.stop()
                
                st.session_state.race_data = race_session
                
                # Load qualifying session if comparison is requested
                if show_qual_vs_race:
                    with st.spinner("⏳ Loading qualifying data..."):
                        qual_session = load_race_session(selected_year, selected_round, 'Q')
                        if qual_session is not None:
                            st.session_state.qualifying_data = qual_session
                        else:
                            st.warning("Could not load qualifying session. Qualifying vs Race comparison will not be available.")
        
        race_session = st.session_state.race_data
        
        if race_session is None:
            st.warning("Please click 'Load Race Data' to begin.")
            st.stop()
        
        # Display race information
        st.header(f" {race_session.event['EventName']} - {selected_year}")
        
        # Main visualizations
        if len(driver_codes) == 0:
            st.warning("Please enter at least one driver code.")
        else:
            # Primary driver visualization
            primary_driver = driver_codes[0]
            
            # Get telemetry data for primary driver
            telemetry = get_fastest_lap_telemetry(race_session, primary_driver)
            
            if telemetry is None:
                st.error(f"Could not load telemetry for {primary_driver}")
            else:
                # Main speed heatmap - smaller size
                st.subheader(f"🏁 Racing Line - {primary_driver}")
                fig_speed = plot_racing_line_heatmap(telemetry, f"Speed Heatmap - {primary_driver}", "Speed", width=700, height=600)
                if fig_speed:
                    st.plotly_chart(fig_speed, use_container_width=True)
                
                # Optional visualizations - show all selected in pairs of 2 side by side
                optional_viz_count = sum([show_throttle, show_brake, show_gear, show_drs])
                
                if optional_viz_count > 0:
                    st.subheader("Additional Telemetry Visualizations")
                    
                    # Collect all visualizations to show in order
                    viz_list = []
                    if show_throttle:
                        viz_list.append(("Throttle", "", "Throttle"))
                    if show_brake:
                        viz_list.append(("Brake", "", "Brake"))
                    if show_gear:
                        viz_list.append(("Gear", "", "Gear"))
                    if show_drs:
                        viz_list.append(("DRS", "", "DRS"))
                    
                    # Display in pairs of 2 maps side by side
                    for i in range(0, len(viz_list), 2):
                        cols = st.columns(2)
                        
                        # First visualization in the pair
                        with cols[0]:
                            viz_name, icon, color_by = viz_list[i]
                            st.subheader(f"{icon} {viz_name} - {primary_driver}" if viz_name != "Gear" else f"{icon} {viz_name} Usage - {primary_driver}")
                            
                            if viz_name == "Brake":
                                # Check if brake data exists
                                if telemetry is not None:
                                    has_brake = ('Brake' in telemetry.columns or 
                                                'BR' in telemetry.columns or 
                                                any('brake' in col.lower() for col in telemetry.columns))
                                    if has_brake:
                                        fig = plot_racing_line_heatmap(telemetry, f"{viz_name} Zones - {primary_driver}", color_by, width=900, height=800)
                                        if fig:
                                            st.plotly_chart(fig, use_container_width=True)
                                        else:
                                            st.warning("Could not generate brake visualization. The brake data may be invalid or empty.")
                                    else:
                                        st.error(f"Brake data is not available in the telemetry for this session.")
                                else:
                                    st.error("No telemetry data available")
                            elif viz_name == "DRS":
                                # Check if DRS data exists
                                if telemetry is not None:
                                    has_drs = ('DRS' in telemetry.columns or 
                                              'drs' in telemetry.columns or 
                                              any('drs' in col.lower() for col in telemetry.columns))
                                    if has_drs:
                                        fig = plot_racing_line_heatmap(telemetry, f"{viz_name} Map - {primary_driver}", color_by, width=900, height=800)
                                        if fig:
                                            st.plotly_chart(fig, use_container_width=True)
                                        else:
                                            st.warning("Could not generate DRS visualization. The DRS data may be invalid or empty.")
                                    else:
                                        st.error(f"DRS data is not available in the telemetry for this session.")
                                else:
                                    st.error("No telemetry data available")
                            else:
                                # Throttle or Gear - no special checks needed
                                title = f"{viz_name} - {primary_driver}" if viz_name != "Gear" else f"{viz_name} Usage - {primary_driver}"
                                fig = plot_racing_line_heatmap(telemetry, title, color_by, width=900, height=800)
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True)
                        
                        # Second visualization in the pair (if exists)
                        if i + 1 < len(viz_list):
                            with cols[1]:
                                viz_name, icon, color_by = viz_list[i + 1]
                                st.subheader(f"{icon} {viz_name} - {primary_driver}" if viz_name != "Gear" else f"{icon} {viz_name} Usage - {primary_driver}")
                                
                                if viz_name == "Brake":
                                    # Check if brake data exists
                                    if telemetry is not None:
                                        has_brake = ('Brake' in telemetry.columns or 
                                                    'BR' in telemetry.columns or 
                                                    any('brake' in col.lower() for col in telemetry.columns))
                                        if has_brake:
                                            fig = plot_racing_line_heatmap(telemetry, f"{viz_name} Zones - {primary_driver}", color_by, width=900, height=800)
                                            if fig:
                                                st.plotly_chart(fig, use_container_width=True)
                                            else:
                                                st.warning("Could not generate brake visualization. The brake data may be invalid or empty.")
                                        else:
                                            st.error(f"Brake data is not available in the telemetry for this session.")
                                    else:
                                        st.error("No telemetry data available")
                                elif viz_name == "DRS":
                                    # Check if DRS data exists
                                    if telemetry is not None:
                                        has_drs = ('DRS' in telemetry.columns or 
                                                  'drs' in telemetry.columns or 
                                                  any('drs' in col.lower() for col in telemetry.columns))
                                        if has_drs:
                                            fig = plot_racing_line_heatmap(telemetry, f"{viz_name} Map - {primary_driver}", color_by, width=900, height=800)
                                            if fig:
                                                st.plotly_chart(fig, use_container_width=True)
                                            else:
                                                st.warning("Could not generate DRS visualization. The DRS data may be invalid or empty.")
                                        else:
                                            st.error(f"DRS data is not available in the telemetry for this session.")
                                    else:
                                        st.error("No telemetry data available")
                                else:
                                    # Throttle or Gear - no special checks needed
                                    title = f"{viz_name} - {primary_driver}" if viz_name != "Gear" else f"{viz_name} Usage - {primary_driver}"
                                    fig = plot_racing_line_heatmap(telemetry, title, color_by, width=900, height=800)
                                    if fig:
                                        st.plotly_chart(fig, use_container_width=True)
                        else:
                            # If odd number, leave second column empty
                            with cols[1]:
                                pass
            
            # Driver comparison - FIXED
            if show_comparison:
                st.subheader("Driver Comparison")
                if len(driver_codes) < 2:
                    st.info("Enter multiple driver codes separated by commas (e.g., VER, HAM, LEC) to compare them.")
                else:
                    fig_compare = plot_driver_comparison(race_session, driver_codes, height=1000, width=1200)
                    if fig_compare:
                        st.plotly_chart(fig_compare, use_container_width=True)
            
            # Sector delta
            if show_sector_delta:
                st.subheader(f"Sector-wise Lap Delta - {primary_driver}")
                fig_sector = plot_sector_delta(race_session, primary_driver)
                if fig_sector:
                    st.plotly_chart(fig_sector, use_container_width=True)
                else:
                    st.warning(f"Sector delta data not available for {primary_driver}")
            
            # Qualifying vs Race - FIXED
            if show_qual_vs_race:
                st.subheader(f"Qualifying vs Race - {primary_driver}")
                qual_session = st.session_state.qualifying_data
                if qual_session is not None:
                    fig_qual_race = plot_qualifying_vs_race(qual_session, race_session, primary_driver, height=600, width=700)
                    if fig_qual_race:
                        st.plotly_chart(fig_qual_race, use_container_width=True)
                else:
                    st.warning("Qualifying session data not available. Try loading the race data again with 'Qualifying vs Race' option checked.")
    
    else:
        # Welcome screen
        st.info("Use the sidebar to select a race and driver, then click 'Load Race Data' to begin!")
        
        st.markdown("""
        ### Features
        
        - **Racing Line Heatmap**: Visualize the racing line with speed-based coloring
        - **Throttle/Brake/Gear Visualization**: Toggle additional telemetry overlays
        - **Driver Comparison**: Compare multiple drivers on the same track
        - **Sector Analysis**: Analyze sector-wise lap deltas
        - **Qualifying vs Race**: Compare qualifying and race laps
        
        ###  How It Works
        
        1. **Data Fetching**: Uses the FastF1 library to fetch official F1 timing and telemetry data
        2. **Caching**: Data is cached locally in the `cache` folder for faster subsequent loads
        3. **Telemetry Extraction**: Extracts fastest lap telemetry for selected drivers
        4. **Visualization**: Creates interactive Plotly charts for analysis
        
        ### Tips
        
        - Enter multiple drivers separated by commas for comparison (e.g., VER, HAM, LEC)
        - Check "Qualifying vs Race" BEFORE loading data to ensure qualifying data is loaded
        - The track maps now show larger with better visibility!
        """)


if __name__ == "__main__":
    main()