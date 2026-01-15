import streamlit as st
import pandas as pd
from datetime import timedelta
import plotly.graph_objects as go

# --- App title ---
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center; color: #2F4F4F;'>📊 Sunil's CPR, Camarilla & Golden Pivot Zone (GPZ) Calculator</h1>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center; color: #16a34a; font-size:32px; font-weight:600; margin-bottom:18px;'><b><i>Plan the trade ; Trade the plan</i></b></div>", unsafe_allow_html=True)

# ==========================================================
# --- Market Selection ---
col1, col2 = st.columns([1, 1])

with col1:
    market_type = st.radio(
        "Select Market Type:",
        ["Stock Market", "Bitcoin"],
        horizontal=True
    )
with col2:
    data_freq = st.radio(
        "Select Data Frequency:",
        ["Daily", "Weekly", "Monthly"],
        horizontal=True
    )

# label to use everywhere instead of hardcoded "Day"
if data_freq == "Daily":
    next_period_label = "next trading day"
    current_period_label = "Current Trading Day"
    prev_period_label = "Previous Trading Day"
elif data_freq == "Weekly":
    next_period_label = "next trading week"
    current_period_label = "Current Trading Week"
    prev_period_label = "Previous Trading Week"
else:
    next_period_label = "next trading month"
    current_period_label = "Current Trading Month"
    prev_period_label = "Previous Trading Month"

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

    df = df.sort_values("Date").reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    if len(df) < 2:
        st.warning("Need at least 2 trading days in the file.")
        st.stop()

    # ==========================================================
    # --- Resample for Weekly / Monthly ---
    if data_freq == "Weekly":
        # Resample to Friday for week ending OHLC
        df = (df.set_index("Date")
                .resample('W-FRI')
                .agg({'High':'max', 'Low':'min', 'Close':'last'})
                .reset_index())
        df["NextDate"] = df["Date"] + pd.offsets.Week(weekday=0)  # Next Monday
    elif data_freq == "Monthly":
        # Resample to month end for monthly OHLC
        df = (df.set_index("Date")
                .resample('M')
                .agg({'High':'max', 'Low':'min', 'Close':'last'})
                .reset_index())
        df["NextDate"] = df["Date"] + pd.offsets.MonthBegin(1)   # First day next month
    else:
        # Daily calculation — untouched
        df["NextDate"] = df["Date"] + timedelta(days=1)

    # ==========================================================
    # --- CPR CALCULATION ---
    df["Pivot_T_to_T1"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["BC_T_to_T1"] = (df["High"] + df["Low"]) / 2
    df["TC_T_to_T1"] = df["Pivot_T_to_T1"] + (df["Pivot_T_to_T1"] - df["BC_T_to_T1"])

    # Fix swapped TC/BC values
    mask_swap = df["BC_T_to_T1"] > df["TC_T_to_T1"]
    df.loc[mask_swap, ["TC_T_to_T1", "BC_T_to_T1"]] = df.loc[mask_swap, ["BC_T_to_T1", "TC_T_to_T1"]].values

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
        swap_note = f"<br><span style='color:red;'><i>⚠️ Note:</i> BC and TC were swapped due to BC > TC condition."
    else:
        swap_note = f"<br><i> </i> "

    curr_date = last_day_data["Date"]
    next_date = last_day_data["NextDate"]
    if market_type == "Stock Market" and data_freq == "Daily":
        while next_date.weekday() >= 5:
            next_date += timedelta(days=1)

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

    st.subheader(f"📊 {market_type} CPR Levels for {next_period_label} ({next_date.strftime('%A, %d-%b-%Y')})")
    st.dataframe(styled_df, use_container_width=True)

    # ==========================================================
    # --- Two-day pivot relationship ---
    df_cpr_ready = df.dropna(subset=["Pivot", "BC", "TC"]).copy()
    
    if len(df_cpr_ready) < 1:
         st.warning("Not enough data to compute T-day levels for relationship analysis.")
         sentiment, relationship, condition_text = "N/A", "N/A", "N/A"
         prev_pivot, prev_bc, prev_tc = 0.0, 0.0, 0.0
         prev_date = curr_date
    else:
        prev_row_cpr = df_cpr_ready.iloc[-1]
        prev_pivot, prev_bc, prev_tc = float(prev_row_cpr["Pivot"]), float(prev_row_cpr["BC"]), float(prev_row_cpr["TC"])
        prev_date = prev_row_cpr["Date"]
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
        elif curr_tc > prev_bc and curr_tc < prev_tc:
            relationship, sentiment = "Overlapping Lower Value Relationship", "Moderately Bearish"
            condition_text = f"Next Day BC ({curr_bc:.2f}) < Current Day BC ({prev_bc:.2f}) and TC ({curr_tc:.2f}) > Current Day BC ({prev_bc:.2f})"
        elif abs(curr_tc - prev_tc) < 0.05 and abs(curr_bc - prev_bc) < 0.05:
            relationship, sentiment = "Unchanged Value Relationship", "Sideways/Breakout"
            condition_text = f"Next and Current {data_freq.lower()} CPRs nearly equal"
        elif curr_tc > prev_tc and curr_bc < prev_bc:
            relationship, sentiment = "Outside Value Relationship", "Sideways"
            condition_text = f"Next {data_freq.lower()} range fully engulfs Current {data_freq.lower()} range"
        elif curr_tc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Inside Value Relationship", "Breakout"
            condition_text = f"Next {data_freq.lower()} range inside Current {data_freq.lower()} range"
        else:
            relationship, sentiment = "No Clear Relationship", "Neutral"
            condition_text = "N/A"

    next_tc_pivot_diff = next_tc - next_pivot
    next_pivot_bc_diff = next_pivot - next_bc
    prev_tc_pivot_diff = prev_tc - prev_pivot
    prev_pivot_bc_diff = prev_pivot - prev_bc

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

    st.markdown(f"""
        <div style="text-align:center;font-size:22px;font-weight:bold;background: linear-gradient(145deg, #f0f9ff, #ffffff);
        padding:22px;border-radius:15px;box-shadow: 0px 4px 8px rgba(0,0,0,0.08);margin-top:25px;border: 1px solid #d1d5db;">
        <div style="font-size:26px;color:#1E40AF;margin-bottom:10px;text-transform:uppercase;">
            🧭 Two {data_freq} Pivot Relationship Details
        </div>
        <div style="font-size:24px;color:#1f2937;margin-bottom:8px;">
            {relationship or '—'} →
            <span style="color:{sentiment_color}; font-weight:bold;">{sentiment or '—'}</span>
        </div>
        <span style="font-weight:bold;text-decoration:underline;font-size:19px;color:#1E3A8A;
        background-color:#DBEAFE;padding:3px 8px;border-radius:6px;display:inline-block;margin-bottom:5px;">
        📅 Details for {current_period_label} ({prev_date.strftime('%d-%b-%Y')})
        </span><br>
        <span style="font-weight:600;color:#374151;">Pivot Levels :</span>
        <span style="color:#1E40AF;font-size:22px">TC = {prev_tc:.2f}</span>, 
        <span style="color:#047857;font-size:22px">BC = {prev_bc:.2f}</span>, 
        <span style="color:#9333EA;font-size:22px">Pivot = {prev_pivot:.2f}</span><br>
        <span style="font-weight:600;color:#374151;">Pivot Width :</span>
        <span style="color:#DC2626;font-weight:bold;font-size:22px">TC - Pivot = {prev_tc_pivot_diff:.2f}</span>, 
        <span style="color:#16A34A;font-weight:bold;font-size:22px">Pivot - BC = {prev_pivot_bc_diff:.2f}</span><br><br>
        <span style="font-weight:bold;text-decoration:underline;font-size:19px;color:#1E3A8A;
            background-color:#DBEAFE;padding:3px 8px;border-radius:6px;display:inline-block;margin-bottom:5px;">
            📅 Details for {next_period_label.capitalize()} ({next_date.strftime('%A, %d-%b-%Y')})
            </span><br>          
            <span style="font-weight:600;color:#374151;">Pivot Levels :</span>
            <span style="color:#1E40AF;font-size:22px">TC = {next_tc:.2f}</span>, 
            <span style="color:#047857;font-size:22px">BC = {next_bc:.2f}</span>, 
            <span style="color:#9333EA;font-size:22px">Pivot = {next_pivot:.2f}</span><br>
            <span style="font-weight:600;color:#374151;">Pivot Width :</span>
            <span style="color:#DC2626;font-weight:bold;font-size:22px">TC - Pivot = {next_tc_pivot_diff:.2f}</span>, 
            <span style="color:#16A34A;font-weight:bold;font-size:22px">Pivot - BC = {next_pivot_bc_diff:.2f}</span><br><br>
            <i>Condition satisfied:</i> {condition_text or 'N/A'}
            {swap_note}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ==========================================================
    # --- CPR CHART ---
    df_trading = df.dropna(subset=["Pivot", "BC", "TC"]).copy()
    selected_days_cpr = st.slider("Select number of periods to display (CPR Levels)", 1, len(df_trading) + 1, min(7, len(df_trading)) + 1)
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
    fig_cpr.update_layout(title=f"CPR Levels (Historical + {next_period_label.capitalize()})", height=600,
                          template="plotly_white", xaxis_title="Date",
                          yaxis_title="Price", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_cpr, use_container_width=True)

    # ==========================================================
    # --- CAMARILLA CALCULATION ---
    df["Range"] = df["High"] - df["Low"]
    df["R4"] = df["Close"] + df["Range"] * 1.1 / 2
    df["R3"] = df["Close"] + df["Range"] * 1.1 / 4
    df["R2"] = df["Close"] + df["Range"] * 1.1 / 6
    df["R1"] = df["Close"] + df["Range"] * 1.1 / 12
    df["S1"] = df["Close"] - df["Range"] * 1.1 / 12
    df["S2"] = df["Close"] - df["Range"] * 1.1 / 6
    df["S3"] = df["Close"] - df["Range"] * 1.1 / 4
    df["S4"] = df["Close"] - df["Range"] * 1.1 / 2

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

    st.subheader(f"📊 {market_type} Camarilla Levels for {next_period_label} ({next_date.strftime('%A, %d-%b-%Y')})")
    st.dataframe(styled_camarilla, use_container_width=True)

    # --- CE TWO-DAY RELATIONSHIP (R3 & S3) ---
    df_camarilla_ready = df_camarilla.dropna(subset=["R3", "S3"]).copy()
    if len(df_camarilla_ready) < 2:
        st.warning("Not enough data for CE two-period relationship.")
    else:
        prev_row = df_camarilla_ready.iloc[-2]
        curr_row = df_camarilla_ready.iloc[-1]

        prev_R3, prev_S3 = prev_row["R3"], prev_row["S3"]
        curr_R3, curr_S3 = curr_row["R3"], curr_row["S3"]

        if curr_S3 > prev_R3:
            relationship, sentiment = f"CE Higher Value {data_freq} Relationship", "Bullish"
        elif curr_R3 > prev_R3 and curr_S3 < prev_R3 and curr_S3 > prev_S3:
            relationship, sentiment = f"CE Overlapping Higher Value {data_freq} Relationship", "Moderately Bullish"
        elif curr_R3 < prev_S3:
            relationship, sentiment = f"CE Lower Value {data_freq} Relationship", "Bearish"
        elif curr_R3 < prev_R3 and curr_S3 < prev_S3 and curr_R3 > prev_S3:
            relationship, sentiment = f"CE Overlapping Lower Value {data_freq} Relationship", "Moderately Bearish"
        elif abs(curr_R3 - prev_R3) < 0.05 and abs(curr_S3 - prev_S3) < 0.05:
            relationship, sentiment = f"CE Unchanged Value {data_freq} Relationship", "Sideways/Breakout"
        elif curr_R3 > prev_R3 and curr_S3 < prev_S3:
            relationship, sentiment = f"CE Outside Value {data_freq} Relationship", "Sideways"
        elif curr_R3 < prev_R3 and curr_S3 > prev_S3:
            relationship, sentiment = f"CE Inside Value {data_freq} Relationship", "Breakout"
        else :
            relationship, sentiment = "Not satisfying any of the conditions", "Unknown"

        curr_cm_diff = prev_R3 - prev_S3
        next_cm_diff = curr_R3 - curr_S3

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
                    🎯 Two-{data_freq} Camarilla Relationship
                </div>
                <div style="font-size:24px;color:#1f2937;margin-bottom:8px;">
                    {relationship} →
                    <span style="color:{sentiment_color};font-weight:bold;">{sentiment}</span>
                </div>
                <div style="font-size:15px;color:#374151;">
                    <span style="font-weight:bold;text-decoration:underline;font-size:19px;color:#1E3A8A;
                    background-color:#DBEAFE;padding:3px 8px;border-radius:6px;display:inline-block;margin-bottom:5px;">
                    📅 Details for {prev_period_label} ({prev_date.strftime('%d-%b-%Y')})
                    </span><br>
                    <span style="font-weight:600;color:#374151;">Prev :</span>
                    <span style="color:#1E40AF;font-size:22px">R3={prev_R3:.2f}</span>, 
                    <span style="color:#047857;font-size:22px">S3={prev_S3:.2f}</span>, 
                    <span style="font-weight:600;color:#374151;">Pivot Width :</span>
                    <span style="color:#DC2626;font-weight:bold;font-size:22px">Width (R3 - S3) ={curr_cm_diff:.2f}</span>
                    <br><br><br>
                    <span style="font-weight:bold;text-decoration:underline;font-size:19px;color:#1E3A8A;
                    background-color:#DBEAFE;padding:3px 8px;border-radius:6px;display:inline-block;margin-bottom:5px;">
                    📅 Details for {next_period_label.capitalize()} ({next_date.strftime('%A, %d-%b-%Y')})
                    </span><br>
                    <span style="font-weight:600;color:#374151;">Details :</span>
                    <span style="color:#1E40AF;font-size:22px">R3={next_R3:.2f}</span>, 
                    <span style="color:#047857;font-size:22px">S3={next_S3:.2f}</span>, 
                    <span style="font-weight:600;color:#374151;">Pivot Width :</span>
                    <span style="color:#DC2626;font-weight:bold;font-size:22px">Width (R3 - S3) ={next_cm_diff:.2f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # --- Camarilla Chart (ONLY R3 and S3) ---
    selected_days_cam = st.slider(f"Select number of periods to display (Camarilla R3/S3)", 1, len(df_camarilla), min(7, len(df_camarilla)))
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

    # ==========================================================
    # === GOLDEN PIVOT HOT ZONE (with conditions and comments) ===
    golden_pivot_map = {
        "Bullish": "#16a34a",
        "Bearish": "#dc2626",
        "Neutral": "#404040"
    }
    
    # Previous period's CPR
    prev_bc = float(df.iloc[-2]["BC_T_to_T1"])
    prev_tc = float(df.iloc[-2]["TC_T_to_T1"])
    prev_close = float(df.iloc[-2]["Close"])
    
    # Handle Open price (if not present, use Close as fallback)
    curr_open = last_day_data["Open"] if "Open" in last_day_data else last_day_data["Close"]
    curr_close = last_day_data["Close"]
    
    bearish_comment = ""
    bullish_comment = ""
    
    if next_tc >= next_R3 >= next_bc:
        golden_pivot_sentiment = "Bearish (GPZ)"
        golden_pivot_cond = "TC ≥ R3 ≥ BC"
        golden_pivot_comment = f"(TC ≥ R3 ≥ BC)<br>TC = {next_tc:.2f}, R3 = {next_R3:.2f}, BC = {next_bc:.2f}"
    
        first_fact = curr_open < next_bc or curr_open < next_tc
        second_fact = prev_close < prev_bc and prev_close < prev_tc
        third_fact = next_bc > curr_close
    
        bearish_comment = f"""
        <b>However, there are a couple of factors that must be in place in order for a "Sell the rip" opportunity to exist.<br>
        <b><u>First</u></b>, price should open the day below the central pivot range.<br>
        <span style="color:{'#dc2626' if first_fact else '#404040'};">(Close={curr_open:.2f}; CPR: BC={next_bc:.2f} TC={next_tc:.2f})</span><br>
        <b><u>Second</u></b>, the prior day's closing price should fall below the prior day's central pivot range.<br>
        <span style="font-size:24px; color:{'#dc2626' if third_fact else '#404040'};">2nd condition satisfied: {"Yes" if third_fact else "No"}</span>
        </b>
        """
    
    elif next_bc <= next_S3 <= next_tc:
        golden_pivot_sentiment = "Bullish (GPZ)"
        golden_pivot_cond = "BC ≤ S3 ≤ TC"
        golden_pivot_comment = f"(BC ≤ S3 ≤ TC)<br>BC = {next_bc:.2f}, S3 = {next_S3:.2f}, TC = {next_tc:.2f}"
    
        first_fact = curr_open > next_bc or curr_open > next_tc
        second_fact = prev_close > prev_bc and prev_close > prev_tc
        third_fact = next_tc < curr_close
    
        bullish_comment = f"""
        <b>However, there are a couple of factors that must be in place in order for a "buy the dip" opportunity to exist.<br>
        <b><u>First</u></b>, price should open the day above the central pivot range.<br>
        <span style="color:{'#16a34a' if first_fact else '#404040'};">(Close={curr_open:.2f}; CPR: BC={next_bc:.2f} TC={next_tc:.2f})</span><br>
        <b><u>Second</u></b>, the prior day's closing price should fall above the prior day's central pivot range.<br>
        <span style="font-size:24px; color:{'#16a34a' if third_fact else '#404040'};">2nd condition satisfied: {"Yes" if third_fact else "No"}</span><br><br>
        If both of these factors pass the test, the market is likely primed for another "buy the dip" opportunity (reverse for shorts).</b>
        """
    
    else:
        golden_pivot_sentiment = "Neutral"
        golden_pivot_cond = "No condition"
        golden_pivot_comment = f"No condition for golden pivot satisfied.<br>TC = {next_tc:.2f}, R3 = {next_R3:.2f}, BC = {next_bc:.2f}, S3 = {next_S3:.2f}"
    
    golden_pivot_color = golden_pivot_map.get(golden_pivot_sentiment, "#404040")
    
    st.markdown(f"""
        <div style="text-align:center;font-size:22px;font-weight:bold;
            background:linear-gradient(145deg,#f0f9ff,#ffffff);padding:22px;border-radius:15px;
            box-shadow:0px 4px 8px rgba(0,0,0,0.08);margin-top:25px;border:1px solid #d1d5db;">
            <div style="font-size:26px;color:#1E40AF;margin-bottom:10px;text-transform:uppercase;">
                🌟 Golden Pivot Hot Zone (GPZ)
            </div>
            <div style="font-size:20px;color:#16a34a;margin-bottom:10px;">
                <b><i>🌟😇🎵🌟 When this pattern occurs, Oceans are parted and Angels sing as you trade</i></b>
            </div>
            <div style="font-size:24px;color:#1f2937;margin-bottom:8px;">
                {golden_pivot_cond} →
                <span style="color:{golden_pivot_color};font-weight:bold;">{golden_pivot_sentiment}</span>
            </div>
            <div style="font-size:17px;color:{golden_pivot_color};margin-top:7px;">
                {golden_pivot_comment}
            </div>
            <div style="font-size:17px;color:#404040;margin-top:7px;">
                {bearish_comment if golden_pivot_sentiment == "Bearish (GPZ)" else ""}
                {bullish_comment if golden_pivot_sentiment == "Bullish (GPZ)" else ""}
        
    """, unsafe_allow_html=True)

    # ==========================================================
    # === DOUBLE PIVOT HOT ZONE (DPZ) ===
    # Using CPR (classic pivot) & Camarilla levels already computed above

    # tolerance as % of price (can tweak, e.g. 0.001 = 0.1%)
    tolerance_pct = 0.001

    # helper to check if two levels are within tolerance
    def is_within_tolerance(a, b, ref_price):
        if ref_price == 0:
            return False
        return abs(a - b) <= ref_price * tolerance_pct

    current_price_ref = last_day_data["Close"]

    dpz_messages = []
    dpz_type = "None"

    # --- Resistance DPZ: Classic vs Camarilla ---
    # 1) Classic R1 with Camarilla R3
    if is_within_tolerance(r1, next_R3, current_price_ref):
        dpz_messages.append(f"Classic R1 ({r1:.2f}) and Camarilla R3 ({next_R3:.2f}) are overlapping → Resistance DPZ")

    # 2) Classic R1 with Camarilla R4
    if is_within_tolerance(r1, next_R4, current_price_ref):
        dpz_messages.append(f"Classic R1 ({r1:.2f}) and Camarilla R4 ({next_R4:.2f}) are overlapping → Strong Resistance DPZ")

    # 3) Classic R2 with Camarilla R3
    if is_within_tolerance(r2, next_R3, current_price_ref):
        dpz_messages.append(f"Classic R2 ({r2:.2f}) and Camarilla R3 ({next_R3:.2f}) are overlapping → Resistance DPZ")

    # 4) Classic R2 with Camarilla R4
    if is_within_tolerance(r2, next_R4, current_price_ref):
        dpz_messages.append(f"Classic R2 ({r2:.2f}) and Camarilla R4 ({next_R4:.2f}) are overlapping → Very Strong Resistance DPZ")

    # 5) Classic Pivot with Camarilla R3/R4
    if is_within_tolerance(pivot, next_R3, current_price_ref):
        dpz_messages.append(f"Classic Pivot ({pivot:.2f}) and Camarilla R3 ({next_R3:.2f}) are overlapping → Resistance DPZ")
    if is_within_tolerance(pivot, next_R4, current_price_ref):
        dpz_messages.append(f"Classic Pivot ({pivot:.2f}) and Camarilla R4 ({next_R4:.2f}) are overlapping → Very Strong Resistance DPZ")

    # --- Support DPZ: Classic vs Camarilla ---
    # 6) Classic S1 with Camarilla S3/S4
    if is_within_tolerance(s1, next_S3, current_price_ref):
        dpz_messages.append(f"Classic S1 ({s1:.2f}) and Camarilla S3 ({next_S3:.2f}) are overlapping → Support DPZ")
    if is_within_tolerance(s1, next_S4, current_price_ref):
        dpz_messages.append(f"Classic S1 ({s1:.2f}) and Camarilla S4 ({next_S4:.2f}) are overlapping → Strong Support DPZ")

    # 7) Classic S2 with Camarilla S3/S4
    if is_within_tolerance(s2, next_S3, current_price_ref):
        dpz_messages.append(f"Classic S2 ({s2:.2f}) and Camarilla S3 ({next_S3:.2f}) are overlapping → Support DPZ")
    if is_within_tolerance(s2, next_S4, current_price_ref):
        dpz_messages.append(f"Classic S2 ({s2:.2f}) and Camarilla S4 ({next_S4:.2f}) are overlapping → Very Strong Support DPZ")

    # 8) Classic Pivot with Camarilla S3/S4
    if is_within_tolerance(pivot, next_S3, current_price_ref):
        dpz_messages.append(f"Classic Pivot ({pivot:.2f}) and Camarilla S3 ({next_S3:.2f}) are overlapping → Support DPZ")
    if is_within_tolerance(pivot, next_S4, current_price_ref):
        dpz_messages.append(f"Classic Pivot ({pivot:.2f}) and Camarilla S4 ({next_S4:.2f}) are overlapping → Strong Support DPZ")

    if dpz_messages:
        has_res = any("Resistance" in m for m in dpz_messages)
        has_sup = any("Support" in m for m in dpz_messages)
        if has_res and has_sup:
            dpz_type = "Mixed (Support & Resistance DPZ)"
            dpz_color = "#9333ea"
        elif has_res:
            dpz_type = "Resistance Double Pivot Hot Zone"
            dpz_color = "#dc2626"
        else:
            dpz_type = "Support Double Pivot Hot Zone"
            dpz_color = "#16a34a"

        dpz_html_lines = "<br>".join(dpz_messages)

        st.markdown(f"""
            <div style="text-align:center;font-size:22px;font-weight:bold;
                background:linear-gradient(145deg,#fef3c7,#ffffff);padding:22px;border-radius:15px;
                box-shadow:0px 4px 8px rgba(0,0,0,0.08);margin-top:25px;border:1px solid #fbbf24;">
                <div style="font-size:26px;color:#b45309;margin-bottom:10px;text-transform:uppercase;">
                    🔥 Double Pivot Hot Zone (DPZ)
                </div>
                <div style="font-size:20px;color:{dpz_color};margin-bottom:8px;">
                    {dpz_type}
                </div>
                <div style="font-size:17px;color:#111827;text-align:left;display:inline-block;">
                    {dpz_html_lines}
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style="text-align:center;font-size:20px;font-weight:bold;
                background:#f9fafb;padding:18px;border-radius:12px;border:1px dashed #d1d5db;margin-top:20px;">
                🔍 No Double Pivot Hot Zone (DPZ) detected for the next session within the current tolerance ({tolerance_pct*100:.2f}% of price).
            </div>
        """, unsafe_allow_html=True)





