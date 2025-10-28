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
    mask_swap = df["BC_T_to_T1"] > df["TC_T_to_T1"]
    df.loc[mask_swap, ["TC_T_to_T1", "BC_T_to_T1"]] = df.loc[mask_swap, ["BC_T_to_T1", "TC_T_to_T1"]].values
    df["Pivot"] = df["Pivot_T_to_T1"].shift(1)
    df["BC"] = df["BC_T_to_T1"].shift(1)
    df["TC"] = df["TC_T_to_T1"].shift(1)

    last_day_data = df.iloc[-1]
    next_pivot = (last_day_data["High"] + last_day_data["Low"] + last_day_data["Close"]) / 3
    next_bc = (last_day_data["High"] + last_day_data["Low"]) / 2
    next_tc = next_pivot + (next_pivot - next_bc)
    if next_bc > next_tc:
        next_tc, next_bc = next_bc, next_tc

    curr_date = last_day_data["Date"]
    next_day = curr_date + timedelta(days=1)
    # For stock market skip weekends, for bitcoin include weekends
    if market_type == "Stock Market":
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
    next_date = next_day

    pivot = next_pivot
    bc = next_bc
    tc = next_tc
    high = last_day_data["High"]
    low = last_day_data["Low"]

    # CPR R/S Levels
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

    # ==========================================================
    # --- CAMARILLA CALCULATION (ONLY R3 & S3) ---
    df["Range"] = df["High"] - df["Low"]
    df["R3"] = df["Close"] + df["Range"] * 1.1 / 4
    df["S3"] = df["Close"] - df["Range"] * 1.1 / 4
    df["R3"] = df["R3"].shift(1)
    df["S3"] = df["S3"].shift(1)

    rng = last_day_data["High"] - last_day_data["Low"]
    next_R3 = last_day_data["Close"] + rng * 1.1 / 4
    next_S3 = last_day_data["Close"] - rng * 1.1 / 4

    next_row = pd.DataFrame({
        "Date": [next_date], "Range": [rng],
        "R3": [next_R3], "S3": [next_S3]
    })

    df_camarilla = pd.concat([df[["Date", "Range", "R3", "S3"]], next_row], ignore_index=True)

    # --- Camarilla Table ---
    camarilla_table = pd.DataFrame({
        "Metric": ["Range", "R3", "S3"],
        "Value": [rng, next_R3, next_S3]
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
    # --- Camarilla Chart (ONLY R3 and S3) ---
    selected_days_cam = st.slider("Select number of days to display (Camarilla R3/S3)",
                                  1, len(df_camarilla), min(7, len(df_camarilla)))
    df_plot_cam = df_camarilla.tail(selected_days_cam)

    fig_cam = go.Figure()
    for _, row in df_plot_cam.iterrows():
        date = row["Date"]
        x0, x1 = date - pd.Timedelta(hours=8), date + pd.Timedelta(hours=8)
        fig_cam.add_trace(go.Scatter(
            x=[x0, x1],
            y=[row["R3"], row["R3"]],
            mode="lines",
            line=dict(color="red", width=2),
            name="R3"
        ))
        fig_cam.add_trace(go.Scatter(
            x=[x0, x1],
            y=[row["S3"], row["S3"]],
            mode="lines",
            line=dict(color="green", width=2),
            name="S3"
        ))

    fig_cam.update_layout(title=f"{market_type} Camarilla Levels (R3 & S3 Only)",
                          height=600, template="plotly_white",
                          xaxis_title="Date", yaxis_title="Price",
                          xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_cam, use_container_width=True)
