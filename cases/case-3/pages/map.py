import streamlit as st
import requests
import pandas as pd
import geopandas as gpd
import json
import pydeck as pdk

st.set_page_config(
    page_title="Laadpalen Nederland",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded"
)

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


# Laadt de nederlandse laadpalen op bij ocm
ocm_url = "https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=10000&compact=true&verbose=false&key=93b912b5-9d70-4b1f-960b-fb80a4c9c017"
laadpalen = fetch_data(ocm_url)
laadpalen.columns = laadpalen.columns.str.replace('.', '_', regex=False)
laadpalen = laadpalen[laadpalen['AddressInfo_Latitude'].notna() & laadpalen['AddressInfo_Longitude'].notna()]

# Laadt gemeenten GeoJSON
geojson_url = "https://cartomap.github.io/nl/wgs84/gemeente_2023.geojson"
geojson_data = fetch_data(geojson_url, as_dataframe=False)


# Zorgt ervoor dat alle namen consistent zijn
gemeente_map = {normalize_name(f['properties']['statnaam']): f['properties']['statnaam']
                for f in geojson_data['features']}

laadpalen['gemeente_norm'] = laadpalen['AddressInfo_Town'].apply(normalize_name)
laadpalen['gemeente_officieel'] = laadpalen['gemeente_norm'].map(gemeente_map)
laadpalen = laadpalen[laadpalen['gemeente_officieel'].notna()]

st.title("Laadpalen in Nederland")
kaart_keuze = st.radio("Kies welke kaart je wilt zien:", ["Laadpalenkaart", "Laadpalen per gemeente"])
kaart_hoogte = 1000
col1, col2 = st.columns([4, 6])

with col1:
    if kaart_keuze == "Laadpalen per gemeente":
        max_count = laadpalen['gemeente_officieel'].value_counts().max() if not laadpalen.empty else 1
        stappen = 5
        stap_waarden = [int(i * max_count / (stappen - 1)) for i in range(stappen)]
        width_px = 300

        # Maakt de gradatiebalk linksboven
        st.markdown(
            f"""
            <div style='position:absolute; top:30px; left:10px; z-index:9999;
                        background-color:white; padding:10px; border-radius:5px;
                        box-shadow: 2px 2px 5px rgba(0,0,0,0.3); width:{width_px}px;'>
                <b>Aantal laadpalen</b><br>
                <div style='height:20px; width:100%; 
                            background: linear-gradient(to right, rgba(0,255,0,0.6), rgba(0,150,255,0.6)); 
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

    if kaart_keuze == "Laadpalenkaart":
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

    else:
        # Laadt GeoJSON in GeoPandas
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        gdf['statnaam_norm'] = gdf['statnaam'].str.lower().str.replace(" ", "")
        
        # Voegt het aantal laadpalen toe per gemeente
        counts = laadpalen['gemeente_officieel'].value_counts().to_dict()
        gdf['aantal_laadpalen'] = gdf['statnaam'].map(counts).fillna(0).astype(int)
        
        # Probeert de kleur van de gradatiebalk en choropleth te matchen
        max_count = gdf['aantal_laadpalen'].max() if not gdf.empty else 1
        gdf['ratio'] = gdf['aantal_laadpalen'] / max_count
        gdf['fill_color'] = gdf['ratio'].apply(lambda r: [0, int(255*(1-r)), int(255*r), 150])
        
        # Vereenvoudigt de geometrie voor betere prestatie
        gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.001, preserve_topology=True)
        
        gdf = gdf[['geometry', 'statnaam', 'aantal_laadpalen', 'fill_color']]
        
        # Converteer naar GeoJSON
        geojson_data_for_pydeck = json.loads(gdf.to_json())
        
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
                "html": "<b>{statnaam}</b><br>Aantal laadpalen: {aantal_laadpalen}",
                "style": {"color": "black", "backgroundColor": "white"}
            },
            map_style="mapbox://styles/mapbox/light-v10"
        )
        st.pydeck_chart(r, use_container_width=True, height=kaart_hoogte)