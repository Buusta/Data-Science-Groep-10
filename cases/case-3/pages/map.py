import streamlit as st
import pandas as pd
import geopandas as gpd
import json
import pydeck as pdk
import requests
import os


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
    return str(name).strip().lower().replace(" ", "")

# -------------------------------
# Laadt individuele laadpalen op bij OpenChargeMap
# -------------------------------
ocm_url = "https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=10000&compact=true&verbose=false&key=93b912b5-9d70-4b1f-960b-fb80a4c9c017"
laadpalen = fetch_data(ocm_url)
laadpalen.columns = laadpalen.columns.str.replace('.', '_', regex=False)
laadpalen = laadpalen[laadpalen['AddressInfo_Latitude'].notna() & laadpalen['AddressInfo_Longitude'].notna()]

# -------------------------------
# Laadt gemeente-geojson
# -------------------------------
geojson_url = "https://cartomap.github.io/nl/wgs84/gemeente_2023.geojson"
gdf = gpd.read_file(geojson_url)

# -------------------------------
# Laad gemeente-data
# -------------------------------
gemeente_data = pd.read_csv(f"{os.getcwd()}\laadpunten_per_gemeente.csv")
gemeente_data.columns = gemeente_data.columns.str.strip()  # verwijder spaties

# -------------------------------
# Bereken totaal aantal publieke laadpalen voor de laatste maand
# -------------------------------
laatste_maand = "August 2025"

# Selecteer alleen kolommen van de laatste maand met "Publiek"
type_kolommen = [col for col in gemeente_data.columns 
                 if laatste_maand in col and "Publiek" in col]

# Tel deze kolommen bij elkaar op
gemeente_data['Aantal_Laadpalen'] = gemeente_data[type_kolommen].sum(axis=1)

# -------------------------------
# Naam normalisatie en mapping
# -------------------------------
gemeente_map = {normalize_name(name): name for name in gemeente_data['Gemeenten']}
gdf['statnaam_norm'] = gdf['statnaam'].apply(normalize_name)

# Voeg aantal laadpalen toe aan GeoDataFrame
gdf['aantal_laadpalen'] = gdf['statnaam_norm'].map(
    lambda x: gemeente_data.loc[gemeente_data['Gemeenten'] == gemeente_map.get(x, ""), 'Aantal_Laadpalen'].sum()
)
gdf['aantal_laadpalen'] = gdf['aantal_laadpalen'].fillna(0).astype(int)

# -------------------------------
# Bereken kleuren voor gemeenten
# -------------------------------
max_count = gdf['aantal_laadpalen'].max() if not gdf.empty else 1

def compute_color(count, max_count):
    if max_count == 0:
        return [200, 200, 200, 180]  # fallback lichtgrijs
    ratio = count / max_count
    r = 0
    g = int(255 * (1 - ratio))  # meer laadpalen → minder groen
    b = int(255 * ratio)        # meer laadpalen → meer blauw
    return [r, g, b, 180]

gdf['fill_color'] = gdf['aantal_laadpalen'].apply(lambda x: compute_color(x, max_count))
gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.001, preserve_topology=True)
geojson_data_for_pydeck = json.loads(gdf.to_json())

st.title("Laadpalen in Nederland")
kaart_keuze = st.radio("Kies welke kaart je wilt zien:", ["Laadpalenkaart", "Laadpalen per gemeente"])
kaart_hoogte = 1000

# -------------------------------
# Laadpalen per gemeente
# -------------------------------
if kaart_keuze == "Laadpalen per gemeente":
    # Gradient legend
    stappen = 5
    stap_waarden = [int(i * max_count / (stappen - 1)) for i in range(stappen)]
    width_px = 300

    st.markdown(
        f"""
        <div style='position:absolute; top:30px; left:10px; z-index:9999;
                    background-color:white; padding:10px; border-radius:5px;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.3); width:{width_px}px;'>
            <b>Aantal laadpalen ({laatste_maand}, laadinfrastuctuur)</b><br>
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

    # PyDeck layer
    geojson_layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson_data_for_pydeck,
        get_fill_color="properties.fill_color",
        get_line_color=[0,0,0,150],
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
            "html": "<b>{statnaam}</b><br>Aantal laadpalen: {aantal_laadpalen}",
            "style": {"color": "black", "backgroundColor": "white"}
        }
        map_style="mapbox://styles/mapbox/light-v10"
    )
    st.pydeck_chart(r, use_container_width=True, height=kaart_hoogte)

# -------------------------------
# Laadpalenkaart (individuele locaties)
# -------------------------------
else:
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
