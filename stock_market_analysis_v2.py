import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import plotly.graph_objects as go

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
        def color_metrics(val, metric):
            if "S" in metric or metric == "CPR - Bottom Central":
                return 'color: green; font-weight: bold;'
            elif "R" in metric:
                return 'color: red; font-weight: bold;'
            else:  # Pivot / CPR top
                return 'color: black; font-weight: bold;'

        styled_df = result_df.style.format({"Value": "{:.2f}"})\
            .apply(lambda col: [color_metrics(v, m) for v, m in zip(result_df["Value"], result_df["Metric"])], axis=0)\
            .set_properties(**{"font-size": "16px", "text-align": "center"})\
            .set_table_styles([{"selector": "th", "props": [("font-size", "16px"), ("text-align", "center")]}])

        # --- Display table ---
        st.subheader(f"Stock Levels for {next_day.strftime('%A, %d-%b-%Y')} (Next Day after last row in Excel)")
        st.dataframe(styled_df, use_container_width=True)

        # --- Add Candlestick Chart with CPR for upcoming day ---
        df_tail = df.tail(30).copy()
        next_row = pd.DataFrame({"Date": [next_day], "High": [np.nan], "Low": [np.nan], "Close": [np.nan]})
        df_tail = pd.concat([df_tail, next_row], ignore_index=True)

        fig = go.Figure()

        # Candlestick chart
        fig.add_trace(go.Candlestick(
            x=df_tail["Date"],
            open=df_tail["Close"],   # ⚠ Replace with df_tail["Open"] if available in your data
            high=df_tail["High"],
            low=df_tail["Low"],
            close=df_tail["Close"],
            name="Price",
            increasing_line_color="green",
            decreasing_line_color="red"
        ))

        # CPR rectangle for upcoming day
        fig.add_shape(
            type="rect",
            x0=next_day,
            x1=next_day + pd.Timedelta(days=1),
            y0=bc,
            y1=tc,
            fillcolor="lightpink",
            opacity=0.4,
            line=dict(width=0),
            layer="below"
        )

        # Pivot line
        fig.add_shape(
            type="line",
            x0=next_day, x1=next_day + pd.Timedelta(days=1),
            y0=pivot, y1=pivot,
            line=dict(color="black", width=2, dash="solid"),
            layer="above"
        )

        # Supports
        for i, s in enumerate([s1, s2, s3, s4, s5], start=1):
            fig.add_shape(
                type="line",
                x0=next_day, x1=next_day + pd.Timedelta(days=1),
                y0=s, y1=s,
                line=dict(color="green", dash="dash"),
                layer="above"
            )

        # Resistances
        for i, r in enumerate([r1, r2, r3, r4, r5], start=1):
            fig.add_shape(
                type="line",
                x0=next_day, x1=next_day + pd.Timedelta(days=1),
                y0=r, y1=r,
                line=dict(color="red", dash="dash"),
                layer="above"
            )

        # Layout updates
        fig.update_layout(
            title=f"Upcoming Day CPR & Levels ({next_day.strftime('%A, %d-%b-%Y')})",
            xaxis_title="Date",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False,
            height=700,
            template="plotly_white"
        )

        # Show chart
        st.plotly_chart(fig, use_container_width=True)
