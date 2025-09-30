import streamlit as st
import pandas as pd
from datetime import timedelta

# --- Title with formatting ---
st.markdown("<h1 style='text-align: center; color: #2F4F4F;'>Sunil's CPR Calculator</h1>", unsafe_allow_html=True)

# File uploader
uploaded_file = st.file_uploader("Upload Excel File with Stock Data (Date, High, Low, Close)", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Read Excel file
    df = pd.read_excel(uploaded_file)

    # Ensure required columns
    required_cols = {"Date", "High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        st.error(f"Excel file must contain columns: {required_cols}")
    else:
        # Sort and convert Date
        df = df.sort_values("Date")
        df["Date"] = pd.to_datetime(df["Date"])

        # Last row
        last_row = df.iloc[-1]
        high = last_row["High"]
        low = last_row["Low"]
        close = last_row["Close"]

        # Pivot Point
        pivot = (high + low + close) / 3

        # CPR
        bc = (high + low) / 2
        tc = pivot + (pivot - bc)

        # Support and Resistance
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = r1 + (high - low)
        s3 = s1 + (high - pivot)
        r4 = r3 + (r2 - r1)
        s4 = s3 - (s1 - s2)
        r5 = r4 + (r2 - r1)
        s5 = s4 - (s1 - s2)

        # Create DataFrame
        data = {
            "Metric": ["R5", "R4", "R3", "R2", "R1", 
                       "CPR - Top Central", "Pivot", "CPR - Bottom Central", 
                       "S1", "S2", "S3", "S4", "S5"],
            "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
        }
        result_df = pd.DataFrame(data)

        # --- Next weekday date ---
        last_date = df["Date"].iloc[-1]
        next_day = last_date + timedelta(days=1)
        if next_day.weekday() == 5:  # Saturday
            next_day += timedelta(days=2)
        elif next_day.weekday() == 6:  # Sunday
            next_day += timedelta(days=1)

        # --- Style the table ---
        def color_metrics(val, metric_name):
            if "R" in metric_name:
                return 'color: red; font-weight: bold;'
            elif "S" in metric_name:
                return 'color: green; font-weight: bold;'
            else:  # Pivot / CPR
                return 'color: black; font-weight: bold;'

        styled_df = result_df.style.format({"Value": "{:.2f}"})\
            .apply(lambda x: [color_metrics(v, m) for v, m in zip(x["Value"], x["Metric"])], axis=1)\
            .set_properties(**{"font-size": "16px", "text-align": "center"})\
            .set_table_styles([{"selector": "th", "props": [("font-size", "16px"), ("text-align", "center")]}])

        # --- Display ---
        st.subheader(f"Stock Levels for {next_day.strftime('%A, %d-%b-%Y')}")
        st.dataframe(styled_df, use_container_width=True)
