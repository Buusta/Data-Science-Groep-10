import streamlit as st
import pandas as pd
import geopandas as gpd
import json
import pydeck as pdk
import requests
import os
import matplotlib.pyplot as plt
import numpy as np

# -------------------------------
# Pagina-instellingen
# -------------------------------
st.set_page_config(
    page_title="Laadpalen Nederland",
    page_icon="🔌",
    layout="wide"
)

# -------------------------------
# Functies
# -------------------------------
@st.cache_data(ttl=3600)
def fetch_data(url, as_dataframe=True):
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    if as_dataframe:
        return pd.json_normalize(data)
    else:
        return data

def normalize_name(name):
    return str(name).strip().lower().replace(" ", "").replace("-", "").replace("'", "")

# -------------------------------
# Laad gemeente-geojson
# -------------------------------
geojson_url = "https://cartomap.github.io/nl/wgs84/gemeente_2023.geojson"
gdf = gpd.read_file(geojson_url)

# -------------------------------
# Laad gemeente-data
# -------------------------------
gemeente_data = pd.read_csv(os.path.join(os.getcwd(), "laadpunten_per_gemeente.csv"))
gemeente_data.columns = gemeente_data.columns.str.strip()

# -------------------------------
# Definieer laatste maand voor analyse
# -------------------------------
laatste_maand = "December 2024"

# -------------------------------
# Selecteer alleen kolommen van de laatste maand voor reguliere publieke laadpalen
# -------------------------------
publieke_kolommen = [
    col for col in gemeente_data.columns
    if laatste_maand in col and "Regulier Publiek" in col
]

# Tel deze kolommen bij elkaar op
gemeente_data['Aantal_Laadpalen_Publiek'] = gemeente_data[publieke_kolommen].sum(axis=1)

# -------------------------------
# Normaliseer gemeentenaam en voeg aantal laadpalen toe aan GeoDataFrame
# -------------------------------
gemeente_map = {normalize_name(name): val for name, val in zip(gemeente_data['Gemeenten'], gemeente_data['Aantal_Laadpalen_Publiek'])}
gdf['statnaam_norm'] = gdf['statnaam'].apply(normalize_name)
gdf['aantal_laadpalen'] = gdf['statnaam_norm'].map(lambda x: gemeente_map.get(x, 0)).astype(int)

# -------------------------------
# Bereken kleuren voor gemeenten
# -------------------------------
max_count = gdf['aantal_laadpalen'].max() if not gdf.empty else 1

def compute_color(count, max_count):
    if max_count == 0:
        return [200, 200, 200, 180]
    ratio = count / max_count
    r = 0
    g = int(255 * (1 - ratio))
    b = int(255 * ratio)
    return [r, g, b, 180]

gdf['fill_color'] = gdf['aantal_laadpalen'].apply(lambda x: compute_color(x, max_count))
gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.001, preserve_topology=True)
geojson_data_for_pydeck = json.loads(gdf.to_json())

# -------------------------------
# Streamlit UI
# -------------------------------
kaart_keuze = st.sidebar.radio("Kies welke kaart je wilt zien:", ["Steekproef", "Choropleth"])
kaart_hoogte = 1000

# -------------------------------
# Laadpalen per gemeente (GeoJSON / choropleth)
# -------------------------------
if kaart_keuze == "Choropleth":
    st.title("Laadpalen per gemeente")
    
    stappen = 5
    stap_waarden = [int(i * max_count / (stappen - 1)) for i in range(stappen)]
    width_px = 300

    st.markdown(
        f"""
        <div style='position:absolute; top:30px; left:10px; z-index:9999;
                    background-color:white; padding:10px; border-radius:5px;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.3); width:{width_px}px;'>
            <b>Aantal reguliere publieke laadpalen ({laatste_maand})</b><br>
            <div style='height:20px; width:100%; 
                        background: linear-gradient(to right, rgba(0,255,0,0.6), rgba(0,0,255,0.6)); 
                        position: relative; margin-top:5px;'>
                {"".join([f"<div style='position:absolute; left:{i/(stappen-1)*100}%; top:20px; width:1px; height:8px; background:black; transform: translateX(-0.5px);'></div>" for i in range(stappen)])}
            </div>
            <div style='display:flex; justify-content: space-between; font-size:12px; margin-top:3px;'>
                {"".join([f"<span>{val}</span>" for val in stap_waarden])}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    geojson_layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson_data_for_pydeck,
        get_fill_color="properties.fill_color",
        get_line_color=[0, 0, 0, 150],
        pickable=True,
        auto_highlight=True,
        stroked=True,
        filled=True
    )

    view_state = pdk.ViewState(latitude=52.379189, longitude=5, zoom=7, pitch=0)
    r = pdk.Deck(
        layers=[geojson_layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{statnaam}</b><br>Aantal reguliere publieke laadpalen: {aantal_laadpalen}",
            "style": {"color": "black", "backgroundColor": "white"}
        },
        map_style="mapbox://styles/mapbox/light-v10"
    )
    st.pydeck_chart(r, use_container_width=True, height=kaart_hoogte)

# -------------------------------
# Individuele laadpalen (Scatterplot)
# -------------------------------
else:
    st.title("Steekproef van 10.000 willekeurig gekozen laadpalen in Nederland")
    
    ocm_url = "https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=10000&compact=true&verbose=false&key=93b912b5-9d70-4b1f-960b-fb80a4c9c017"
    laadpalen = fetch_data(ocm_url)
    laadpalen.columns = laadpalen.columns.str.replace('.', '_', regex=False)
    laadpalen = laadpalen[laadpalen['AddressInfo_Latitude'].notna() & laadpalen['AddressInfo_Longitude'].notna()]

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=laadpalen,
        get_position=["AddressInfo_Longitude", "AddressInfo_Latitude"],
        get_fill_color=[0, 150, 255, 180],
        get_radius=500,
        radius_scale=1,
        radius_min_pixels=5,
        radius_max_pixels=50,
        pickable=True,
    )
    view_state = pdk.ViewState(latitude=52.379189, longitude=5, zoom=7, pitch=0)
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{AddressInfo_Title}</b><br>{AddressInfo_Town}<br>Aantal laadpunten: {NumberOfPoints}<br>Kosten: {UsageCost}",
            "style": {"color": "black", "backgroundColor": "white"}
        },
        map_style="mapbox://styles/mapbox/light-v10"
    )
    st.pydeck_chart(r, use_container_width=True, height=kaart_hoogte)

# -------------------------------
# Top 20 grootste gemeenten bar chart
# -------------------------------
df = pd.read_csv("top20_gemeenten_laadpalen_2025.csv")

# Sorteer op ratio (Laadpalen_per_1000_inwoners)
df = df.sort_values("Laadpalen_per_1000_inwoners", ascending=False)

# Laatste maand (voor titel)
laatste_maand = "oktober 2025"

# Plot maken
fig, ax = plt.subplots(figsize=(14, 6))
bars = ax.bar(df["Gemeente"], df["Laadpalen_per_1000_inwoners"])

# Labeling
ax.set_ylabel("Laadpalen", fontsize=12)
ax.set_xlabel("Gemeente", fontsize=12)
ax.set_title(f"Aantal reguliere publieke laadpalen per 1000 inwoners in de 20 grootste gemeenten ({laatste_maand}, Laadinfrastructuur)", fontsize=14)

# X-as labels
ax.set_xticks(range(len(df)))
ax.set_xticklabels(df["Gemeente"], rotation=45, ha="right", fontsize=10)

# Y-as ticks en grid
max_ratio = int(np.ceil(df["Laadpalen_per_1000_inwoners"].max()))
ax.set_yticks(np.arange(0, max_ratio + 1, 1))
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Toon waarden boven de balken
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height + 0.1, f"{height:.2f}", 
            ha='center', va='bottom', fontsize=9)

# Plot tonen in Streamlit
st.pyplot(fig)
