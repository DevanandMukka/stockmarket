import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import plotly.graph_objects as go

# --- App title ---
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center; color: #2F4F4F;'>📊 Sunil's CPR Calculator</h1>", unsafe_allow_html=True)

# --- File uploader ---
uploaded_file = st.file_uploader("Upload Excel File with Stock Data (Date, High, Low, Close)", type=["xlsx", "xls"])

if uploaded_file is None:
    st.info("Please upload an Excel file with columns: Date, High, Low, Close.")
else:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Could not read uploaded file: {e}")
        st.stop()

    required_cols = {"Date", "High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        st.error(f"Excel file must contain columns: {required_cols}")
        st.stop()

    # --- Data preparation ---
    df = df.sort_values("Date").reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    if len(df) < 2:
        st.warning("Need at least 2 trading days in the file to compute relationships.")
        st.stop()

    # --- CPR calculations ---
    df["Pivot"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["BC"] = (df["High"] + df["Low"]) / 2
    df["TC"] = df["Pivot"] + (df["Pivot"] - df["BC"])
    mask_swap = df["BC"] > df["TC"]
    df.loc[mask_swap, ["TC", "BC"]] = df.loc[mask_swap, ["BC", "TC"]].values

    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]

    # --- Current day values ---
    curr_date = last_row["Date"]
    curr_pivot, curr_bc, curr_tc = float(last_row["Pivot"]), float(last_row["BC"]), float(last_row["TC"])
    prev_pivot, prev_bc, prev_tc = float(prev_row["Pivot"]), float(prev_row["BC"]), float(prev_row["TC"])
    high, low, close = float(last_row["High"]), float(last_row["Low"]), float(last_row["Close"])

    # --- Support/resistance levels ---
    pivot = curr_pivot
    bc = curr_bc
    tc = curr_tc
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

    # --- Result table ---
    result_df = pd.DataFrame({
        "Metric": ["R5", "R4", "R3", "R2", "R1",
                   "CPR - Top Central", "Pivot", "CPR - Bottom Central",
                   "S1", "S2", "S3", "S4", "S5"],
        "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
    })

    # --- Next trading day ---
    next_day = curr_date + timedelta(days=1)
    while next_day.weekday() >= 5:  # skip weekends
        next_day += timedelta(days=1)
    next_date = next_day

    # --- Project next-day CPR ---
    df["CPR_Width"] = df["TC"] - df["BC"]
    avg_width = df["CPR_Width"].tail(5).mean()
    pivot_diffs = df["Pivot"].diff().tail(5).dropna()
    avg_pivot_change = pivot_diffs.mean() if len(pivot_diffs) > 0 else 0.0
    next_pivot = pivot + avg_pivot_change
    next_bc = next_pivot - avg_width / 2
    next_tc = next_pivot + avg_width / 2

    # --- Style result table ---
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

    st.subheader(f"Stock Levels for {next_date.strftime('%A, %d-%b-%Y')} (Projected Next Trading Day)")
    st.dataframe(styled_df, use_container_width=True)

    # --- Two-day pivot relationship ---
    relationship, sentiment, condition_text = None, None, ""

    if curr_bc > prev_tc:
        relationship, sentiment = "Higher Value Relationship", "Bullish"
        condition_text = f"Current BC ({curr_bc:.2f}) > Previous TC ({prev_tc:.2f})"
    elif curr_tc > prev_tc and curr_bc < prev_tc and curr_bc > prev_bc:
        relationship, sentiment = "Overlapping Higher Value Relationship", "Moderately Bullish"
        condition_text = f"Current TC ({curr_tc:.2f}) > Prev TC ({prev_tc:.2f}) and BC between ranges"
    elif curr_tc < prev_bc:
        relationship, sentiment = "Lower Value Relationship", "Bearish"
        condition_text = f"Current TC ({curr_tc:.2f}) < Previous BC ({prev_bc:.2f})"
    elif curr_bc < prev_bc and curr_tc > prev_bc:
        relationship, sentiment = "Overlapping Lower Value Relationship", "Moderately Bearish"
        condition_text = f"Current BC ({curr_bc:.2f}) < Prev BC ({prev_bc:.2f}) and TC > Prev BC"
    elif abs(curr_tc - prev_tc) < 0.05 and abs(curr_bc - prev_bc) < 0.05:
        relationship, sentiment = "Unchanged Value Relationship", "Sideways/Breakout"
        condition_text = f"Current and Previous CPR nearly equal"
    elif curr_tc > prev_tc and curr_bc < prev_bc:
        relationship, sentiment = "Outside Value Relationship", "Sideways"
        condition_text = f"Current range fully engulfs previous range"
    elif curr_tc < prev_tc and curr_bc > prev_bc:
        relationship, sentiment = "Inside Value Relationship", "Breakout"
        condition_text = f"Current range inside previous range"

    color_map = {
        "Bullish": "#16a34a",
        "Moderately Bullish": "#22c55e",
        "Bearish": "#dc2626",
        "Moderately Bearish": "#ef4444",
        "Sideways/Breakout": "#2563eb",
        "Sideways": "#3b82f6",
        "Breakout": "#9333ea"
    }
    sentiment_color = color_map.get(sentiment, "#111827")

    # --- Relationship info box ---
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
                {relationship or '—'} →
                <span style="color:{sentiment_color}; font-weight:bold;">{sentiment or '—'}</span>
            </div>
            <div style="font-size:15px; color:#374151;">
                <b>Current Day ({curr_date.strftime('%d-%b-%Y')}):</b> TC = {curr_tc:.2f}, BC = {curr_bc:.2f}, Pivot = {curr_pivot:.2f}<br>
                <b>Next Trading Day ({next_date.strftime('%d-%b-%Y')} - projected):</b> TC = {next_tc:.2f}, BC = {next_bc:.2f}, Pivot = {next_pivot:.2f}<br>
                <i>Condition satisfied:</i> {condition_text or 'N/A'}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- Dynamic CPR chart ---
    df_trading = df[df["Date"].dt.weekday < 5].reset_index(drop=True)
    max_days = len(df_trading)
    default_days = min(7, max_days)

    selected_days = st.slider(
        "Select number of trading days to display on chart",
        min_value=2,
        max_value=max_days,
        value=default_days,
        step=1
    )

    df_tail = df_trading.tail(selected_days).copy()
    fig = go.Figure()

    # Plot CPR lines for each actual trading day
    for _, row in df_tail.iterrows():
        date = row["Date"]
        x0, x1 = date - pd.Timedelta(hours=8), date + pd.Timedelta(hours=8)
        tc_val, pivot_val, bc_val = float(row["TC"]), float(row["Pivot"]), float(row["BC"])

        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[tc_val, tc_val],
            mode="lines", line=dict(color="red", width=2),
            hovertemplate=f"Date: {date.strftime('%d-%b-%Y')}<br>TC: {tc_val:.2f}<extra></extra>",
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[pivot_val, pivot_val],
            mode="lines", line=dict(color="black", width=2, dash="dot"),
            hovertemplate=f"Date: {date.strftime('%d-%b-%Y')}<br>Pivot: {pivot_val:.2f}<extra></extra>",
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[bc_val, bc_val],
            mode="lines", line=dict(color="green", width=2),
            hovertemplate=f"Date: {date.strftime('%d-%b-%Y')}<br>BC: {bc_val:.2f}<extra></extra>",
            showlegend=False
        ))

    # --- Add next trading day's projected CPR (like other days) ---
    next_x0, next_x1 = next_date - pd.Timedelta(hours=8), next_date + pd.Timedelta(hours=8)

    # Highlight box
    fig.add_shape(
        type="rect",
        x0=next_x0, x1=next_x1,
        y0=next_bc, y1=next_tc,
        fillcolor="rgba(255,192,203,0.25)",
        line=dict(color="rgba(255,105,180,0.6)", width=2),
        layer="below"
    )

    # Draw next day CPR lines
    fig.add_trace(go.Scatter(
        x=[next_x0, next_x1], y=[next_tc, next_tc],
        mode="lines", line=dict(color="red", width=2, dash="solid"),
        hovertemplate=f"Date: {next_date.strftime('%d-%b-%Y')}<br>Next TC: {next_tc:.2f}<extra></extra>",
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=[next_x0, next_x1], y=[next_pivot, next_pivot],
        mode="lines", line=dict(color="black", width=2, dash="dot"),
        hovertemplate=f"Date: {next_date.strftime('%d-%b-%Y')}<br>Next Pivot: {next_pivot:.2f}<extra></extra>",
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=[next_x0, next_x1], y=[next_bc, next_bc],
        mode="lines", line=dict(color="green", width=2),
        hovertemplate=f"Date: {next_date.strftime('%d-%b-%Y')}<br>Next BC: {next_bc:.2f}<extra></extra>",
        showlegend=False
    ))

    # --- Layout ---
    fig.update_layout(
        title=f"CPR Levels (Last {selected_days} Trading Days + Projected {next_date.strftime('%d-%b-%Y')})",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=700,
        template="plotly_white",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
