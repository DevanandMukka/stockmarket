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

    # --- Swapped note only for current or next trading day ---
    swap_note = ""
    recent_mask = mask_swap.iloc[-2:]
    swapped_recent = df.loc[recent_mask.tail(2), "Date"].dt.strftime("%d-%b-%Y").tolist()
    if swapped_recent:
        swap_note = f"<br><span style='color:red;'><i>⚠️ Note:</i> BC and TC were swapped for {' & '.join(swapped_recent)} (BC > TC condition).</span>"

    # Shift for next-day CPR
    df["Pivot"] = df["Pivot_T_to_T1"].shift(1)
    df["BC"] = df["BC_T_to_T1"].shift(1)
    df["TC"] = df["TC_T_to_T1"].shift(1)

    # --- Next Day CPR ---
    last_day_data = df.iloc[-1]
    next_pivot = (last_day_data["High"] + last_day_data["Low"] + last_day_data["Close"]) / 3
    next_bc = (last_day_data["High"] + last_day_data["Low"]) / 2
    next_tc = next_pivot + (next_pivot - next_bc)
    if next_bc > next_tc:
        next_tc, next_bc = next_bc, next_tc

    curr_date = last_day_data["Date"]
    next_day = curr_date + timedelta(days=1)
    if market_type == "Stock Market":
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
    next_date = next_day

    # ==========================================================
    # --- Two-day Pivot Relationship ---
    df_cpr_ready = df.dropna(subset=["Pivot", "BC", "TC"]).copy()
    if len(df_cpr_ready) < 1:
        st.warning("Not enough data for CPR relationship analysis.")
    else:
        prev_row = df_cpr_ready.iloc[-1]
        prev_pivot, prev_bc, prev_tc = prev_row["Pivot"], prev_row["BC"], prev_row["TC"]
        prev_date = prev_row["Date"]

        curr_pivot, curr_bc, curr_tc = next_pivot, next_bc, next_tc

        # Determine relationship
        if curr_bc > prev_tc:
            relationship, sentiment = "Higher Value Relationship", "Bullish"
            condition_text = f"Next Day BC ({curr_bc:.2f}) > Current Day TC ({prev_tc:.2f})"
        elif curr_tc > prev_tc and curr_bc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Overlapping Higher Value Relationship", "Moderately Bullish"
            condition_text = "Next Day TC > Current Day TC and BC between ranges"
        elif curr_tc < prev_bc:
            relationship, sentiment = "Lower Value Relationship", "Bearish"
            condition_text = "Next Day TC < Current Day BC"
        elif curr_bc < prev_bc and curr_tc > prev_bc:
            relationship, sentiment = "Overlapping Lower Value Relationship", "Moderately Bearish"
            condition_text = "Next Day BC < Current Day BC and TC > Current Day BC"
        elif abs(curr_tc - prev_tc) < 0.05 and abs(curr_bc - prev_bc) < 0.05:
            relationship, sentiment = "Unchanged Value Relationship", "Sideways/Breakout"
            condition_text = "CPRs nearly equal"
        elif curr_tc > prev_tc and curr_bc < prev_bc:
            relationship, sentiment = "Outside Value Relationship", "Sideways"
            condition_text = "Next Day range fully engulfs Current Day"
        elif curr_tc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Inside Value Relationship", "Breakout"
            condition_text = "Next Day range inside Current Day"
        else:
            relationship, sentiment = "No Clear Relationship", "Neutral"
            condition_text = "N/A"

        # Pivot widths
        prev_tc_pivot_diff = prev_tc - prev_pivot
        prev_pivot_bc_diff = prev_pivot - prev_bc
        curr_tc_pivot_diff = curr_tc - curr_pivot
        curr_pivot_bc_diff = curr_pivot - curr_bc

        color_map = {
            "Bullish": "#16a34a", "Moderately Bullish": "#22c55e",
            "Bearish": "#dc2626", "Moderately Bearish": "#ef4444",
            "Sideways/Breakout": "#2563eb", "Sideways": "#3b82f6",
            "Breakout": "#9333ea", "Neutral": "#9ca3af"
        }
        sentiment_color = color_map.get(sentiment, "#111827")

        # --- Relationship info box ---
        st.markdown(f"""
            <div style="text-align:center;font-size:22px;font-weight:bold;background:linear-gradient(145deg,#f0f9ff,#ffffff);
                padding:22px;border-radius:15px;box-shadow:0px 4px 8px rgba(0,0,0,0.08);
                margin-top:25px;border:1px solid #d1d5db;">
                <div style="font-size:26px;color:#1E40AF;margin-bottom:10px;text-transform:uppercase;">
                    🧭 Two Day Pivot Relationship Details
                </div>
                <div style="font-size:24px;color:#1f2937;margin-bottom:8px;">
                    {relationship} →
                    <span style="color:{sentiment_color};font-weight:bold;">{sentiment}</span>
                </div>

                <div style="font-size:15px;color:#374151;text-align:left;display:inline-block;margin:auto;">
                    <b>Current Trading Day ({prev_date.strftime('%d-%b-%Y')}):</b><br>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:500px;">
                        <span>TC = {prev_tc:.2f}</span>
                        <span style="color:#ef4444;">TC - Pivot = {prev_tc_pivot_diff:.2f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:500px;">
                        <span>Pivot = {prev_pivot:.2f}</span>
                        <span style="color:#16a34a;">Pivot - BC = {prev_pivot_bc_diff:.2f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:500px;">
                        <span>BC = {prev_bc:.2f}</span><span>&nbsp;</span>
                    </div><br>

                    <b>Next Trading Day ({next_date.strftime('%d-%b-%Y')}):</b><br>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:500px;">
                        <span>TC = {curr_tc:.2f}</span>
                        <span style="color:#ef4444;">TC - Pivot = {curr_tc_pivot_diff:.2f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:500px;">
                        <span>Pivot = {curr_pivot:.2f}</span>
                        <span style="color:#16a34a;">Pivot - BC = {curr_pivot_bc_diff:.2f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:500px;">
                        <span>BC = {curr_bc:.2f}</span><span>&nbsp;</span>
                    </div><br>

                    <i>Condition satisfied:</i> {condition_text}
                    {swap_note}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ==========================================================
    # --- CAMARILLA CALCULATION ---
    df["Range"] = df["High"] - df["Low"]
    df["R3"] = df["Close"] + df["Range"] * 1.1 / 4
    df["S3"] = df["Close"] - df["Range"] * 1.1 / 4
    for col in ["R3", "S3"]:
        df[col] = df[col].shift(1)

    rng = last_day_data["High"] - last_day_data["Low"]
    next_R3 = last_day_data["Close"] + rng * 1.1 / 4
    next_S3 = last_day_data["Close"] - rng * 1.1 / 4

    df_cam = pd.concat([
        df[["Date", "R3", "S3"]],
        pd.DataFrame({"Date": [next_date], "R3": [next_R3], "S3": [next_S3]})
    ], ignore_index=True)

    if len(df_cam) < 2:
        st.warning("Not enough data for Camarilla relationship.")
    else:
        prev_row = df_cam.iloc[-2]
        curr_row = df_cam.iloc[-1]

        prev_R3, prev_S3 = prev_row["R3"], prev_row["S3"]
        curr_R3, curr_S3 = curr_row["R3"], curr_row["S3"]

        prev_width = prev_R3 - prev_S3
        curr_width = curr_R3 - curr_S3

        if curr_S3 > prev_R3:
            relationship, sentiment = "CE Higher Value Relationship", "Bullish"
        elif curr_R3 > prev_R3 and curr_S3 < prev_R3 and curr_S3 > prev_S3:
            relationship, sentiment = "CE Overlapping Higher Value Relationship", "Moderately Bullish"
        elif curr_R3 < prev_S3:
            relationship, sentiment = "CE Lower Value Relationship", "Bearish"
        elif curr_R3 > prev_S3 and curr_S3 < prev_S3 and curr_S3 < prev_R3:
            relationship, sentiment = "CE Overlapping Lower Value Relationship", "Moderately Bearish"
        elif abs(curr_R3 - prev_R3) < 0.05 and abs(curr_S3 - prev_S3) < 0.05:
            relationship, sentiment = "CE Unchanged Value Relationship", "Sideways/Breakout"
        elif curr_R3 > prev_R3 and curr_S3 < prev_S3:
            relationship, sentiment = "CE Outside Value Relationship", "Sideways"
        elif curr_R3 < prev_R3 and curr_S3 > prev_S3:
            relationship, sentiment = "CE Inside Value Relationship", "Breakout"
        else:
            relationship, sentiment = "Unknown", "Neutral"

        sentiment_color = {
            "Bullish": "#16a34a", "Moderately Bullish": "#22c55e",
            "Bearish": "#dc2626", "Moderately Bearish": "#ef4444",
            "Sideways/Breakout": "#2563eb", "Sideways": "#3b82f6",
            "Breakout": "#9333ea", "Neutral": "#9ca3af"
        }.get(sentiment, "#111827")

        st.markdown(f"""
            <div style="text-align:center;font-size:22px;font-weight:bold;background:linear-gradient(145deg,#f0f9ff,#ffffff);
                padding:22px;border-radius:15px;box-shadow:0px 4px 8px rgba(0,0,0,0.08);margin-top:25px;border:1px solid #d1d5db;">
                <div style="font-size:26px;color:#1E40AF;margin-bottom:10px;text-transform:uppercase;">
                    🎯 Two-Day Camarilla Relationship
                </div>
                <div style="font-size:24px;color:#1f2937;margin-bottom:8px;">
                    {relationship} →
                    <span style="color:{sentiment_color};font-weight:bold;">{sentiment}</span>
                </div>
                <div style="font-size:15px;color:#374151;text-align:left;display:inline-block;margin:auto;">
                    <b>Previous Trading Day:</b><br>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:400px;">
                        <span>R3 = {prev_R3:.2f}</span>
                        <span style="color:#ef4444;">Width (R3 - S3) = {prev_width:.2f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:400px;">
                        <span>S3 = {prev_S3:.2f}</span><span>&nbsp;</span>
                    </div><br>
                    <b>Next Trading Day:</b><br>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:400px;">
                        <span>R3 = {curr_R3:.2f}</span>
                        <span style="color:#ef4444;">Width (R3 - S3) = {curr_width:.2f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;width:100%;max-width:400px;">
                        <span>S3 = {curr_S3:.2f}</span><span>&nbsp;</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
