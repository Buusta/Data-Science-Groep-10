import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

st.set_page_config(
    page_title="Laadpalen Nederland",
    page_icon="🔌",
    layout="wide",       # Brede layout
    initial_sidebar_state="expanded"
)

# =============================
# Functies om data te laden en te cachen
# =============================
@st.cache_data(ttl=3600)
def fetch_data(url, as_dataframe=True):
    response = requests.get(url)
    data = response.json()
    if as_dataframe:
        return pd.json_normalize(data)
    else:
        return data

# =============================
# Laad laadpalen data
# =============================
ocm_url = "https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=1000&compact=true&verbose=false&key=93b912b5-9d70-4b1f-960b-fb80a4c9c017"
laadpalen = fetch_data(ocm_url)

laadpalen.columns = laadpalen.columns.str.replace('.', '_', regex=False)

col1, col2, col3 = st.columns([1, 4, 1])

with col2:
    st.title("Laadpalen in Nederland")
    
    # =============================
    # Toggle keuze
    # =============================
    kaart_keuze = st.radio("Kies welke kaart je wilt zien:", ["Laadpalenkaart", "Laadpalen per gemeente"])
    
    # =============================
    # Laadpalenkaart
    # =============================
    m = folium.Map(
        location=(52.379189, 5),
        zoom_start=8,
    )

    if kaart_keuze == "Laadpalenkaart":
        marker_cluster = MarkerCluster().add_to(m)

        for laadpaal in laadpalen.itertuples():
            usage_cost = getattr(laadpaal, 'UsageCost', None)
            kosten_text = (
                "Onbekend" if pd.isna(usage_cost)
                else "Gratis" if "Free" in str(usage_cost)
                else usage_cost
            )

            popup_html = (
                f"<h4>{getattr(laadpaal, 'AddressInfo_Title', 'Onbekend')}</h4>"
                f"{getattr(laadpaal, 'AddressInfo_AddressLine1', '')} "
                f"{getattr(laadpaal, 'AddressInfo_Town', '')} "
                f"{getattr(laadpaal, 'AddressInfo_Postcode', '')}<br>"
                f"Aantal laadpunten: {int(getattr(laadpaal, 'NumberOfPoints', 0)) if pd.notna(getattr(laadpaal, 'NumberOfPoints', None)) else 'onbekend'}<br>"
                f"Kosten: {kosten_text}"
            )

            folium.CircleMarker(
                location=[getattr(laadpaal, 'AddressInfo_Latitude', 0), getattr(laadpaal, 'AddressInfo_Longitude', 0)],
                radius=5,
                color="blue",
                fill=True,
                fill_color="blue",
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=400),
                tooltip=getattr(laadpaal, 'AddressInfo_Title', 'Onbekend')
            ).add_to(marker_cluster)

    # =============================
    # Choropleth kaart
    # =============================
    else:
        df = pd.DataFrame({"gemeente": laadpalen['AddressInfo_Town']})
        df = df[df['gemeente'].notna() & (df['gemeente'] != "")]

        data = df['gemeente'].value_counts().reset_index()
        
        data.columns = ['gemeente', 'aantal_laadpalen']

        geojson_url = "https://cartomap.github.io/nl/wgs84/gemeente_2023.geojson"
        geojson_data = fetch_data(geojson_url, as_dataframe=False)

        folium.Choropleth(
            geo_data=geojson_data,
            data=data,
            columns=['gemeente', 'aantal_laadpalen'],
            key_on='feature.properties.statnaam',
            fill_color='YlGn',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name="Aantal laadpalen"
        ).add_to(m)

    st_folium(m, width=900, height=1000)
