import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from dashboard import load_data
from sidebar import render_sidebar

# --- Helper functions for parsing ---
def parse_price(price):
    """Remove currency symbols and convert to numeric."""
    if pd.isna(price):
        return 0.0
    price_str = str(price).replace(",", ".")
    price_str = "".join(c for c in price_str if c.isdigit() or c == ".")
    try:
        return float(price_str)
    except ValueError:
        return 0.0

def parse_percentage(pct):
    """Remove % sign and convert to numeric."""
    if pd.isna(pct):
        return 0.0
    pct_str = str(pct).replace("%","")
    try:
        return float(pct_str)
    except ValueError:
        return 0.0

# --- Load data ---
df = load_data()

if df.empty:
    st.warning("No data available")
    st.stop()

# --- Clean data ---
df["price"] = df.get("price", 0).apply(parse_price)
df["salePercentage"] = df.get("salePercentage", 0).apply(parse_percentage)
df["salePrice"] = (df["price"] * (1 - df["salePercentage"] / 100)).round(2)
df["salePercentage"] = df["salePercentage"].abs()  # ensure positive discount

# --- UI ---
st.title("Price & Discounts")

# KPI: price ↔ discount correlation
st.subheader("Correlation between price and discount")
correlation = df["price"].corr(df["salePercentage"])
st.metric(label="Price ↔ Discount", value=f"{correlation:.2f}")

# Plot selectbox
plot_choice = st.selectbox(
    "Select the plot you want to view:",
    ["Scatterplot Price vs Discount", "Boxplot Original Price vs Sale Price"]
)

if plot_choice == "Scatterplot Price vs Discount":
    fig, ax = plt.subplots(figsize=(8,6))
    sns.scatterplot(x="price", y="salePercentage", data=df, alpha=0.5, ax=ax)
    sns.regplot(x="price", y="salePercentage", data=df, scatter=False, ax=ax, color='red')
    ax.set_xlabel("Price (€)")
    ax.set_ylabel("Discount (%)")
    ax.set_title("Price vs Discount")
    st.pyplot(fig)

elif plot_choice == "Boxplot Original Price vs Sale Price":
    df_melt = df.melt(value_vars=["price", "salePrice"], 
                      var_name="Type", 
                      value_name="Price (€)")
    # Translate column names to English
    df_melt["Type"] = df_melt["Type"].map({"price": "Original Price", "salePrice": "Sale Price"})
    
    fig, ax = plt.subplots(figsize=(8,6))
    sns.boxplot(x="Type", y="Price (€)", data=df_melt, ax=ax, palette="Set2")
    ax.set_ylabel("Price (€)")
    ax.set_xlabel("")
    ax.set_title("Comparison of Original Price and Sale Price")
    st.pyplot(fig)

# Render sidebar with dataset info and refresh button
render_sidebar()
