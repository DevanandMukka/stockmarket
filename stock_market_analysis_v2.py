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
        # Sort and convert Date
        df = df.sort_values("Date")
        df["Date"] = pd.to_datetime(df["Date"])

        # --- Calculate current day's CPR ---
        last_row = df.iloc[-1]
        high, low, close = last_row["High"], last_row["Low"], last_row["Close"]

        pivot = (high + low + close) / 3
        bc = (high + low) / 2
        tc = pivot + (pivot - bc)
        if bc > tc:
            tc, bc = bc, tc

        # --- Calculate supports & resistances ---
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

        # --- Create DataFrame for display ---
        data = {
            "Metric": ["R5", "R4", "R3", "R2", "R1",
                       "CPR - Top Central", "Pivot", "CPR - Bottom Central",
                       "S1", "S2", "S3", "S4", "S5"],
            "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
        }
        result_df = pd.DataFrame(data)

        # --- Find next trading day ---
        last_date = df["Date"].iloc[-1]
        next_day = last_date + timedelta(days=1)
        if next_day.weekday() == 5:  # Saturday
            next_day += timedelta(days=2)
        elif next_day.weekday() == 6:  # Sunday
            next_day += timedelta(days=1)

        # --- Style table ---
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

        # --- Display CPR table ---
        st.subheader(f"Stock Levels for {next_day.strftime('%A, %d-%b-%Y')} (Next trading day)")
        st.dataframe(styled_df, use_container_width=True)

        # --- Chart: Horizontal CPR lines for last 10 days + next day ---
        df_tail = df.tail(10).copy()
        next_row = pd.DataFrame({"Date": [next_day], "High": [np.nan], "Low": [np.nan], "Close": [np.nan]})
        df_tail = pd.concat([df_tail, next_row], ignore_index=True)

        # Compute CPR levels for each day
        df_tail["Pivot"] = (df_tail["High"] + df_tail["Low"] + df_tail["Close"]) / 3
        df_tail["BC"] = (df_tail["High"] + df_tail["Low"]) / 2
        df_tail["TC"] = df_tail["Pivot"] + (df_tail["Pivot"] - df_tail["BC"])
        df_tail.loc[df_tail["BC"] > df_tail["TC"], ["TC", "BC"]] = df_tail.loc[df_tail["BC"] > df_tail["TC"], ["BC", "TC"]].values

        # Add next day's calculated values
        df_tail.loc[df_tail.index[-1], ["Pivot", "BC", "TC"]] = [pivot, bc, tc]

        # --- Plot ---
        fig = go.Figure()

        # Horizontal CPR lines per date
        for i, row in df_tail.iterrows():
            date = row["Date"]
            # Make each day's CPR lines visually wider (±16 hours)
            x0 = date - pd.Timedelta(hours=16)
            x1 = date + pd.Timedelta(hours=16)

            # TC line
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[row["TC"], row["TC"]],
                mode="lines",
                line=dict(color="red", width=2),
                name="TC" if i == 0 else None,
                hovertemplate=f"Date: {date.strftime('%d-%b-%Y')}<br>TC: %{{y:.2f}}<extra></extra>"
            ))

            # Pivot line
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[row["Pivot"], row["Pivot"]],
                mode="lines",
                line=dict(color="black", width=2, dash="dot"),
                name="Pivot" if i == 0 else None,
                hovertemplate=f"Date: {date.strftime('%d-%b-%Y')}<br>Pivot: %{{y:.2f}}<extra></extra>"
            ))

            # BC line
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[row["BC"], row["BC"]],
                mode="lines",
                line=dict(color="green", width=2),
                name="BC" if i == 0 else None,
                hovertemplate=f"Date: {date.strftime('%d-%b-%Y')}<br>BC: %{{y:.2f}}<extra></extra>"
            ))

        # --- Highlight next day's CPR band ---
        fig.add_shape(
            type="rect",
            x0=next_day - pd.Timedelta(hours=16),
            x1=next_day + pd.Timedelta(hours=16),
            y0=bc, y1=tc,
            fillcolor="lightpink", opacity=0.25, line=dict(width=0)
        )

        # --- Layout ---
        fig.update_layout(
            title=f"CPR Levels (Last 10 Days + {next_day.strftime('%d-%b-%Y')})",
            xaxis_title="Date",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False,
            height=700,
            template="plotly_white",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)
