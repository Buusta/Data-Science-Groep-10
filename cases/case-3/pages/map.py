import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import numpy as np
import requests

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
gemeente_data = pd.read_csv("laadpunten_per_gemeente.csv")
gemeente_data.columns = gemeente_data.columns.str.strip()

# -------------------------------
# Laatste maand
# -------------------------------
laatste_maand = "December 2024"

# -------------------------------
# Bereken aantal reguliere publieke laadpalen
# -------------------------------
publieke_kolommen = [col for col in gemeente_data.columns if laatste_maand in col and "Regulier Publiek" in col]
gemeente_data['Aantal_Laadpalen_Publiek'] = gemeente_data[publieke_kolommen].sum(axis=1)

# Normaliseer namen en voeg toe aan GeoDataFrame
gemeente_map = {normalize_name(name): val for name, val in zip(gemeente_data['Gemeenten'], gemeente_data['Aantal_Laadpalen_Publiek'])}
gdf['statnaam_norm'] = gdf['statnaam'].apply(normalize_name)
gdf['aantal_laadpalen'] = gdf['statnaam_norm'].map(lambda x: gemeente_map.get(x, 0)).astype(int)

# -------------------------------
# Sidebar keuze
# -------------------------------
kaart_keuze = st.sidebar.radio("Kies welke kaart je wilt zien:", ["Choropleth", "Scatterplot"])

# -------------------------------
# Choropleth-kaart
# -------------------------------
if kaart_keuze == "Choropleth":
    st.title("Laadpalen per gemeente")
    
    m = folium.Map(location=[52.379189, 5], zoom_start=7)
    
    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=['statnaam', 'aantal_laadpalen'],
        key_on='feature.properties.statnaam',
        fill_color='YlGnBu',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=f"Aantal reguliere publieke laadpalen"
    ).add_to(m)
    
    for _, row in gdf.iterrows():
        folium.GeoJson(
            row['geometry'],
            style_function=lambda x: {'fillColor': 'transparent', 'color': 'black', 'weight':1},
            tooltip=f"{row['statnaam']}: {row['aantal_laadpalen']} laadpalen"
        ).add_to(m)
    
    st_folium(m, width=1000, height=700)

# -------------------------------
# Scatterplot van individuele laadpalen
# -------------------------------
else:
    st.title("Steekproef van 1.000 willekeurig gekozen laadpalen in Nederland")
    
    # Haal data op
    ocm_url = "https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=1000&compact=true&verbose=false&key=93b912b5-9d70-4b1f-960b-fb80a4c9c017"
    response = requests.get(ocm_url).json()
    
    # Flatten JSON met underscores
    laadpalen = pd.json_normalize(response, sep="_")
    laadpalen = laadpalen[laadpalen['AddressInfo_Latitude'].notna() & laadpalen['AddressInfo_Longitude'].notna()]
    
    m = folium.Map(location=[52.379189, 5], zoom_start=7)
    
    for _, row in laadpalen.iterrows():
        folium.CircleMarker(
            location=[row['AddressInfo_Latitude'], row['AddressInfo_Longitude']],
            radius=3,
            color='blue',
            fill=True,
            fill_opacity=0.6,
            popup=f"{row.get('AddressInfo_Title','N/A')}<br>{row.get('AddressInfo_Town','N/A')}<br>Aantal laadpunten: {row.get('NumberOfPoints','N/A')}<br>Kosten: {row.get('UsageCost','N/A')}"
        ).add_to(m)
    
    st_folium(m, width=1000, height=700)

# -------------------------------
# Top 20 grootste gemeenten bar chart
# -------------------------------
df = pd.read_csv("top20_gemeenten_laadpalen_2025.csv")
df = df.sort_values("Laadpalen_per_1000_inwoners", ascending=False)
laatste_maand_chart = "oktober 2025"

fig, ax = plt.subplots(figsize=(14, 6))
bars = ax.bar(df["Gemeente"], df["Laadpalen_per_1000_inwoners"])
ax.set_ylabel("Laadpalen per 1000 inwoners", fontsize=12)
ax.set_xlabel("Gemeente", fontsize=12)
ax.set_title(f"Aantal reguliere publieke laadpalen per 1000 inwoners in de 20 grootste gemeenten ({laatste_maand_chart}, Laadinfrastructuur)", fontsize=14)
ax.set_xticks(range(len(df)))
ax.set_xticklabels(df["Gemeente"], rotation=45, ha="right", fontsize=10)
max_ratio = int(np.ceil(df["Laadpalen_per_1000_inwoners"].max()))
ax.set_yticks(np.arange(0, max_ratio + 1, 1))
ax.grid(axis='y', linestyle='--', alpha=0.7)
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height + 0.1, f"{height:.2f}", ha='center', va='bottom', fontsize=9)
st.pyplot(fig)
