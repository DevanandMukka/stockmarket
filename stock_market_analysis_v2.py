import streamlit as st
import pandas as pd
from datetime import timedelta
import plotly.graph_objects as go

# --- App title ---
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center; color: #2F4F4F;'>📊 Sunil's CPR & Camarilla Calculator</h1>", unsafe_allow_html=True)

# ==========================================================
# --- Market Selection ---
market_type = st.radio(
    "Select Market Type:",
    ["Stock Market", "Bitcoin"],
    horizontal=True
)

# --- File uploader ---
uploaded_file = st.file_uploader("Upload Excel File with Data (Date, High, Low, Close)", type=["xlsx", "xls"])

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

    # --- Data Prep ---
    df = df.sort_values("Date").reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    if len(df) < 2:
        st.warning("Need at least 2 trading days in the file.")
        st.stop()

    # ==========================================================
    # --- CPR CALCULATION ---
    df["Pivot_T_to_T1"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["BC_T_to_T1"] = (df["High"] + df["Low"]) / 2
    df["TC_T_to_T1"] = df["Pivot_T_to_T1"] + (df["Pivot_T_to_T1"] - df["BC_T_to_T1"])

    # Fix swapped TC/BC values
    mask_swap = df["BC_T_to_T1"] > df["TC_T_to_T1"]
    df.loc[mask_swap, ["TC_T_to_T1", "BC_T_to_T1"]] = df.loc[mask_swap, ["BC_T_to_T1", "TC_T_to_T1"]].values

    # Note for swap
    swap_note = ""
    df["Pivot"] = df["Pivot_T_to_T1"].shift(1)
    df["BC"] = df["BC_T_to_T1"].shift(1)
    df["TC"] = df["TC_T_to_T1"].shift(1)

    # --- Next Day CPR Calculation ---
    last_day_data = df.iloc[-1]
    next_pivot = (last_day_data["High"] + last_day_data["Low"] + last_day_data["Close"]) / 3
    next_bc = (last_day_data["High"] + last_day_data["Low"]) / 2
    next_tc = next_pivot + (next_pivot - next_bc)

    if next_bc > next_tc:
        next_tc, next_bc = next_bc, next_tc
        swap_note = f"<br><span style='color:red;'><i>⚠️ Note:</i> BC and TC were swapped due to BC > TC condition.</span>"

    curr_date = last_day_data["Date"]
    next_day = curr_date + timedelta(days=1)
    if market_type == "Stock Market":
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
    next_date = next_day

    # --- CPR Table ---
    high = last_day_data["High"]
    low = last_day_data["Low"]
    pivot = next_pivot
    bc = next_bc
    tc = next_tc

    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = r1 + (high - low)
    s3 = s1 - (high - low)
    r4 = r3 + (r2 - r1)
    s4 = s3 - (s1 - s2)
    r5 = r4 + (r2 - r1)
    s5 = s4 - (s1 - s2)

    result_df = pd.DataFrame({
        "Metric": ["R5", "R4", "R3", "R2", "R1",
                   "CPR - Top Central", "Pivot", "CPR - Bottom Central",
                   "S1", "S2", "S3", "S4", "S5"],
        "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
    })

    def color_metrics(val, metric):
        if "S" in metric or metric == "CPR - Bottom Central":
            return 'color: green; font-weight: bold;'
        elif "R" in metric:
            return 'color: red; font-weight: bold;'
        return 'color: black; font-weight: bold;'

    styled_df = result_df.style.format({"Value": "{:.2f}"}) \
        .apply(lambda col: [color_metrics(v, m) for v, m in zip(result_df["Value"], result_df["Metric"])], axis=0)

    st.subheader(f"📊 {market_type} CPR Levels for next day ({next_date.strftime('%A, %d-%b-%Y')})")
    st.dataframe(styled_df, use_container_width=True)

    # =================================================================
    # --- Two-day pivot relationship ---
    df_cpr_ready = df.dropna(subset=["Pivot", "BC", "TC"]).copy()

    if len(df_cpr_ready) < 1:
        st.warning("Not enough data to compute T-day levels for relationship analysis.")
    else:
        prev_row_cpr = df_cpr_ready.iloc[-1]
        prev_pivot, prev_bc, prev_tc = float(prev_row_cpr["Pivot"]), float(prev_row_cpr["BC"]), float(prev_row_cpr["TC"])
        prev_date = prev_row_cpr["Date"]
        curr_pivot, curr_bc, curr_tc = next_pivot, next_bc, next_tc

        # Pivot Widths
        prev_tc_pivot_diff = prev_tc - prev_pivot
        prev_pivot_bc_diff = prev_pivot - prev_bc
        next_tc_pivot_diff = next_tc - next_pivot
        next_pivot_bc_diff = next_pivot - next_bc

        # Relationship logic
        if curr_bc > prev_tc:
            relationship, sentiment = "Higher Value Relationship", "Bullish"
            condition_text = f"Next Day BC ({curr_bc:.2f}) > Current Day TC ({prev_tc:.2f})"
        elif curr_tc > prev_tc and curr_bc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Overlapping Higher Value Relationship", "Moderately Bullish"
            condition_text = f"Next Day TC ({curr_tc:.2f}) > Current Day TC ({prev_tc:.2f})"
        elif curr_tc < prev_bc:
            relationship, sentiment = "Lower Value Relationship", "Bearish"
            condition_text = f"Next Day TC ({curr_tc:.2f}) < Current Day BC ({prev_bc:.2f})"
        elif curr_bc < prev_bc and curr_tc > prev_bc:
            relationship, sentiment = "Overlapping Lower Value Relationship", "Moderately Bearish"
            condition_text = f"Next Day BC ({curr_bc:.2f}) < Current Day BC ({prev_bc:.2f})"
        elif curr_tc > prev_tc and curr_bc < prev_bc:
            relationship, sentiment = "Outside Value Relationship", "Sideways"
            condition_text = "Next Day range fully engulfs Current Day range"
        elif curr_tc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Inside Value Relationship", "Breakout"
            condition_text = "Next Day range inside Current Day range"
        else:
            relationship, sentiment = "No Clear Relationship", "Neutral"
            condition_text = "N/A"

        color_map = {
            "Bullish": "#16a34a", "Moderately Bullish": "#22c55e",
            "Bearish": "#dc2626", "Moderately Bearish": "#ef4444",
            "Sideways": "#3b82f6", "Breakout": "#9333ea", "Neutral": "#9ca3af"
        }
        sentiment_color = color_map.get(sentiment, "#111827")

        # --- Relationship info box with pivot width ---
        st.markdown(f"""
            <div style="text-align:center;font-size:22px;font-weight:bold;background:linear-gradient(145deg,#f0f9ff,#ffffff);
                padding:22px;border-radius:15px;box-shadow:0px 4px 8px rgba(0,0,0,0.08);margin-top:25px;border:1px solid #d1d5db;">
                <div style="font-size:26px;color:#1E40AF;margin-bottom:10px;text-transform:uppercase;">
                    🧭 Two Day Pivot Relationship Details
                </div>
                <div style="font-size:24px;color:#1f2937;margin-bottom:8px;">
                    {relationship or '—'} →
                    <span style="color:{sentiment_color};font-weight:bold;">{sentiment or '—'}</span>
                </div>
                <div style="font-size:15px;color:#374151;text-align:left;margin:auto;display:flex;justify-content:space-between;">
                    <div>
                        <b>Current Trading Day ({prev_date.strftime('%d-%b-%Y')}):</b><br>
                        TC = {prev_tc:.2f}, Pivot = {prev_pivot:.2f}, BC = {prev_bc:.2f}
                    </div>
                    <div style="color:#2563eb;">
                        TC−Pivot = {prev_tc_pivot_diff:.2f}<br>
                        Pivot−BC = {prev_pivot_bc_diff:.2f}
                    </div>
                </div>
                <div style="font-size:15px;color:#374151;text-align:left;margin:auto;display:flex;justify-content:space-between;">
                    <div>
                        <b>Next Trading Day ({next_date.strftime('%d-%b-%Y')}):</b><br>
                        TC = {next_tc:.2f}, Pivot = {next_pivot:.2f}, BC = {next_bc:.2f}
                    </div>
                    <div style="color:#2563eb;">
                        TC−Pivot = {next_tc_pivot_diff:.2f}<br>
                        Pivot−BC = {next_pivot_bc_diff:.2f}
                    </div>
                </div>
                <div style="font-size:15px;color:#374151;">
                    <i>Condition satisfied:</i> {condition_text or 'N/A'}
                    {swap_note}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ==========================================================
    # --- CAMARILLA CALCULATION ---
    df["Range"] = df["High"] - df["Low"]
    df["R3"] = df["Close"] + df["Range"] * 1.1 / 4
    df["S3"] = df["Close"] - df["Range"] * 1.1 / 4
    df["R4"] = df["Close"] + df["Range"] * 1.1 / 2
    df["S4"] = df["Close"] - df["Range"] * 1.1 / 2
    df[["R3", "S3", "R4", "S4"]] = df[["R3", "S3", "R4", "S4"]].shift(1)

    rng = last_day_data["High"] - last_day_data["Low"]
    next_R3 = last_day_data["Close"] + rng * 1.1 / 4
    next_S3 = last_day_data["Close"] - rng * 1.1 / 4

    df_camarilla = pd.concat([df[["Date", "R3", "S3"]], pd.DataFrame({"Date": [next_date], "R3": [next_R3], "S3": [next_S3]})])

    prev_row = df_camarilla.iloc[-2]
    curr_row = df_camarilla.iloc[-1]
    prev_R3, prev_S3 = prev_row["R3"], prev_row["S3"]
    curr_R3, curr_S3 = curr_row["R3"], curr_row["S3"]

    prev_width = prev_R3 - prev_S3
    curr_width = curr_R3 - curr_S3

    st.markdown(f"""
        <div style="text-align:center;font-size:22px;font-weight:bold;background:linear-gradient(145deg,#f0f9ff,#ffffff);
            padding:22px;border-radius:15px;box-shadow:0px 4px 8px rgba(0,0,0,0.08);margin-top:25px;border:1px solid #d1d5db;">
            <div style="font-size:26px;color:#1E40AF;margin-bottom:10px;text-transform:uppercase;">
                🎯 Two-Day Camarilla Relationship
            </div>
            <div style="font-size:15px;color:#374151;text-align:left;margin:auto;display:flex;justify-content:space-between;">
                <div>
                    <b>Previous Day:</b><br>R3={prev_R3:.2f}, S3={prev_S3:.2f}
                </div>
                <div style="color:#2563eb;">
                    R3−S3 = {prev_width:.2f}
                </div>
            </div>
            <div style="font-size:15px;color:#374151;text-align:left;margin:auto;display:flex;justify-content:space-between;">
                <div>
                    <b>Current Day:</b><br>R3={curr_R3:.2f}, S3={curr_S3:.2f}
                </div>
                <div style="color:#2563eb;">
                    R3−S3 = {curr_width:.2f}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
