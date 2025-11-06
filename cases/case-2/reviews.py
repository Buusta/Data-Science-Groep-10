from dashboard import load_data
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sidebar import render_sidebar

# --- Helper functie voor review mapping ---
def map_review(series):
    review_mapping = {
        "Overwhelmingly Positive": 100,
        "Very Positive": 90,
        "Positive": 75,
        "Mostly Positive": 60,
        "Mixed": 50,
        "Mostly Negative": 40,
        "Negative": 25,
        "Very Negative": 10,
        "Overwhelmingly Negative": 0
    }
    return series.astype(str).str.strip().map(review_mapping)

# --- Data laden ---
df = load_data()

st.title("Publisher Reviews")

# --- Maak numerieke reviewkolommen aan ---
df["recentReviews_num"] = map_review(df["recentReviews"]) if "recentReviews" in df.columns else np.nan
df["allReviews_num"] = map_review(df["allReviews"]) if "allReviews" in df.columns else np.nan

# --- Toggle voor type review ---
review_type = st.selectbox("Kies reviewtype:", ["recentReviews", "allReviews"])
review_col = "recentReviews_num" if review_type == "recentReviews" else "allReviews_num"

# --- Filter rijen zonder reviewscore voor geselecteerde kolom ---
df_clean = df.dropna(subset=[review_col]).copy()
df_clean[review_col] = df_clean[review_col].astype(float)

# --- Selecteer publisher kolommen ---
publisher_cols = [col for col in df_clean.columns if col.startswith("publishers/")]

# --- Melt zodat elke publisher in één kolom staat ---
df_publishers = df_clean.melt(
    id_vars=[review_col],
    value_vars=publisher_cols,
    var_name="publisher_col",
    value_name="publisher"
).dropna(subset=["publisher"])

# --- Interactief filter voor top N publishers ---
top_n = st.slider("Aantal publishers tonen", min_value=5, max_value=50, value=20)
top_publishers = df_publishers["publisher"].value_counts().nlargest(top_n).index
df_top = df_publishers[df_publishers["publisher"].isin(top_publishers)]

# --- Bereken gemiddelde review per publisher ---
avg_reviews = df_top.groupby("publisher")[review_col].mean().sort_values(ascending=False)

# --- Plotten ---
fig, ax = plt.subplots(figsize=(10,6))
sns.barplot(
    x=avg_reviews.values,
    y=avg_reviews.index,
    palette="tab20",
    ax=ax
)

ax.set_xlim(0, 100)
ax.set_xticks(range(0, 101, 10))
ax.set_xlabel(f"Gemiddelde {review_type}")
ax.set_ylabel("Publisher")
ax.set_title(f"Gemiddelde {review_type} per publisher (top {top_n})")

# --- Legenda verwijderen veilig ---
if ax.legend_ is not None:
    ax.legend_.remove()

st.pyplot(fig)

render_sidebar()