import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
from datetime import timedelta

st.title("Sunil's CPR Calculator")

# File uploader
uploaded_file = st.file_uploader("Upload Excel File with Stock Data (Date, High, Low, Close)", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Read Excel file
    df = pd.read_excel(uploaded_file)

    # Ensure columns exist
    required_cols = {"Date", "High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        st.error(f"Excel file must contain columns: {required_cols}")
    else:

        # Sort by date just in case
        df = df.sort_values("Date")
        df["Date"] = pd.to_datetime(df["Date"])

        # Take the last row for calculations
        last_row = df.iloc[-1]
        high = last_row["High"]
        low = last_row["Low"]
        close = last_row["Close"]

        # Pivot Point
        pivot = (high + low + close) / 3

        # CPR calculations
        bc = (high + low) / 2  # Bottom Central
        tc = pivot + (pivot - bc)  # Top Central

        # Supports and Resistances
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = r1 + (high - low)
        s3 = s1 + (high - low)
        r4 = r3 + (r2 - r1)
        s4 = s3 - (s1 - s2)
        r5 = r4 + (r2 - r1)
        s5 = s4 - (s1 - s2)

        # Create DataFrame for display
        data = {
            "Metric": ["R5", "R4", "R3", "R2", "R1", 
                       "CPR - Top Central", "Pivot", "CPR - Bottom Central", 
                       "S1", "S2", "S3", "S4", "S5"],
            "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
        }
        result_df = pd.DataFrame(data)

        # --- Calculate the upcoming trading day (weekday) ---
        last_date = df["Date"].iloc[-1]

        # Start with the next day
        next_day = last_date + timedelta(days=1)

        # Skip weekends
        if next_day.weekday() == 5:  # Saturday
            next_day += timedelta(days=2)
        elif next_day.weekday() == 6:  # Sunday
            next_day += timedelta(days=1)

        # --- Style the table ---
        styled_df = result_df.style.format({"Value": "{:.2f}"})\
            .background_gradient(subset=["Value"], cmap="YlGnBu")\
            .set_properties(**{"font-size": "16px", "text-align": "center"})\
            .set_table_styles([
                {"selector": "th", "props": [("font-size", "16px"), ("text-align", "center")]}
            ])

        st.subheader(f"Stock Levels for {next_day.strftime('%A, %d-%b-%Y')}")
        st.dataframe(styled_df, use_container_width=True)
