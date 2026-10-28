import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Earthquake Intelligence Dashboard",
    page_icon="🌍",
    layout="wide"
)

# ==========================================
# USGS API URLS
# ==========================================
REALTIME_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
)

HISTORICAL_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
)

# ==========================================
# EARTHQUAKE DATA FETCHING
# ==========================================
@st.cache_data(ttl=60)
def fetch_earthquake_data(url):

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()
    earthquakes = []

    for feature in data.get("features", []):

        properties = feature.get("properties", {})
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates", [])

        if len(coordinates) < 2:
            continue

        magnitude = properties.get("mag")

        if magnitude is None:
            continue

        utc_time = pd.to_datetime(
            properties.get("time"),
            unit="ms",
            utc=True
        )

        ist_time = utc_time.tz_convert("Asia/Kolkata")

        if magnitude >= 5.0:
            category = "High (5.0+)"
        elif magnitude >= 3.0:
            category = "Moderate (3.0-4.9)"
        elif magnitude >= 1.0:
            category = "Low (1.0-2.9)"
        else:
            category = "Very Low (<1.0)"

        earthquakes.append({
            "Place": properties.get("place", "Unknown"),
            "Magnitude": magnitude,
            "Time UTC": utc_time,
            "Time IST": ist_time.strftime(
                "%d-%m-%Y %I:%M:%S %p"
            ),
            "Latitude": coordinates[1],
            "Longitude": coordinates[0],
            "Depth (km)": (
                coordinates[2]
                if len(coordinates) > 2
                else None
            ),
            "Category": category
        })

    return pd.DataFrame(earthquakes)


# ==========================================
# HEADER
# ==========================================
st.title("🌍 Earthquake Intelligence Dashboard")

st.markdown(
    """
    Monitor earthquake activity worldwide using USGS data.

    **Live earthquake monitoring | Satellite imagery | Historical analysis**
    """
)

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.title("⚙️ Map Settings")

map_mode = st.sidebar.selectbox(
    "Choose Map Style",
    [
        "Satellite",
        "Street",
        "Dark",
        "OpenStreetMap"
    ]
)

min_magnitude = st.sidebar.slider(
    "Minimum Magnitude",
    min_value=0.0,
    max_value=9.0,
    value=1.0,
    step=0.1
)

show_historical = st.sidebar.checkbox(
    "Show Historical Earthquakes",
    value=True
)

# ==========================================
# MAP STYLE CONFIGURATION
# ==========================================
map_styles = {
    "Satellite": "satellite",
    "Street": "carto-positron",
    "Dark": "carto-darkmatter",
    "OpenStreetMap": "open-street-map"
}

selected_map_style = map_styles[map_mode]

# ==========================================
# COLOR CONFIGURATION
# ==========================================
color_map = {
    "High (5.0+)": "#FF0000",
    "Moderate (3.0-4.9)": "#FF8C00",
    "Low (1.0-2.9)": "#FFD700",
    "Very Low (<1.0)": "#00C853"
}

# ==========================================
# FETCH DATA
# ==========================================
try:

    with st.spinner("Loading earthquake data..."):

        realtime_data = fetch_earthquake_data(
            REALTIME_URL
        )

        historical_data = fetch_earthquake_data(
            HISTORICAL_URL
        )

except requests.RequestException as error:

    st.error(f"Unable to fetch USGS data: {error}")
    st.stop()

except (ValueError, KeyError, TypeError) as error:

    st.error(f"Error processing earthquake data: {error}")
    st.stop()

# ==========================================
# FILTER DATA
# ==========================================
if not realtime_data.empty:

    filtered_realtime = realtime_data[
        realtime_data["Magnitude"] >= min_magnitude
    ].copy()

else:
    filtered_realtime = realtime_data.copy()


if not historical_data.empty:

    filtered_historical = historical_data[
        historical_data["Magnitude"] >= min_magnitude
    ].copy()

else:
    filtered_historical = historical_data.copy()

# ==========================================
# STATISTICS
# ==========================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Earthquakes (Last Hour)",
        len(realtime_data)
    )

with col2:
    st.metric(
        "Filtered Events",
        len(filtered_realtime)
    )

with col3:
    st.metric(
        "Earthquakes (Last Month)",
        len(historical_data)
    )

with col4:

    strong_count = (
        (realtime_data["Magnitude"] >= 5.0).sum()
        if not realtime_data.empty
        else 0
    )

    st.metric(
        "Magnitude 5.0+",
        int(strong_count)
    )

# ==========================================
# MAP FUNCTION
# ==========================================
def create_earthquake_map(df, title, height=650):

    fig = px.scatter_map(
        df,
        lat="Latitude",
        lon="Longitude",
        color="Category",
        size="Magnitude",
        size_max=22,
        color_discrete_map=color_map,
        hover_name="Place",
        hover_data={
            "Magnitude": ":.2f",
            "Depth (km)": ":.1f",
            "Time IST": True,
            "Latitude": ":.3f",
            "Longitude": ":.3f",
            "Category": True
        },
        zoom=1,
        height=height,
        map_style=selected_map_style,
        title=title
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=55, b=0),
        legend_title_text="Magnitude Category"
    )

    fig.update_traces(
        marker={
            "opacity": 0.9
        }
    )

    return fig

# ==========================================
# REAL-TIME SATELLITE MAP
# ==========================================
st.subheader("🛰️ Live Earthquake Satellite Map")

st.caption(
    "Earthquake events reported by USGS during the last hour."
)

if not filtered_realtime.empty:

    fig_live = create_earthquake_map(
        filtered_realtime,
        "Live Earthquake Locations",
        height=700
    )

    st.plotly_chart(
        fig_live,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "doubleClick": "reset",
            "responsive": True
        },
        key="live_earthquake_map"
    )

else:

    st.info(
        "No earthquakes match the selected magnitude filter."
    )

# ==========================================
# HISTORICAL MAP
# ==========================================
if show_historical:

    st.subheader("🌎 Historical Earthquake Satellite Map")

    st.caption(
        "Earthquake events reported during the last month."
    )

    if not filtered_historical.empty:

        fig_history = create_earthquake_map(
            filtered_historical,
            "Historical Earthquake Locations",
            height=650
        )

        st.plotly_chart(
            fig_history,
            use_container_width=True,
            config={
                "scrollZoom": True,
                "displayModeBar": True,
                "responsive": True
            },
            key="historical_earthquake_map"
        )

    else:

        st.info(
            "No historical earthquakes match the selected filter."
        )

# ==========================================
# MAGNITUDE DISTRIBUTION
# ==========================================
st.subheader("📊 Earthquake Magnitude Distribution")

if not historical_data.empty:

    fig_distribution = px.histogram(
        historical_data,
        x="Magnitude",
        nbins=30,
        title="Magnitude Distribution — Last Month",
        color_discrete_sequence=["#FF8C00"]
    )

    st.plotly_chart(
        fig_distribution,
        use_container_width=True
    )

# ==========================================
# RECENT EARTHQUAKE TABLE
# ==========================================
st.subheader("📋 Recent Earthquake Records")

if not filtered_realtime.empty:

    st.dataframe(
        filtered_realtime.sort_values(
            "Time UTC",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )

    csv_data = filtered_realtime.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "⬇️ Download Earthquake Data",
        data=csv_data,
        file_name="earthquake_data.csv",
        mime="text/csv"
    )

else:

    st.info("No recent records to display.")

# ==========================================
# HISTORICAL TABLE
# ==========================================
with st.expander("View Historical Earthquake Records"):

    if not filtered_historical.empty:

        st.dataframe(
            filtered_historical.sort_values(
                "Time UTC",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No historical records available.")

# ==========================================
# COLOR LEGEND
# ==========================================
st.sidebar.markdown("---")
st.sidebar.subheader("🌈 Magnitude Legend")

st.sidebar.markdown(
    """
    🔴 **High:** 5.0+

    🟠 **Moderate:** 3.0–4.9

    🟡 **Low:** 1.0–2.9

    🟢 **Very Low:** Below 1.0
    """
)

# ==========================================
# DATA SOURCE
# ==========================================
st.sidebar.markdown("---")

st.sidebar.markdown(
    """
    **Data Source:** USGS

    **Live Feed:** Last hour

    **Historical Feed:** Last month

    **Timezone:** IST

    **Cache Duration:** 60 seconds
    """
)

st.sidebar.caption(
    "This dashboard monitors reported earthquakes. "
    "It does not predict earthquakes or provide official alerts."
)

# ==========================================
# REFRESH BUTTON
# ==========================================
st.markdown("---")

if st.button("🔄 Refresh Earthquake Data"):

    st.cache_data.clear()
    st.rerun()

st.caption(
    f"Last page render: {datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}"
)

