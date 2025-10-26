import streamlit as st
import pandas as pd
from datetime import timedelta
import plotly.graph_objects as go

# --- App setup ---
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center; color: #2F4F4F;'>📊 Sunil's CPR & Camerilla Calculator</h1>", unsafe_allow_html=True)

# --- File uploader ---
uploaded_file = st.file_uploader("Upload Excel File with Stock Data (Date, High, Low, Close)", type=["xlsx", "xls"])

if uploaded_file is None:
    st.info("Please upload an Excel file with columns: Date, High, Low, Close.")
    st.stop()

# --- Read and validate ---
try:
    df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Could not read uploaded file: {e}")
    st.stop()

required_cols = {"Date", "High", "Low", "Close"}
if not required_cols.issubset(df.columns):
    st.error(f"Excel file must contain columns: {required_cols}")
    st.stop()

# --- Data prep ---
df = df.sort_values("Date").reset_index(drop=True)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"])
if len(df) < 2:
    st.warning("Need at least 2 trading days in the file to compute relationships.")
    st.stop()

# === CPR CALCULATION ===
df["Pivot_T_to_T1"] = (df["High"] + df["Low"] + df["Close"]) / 3
df["BC_T_to_T1"] = (df["High"] + df["Low"]) / 2
df["TC_T_to_T1"] = df["Pivot_T_to_T1"] + (df["Pivot_T_to_T1"] - df["BC_T_to_T1"])

mask_swap = df["BC_T_to_T1"] > df["TC_T_to_T1"]
df.loc[mask_swap, ["TC_T_to_T1", "BC_T_to_T1"]] = df.loc[mask_swap, ["BC_T_to_T1", "TC_T_to_T1"]].values

df["Pivot"] = df["Pivot_T_to_T1"].shift(1)
df["BC"] = df["BC_T_to_T1"].shift(1)
df["TC"] = df["TC_T_to_T1"].shift(1)

last_day_data = df.iloc[-1]
curr_date = last_day_data["Date"]
next_day = curr_date + timedelta(days=1)
while next_day.weekday() >= 5:
    next_day += timedelta(days=1)
next_date = next_day

# --- CPR T+1 ---
pivot = (last_day_data["High"] + last_day_data["Low"] + last_day_data["Close"]) / 3
bc = (last_day_data["High"] + last_day_data["Low"]) / 2
tc = pivot + (pivot - bc)
if bc > tc: tc, bc = bc, tc
high, low = last_day_data["High"], last_day_data["Low"]

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

# --- Camerilla Calculation (H1–H6, L1–L6) ---
range_ = high - low
H1 = close_H = last_day_data["Close"]
H1 = close_H + (range_ * 1.1 / 12)
H2 = close_H + (range_ * 1.1 / 6)
H3 = close_H + (range_ * 1.1 / 4)
H4 = close_H + (range_ * 1.1 / 2)
H5 = (high / low) * close_H
H6 = (H5 - H4) + H5

L1 = close_H - (range_ * 1.1 / 12)
L2 = close_H - (range_ * 1.1 / 6)
L3 = close_H - (range_ * 1.1 / 4)
L4 = close_H - (range_ * 1.1 / 2)
L5 = close_H - (H5 - close_H)
L6 = close_H - (H6 - close_H)

# --- Tabs for CPR & Camerilla ---
tab1, tab2 = st.tabs(["📏 CPR Levels", "🎯 Camerilla Levels"])

with tab1:
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
        else:
            return 'color: black; font-weight: bold;'

    styled_df = result_df.style.format({"Value": "{:.2f}"}).apply(
        lambda col: [color_metrics(v, m) for v, m in zip(result_df["Value"], result_df["Metric"])], axis=0
    ).set_properties(**{"font-size": "16px", "text-align": "center"})

    st.subheader(f"CPR Levels for {next_date.strftime('%A, %d-%b-%Y')} (from {curr_date.strftime('%d-%b-%Y')})")
    st.dataframe(styled_df, use_container_width=True)

    # --- Two-day relationship logic (from your docx) ---
    df_cpr_ready = df.dropna(subset=["Pivot", "BC", "TC"]).copy()
    relationship, sentiment, condition_text = "N/A", "N/A", ""

    if len(df_cpr_ready) >= 1:
        prev = df_cpr_ready.iloc[-1]
        prev_tc, prev_bc = prev["TC"], prev["BC"]
        curr_tc, curr_bc = tc, bc

        if curr_bc > prev_tc:
            relationship, sentiment = "Higher Value Relationship", "Bullish"
        elif curr_tc > prev_tc and curr_bc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Overlapping Higher Value Relationship", "Moderately Bullish"
        elif curr_tc < prev_bc:
            relationship, sentiment = "Lower Value Relationship", "Bearish"
        elif curr_bc < prev_bc and curr_tc > prev_bc:
            relationship, sentiment = "Overlapping Lower Value Relationship", "Moderately Bearish"
        elif abs(curr_tc - prev_tc) < 0.05 and abs(curr_bc - prev_bc) < 0.05:
            relationship, sentiment = "Unchanged Value Relationship", "Sideways/Breakout"
        elif curr_tc > prev_tc and curr_bc < prev_bc:
            relationship, sentiment = "Outside Value Relationship", "Sideways"
        elif curr_tc < prev_tc and curr_bc > prev_bc:
            relationship, sentiment = "Inside Value Relationship", "Breakout"

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

    st.markdown(f"""
        <div style="text-align:center; padding:18px; border-radius:15px;
                    background: linear-gradient(145deg, #f0f9ff, #ffffff);
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-top:20px;">
            <div style="font-size:26px; font-weight:bold; color:#1E40AF;">🧭 Two-Day Pivot Relationship</div>
            <div style="font-size:22px; color:#111;">
                {relationship} →
                <span style="color:{color_map.get(sentiment, '#111')}; font-weight:bold;">{sentiment}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- CPR Chart ---
    df_plot = df_cpr_ready.tail(7).copy()
    next_row = pd.DataFrame({"Date": [next_date], "Pivot": [pivot], "BC": [bc], "TC": [tc]})
    df_plot = pd.concat([df_plot[["Date", "Pivot", "BC", "TC"]], next_row])

    fig = go.Figure()
    for col, color in zip(["TC", "Pivot", "BC"], ["red", "black", "green"]):
        fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot[col], mode="lines+markers", name=col, line=dict(color=color)))

    fig.update_layout(title="CPR Levels Over Time", height=600, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    # --- Camerilla Table ---
    cam_df = pd.DataFrame({
        "Metric": ["H6", "H5", "H4", "H3", "H2", "H1", "L1", "L2", "L3", "L4", "L5", "L6"],
        "Value": [H6, H5, H4, H3, H2, H1, L1, L2, L3, L4, L5, L6]
    })
    st.subheader(f"Camerilla Levels for {next_date.strftime('%A, %d-%b-%Y')}")
    st.dataframe(cam_df.style.format({"Value": "{:.2f}"}), use_container_width=True)

    # --- Camerilla Chart ---
    fig2 = go.Figure()
    for i, row in cam_df.iterrows():
        fig2.add_trace(go.Scatter(
            x=[next_date - pd.Timedelta(hours=8), next_date + pd.Timedelta(hours=8)],
            y=[row["Value"], row["Value"]],
            mode="lines",
            line=dict(width=2),
            name=row["Metric"]
        ))

    fig2.update_layout(title="Camerilla Levels", height=600, template="plotly_white")
    st.plotly_chart(fig2, use_container_width=True)
