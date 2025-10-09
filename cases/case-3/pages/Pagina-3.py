import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
import plotly.express as px
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import numpy as np
import requests
import os

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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.dirname(BASE_DIR)

gemeente_data = pd.read_csv(os.path.join(CASE_DIR,"laadpunten_per_gemeente.csv"))
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
df = pd.read_csv(os.path.join(CASE_DIR,"top20_gemeenten_laadpalen_2025.csv"))
df = df.sort_values("Laadpalen_per_1000_inwoners", ascending=False)
laatste_maand_chart = "oktober 2025"

# Plotly Express bar chart
fig = px.bar(
    df,
    x="Gemeente",
    y="Laadpalen_per_1000_inwoners",
    text=df["Laadpalen_per_1000_inwoners"].round(2),
    labels={"Laadpalen_per_1000_inwoners": "Laadpalen per 1000 inwoners"},
    title=f"Aantal reguliere publieke laadpalen per 1000 inwoners in de 20 grootste gemeenten ({laatste_maand_chart}, Laadinfrastructuur)",
)
 
# Layout aanpassen
fig.update_traces(textposition='outside')
fig.update_layout(
    xaxis_tickangle=-45,
    xaxis_title="Gemeente",
    yaxis_title="Laadpalen per 1000 inwoners",
    yaxis=dict(dtick=1),
    uniformtext_minsize=10,
    uniformtext_mode='hide',
    template='plotly_white'
)
 
# In Streamlit tonen
st.plotly_chart(fig)