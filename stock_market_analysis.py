import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Central Pivot Range (CPR) Calculator with Support & Resistance Levels")

# File uploader
uploaded_file = st.file_uploader("Upload Excel file with columns: Date, High, Low, Close", type=["xlsx"])

if uploaded_file:
    # Read Excel file
    df = pd.read_excel(uploaded_file)

    # Ensure correct column names
    required_cols = {"Date", "High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        st.error(f"Excel must contain columns: {required_cols}")
    else:
        # Sort by date just in case
        df = df.sort_values("Date")

        # CPR Calculation for next day
        df["Pivot"] = (df["High"] + df["Low"] + df["Close"]) / 3
        df["BC"] = (df["High"] + df["Low"]) / 2
        df["TC"] = 2 * df["Pivot"] - df["BC"]

        # Calculate support/resistance
        df["R1"] = 2 * df["Pivot"] - df["Low"]
        df["S1"] = 2 * df["Pivot"] - df["High"]
        df["R2"] = df["Pivot"] + (df["High"] - df["Low"])
        df["S2"] = df["Pivot"] - (df["High"] - df["Low"])
        df["R3"] = df["R1"]  + (df["High"] - df["Low"])
        df["S3"] = df["S1"]  + (df["High"] - df["Low"])
        df["R4"] = df["R3"] + (df["R2"] - df["R1"])
        df["S4"] = df["S3"] - (df["S1"] - df["S2"])
        df["R5"] = df["R4"] + (df["R2"] - df["Pivot"])
        df["S5"] = df["S4"] - (df["S1"] - df["S2"])

        # Shift to next day
        for col in ["Pivot", "BC", "TC", "R1", "S1", "R2", "S2", "R3", "S3", "R4", "S4", "R5", "S5"]:
            df[f"{col}_next"] = df[col].shift(1)

        st.subheader("Data with CPR & Support/Resistance Levels")
        st.dataframe(df.tail(10))

        # Plot latest CPR with stock price
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df["Date"], df["Close"], label="Close Price", marker="o")

        # CPR levels
        ax.plot(df["Date"], df["Pivot_next"], label="Pivot (Next Day)", linestyle="--")
        ax.plot(df["Date"], df["BC_next"], label="BC (Next Day)", linestyle="--")
        ax.plot(df["Date"], df["TC_next"], label="TC (Next Day)", linestyle="--")
        ax.fill_between(df["Date"], df["BC_next"], df["TC_next"], color="orange", alpha=0.2, label="CPR Range")

        # Support & resistance levels
        for level in ["R1", "S1", "R2", "S2", "R3", "S3", "R4", "S4", "R5", "S5"]:
            ax.plot(df["Date"], df[f"{level}_next"], linestyle=":", label=f"{level} (Next Day)")

        ax.set_title("Next Day Central Pivot Range (CPR) with Support & Resistance Levels")
        ax.legend(loc="best", fontsize=8)
        plt.xticks(rotation=45)

        st.pyplot(fig)