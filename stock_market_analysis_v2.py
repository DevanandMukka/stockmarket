import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

st.title("Sunil's CPR Calculator")

# File uploader
uploaded_file = st.file_uploader("Upload Excel File with Stock Data (Date, High, Low, Close)", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Read Excel file
    df = pd.read_excel(uploaded_file)

    # Ensure columns exist
    required_cols = {"Date", "High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        st.error(f"Excel file must contain columns: {required_cols}")
    else:

       # Sort by date just in case
        df = df.sort_values("Date")

        # Take the last row for calculations
        last_row = df.iloc[-1]
        high = last_row["High"]
        low = last_row["Low"]
        close = last_row["Close"]

        # Pivot Point
        pivot = (high + low + close) / 3

        # CPR calculations
        bc = (high + low) / 2  # Bottom Central
        tc = pivot + (pivot - bc)  # Top Central

        # Supports and Resistances
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = r1 + (high - low)
        s3 = s1 + (high - low)
        r4 = r3 + (r2 - r1)
        s4 = s3 - (s1 - s2)
        r5 = r4 + (r2 - r1)
        s5 = s4 - (s1 - s2)

        # Create DataFrame for display
        data = {
            "Metric": ["R5", "R4", "R3", "R2", "R1", 
		               "CPR - Top Central" , "Pivot", "CPR - Bottom Central", 
                       "S1", "S2", "S3", "S4", "S5"],
            "Value": [r5, r4, r3, r2, r1, tc, pivot, bc, s1, s2, s3, s4, s5]
        }
        result_df = pd.DataFrame(data)

        # Display results
        st.subheader("Upcoming Day Levels (Next Day after Last Row in File)")
        st.table(result_df)

        # ---- Download Buttons ----
        # st.subheader("Download Results")
        
        # # CSV download
        # csv = result_df.to_csv(index=False).encode("utf-8")
        # st.download_button(
        #     label="Download as CSV",
        #     data=csv,
        #     file_name="pivot_levels.csv",
        #     mime="text/csv",
        # )

        # # Excel download
        # output = BytesIO()
        # with pd.ExcelWriter(output, engine="openpyxl") as writer:
        #     result_df.to_excel(writer, sheet_name="Pivot_Levels", index=False)
        # excel_data = output.getvalue()

        # st.download_button(
        #     label="Download as Excel",
        #     data=excel_data,
        #     file_name="pivot_levels.xlsx",
        #     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        # )

        # # ---- Chart days selector ----
        # st.subheader("Price Chart with CPR & Pivot Levels")
        # num_days = st.slider("Select number of past days to display", min_value=5, max_value=100, value=20, step=5)

        # df_plot = df.tail(num_days)
        # fig = go.Figure(data=[go.Candlestick(
        #     x=df_plot["Date"],
        #     open=df_plot["Close"],  # using Close if Open not available
        #     high=df_plot["High"],
        #     low=df_plot["Low"],
        #     close=df_plot["Close"],
        #     name="Price"
        # )])

        # # Add pivot, CPR, support, and resistance lines
        # levels = {
        #     "Pivot": pivot, "TC": tc, "BC": bc,
        #     "S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5,
        #     "R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5
        # }

        # for name, val in levels.items():
        #     fig.add_hline(y=val, line_dash="dot", annotation_text=name, annotation_position="right")

        # fig.update_layout(
        #     xaxis_title="Date",
        #     yaxis_title="Price",
        #     template="plotly_white",
        #     height=600
        # )

        # st.plotly_chart(fig, use_container_width=True)



