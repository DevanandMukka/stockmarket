import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import plotly.graph_objects as go

# --- Title ---
st.markdown("<h1 style='text-align: center; color: #2F4F4F;'>📊 Sunil's CPR Calculator</h1>", unsafe_allow_html=True)

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
        # --- Preprocess ---
        df = df.sort_values("Date")
        df["Date"] = pd.to_datetime(df["Date"])

        # --- CPR Calculations ---
        df["Pivot"] = (df["High"] + df["Low"] + df["Close"]) / 3
        df["BC"] = (df["High"] + df["Low"]) / 2
        df["TC"] = df["Pivot"] + (df["Pivot"] - df["BC"])
        df.loc[df["BC"] > df["TC"], ["TC", "BC"]] = df.loc[df["BC"] > df["TC"], ["BC", "TC"]].values

        # --- Identify Current and Previous Days ---
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else None

        high, low, close = last_row["High"], last_row["Low"], last_row["Close"]
        pivot, bc, tc = last_row["Pivot"], last_row["BC"], last_row["TC"]

        # --- S/R Levels ---
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

        # --- Display Table ---
        data = {
            "Metric": ["R5", "R4", "R3", "R2", "R1",
                       "CPR - Top Central", "Pivot", "CPR - Bottom Central",
                       "S1", "S2", "S3", "S4", "S5"],
            "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
        }
        result_df = pd.DataFrame(data)

        # --- Determine Next Trading Day ---
        last_date = df["Date"].iloc[-1]
        next_day = last_date + timedelta(days=1)
        while next_day.weekday() >= 5:  # skip Sat/Sun
            next_day += timedelta(days=1)

        # --- Project Next Day CPR Values ---
        df["CPR_Width"] = df["TC"] - df["BC"]
        avg_width = df["CPR_Width"].tail(5).mean()
        avg_pivot_change = (df["Pivot"].iloc[-1] - df["Pivot"].iloc[-5]) / 4 if len(df) >= 5 else 0
        next_pivot = pivot + avg_pivot_change
        next_bc = next_pivot - avg_width / 2
        next_tc = next_pivot + avg_width / 2

        # --- Display Table ---
        def color_metrics(val, metric):
            if "S" in metric or metric == "CPR - Bottom Central":
                return 'color: green; font-weight: bold;'
            elif "R" in metric:
                return 'color: red; font-weight: bold;'
            else:
                return 'color: black; font-weight: bold;'

        styled_df = result_df.style.format({"Value": "{:.2f}"}) \
            .apply(lambda col: [color_metrics(v, m) for v, m in zip(result_df["Value"], result_df["Metric"])], axis=0) \
            .set_properties(**{"font-size": "16px", "text-align": "center"}) \
            .set_table_styles([{"selector": "th", "props": [("font-size", "16px"), ("text-align", "center")]}])

        st.subheader(f"Stock Levels for {next_day.strftime('%A, %d-%b-%Y')} (Projected Next Trading Day)")
        st.dataframe(styled_df, use_container_width=True)

        # --- Two-Day Relationship ---
        if prev_row is not None:
            prev_tc, prev_bc = prev_row["TC"], prev_row["BC"]
            curr_tc, curr_bc = last_row["TC"], last_row["BC"]
            curr_date = last_row["Date"].strftime("%d-%b-%Y")
            next_date = next_day.strftime("%d-%b-%Y")

            relationship = None
            sentiment = None
            condition_text = ""

            if curr_bc > prev_tc:
                relationship = "Higher Value Relationship"
                sentiment = "Bullish"
                condition_text = f"Next BC ({curr_bc:.2f}) > Current TC ({prev_tc:.2f})"
            elif curr_tc > prev_tc and curr_bc < prev_tc and curr_bc > prev_bc:
                relationship = "Overlapping Higher Value Relationship"
                sentiment = "Moderately Bullish"
                condition_text = f"Next TC ({curr_tc:.2f}) > Curr TC ({prev_tc:.2f}), and Next BC ({curr_bc:.2f}) < Curr TC but > Curr BC"
            elif curr_tc < prev_bc:
                relationship = "Lower Value Relationship"
                sentiment = "Bearish"
                condition_text = f"Next TC ({curr_tc:.2f}) < Current BC ({prev_bc:.2f})"
            elif curr_bc < prev_bc and curr_tc > prev_bc:
                relationship = "Overlapping Lower Value Relationship"
                sentiment = "Moderately Bearish"
                condition_text = f"Next BC ({curr_bc:.2f}) < Curr BC ({prev_bc:.2f}), and Next TC ({curr_tc:.2f}) > Curr BC"
            elif abs(curr_tc - prev_tc) < 0.05 and abs(curr_bc - prev_bc) < 0.05:
                relationship = "Unchanged Value Relationship"
                sentiment = "Sideways/Breakout"
                condition_text = f"Next and Current CPR nearly equal: ΔTC={abs(curr_tc - prev_tc):.2f}, ΔBC={abs(curr_bc - prev_bc):.2f}"
            elif curr_tc > prev_tc and curr_bc < prev_
