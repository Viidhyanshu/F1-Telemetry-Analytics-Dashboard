# 🏎️ F1 Telemetry Analytics Dashboard

A comprehensive Python-based dashboard for visualizing Formula 1 telemetry data using Streamlit and FastF1.

## 📋 Overview

This application allows you to:
- Select any F1 race from 2018 onwards
- Visualize racing lines with speed-based heatmaps
- Compare multiple drivers on the same track
- Analyze sector-wise lap deltas
- Compare qualifying vs race laps
- View throttle, brake, and gear usage overlays

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Internet connection (for downloading F1 data)

### Installation

1. **Clone or download this repository**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

4. **Open your browser**
   - The app will automatically open at `http://localhost:8501`
   - If it doesn't, navigate to that URL manually

## 📖 How to Use

### Basic Usage

1. **Select Race Parameters**
   - Choose the **Year** from the dropdown (2018-2024+)
   - Select the **Race** from the list
   - Enter **Driver Code(s)** (e.g., `VER`, `HAM`, `LEC`)
     - For multiple drivers, separate with commas: `VER, HAM, LEC`

2. **Load Data**
   - Click the **"🚀 Load Race Data"** button
   - Wait for data to load (first time may take longer due to caching)

3. **Explore Visualizations**
   - The main racing line heatmap will appear automatically
   - Enable additional visualizations using the checkboxes in the sidebar

### Available Visualizations

#### 🏁 Racing Line Heatmap (Speed-based)
- Shows the car's path around the track
- Color-coded by speed (darker = faster)
- Includes track outline and start/finish line marker

#### ⚡ Throttle Heatmap
- Visualize throttle application throughout the lap
- Green color scale (darker = more throttle)

#### 🛑 Brake Zones
- Identify braking points around the track
- Red color scale (darker = more braking)

#### ⚙️ Gear Usage
- See which gear is used at each point
- Color-coded by gear number

#### 🔀 Driver Comparison
- Compare racing lines of multiple drivers
- Useful for analyzing different racing strategies

#### 📊 Sector-wise Lap Delta
- Analyze performance across different sectors
- Shows delta time from best sector time for each lap
- Helps identify where a driver gains or loses time

#### 🏆 Qualifying vs Race
- Compare the fastest qualifying lap with the fastest race lap
- Useful for understanding tire degradation and fuel load effects

## 🔧 How Telemetry Data is Fetched

### FastF1 Library

The application uses the **FastF1** library, which provides:
- Official F1 timing data from the FIA
- High-resolution telemetry data (sampled at 10 Hz)
- Session data including practice, qualifying, and race sessions

### Data Flow

1. **Session Loading**
   ```python
   session = fastf1.get_session(year, round_number, session_type)
   session.load()  # Downloads and processes data
   ```

2. **Telemetry Extraction**
   ```python
   driver_laps = session.laps.pick_driver(driver_code)
   fastest_lap = driver_laps.pick_fastest()
   telemetry = fastest_lap.get_telemetry()
   ```

3. **Caching**
   - FastF1 automatically caches data in the `cache/` folder
   - Subsequent loads are much faster
   - Cache persists between sessions

### Telemetry Data Structure

Each telemetry DataFrame contains:
- **X, Y**: Car position coordinates (meters)
- **Speed**: Car speed (km/h)
- **Throttle**: Throttle position (0-100%)
- **Brake**: Brake pressure (0-100%)
- **nGear**: Current gear (1-8)
- **RPM**: Engine RPM
- **Time**: Timestamp
- **Distance**: Distance traveled (meters)

## 🎨 Technical Details

### Architecture

- **Frontend**: Streamlit (interactive web interface)
- **Data Source**: FastF1 library (official F1 API)
- **Visualization**: Plotly (interactive charts)
- **Data Processing**: Pandas, NumPy

### Key Features

1. **Error Handling**
   - Validates race year and round number
   - Checks driver code availability
   - Handles missing or incomplete data gracefully

2. **Performance Optimization**
   - Local caching for faster subsequent loads
   - Efficient data processing with Pandas
   - Lazy loading of visualizations

3. **User Experience**
   - Clean, intuitive interface
   - Real-time loading indicators
   - Helpful error messages
   - Responsive layout

## 🐛 Troubleshooting

### Common Issues

1. **"Error loading session"**
   - Check your internet connection
   - Verify the race exists for the selected year
   - Some older races may have incomplete data

2. **"Could not load telemetry for [driver]"**
   - Driver may not have participated in that race
   - Driver code may be incorrect (use 3-letter codes)
   - Check if driver completed at least one lap

3. **Slow loading times**
   - First load is always slower (downloading data)
   - Subsequent loads use cache and are faster
   - Large sessions (full race) take longer than qualifying

4. **Missing visualizations**
   - Ensure driver completed the session
   - Some older races have limited telemetry data
   - Check that the session type is correct

### Driver Codes Reference

Common driver codes (2024 season):
- `VER` - Max Verstappen
- `HAM` - Lewis Hamilton
- `LEC` - Charles Leclerc
- `NOR` - Lando Norris
- `PER` - Sergio Pérez
- `SAI` - Carlos Sainz
- `RUS` - George Russell
- `ALO` - Fernando Alonso
- `OCO` - Esteban Ocon
- `STR` - Lance Stroll

*Note: Driver codes may change between seasons*

## 🔮 Future Improvements

### Potential Enhancements

1. **Advanced Analytics**
   - Tire compound analysis
   - Fuel load estimation
   - DRS usage visualization
   - Overtaking analysis

2. **Performance Features**
   - Batch processing for multiple races
   - Export visualizations as images/PDFs
   - Data export to CSV/Excel

3. **User Interface**
   - Dark mode theme
   - Customizable color schemes
   - Interactive lap selection
   - Real-time lap-by-lap comparison

4. **Data Integration**
   - Weather data overlay
   - Safety car periods
   - Pit stop analysis
   - Championship standings integration

5. **Machine Learning**
   - Predictive lap time modeling
   - Optimal racing line suggestions
   - Driver performance classification

## 📝 License

This project is open source and available for educational purposes.

## 🙏 Acknowledgments

- **FastF1** library by theOehrly - [GitHub](https://github.com/theOehrly/Fast-F1)
- **Streamlit** for the amazing framework
- **Formula 1** and the FIA for providing official data

## 📧 Support

For issues, questions, or contributions:
- Check the FastF1 documentation: https://docs.fastf1.dev/
- Review Streamlit documentation: https://docs.streamlit.io/

---

**Enjoy analyzing F1 telemetry data! 🏎️💨**

