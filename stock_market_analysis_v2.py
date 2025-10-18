import streamlit as st
import pandas as pd
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

    # 1. CALCULATE CPR LEVELS FOR THE NEXT DAY (T+1)
    df["Pivot_T_to_T1"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["BC_T_to_T1"] = (df["High"] + df["Low"]) / 2
    df["TC_T_to_T1"] = df["Pivot_T_to_T1"] + (df["Pivot_T_to_T1"] - df["BC_T_to_T1"])
    
    # Ensure TC is always the upper value and BC the lower value
    mask_swap = df["BC_T_to_T1"] > df["TC_T_to_T1"]
    df.loc[mask_swap, ["TC_T_to_T1", "BC_T_to_T1"]] = df.loc[mask_swap, ["BC_T_to_T1", "TC_T_to_T1"]].values
    
    # Shift the T+1 levels back one row so they align with the date they are used on.
    df["Pivot"] = df["Pivot_T_to_T1"].shift(1)
    df["BC"] = df["BC_T_to_T1"].shift(1)
    df["TC"] = df["TC_T_to_T1"].shift(1)
    
    # The last row of the original H, L, C data (T day) is used to calculate the CPR for the *next* day (T+1).
    last_day_data = df.iloc[-1]
    
    # 2. CALCULATE T+1 LEVELS (Based on Last Row of Data)
    next_pivot = (last_day_data["High"] + last_day_data["Low"] + last_day_data["Close"]) / 3
    next_bc = (last_day_data["High"] + last_day_data["Low"]) / 2
    next_tc = next_pivot + (next_pivot - next_bc)
    
    if next_bc > next_tc:
        next_tc, next_bc = next_bc, next_tc
        
    # 3. Determine T+1 Date
    curr_date = last_day_data["Date"] # Last date in the file (T day)
    next_day = curr_date + timedelta(days=1)
    while next_day.weekday() >= 5:  # skip weekends
        next_day += timedelta(days=1)
    next_date = next_day # The date for which the new levels are valid (T+1)

    # --- Support/resistance levels for T+1 ---
    pivot = next_pivot
    bc = next_bc
    tc = next_tc
    high = last_day_data["High"] # Using T day high/low for R/S for T+1
    low = last_day_data["Low"]
    
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

    # --- Result table for T+1 ---
    result_df = pd.DataFrame({
        "Metric": ["R5", "R4", "R3", "R2", "R1",
                   "CPR - Top Central", "Pivot", "CPR - Bottom Central",
                   "S1", "S2", "S3", "S4", "S5"],
        "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
    })
    
    # --- Style result table (Unchanged) ---
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

    st.subheader(f"Stock Levels for {next_date.strftime('%A, %d-%b-%Y')} (Calculated from {curr_date.strftime('%d-%b-%Y')})")
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
            condition_text = f"T+1 BC ({curr_bc:.2f}) > T TC ({prev_tc:.2f})"
        elif curr_tc > prev_tc and curr_bc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Overlapping Higher Value Relationship", "Moderately Bullish"
            condition_text = f"T+1 TC ({curr_tc:.2f}) > T TC ({prev_tc:.2f}) and BC between ranges"
        elif curr_tc < prev_bc:
            relationship, sentiment = "Lower Value Relationship", "Bearish"
            condition_text = f"T+1 TC ({curr_tc:.2f}) < T BC ({prev_bc:.2f})"
        elif curr_bc < prev_bc and curr_tc > prev_bc:
            relationship, sentiment = "Overlapping Lower Value Relationship", "Moderately Bearish"
            condition_text = f"T+1 BC ({curr_bc:.2f}) < T BC ({prev_bc:.2f}) and TC > T BC"
        elif abs(curr_tc - prev_tc) < 0.05 and abs(curr_bc - prev_bc) < 0.05:
            relationship, sentiment = "Unchanged Value Relationship", "Sideways/Breakout"
            condition_text = f"T+1 and T CPRs nearly equal"
        elif curr_tc > prev_tc and curr_bc < prev_bc:
            relationship, sentiment = "Outside Value Relationship", "Sideways"
            condition_text = f"T+1 range fully engulfs T range"
        elif curr_tc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Inside Value Relationship", "Breakout"
            condition_text = f"T+1 range inside T range"
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
                <b>Previous Trading Day ({prev_date.strftime('%d-%b-%Y')} Levels):</b> TC = {prev_tc:.2f}, BC = {prev_bc:.2f}, Pivot = {prev_pivot:.2f}<br>
                <b>Next Trading Day ({next_date.strftime('%d-%b-%Y')} Levels):</b> TC = {next_tc:.2f}, BC = {next_bc:.2f}, Pivot = {next_pivot:.2f}<br>
                <i>Condition satisfied:</i> {condition_text or 'N/A'}
            </div>
        </div>
    """, unsafe_allow_html=True)
    # =================================================================

    # 4. Graph Logic (Unchanged from previous fix)
    df_trading = df.dropna(subset=["Pivot", "BC", "TC"]).copy()
    max_days = len(df_trading)
    default_days = min(7, max_days)

    selected_days = st.slider(
        "Select number of trading days to display on chart (CPR Levels)",
        min_value=1,
        max_value=max_days + 1, 
        value=default_days + 1, 
        step=1
    )

    df_plot_historical = df_trading.tail(selected_days - 1).copy()
    
    next_day_row = pd.DataFrame({
        "Date": [next_date],
        "Pivot": [next_pivot],
        "BC": [next_bc],
        "TC": [next_tc]
    })
    
    df_plot = pd.concat([df_plot_historical[["Date", "Pivot", "BC", "TC"]], next_day_row], ignore_index=True)
    
    fig = go.Figure()
    
    hist_tc_added, hist_pivot_added, hist_bc_added = False, False, False

    # Plot historical CPR lines (T-N to T levels)
    for i, row in df_plot.iloc[:-1].iterrows():
        date = row["Date"]
        x0, x1 = date - pd.Timedelta(hours=8), date + pd.Timedelta(hours=8)
        tc_val, pivot_val, bc_val = float(row["TC"]), float(row["Pivot"]), float(row["BC"])
        
        show_tc_legend = not hist_tc_added
        show_pivot_legend = not hist_pivot_added
        show_bc_legend = not hist_bc_added

        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[tc_val, tc_val],
            mode="lines", line=dict(color="red", width=2),
            name="Historical TC" if show_tc_legend else None,
            hovertemplate=f"Levels for {date.strftime('%d-%b-%Y')}<br>TC: {tc_val:.2f}<extra></extra>",
            showlegend=show_tc_legend
        ))
        if show_tc_legend: hist_tc_added = True

        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[pivot_val, pivot_val],
            mode="lines", line=dict(color="black", width=2, dash="dot"),
            name="Historical Pivot" if show_pivot_legend else None,
            hovertemplate=f"Levels for {date.strftime('%d-%b-%Y')}<br>Pivot: {pivot_val:.2f}<extra></extra>",
            showlegend=show_pivot_legend
        ))
        if show_pivot_legend: hist_pivot_added = True

        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[bc_val, bc_val],
            mode="lines", line=dict(color="green", width=2),
            name="Historical BC" if show_bc_legend else None,
            hovertemplate=f"Levels for {date.strftime('%d-%b-%Y')}<br>BC: {bc_val:.2f}<extra></extra>",
            showlegend=show_bc_legend
        ))
        if show_bc_legend: hist_bc_added = True

    # --- Plot T+1 day CPR (actual calculated levels) ---
    next_x0, next_x1 = next_date - pd.Timedelta(hours=8), next_date + pd.Timedelta(hours=8)

    # Highlight T+1 CPR range
    fig.add_shape(
        type="rect",
        x0=next_x0, x1=next_x1,
        y0=next_bc, y1=next_tc,
        fillcolor="rgba(173, 216, 230, 0.4)",
        line=dict(color="rgba(65, 105, 225, 0.6)", width=2),
        layer="below",
        name="T+1 CPR Range",
        legendgroup='t_plus_1_range',
        showlegend=False
    )
    
    # Draw T+1 CPR lines with explicit legend entries
    fig.add_trace(go.Scatter(
        x=[next_x0, next_x1], y=[next_tc, next_tc],
        mode="lines", line=dict(color="darkred", width=3, dash="dash"),
        name="T+1 TC",
        hovertemplate=f"T+1 TC ({next_date.strftime('%d-%b-%Y')}): {next_tc:.2f}<extra></extra>",
        showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[next_x0, next_x1], y=[next_pivot, next_pivot],
        mode="lines", line=dict(color="darkblue", width=3, dash="dot"),
        name="T+1 Pivot",
        hovertemplate=f"T+1 Pivot ({next_date.strftime('%d-%b-%Y')}): {next_pivot:.2f}<extra></extra>",
        showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[next_x0, next_x1], y=[next_bc, next_bc],
        mode="lines", line=dict(color="darkgreen", width=3, dash="dash"),
        name="T+1 BC",
        hovertemplate=f"T+1 BC ({next_date.strftime('%d-%b-%Y')}): {next_bc:.2f}<extra></extra>",
        showlegend=True
    ))
    
    # Add a custom invisible trace for the CPR Range Area legend entry
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='lines',
        line=dict(color='rgba(65, 105, 225, 0.6)', width=4, dash='solid'),
        name='T+1 CPR Area',
        showlegend=True
    ))


    # --- Layout ---
    fig.update_layout(
        title=f"CPR Levels (Last {selected_days - 1} Trading Days + Levels for {next_date.strftime('%d-%b-%Y')})",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=700,
        template="plotly_white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig, use_container_width=True)
