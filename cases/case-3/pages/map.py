import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

## Haal de laadpalen data op bij Open Charge Map en cache het ##
@st.cache_data(ttl=3600)
def fetch_data():
    response = requests.get("https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=1000&compact=true&verbose=false&key=93b912b5-9d70-4b1f-960b-fb80a4c9c017")
    return pd.json_normalize(response.json())

laadpalen = fetch_data()

df4 = pd.json_normalize(laadpalen.Connections)

laadpalen["Connections"] = df4[0]

## Toon een kaart van Nederland met daarop de laadpalen
st.title("Kaart van de laadpalen in Nederland ")

m = folium.Map(
    location=(52.0000, 7.0000),
    zoom_start=8
)

laadpalen.columns = laadpalen.columns.str.replace('.', '_')

marker_cluster = MarkerCluster().add_to(m)

# Voeg laadpalen toe met itertuples() (sneller dan iterrows)
for laadpaal in laadpalen.itertuples():
    folium.Marker(
        [laadpaal.AddressInfo_Latitude, laadpaal.AddressInfo_Longitude],
        popup=laadpaal.AddressInfo_Title
    ).add_to(marker_cluster)

# Kaart weergeven in Streamlit
st_folium(m, width=1400, height=800)