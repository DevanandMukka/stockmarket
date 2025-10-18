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

        # --- Calculate CPR values for all days ---
        df["Pivot"] = (df["High"] + df["Low"] + df["Close"]) / 3
        df["BC"] = (df["High"] + df["Low"]) / 2
        df["TC"] = df["Pivot"] + (df["Pivot"] - df["BC"])
        df.loc[df["BC"] > df["TC"], ["TC", "BC"]] = df.loc[df["BC"] > df["TC"], ["BC", "TC"]].values

        # --- Current day's CPR ---
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else None

        high, low, close = last_row["High"], last_row["Low"], last_row["Close"]
        pivot, bc, tc = last_row["Pivot"], last_row["BC"], last_row["TC"]

        # --- Supports & Resistances ---
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

        # --- DataFrame for Display ---
        data = {
            "Metric": ["R5", "R4", "R3", "R2", "R1",
                       "CPR - Top Central", "Pivot", "CPR - Bottom Central",
                       "S1", "S2", "S3", "S4", "S5"],
            "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
        }
        result_df = pd.DataFrame(data)

        # --- Next trading day ---
        last_date = df["Date"].iloc[-1]
        next_day = last_date + timedelta(days=1)
        if next_day.weekday() == 5:
            next_day += timedelta(days=2)
        elif next_day.weekday() == 6:
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

        st.subheader(f"Stock Levels for {next_day.strftime('%A, %d-%b-%Y')} (Next trading day)")
        st.dataframe(styled_df, use_container_width=True)

        # --- Determine Two-Day Pivot Relationship ---
        if prev_row is not None:
            prev_tc, prev_bc = prev_row["TC"], prev_row["BC"]
            curr_tc, curr_bc = last_row["TC"], last_row["BC"]
            prev_date = prev_row["Date"].strftime("%d-%b-%Y")
            curr_date = last_row["Date"].strftime("%d-%b-%Y")

            relationship = None
            sentiment = None
            condition_text = ""

            # 1️⃣ Higher Value Relationship
            if curr_bc > prev_tc:
                relationship = "Higher Value Relationship"
                sentiment = "Bullish"
                condition_text = f"Current BC ({curr_bc:.2f}) > Previous TC ({prev_tc:.2f})"

            # 2️⃣ Overlapping Higher Value Relationship
            elif curr_tc > prev_tc and curr_bc < prev_tc and curr_bc > prev_bc:
                relationship = "Overlapping Higher Value Relationship"
                sentiment = "Moderately Bullish"
                condition_text = f"Current TC ({curr_tc:.2f}) > Prev TC ({prev_tc:.2f}), and Current BC ({curr_bc:.2f}) < Prev TC but > Prev BC"

            # 3️⃣ Lower Value Relationship
            elif curr_tc < prev_bc:
                relationship = "Lower Value Relationship"
                sentiment = "Bearish"
                condition_text = f"Current TC ({curr_tc:.2f}) < Previous BC ({prev_bc:.2f})"

            # 4️⃣ Overlapping Lower Value Relationship
            elif curr_bc < prev_bc and curr_tc > prev_bc:
                relationship = "Overlapping Lower Value Relationship"
                sentiment = "Moderately Bearish"
                condition_text = f"Current BC ({curr_bc:.2f}) < Prev BC ({prev_bc:.2f}), and Current TC ({curr_tc:.2f}) > Prev BC"

            # 5️⃣ Unchanged Value Relationship
            elif abs(curr_tc - prev_tc) < 0.05 and abs(curr_bc - prev_bc) < 0.05:
                relationship = "Unchanged Value Relationship"
                sentiment = "Sideways/Breakout"
                condition_text = f"Current and Previous CPR nearly equal: Diff in TC={abs(curr_tc - prev_tc):.2f},  Diff in BC={abs(curr_bc - prev_bc):.2f}"

            # 6️⃣ Outside Value Relationship
            elif curr_tc > prev_tc and curr_bc < prev_bc:
                relationship = "Outside Value Relationship"
                sentiment = "Sideways"
                condition_text = f"Current TC ({curr_tc:.2f}) > Prev TC ({prev_tc:.2f}) and Current BC ({curr_bc:.2f}) < Prev BC ({prev_bc:.2f})"

            # 7️⃣ Inside Value Relationship
            elif curr_tc < prev_tc and curr_bc > prev_bc:
                relationship = "Inside Value Relationship"
                sentiment = "Breakout"
                condition_text = f"Current TC ({curr_tc:.2f}) < Prev TC ({prev_tc:.2f}) and Current BC ({curr_bc:.2f}) > Prev BC ({prev_bc:.2f})"

            # --- Choose sentiment color ---
            color_map = {
                "Bullish": "#16a34a",           # green
                "Moderately Bullish": "#22c55e",
                "Bearish": "#dc2626",           # red
                "Moderately Bearish": "#ef4444",
                "Sideways/Breakout": "#2563eb", # blue
                "Sideways": "#3b82f6",
                "Breakout": "#9333ea"           # violet
            }
            sentiment_color = color_map.get(sentiment, "#111827")

            # --- Display Relationship Box with Condition Details ---
            st.markdown(f"""
                <div style="
                    text-align:center;
                    font-size:22px;
                    font-weight:bold;
                    background: linear-gradient(145deg, #f0f9ff, #ffffff);
                    padding:22px;
                    border-radius:15px;
                    box-shadow: 0px 4px 8px rgba(0,0,0,0.08);
                    margin-top:25px;
                    border: 1px solid #d1d5db;
                ">
                    <div style="font-size:26px; color:#1E40AF; margin-bottom:10px; text-transform:uppercase;">
                        🧭 Two Day Pivot Relationship Details
                    </div>
                    <div style="font-size:24px; color:#1f2937; margin-bottom:8px;">
                        {relationship} → 
                        <span style="color:{sentiment_color}; font-weight:bold;">{sentiment}</span>
                    </div>
                    <div style="font-size:15px; color:#374151;">
                        <b>Previous Day ({prev_date}):</b> TC = {prev_tc:.2f}, BC = {prev_bc:.2f}<br>
                        <b>Current Day ({curr_date}):</b> TC = {curr_tc:.2f}, BC = {curr_bc:.2f}<br>
                        <i>Condition satisfied:</i> {condition_text}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # --- Chart: CPR Lines ---
        df_tail = df.tail(10).copy()
        next_row = pd.DataFrame({"Date": [next_day], "High": [np.nan], "Low": [np.nan], "Close": [np.nan]})
        df_tail = pd.concat([df_tail, next_row], ignore_index=True)
        df_tail.loc[df_tail.index[-1], ["Pivot", "BC", "TC"]] = [pivot, bc, tc]

        fig = go.Figure()

        for i, row in df_tail.iterrows():
            date = row["Date"]
            x0 = date - pd.Timedelta(hours=16)
            x1 = date + pd.Timedelta(hours=16)

            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[row["TC"], row["TC"]],
                mode="lines", line=dict(color="red", width=2),
                name="TC" if i == 0 else None))
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[row["Pivot"], row["Pivot"]],
                mode="lines", line=dict(color="black", width=2, dash="dot"),
                name="Pivot" if i == 0 else None))
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[row["BC"], row["BC"]],
                mode="lines", line=dict(color="green", width=2),
                name="BC" if i == 0 else None))

        fig.add_shape(type="rect",
                      x0=next_day - pd.Timedelta(hours=16),
                      x1=next_day + pd.Timedelta(hours=16),
                      y0=bc, y1=tc,
                      fillcolor="lightpink", opacity=0.25, line=dict(width=0))

        fig.update_layout(
            title=f"CPR Levels (Last 10 Days + {next_day.strftime('%d-%b-%Y')})",
            xaxis_title="Date", yaxis_title="Price",
            xaxis_rangeslider_visible=False, height=700,
            template="plotly_white", showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

