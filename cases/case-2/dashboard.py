import pandas as pd
import numpy as np
import requests
from datetime import datetime
import os
import streamlit as st
import time
import matplotlib.pyplot as plt
from sidebar import render_sidebar

# --- Config ---
API_TOKEN = "apify_api_0ak6aJo3hdcmSO2I37o9QgIu0E7YfO1S2Hpb"
ACT_ID = "m0uka~steam-store-scraper"
STEAM_URL = "https://store.steampowered.com/search/?filter=topsellers"
MAX_GAMES = 200
LOCAL_CSV = "games.csv"

# --- Helper functies ---
def parse_date(c):
    if pd.isna(c):
        return np.nan
    c = str(c).strip()
    if c.startswith("Q"):
        q, year = c.split()
        q_num = int(q[1])
        month = 3 * (q_num - 1) + 1
        return datetime(int(year), month, 1)
    try:
        return datetime.strptime(c, "%b %d, %Y")
    except ValueError:
        return np.nan

def parse_price(price):
    if pd.isna(price):
        return 0.0
    price_str = str(price).replace(",", ".")
    price_str = "".join(c for c in price_str if c.isdigit() or c == ".")
    try:
        return float(price_str)
    except ValueError:
        return 0.0

def parse_percentage(pct):
    if pd.isna(pct):
        return 0.0
    pct_str = str(pct).replace("%","")
    try:
        return float(pct_str)
    except ValueError:
        return 0.0

def flatten_list_columns(df, list_cols, max_items=20):
    for col in list_cols:
        if col in df.columns:
            for i in range(max_items):
                df[f"{col}/{i}"] = df[col].apply(lambda x: x[i] if isinstance(x, list) and i < len(x) else np.nan)
            df.drop(columns=[col], inplace=True)
    return df

def flatten_languages(df, languages_list):
    if 'languages' not in df.columns:
        return df
    for lang in languages_list:
        for typ in ['interface','sound','subtitles']:
            df[f'languages/{lang}/{typ}'] = df['languages'].apply(
                lambda x: x.get(lang, {}).get(typ) if isinstance(x, dict) else np.nan
            )
    df.drop(columns=['languages'], inplace=True)
    return df

# --- Scraper functie ---
@st.cache_data(show_spinner=True)
def fetch_latest_data(steam_url=STEAM_URL):
    run_url = f"https://api.apify.com/v2/acts/{ACT_ID}/runs?token={API_TOKEN}"
    payload = {"startUrls": [{"url": steam_url}], "maxItems": MAX_GAMES}
    r = requests.post(run_url, json=payload)
    r.raise_for_status()
    
    run_id = r.json()["data"]["id"]
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={API_TOKEN}"
    dataset_url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={API_TOKEN}"

    total_wait = 0
    max_wait = 120
    while total_wait < max_wait:
        resp = requests.get(status_url).json()
        status = resp["data"]["status"]
        if status in ["SUCCEEDED", "FAILED", "ABORTED"]:
            break
        time.sleep(5)
        total_wait += 5

    if status != "SUCCEEDED":
        return pd.DataFrame()

    results = requests.get(dataset_url).json()
    df = pd.DataFrame(results)

    list_cols = ['developers','features','genres','popularTags','publishers','supportedPlatforms']
    df = flatten_list_columns(df, list_cols)
    
    languages_needed = ["English", "French", "German", "Spanish - Spain"]
    df = flatten_languages(df, languages_needed)
    
    return df

# --- Data laden ---
@st.cache_data(show_spinner=True)
def load_data(use_csv=True):
    if use_csv and os.path.exists(LOCAL_CSV):
        df = pd.read_csv(LOCAL_CSV)
    else:
        df = fetch_latest_data()
        if not df.empty:
            df.to_csv(LOCAL_CSV, index=False)
    
    if df.empty:
        return df

    df["price"] = df.get("price", 0).apply(parse_price)
    df["salePercentage"] = df.get("salePercentage", 0).apply(parse_percentage)
    df["salePrice"] = (df["price"] * (1 - df["salePercentage"]/100)).round(2)

    if "releaseDate" in df.columns:
        df["releaseDate"] = df["releaseDate"].replace("Coming soon", np.nan).apply(parse_date)
    else:
        df["releaseDate"] = np.nan

    return df

# --- Classificatie ---
def classify_game_type(df):
    feature_cols = [col for col in df.columns if col.startswith("features/")]
    if not feature_cols:
        df["Type"] = np.nan
        return df

    multiplayer_keywords = [
        "Online Co-op", "Online PvP", "Cross-Platform Multiplayer",
        "LAN Co-op", "LAN PvP", "Shared/Split Screen Co-op",
        "Shared/Split Screen PvP", "MMO"
    ]

    def classify_row_type(row):
        features = [str(row[col]) for col in feature_cols if pd.notna(row[col])]
        has_single = any("Single-player" in f for f in features)
        has_multi = any(f in multiplayer_keywords for f in features)
        if has_single and has_multi:
            return "Mixed"
        elif has_single:
            return "Single-player"
        elif has_multi:
            return "Multiplayer"
        else:
            return np.nan

    df["Type"] = df.apply(classify_row_type, axis=1)
    return df

def classify_platform(row):
    """
    Classify the game platform based on supportedPlatforms columns.
    Returns 'Multiple' if more than one of Windows, Mac, Linux is supported.
    """
    platform_cols = ['supportedPlatforms/0', 'supportedPlatforms/1', 'supportedPlatforms/2']
    platforms = [str(row[col]) for col in platform_cols if col in row and pd.notna(row[col])]
    
    # Keep only valid platforms
    valid_platforms = [p for p in platforms if p in ["windows", "mac", "linux"]]
    
    if not valid_platforms:
        return np.nan
    
    unique_platforms = set(valid_platforms)
    
    if len(unique_platforms) > 1:
        return "Multiple"
    else:
        return unique_platforms.pop()

# --- Pie chart ---
def show_distribution(df, choice="Game Type"):
    """
    Shows a pie chart based on either Game Type or Platform.
    """
    if choice == "Game Type":
        df = classify_game_type(df)
        col_name = "Type"
        title = "Game Types"
    elif choice == "Platform":
        df["PlatformType"] = df.apply(classify_platform, axis=1)
        col_name = "PlatformType"
        title = "Supported Platforms"
    else:
        st.warning("Invalid choice for pie chart.")
        return

    counts = df[col_name].value_counts()
    if counts.empty:
        st.warning(f"No data available for {title} pie chart.")
        return

    st.subheader(title)
    fig, ax = plt.subplots()
    ax.pie(
        counts,
        labels=counts.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=['#66b3ff','#99ff99','#ffcc99', '#ff9999', '#ffcc66']  # more colors if needed
    )
    ax.axis('equal')
    st.pyplot(fig)

# --- UI ---
df = load_data()
st.title("Game Types & Features")
from sidebar import render_sidebar  
render_sidebar()

if not df.empty:
    # Add selectbox to switch between distributions
    distribution_choice = st.selectbox("Select distribution to display:", ["Game Type", "Platform"])
    show_distribution(df, distribution_choice)
else:
    st.warning("No data available for dashboard.")

st.write(df.head())