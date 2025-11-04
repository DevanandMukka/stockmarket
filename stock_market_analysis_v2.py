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

    # Note flag for swapped BC/TC values
    swap_note = ""
    # if mask_swap.any():
    #     swapped_dates = df.loc[mask_swap, "Date"].dt.strftime("%d-%b-%Y").tolist()
    #     swap_note = f"<br><i>Note:</i> BC and TC were swapped on {', '.join(swapped_dates)} due to BC > TC condition."


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
        swap_note = f"<br><i>Note:</i> BC and TC were swapped due to BC > TC condition."

    curr_date = last_day_data["Date"]
    next_day = curr_date + timedelta(days=1)
    if market_type == "Stock Market":
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
    next_date = next_day

    # --- CPR R/S Levels ---
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

    # --- CPR Table ---
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
    # Fix: Use the T-day date and the CPR levels for the T day (calculated from T-1 data)
    # The T-day levels are found in the 'Pivot', 'BC', 'TC' columns of the LAST ROW (iloc[-1])
    # The date is the LAST ROW's date (iloc[-1]["Date"])
    
    df_cpr_ready = df.dropna(subset=["Pivot", "BC", "TC"]).copy()
    
    if len(df_cpr_ready) < 1:
         st.warning("Not enough data to compute T-day levels for relationship analysis.")
         # Fallback to display the T+1 table and graph only
         sentiment, relationship, condition_text = "N/A", "N/A", "N/A"
         prev_pivot, prev_bc, prev_tc = 0.0, 0.0, 0.0
         prev_date = curr_date # Use current date as placeholder
    else:
        # T-day levels (calculated from T-1 data, relevant for T day)
        prev_row_cpr = df_cpr_ready.iloc[-1] 
        prev_pivot, prev_bc, prev_tc = float(prev_row_cpr["Pivot"]), float(prev_row_cpr["BC"]), float(prev_row_cpr["TC"])
        prev_date = prev_row_cpr["Date"] # This is T-day's date!
    
        # T+1 levels (calculated from T data, relevant for T+1 day)
        curr_pivot, curr_bc, curr_tc = next_pivot, next_bc, next_tc 
    
        relationship, sentiment, condition_text = None, None, ""

        if curr_bc > prev_tc:
            relationship, sentiment = "Higher Value Relationship", "Bullish"
            condition_text = f"Next Day BC ({curr_bc:.2f}) > Current Day TC ({prev_tc:.2f})"
        elif curr_tc > prev_tc and curr_bc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Overlapping Higher Value Relationship", "Moderately Bullish"
            condition_text = f"Next Day TC ({curr_tc:.2f}) > Current Day TC ({prev_tc:.2f}) and BC between ranges"
        elif curr_tc < prev_bc:
            relationship, sentiment = "Lower Value Relationship", "Bearish"
            condition_text = f"Next Day TC ({curr_tc:.2f}) < Current Day BC ({prev_bc:.2f})"
        elif curr_bc < prev_bc and curr_tc > prev_bc:
            relationship, sentiment = "Overlapping Lower Value Relationship", "Moderately Bearish"
            condition_text = f"Next Day BC ({curr_bc:.2f}) < Current Day BC ({prev_bc:.2f}) and TC > Current Day BC"
        elif abs(curr_tc - prev_tc) < 0.05 and abs(curr_bc - prev_bc) < 0.05:
            relationship, sentiment = "Unchanged Value Relationship", "Sideways/Breakout"
            condition_text = f"Next Day and Current Day CPRs nearly equal"
        elif curr_tc > prev_tc and curr_bc < prev_bc:
            relationship, sentiment = "Outside Value Relationship", "Sideways"
            condition_text = f"Next Day range fully engulfs Current Day range"
        elif curr_tc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Inside Value Relationship", "Breakout"
            condition_text = f"Next Day range inside Current Day range"
        else:
            relationship, sentiment = "No Clear Relationship", "Neutral"
            condition_text = "N/A"

    color_map = {
        "Bullish": "#16a34a",
        "Moderately Bullish": "#22c55e",
        "Bearish": "#dc2626",
        "Moderately Bearish": "#ef4444",
        "Sideways/Breakout": "#2563eb",
        "Sideways": "#3b82f6",
        "Breakout": "#9333ea",
        "Neutral": "#9ca3af"
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
                <b>Current Trading Day ({prev_date.strftime('%d-%b-%Y')} Levels):</b> TC = {prev_tc:.2f}, BC = {prev_bc:.2f}, Pivot = {prev_pivot:.2f}<br>
                <b>Next Trading Day ({next_date.strftime('%d-%b-%Y')} Levels):</b> TC = {next_tc:.2f}, BC = {next_bc:.2f}, Pivot = {next_pivot:.2f}<br>
                <i>Condition satisfied:</i> {condition_text or 'N/A'}
                {swap_note}
            </div>
        </div>
    """, unsafe_allow_html=True)
    # =================================================================


    # ==========================================================
    # --- CPR CHART ---
    df_trading = df.dropna(subset=["Pivot", "BC", "TC"]).copy()
    selected_days_cpr = st.slider("Select number of days to display (CPR Levels)", 1, len(df_trading) + 1, min(7, len(df_trading)) + 1)
    df_plot_historical = df_trading.tail(selected_days_cpr - 1).copy()
    next_day_row = pd.DataFrame({"Date": [next_date], "Pivot": [next_pivot], "BC": [next_bc], "TC": [next_tc]})
    df_plot = pd.concat([df_plot_historical[["Date", "Pivot", "BC", "TC"]], next_day_row], ignore_index=True)

    fig_cpr = go.Figure()
    for _, row in df_plot.iterrows():
        date = row["Date"]
        x0, x1 = date - pd.Timedelta(hours=8), date + pd.Timedelta(hours=8)
        fig_cpr.add_trace(go.Scatter(x=[x0, x1], y=[row["TC"], row["TC"]],
                                     mode="lines", line=dict(color="red", width=2), name="TC"))
        fig_cpr.add_trace(go.Scatter(x=[x0, x1], y=[row["Pivot"], row["Pivot"]],
                                     mode="lines", line=dict(color="black", dash="dot"), name="Pivot"))
        fig_cpr.add_trace(go.Scatter(x=[x0, x1], y=[row["BC"], row["BC"]],
                                     mode="lines", line=dict(color="green", width=2), name="BC"))
    fig_cpr.update_layout(title="CPR Levels (Historical + Next Day)", height=600,
                          template="plotly_white", xaxis_title="Date",
                          yaxis_title="Price", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_cpr, use_container_width=True)

    # ==========================================================
    # --- CAMARILLA CALCULATION (Full Table, R4 to S4 + Range) ---
    df["Range"] = df["High"] - df["Low"]
    df["R4"] = df["Close"] + df["Range"] * 1.1 / 2
    df["R3"] = df["Close"] + df["Range"] * 1.1 / 4
    df["R2"] = df["Close"] + df["Range"] * 1.1 / 6
    df["R1"] = df["Close"] + df["Range"] * 1.1 / 12
    df["S1"] = df["Close"] - df["Range"] * 1.1 / 12
    df["S2"] = df["Close"] - df["Range"] * 1.1 / 6
    df["S3"] = df["Close"] - df["Range"] * 1.1 / 4
    df["S4"] = df["Close"] - df["Range"] * 1.1 / 2

    # Shift by one day
    for col in ["R1", "R2", "R3", "R4", "S1", "S2", "S3", "S4"]:
        df[col] = df[col].shift(1)

    rng = last_day_data["High"] - last_day_data["Low"]
    next_R4 = last_day_data["Close"] + rng * 1.1 / 2
    next_R3 = last_day_data["Close"] + rng * 1.1 / 4
    next_R2 = last_day_data["Close"] + rng * 1.1 / 6
    next_R1 = last_day_data["Close"] + rng * 1.1 / 12
    next_S1 = last_day_data["Close"] - rng * 1.1 / 12
    next_S2 = last_day_data["Close"] - rng * 1.1 / 6
    next_S3 = last_day_data["Close"] - rng * 1.1 / 4
    next_S4 = last_day_data["Close"] - rng * 1.1 / 2

    next_row = pd.DataFrame({
        "Date": [next_date], "Range": [rng],
        "R4": [next_R4], "R3": [next_R3], "R2": [next_R2], "R1": [next_R1],
        "S1": [next_S1], "S2": [next_S2], "S3": [next_S3], "S4": [next_S4]
    })

    df_camarilla = pd.concat([df[["Date", "Range", "R4", "R3", "R2", "R1", "S1", "S2", "S3", "S4"]], next_row], ignore_index=True)

    # --- Camarilla Table ---
    camarilla_table = pd.DataFrame({
        "Metric": ["Range", "R4", "R3", "R2", "R1", "S1", "S2", "S3", "S4"],
        "Value": [rng, next_R4, next_R3, next_R2, next_R1, next_S1, next_S2, next_S3, next_S4]
    })

    def color_camarilla(val, metric):
        if "Range" in metric:
            return 'color: blue; font-weight: bold;'
        elif "S" in metric:
            return 'color: green; font-weight: bold;'
        elif "R" in metric:
            return 'color: red; font-weight: bold;'
        return 'color: black; font-weight: bold;'

    styled_camarilla = camarilla_table.style.format({"Value": "{:.2f}"}) \
        .apply(lambda col: [color_camarilla(v, m) for v, m in zip(camarilla_table["Value"], camarilla_table["Metric"])], axis=0)

    st.subheader(f"📊 {market_type} Camarilla Levels for next day ({next_date.strftime('%A, %d-%b-%Y')})")
    st.dataframe(styled_camarilla, use_container_width=True)

        # ==========================================================
    # --- CE TWO-DAY RELATIONSHIP (R3 & S3) ---
    df_camarilla_ready = df_camarilla.dropna(subset=["R3", "S3"]).copy()
    if len(df_camarilla_ready) < 2:
        st.warning("Not enough data for CE two-day relationship.")
    else:
        prev_row = df_camarilla_ready.iloc[-2]
        curr_row = df_camarilla_ready.iloc[-1]

        prev_R3, prev_S3 = prev_row["R3"], prev_row["S3"]
        curr_R3, curr_S3 = curr_row["R3"], curr_row["S3"]

        # relationship, sentiment = "N/A", "N/A"

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
        else :
            relationship, sentiment = "Not satisfying any of the conditions", "Unknown"

        color_map = {
            "Bullish": "#16a34a", "Moderately Bullish": "#22c55e",
            "Bearish": "#dc2626", "Moderately Bearish": "#ef4444",
            "Sideways/Breakout": "#2563eb", "Sideways": "#3b82f6",
            "Breakout": "#9333ea", "Neutral": "#9ca3af"
        }
        sentiment_color = color_map.get(sentiment, "#111827")

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
                <div style="font-size:15px;color:#374151;">
                    <b>Prev Day:</b> R3={prev_R3:.2f}, S3={prev_S3:.2f} <br>
                    <b>Current Day:</b> R3={curr_R3:.2f}, S3={curr_S3:.2f}
                </div>
            </div>
        """, unsafe_allow_html=True)



    # ==========================================================
    # --- Camarilla Chart (ONLY R3 and S3) ---
    selected_days_cam = st.slider("Select number of days to display (Camarilla R3/S3)",
                                  1, len(df_camarilla), min(7, len(df_camarilla)))
    df_plot_cam = df_camarilla.tail(selected_days_cam)

    fig_cam = go.Figure()
    for _, row in df_plot_cam.iterrows():
        date = row["Date"]
        x0, x1 = date - pd.Timedelta(hours=8), date + pd.Timedelta(hours=8)
        fig_cam.add_trace(go.Scatter(
            x=[x0, x1], y=[row["R3"], row["R3"]],
            mode="lines", line=dict(color="red", width=2), name="R3"
        ))
        fig_cam.add_trace(go.Scatter(
            x=[x0, x1], y=[row["S3"], row["S3"]],
            mode="lines", line=dict(color="green", width=2), name="S3"
        ))

    fig_cam.update_layout(title=f"{market_type} Camarilla Levels (R3 & S3 Only)",
                          height=600, template="plotly_white",
                          xaxis_title="Date", yaxis_title="Price",
                          xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_cam, use_container_width=True)






