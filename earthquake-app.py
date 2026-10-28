
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone

# -----------------------------------
# PAGE CONFIGURATION
# -----------------------------------
st.set_page_config(
    page_title="Real-Time Earthquake Monitor",
    page_icon="🌍",
    layout="wide"
)

# -----------------------------------
# USGS API LINKS
# -----------------------------------
REALTIME_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
)

HISTORICAL_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
)

# -----------------------------------
# FETCH EARTHQUAKE DATA
# -----------------------------------
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

        # Convert UTC to Indian Standard Time
        ist_time = utc_time.tz_convert("Asia/Kolkata")

        # Classify earthquake by magnitude
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
            "Time IST": ist_time,
            "Latitude": coordinates[1],
            "Longitude": coordinates[0],
            "Depth (km)": coordinates[2] if len(coordinates) > 2 else None,
            "Category": category
        })

    return pd.DataFrame(earthquakes)


# -----------------------------------
# APP TITLE
# -----------------------------------
st.title("🌍 Real-Time Earthquake Monitoring Dashboard")

st.markdown(
    """
    Monitor earthquake activity using live feeds from the
    **United States Geological Survey (USGS)**.

    The dashboard displays earthquake locations, magnitudes,
    depth and time in Indian Standard Time (IST).
    """
)

st.caption(
    f"Dashboard opened: {datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}"
)

# -----------------------------------
# FETCH DATA
# -----------------------------------
try:
    with st.spinner("Fetching earthquake data from USGS..."):

        realtime_data = fetch_earthquake_data(REALTIME_URL)
        historical_data = fetch_earthquake_data(HISTORICAL_URL)

except requests.RequestException as error:
    st.error(f"Unable to fetch earthquake data: {error}")
    st.info("Check your internet connection and try refreshing the page.")
    st.stop()

except (ValueError, KeyError, TypeError) as error:
    st.error(f"Error processing earthquake data: {error}")
    st.stop()


# -----------------------------------
# SIDEBAR FILTERS
# -----------------------------------
st.sidebar.header("⚙️ Dashboard Filters")

min_magnitude = st.sidebar.slider(
    "Minimum Magnitude",
    min_value=0.0,
    max_value=9.0,
    value=1.0,
    step=0.1
)

show_historical = st.sidebar.checkbox(
    "Show Historical Map",
    value=True
)

# Filter data
filtered_realtime = realtime_data[
    realtime_data["Magnitude"] >= min_magnitude
].copy()

filtered_historical = historical_data[
    historical_data["Magnitude"] >= min_magnitude
].copy()


# -----------------------------------
# COLOR MAPPING
# -----------------------------------
color_map = {
    "High (5.0+)": "#FF0000",
    "Moderate (3.0-4.9)": "#FF8C00",
    "Low (1.0-2.9)": "#FFD700",
    "Very Low (<1.0)": "#00C853"
}


# -----------------------------------
# SUMMARY METRICS
# -----------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Earthquakes (Last Hour)",
        len(realtime_data)
    )

with col2:
    st.metric(
        "Filtered (Last Hour)",
        len(filtered_realtime)
    )

with col3:
    st.metric(
        "Earthquakes (Last Month)",
        len(historical_data)
    )

with col4:
    strong_count = (
        realtime_data["Magnitude"] >= 5.0
    ).sum() if not realtime_data.empty else 0

    st.metric(
        "Magnitude 5.0+ (Last Hour)",
        int(strong_count)
    )


# -----------------------------------
# REAL-TIME EARTHQUAKE MAP
# -----------------------------------
st.subheader("🔴 Live Earthquake Map — Last Hour")

if not filtered_realtime.empty:

    fig_realtime = px.scatter_map(
        filtered_realtime,
        lat="Latitude",
        lon="Longitude",
        color="Category",
        size="Magnitude",
        size_max=25,
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
        height=650,
        title="Earthquake Locations — Last Hour",
        map_style="open-street-map"
    )

    fig_realtime.update_layout(
        margin=dict(l=0, r=0, t=50, b=0),
        legend_title_text="Earthquake Magnitude"
    )

    st.plotly_chart(
    fig_realtime,
    use_container_width=True,
    config={
        "scrollZoom": False,
        "displayModeBar": True
    },
    key="realtime_map"
)

else:
    st.info("No earthquakes match the selected magnitude filter.")


# -----------------------------------
# HISTORICAL EARTHQUAKE MAP
# -----------------------------------
if show_historical:

    st.subheader("🌎 Historical Earthquake Map — Last Month")

    if not filtered_historical.empty:

        fig_historical = px.scatter_map(
            filtered_historical,
            lat="Latitude",
            lon="Longitude",
            color="Category",
            size="Magnitude",
            size_max=20,
            color_discrete_map=color_map,
            hover_name="Place",
            hover_data={
                "Magnitude": ":.2f",
                "Depth (km)": ":.1f",
                "Time IST": True,
                "Category": True
            },
            zoom=1,
            height=600,
            title="Earthquake Locations — Last Month",
            map_style="open-street-map"
        )

        fig_historical.update_layout(
            margin=dict(l=0, r=0, t=50, b=0),
            legend_title_text="Earthquake Magnitude"
        )

        st.plotly_chart(
    fig_historical,
    use_container_width=True,
    config={
        "scrollZoom": False,
        "displayModeBar": True
    },
    key="historical_map"
)

    else:
        st.info("No historical earthquakes match the selected filter.")


# -----------------------------------
# MAGNITUDE DISTRIBUTION
# -----------------------------------
st.subheader("📊 Earthquake Magnitude Distribution")

if not historical_data.empty:

    fig_magnitude = px.histogram(
        historical_data,
        x="Magnitude",
        nbins=30,
        title="Earthquake Magnitudes — Last Month",
        labels={"Magnitude": "Magnitude"},
        color_discrete_sequence=["#1E88E5"]
    )

    st.plotly_chart(
        fig_magnitude,
        use_container_width=True
    )


# -----------------------------------
# RAW EARTHQUAKE DATA
# -----------------------------------
st.subheader("📋 Recent Earthquake Records")

st.dataframe(
    filtered_realtime.sort_values(
        "Time UTC",
        ascending=False
    ),
    use_container_width=True,
    hide_index=True
)

with st.expander("View Historical Earthquake Records"):

    st.dataframe(
        filtered_historical.sort_values(
            "Time UTC",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )


# -----------------------------------
# DOWNLOAD CSV
# -----------------------------------
if not filtered_realtime.empty:

    csv_data = filtered_realtime.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="⬇️ Download Recent Earthquake Data (CSV)",
        data=csv_data,
        file_name="earthquake_data.csv",
        mime="text/csv"
    )


# -----------------------------------
# SIDEBAR INFORMATION
# -----------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Magnitude Color Guide")

st.sidebar.markdown(
    """
    🔴 **Red:** Magnitude 5.0+

    🟠 **Orange:** Magnitude 3.0–4.9

    🟡 **Yellow:** Magnitude 1.0–2.9

    🟢 **Green:** Magnitude below 1.0
    """
)

st.sidebar.markdown("---")

st.sidebar.info(
    """
    **Data Source:** USGS Earthquake Hazards Program

    Recent feed: Last hour

    Historical feed: Last month

    Timezone: Indian Standard Time (IST)

    Refresh interval: 60 seconds
    """
)

st.sidebar.caption(
    "Earthquake data is provided by USGS. "
    "The dashboard is a monitoring tool, not an earthquake warning system."
)

# -----------------------------------
# AUTO REFRESH
# -----------------------------------
st.markdown("---")

if st.button("🔄 Refresh Earthquake Data Now"):
    st.cache_data.clear()
    st.rerun()
