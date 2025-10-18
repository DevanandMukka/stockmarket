import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import plotly.graph_objects as go

# --- Title ---
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center; color: #2F4F4F;'>📊 Sunil's CPR Calculator</h1>", unsafe_allow_html=True)

# File uploader
uploaded_file = st.file_uploader("Upload Excel File with Stock Data (Date, High, Low, Close)", type=["xlsx", "xls"])

if uploaded_file is None:
    st.info("Please upload an Excel file with columns: Date, High, Low, Close.")
else:
    # Try reading and validating the file
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Could not read uploaded file: {e}")
        st.stop()

    required_cols = {"Date", "High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        st.error(f"Excel file must contain columns: {required_cols}")
        st.stop()

    # Preprocess and basic validation
    df = df.copy()
    df = df.sort_values("Date").reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if df["Date"].isna().any():
        st.error("One or more 'Date' values could not be parsed. Ensure Date column is valid.")
        st.stop()

    if len(df) < 2:
        st.warning("Need at least 2 trading days in the file to compute two-day relationships. Upload more data.")
        st.stop()

    # --- CPR Calculations ---
    df["Pivot"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["BC"] = (df["High"] + df["Low"]) / 2
    df["TC"] = df["Pivot"] + (df["Pivot"] - df["BC"])

    # Ensure TC/BC order
    mask_swap = df["BC"] > df["TC"]
    if mask_swap.any():
        df.loc[mask_swap, ["TC", "BC"]] = df.loc[mask_swap, ["BC", "TC"]].values

    # Identify current (latest) and previous rows
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]

    # Extract current values
    curr_date = last_row["Date"]
    curr_pivot = float(last_row["Pivot"])
    curr_bc = float(last_row["BC"])
    curr_tc = float(last_row["TC"])

    prev_date = prev_row["Date"]
    prev_pivot = float(prev_row["Pivot"])
    prev_bc = float(prev_row["BC"])
    prev_tc = float(prev_row["TC"])

    # --- Support & Resistances (based on current pivot/high/low/close) ---
    high = float(last_row["High"])
    low = float(last_row["Low"])
    close = float(last_row["Close"])
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

    # --- Prepare result table ---
    result_df = pd.DataFrame({
        "Metric": ["R5", "R4", "R3", "R2", "R1",
                   "CPR - Top Central", "Pivot", "CPR - Bottom Central",
                   "S1", "S2", "S3", "S4", "S5"],
        "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
    })

    # --- Next trading day (skip weekends) ---
    last_date = curr_date
    next_day = last_date + timedelta(days=1)
    while next_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        next_day += timedelta(days=1)
    next_date = next_day

    # --- Project Next Day CPR Values ---
    # CPR width = TC - BC
    df["CPR_Width"] = df["TC"] - df["BC"]
    # Use last up-to-5 widths to get a stable average
    last_widths = df["CPR_Width"].tail(5).dropna()
    avg_width = float(last_widths.mean()) if len(last_widths) > 0 else float(tc - bc)

    # Estimate pivot change: use mean of recent pivot diffs
    pivot_diffs = df["Pivot"].diff().tail(5).dropna()
    avg_pivot_change = float(pivot_diffs.mean()) if len(pivot_diffs) > 0 else 0.0

    next_pivot = pivot + avg_pivot_change
    next_bc = next_pivot - avg_width / 2
    next_tc = next_pivot + avg_width / 2

    # --- Style table for display ---
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

    # --- Determine Two-Day Pivot Relationship (comparing current vs previous available day) ---
    relationship = None
    sentiment = None
    condition_text = ""

    # 1) Higher Value Relationship: Current BC > Previous TC
    if curr_bc > prev_tc:
        relationship = "Higher Value Relationship"
        sentiment = "Bullish"
        condition_text = f"Current BC ({curr_bc:.2f}) > Previous TC ({prev_tc:.2f})"

    # 2) Overlapping Higher Value Relationship
    elif curr_tc > prev_tc and curr_bc < prev_tc and curr_bc > prev_bc:
        relationship = "Overlapping Higher Value Relationship"
        sentiment = "Moderately Bullish"
        condition_text = (f"Current TC ({curr_tc:.2f}) > Prev TC ({prev_tc:.2f}), "
                          f"and Current BC ({curr_bc:.2f}) < Prev TC but > Prev BC ({prev_bc:.2f})")

    # 3) Lower Value Relationship
    elif curr_tc < prev_bc:
        relationship = "Lower Value Relationship"
        sentiment = "Bearish"
        condition_text = f"Current TC ({curr_tc:.2f}) < Previous BC ({prev_bc:.2f})"

    # 4) Overlapping Lower Value Relationship
    elif curr_bc < prev_bc and curr_tc > prev_bc:
        relationship = "Overlapping Lower Value Relationship"
        sentiment = "Moderately Bearish"
        condition_text = (f"Current BC ({curr_bc:.2f}) < Prev BC ({prev_bc:.2f}), "
                          f"and Current TC ({curr_tc:.2f}) > Prev BC ({prev_bc:.2f})")

    # 5) Unchanged Value Relationship (nearly equal)
    elif abs(curr_tc - prev_tc) < 0.05 and abs(curr_bc - prev_bc) < 0.05:
        relationship = "Unchanged Value Relationship"
        sentiment = "Sideways/Breakout"
        condition_text = f"Current and Previous CPR nearly equal: ΔTC={abs(curr_tc - prev_tc):.2f}, ΔBC={abs(curr_bc - prev_bc):.2f}"

    # 6) Outside Value Relationship
    elif curr_tc > prev_tc and curr_bc < prev_bc:
        relationship = "Outside Value Relationship"
        sentiment = "Sideways"
        condition_text = (f"Current TC ({curr_tc:.2f}) > Prev TC ({prev_tc:.2f}) and "
                          f"Current BC ({curr_bc:.2f}) < Prev BC ({prev_bc:.2f})")

    # 7) Inside Value Relationship
    elif curr_tc < prev_tc and curr_bc > prev_bc:
        relationship = "Inside Value Relationship"
        sentiment = "Breakout"
        condition_text = (f"Current TC ({curr_tc:.2f}) < Prev TC ({prev_tc:.2f}) and "
                          f"Current BC ({curr_bc:.2f}) > Prev BC ({prev_bc:.2f})")

    # Color map for sentiment
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

    # --- Plot CPR Chart (only actual trading days from file) ---
    df_tail = df.tail(20).copy()
    df_tail = df_tail[df_tail["Date"].dt.weekday < 5].reset_index(drop=True)  # remove weekends if present

    fig = go.Figure()

    # Plot CPR for real trading days (use literal values in hovertemplate to avoid formatting tokens)
    for i, row in df_tail.iterrows():
        date = row["Date"]
        x0 = date - pd.Timedelta(hours=8)
        x1 = date + pd.Timedelta(hours=8)
        tc_val = float(row["TC"])
        pivot_val = float(row["Pivot"])
        bc_val = float(row["BC"])

        fig.add_trace(go.Scatter(
            x=[x0, x1],
            y=[tc_val, tc_val],
            mode="lines",
            line=dict(color="red", width=2),
            hovertemplate=f"Date: {date.strftime('%d-%b-%Y')}<br>TC: {tc_val:.2f}<extra></extra>",
            name="TC" if i == 0 else None
        ))
        fig.add_trace(go.Scatter(
            x=[x0, x1],
            y=[pivot_val, pivot_val],
            mode="lines",
            line=dict(color="black", width=2, dash="dot"),
            hovertemplate=f"Date: {date.strftime('%d-%b-%Y')}<br>Pivot: {pivot_val:.2f}<extra></extra>",
            name="Pivot" if i == 0 else None
        ))
        fig.add_trace(go.Scatter(
            x=[x0, x1],
            y=[bc_val, bc_val],
            mode="lines",
            line=dict(color="green", width=2),
            hovertemplate=f"Date: {date.strftime('%d-%b-%Y')}<br>BC: {bc_val:.2f}<extra></extra>",
            name="BC" if i == 0 else None
        ))

    # Add projected next-day band (visual only)
    fig.add_shape(
        type="rect",
        x0=next_date - pd.Timedelta(hours=8),
        x1=next_date + pd.Timedelta(hours=8),
        y0=next_bc,
        y1=next_tc,
        fillcolor="rgba(255,182,193,0.3)",
        line=dict(width=0),
        layer="below"
    )

    # Annotate projected next-day values on chart (small labels)
    fig.add_annotation(
        x=next_date,
        y=next_tc,
        text=f"Next TC: {next_tc:.2f}",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-30,
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="#ff6b81"
    )
    fig.add_annotation(
        x=next_date,
        y=next_bc,
        text=f"Next BC: {next_bc:.2f}",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=30,
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="#34d399"
    )
    fig.add_annotation(
        x=next_date,
        y=next_pivot,
        text=f"Next Pivot: {next_pivot:.2f}",
        showarrow=False,
        yshift=10,
        bgcolor="rgba(255,255,255,0.9)"
    )

    fig.update_layout(
        title=f"CPR Levels (Last Trading Days + Projected {next_date.strftime('%d-%b-%Y')})",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=700,
        template="plotly_white",
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)
