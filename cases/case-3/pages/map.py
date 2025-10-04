import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# =============================
# Interactieve kaart met laadpalen
# =============================

# Voorkomt dat elke page refresh een nieuwe get request stuurt naar Open Chage Map API
@st.cache_data(ttl=3600)
def fetch_data():
    response = requests.get("https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=1000&compact=true&verbose=false&key=93b912b5-9d70-4b1f-960b-fb80a4c9c017")
    return pd.json_normalize(response.json())

# Haalt de laadpalen data op
laadpalen = fetch_data()

st.title("Kaart van de laadpalen in Nederland")

# Toont een kaart van Nederland
m = folium.Map(
    location=(52.0000, 7.0000),
    zoom_start=8
)

# Maakt kolomnamen geschikt als attributen voor itertuples()
laadpalen.columns = laadpalen.columns.str.replace('.', '_')

# MarkerCluster zorgt voor betere performance bij veel markers
marker_cluster = MarkerCluster().add_to(m)

# Tuples zijn efficienter en sneller dan Pandas Series
for laadpaal in laadpalen.itertuples():
    usage_cost = laadpaal.UsageCost
    
    if pd.isna(usage_cost):
        kosten_text = "Onbekend"
    elif "Free" in usage_cost:
        kosten_text = "Gratis"
    else:
        kosten_text = usage_cost

    popup_html = (
    f"<h4>{laadpaal.AddressInfo_Title}</h4><br>"
    f"{laadpaal.AddressInfo_AddressLine1} {laadpaal.AddressInfo_Town} {laadpaal.AddressInfo_Postcode}<br>"
    f"Aantal laadpunten: {int(laadpaal.NumberOfPoints) if pd.notna(laadpaal.NumberOfPoints) else 'onbekend'}<br>"
    f"Kosten: {kosten_text}"
    )

    # Plaatst een marker op de kaart met info over de laadpaal
    folium.Marker(
        [laadpaal.AddressInfo_Latitude, laadpaal.AddressInfo_Longitude],
        popup=folium.Popup(popup_html, max_width=400),
        tooltip=laadpaal.AddressInfo_Title
    ).add_to(marker_cluster)

# Geeft de kaart met markers weer
st_folium(m, width=1400, height=800)

# =============================
# Choropleth van het aantal laadpalen per provincie
# =============================

