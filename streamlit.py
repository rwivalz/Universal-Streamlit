import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from datetime import datetime

DATA_DIR = "output"
PARK_NAMES = {
    "USF": "Universal Studios Florida",
    "IOA": "Islands of Adventure"
}

@st.cache_data
def load_ride_data(park_code: str) -> dict:
    """Load ride wait times from text files (JSON per line)."""
    park_folder = os.path.join(DATA_DIR, park_code)
    all_rides = {}

    if not os.path.exists(park_folder):
        st.warning(f"Oops! No data folder found for park: {park_code}")
        return all_rides

    for file in os.listdir(park_folder):
        if file.endswith(".txt"):
            ride_name = file.replace(".txt", "")
            filepath = os.path.join(park_folder, file)

            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    data = [json.loads(line) for line in f if line.strip()]
                except json.JSONDecodeError:
                    continue

            if data:
                df = pd.DataFrame(data)
                if 'time' in df.columns:
                    df['hour'] = df['time'].str[:2].astype(int)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date']).dt.date
                all_rides[ride_name] = df

    return all_rides

def compute_hourly_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Average wait per hour and count of entries."""
    if 'wait' not in df.columns or 'hour' not in df.columns:
        return pd.DataFrame(columns=['hour', 'avg_wait', 'entries'])
    
    grouped = df.groupby('hour')['wait'].agg(['mean', 'count']).reset_index()
    grouped.rename(columns={'mean': 'avg_wait', 'count': 'entries'}, inplace=True)
    return grouped

def hour_to_ampm(h: int) -> str:
    if h == 0:
        return "12 AM"
    elif h < 12:
        return f"{h} AM"
    elif h == 12:
        return "12 PM"
    else:
        return f"{h-12} PM"

st.title("Universal Orlando Wait Times Dashboard")

col1, col2 = st.columns(2)
if 'park' not in st.session_state:
    st.session_state.park = "USF"

if col1.button(PARK_NAMES.get("USF", "USF")):
    st.session_state.park = "USF"
if col2.button(PARK_NAMES.get("IOA", "IOA")):
    st.session_state.park = "IOA"

st.subheader(f"Park: {PARK_NAMES.get(st.session_state.park, st.session_state.park)}")
rides_data = load_ride_data(st.session_state.park)

if not rides_data:
    st.info("No ride data available for this park. Maybe try another day?")
else:
    ride = st.selectbox("Select a Ride", list(rides_data.keys()))
    df = rides_data[ride]

    if 'date' in df.columns:
        min_date = df['date'].min()
        max_date = df['date'].max()
        start_date, end_date = st.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

    hourly_stats = compute_hourly_stats(df)
    if not hourly_stats.empty:
        hourly_stats['hour_label'] = hourly_stats['hour'].apply(hour_to_ampm)

        fig = px.bar(
            hourly_stats,
            x='hour_label',
            y='avg_wait',
            hover_data={'avg_wait': ':.1f', 'entries': True},
            labels={'hour_label': 'Hour of Day', 'avg_wait': 'Average Wait Time (min)'},
            title=f"Average Wait Time per Hour - {ride}"
        )
        fig.update_layout(
            xaxis={'categoryorder':'array', 'categoryarray':hourly_stats['hour_label']},
            margin=dict(t=50, l=20, r=20, b=20),
            showlegend=False,
            hovermode='x unified'
        )
        fig.update_traces(marker_color='steelblue')

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    if st.checkbox("Show raw data"):
        st.dataframe(df)