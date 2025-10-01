import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import plotly.graph_objects as go

# --- Title with formatting ---
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

        # --- Style the table correctly ---
        def color_metrics(val, metric):
            if "S" in metric or metric == "CPR - Bottom Central":
                return 'color: green; font-weight: bold;'
            elif "R" in metric:
                return 'color: red; font-weight: bold;'
            else:  # Pivot / CPR
                return 'color: black; font-weight: bold;'

        styled_df = result_df.style.format({"Value": "{:.2f}"})\
            .apply(lambda col: [color_metrics(v, m) for v, m in zip(result_df["Value"], result_df["Metric"])], axis=0)\
            .set_properties(**{"font-size": "16px", "text-align": "center"})\
            .set_table_styles([{"selector": "th", "props": [("font-size", "16px"), ("text-align", "center")]}])

        # --- Display table ---
        st.subheader(f"Stock Levels for {next_day.strftime('%A, %d-%b-%Y')} (Next trading day)")
        st.dataframe(styled_df, use_container_width=True)

        # --- Chart ---
        df_tail = df.tail(30).copy()
        next_row = pd.DataFrame({"Date": [next_day], "High": [np.nan], "Low": [np.nan], "Close": [np.nan]})
        df_tail = pd.concat([df_tail, next_row], ignore_index=True)

        fig = go.Figure()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df_tail["Date"],
            open=df_tail["Close"],  # ⚠ Replace with df_tail["Open"] if available
            high=df_tail["High"],
            low=df_tail["Low"],
            close=df_tail["Close"],
            name="Price",
            increasing_line_color="green",
            decreasing_line_color="red"
        ))

        # Next day levels as scatter traces (with hover labels)
        levels = {
            "CPR Top": tc,
            "Pivot": pivot,
            "CPR Bottom": bc,
            "S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5,
            "R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5
        }

        for name, value in levels.items():
            fig.add_trace(go.Scatter(
                x=[next_day, next_day + pd.Timedelta(days=1)],
                y=[value, value],
                mode='lines',
                name=name,
                line=dict(
                    color="green" if "S" in name or "Bottom" in name else "red" if "R" in name or "Top" in name else "black",
                    dash="dash" if "S" in name or "R" in name else "solid",
                    width=2
                ),
                hovertemplate=f"{name}: %{{y:.2f}}<extra></extra>"
            ))

        # CPR shaded rectangle (optional, still visual)
        fig.add_shape(
            type="rect",
            x0=next_day, x1=next_day + pd.Timedelta(days=1),
            y0=bc, y1=tc,
            fillcolor="lightpink", opacity=0.2, line=dict(width=0), layer="below"
        )

        # # CPR label annotation
        # fig.add_annotation(
        #     x=next_day + pd.Timedelta(hours=12),
        #     y=(bc + tc) / 2,
        #     text="<b>CPR</b>",
        #     showarrow=False,
        #     font=dict(color="black", size=14, family="Arial"),
        #     align="center",
        #     bgcolor="rgba(255, 192, 203, 0.5)",
        #     bordercolor="black",
        #     borderwidth=1
        # )

        # Layout
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


