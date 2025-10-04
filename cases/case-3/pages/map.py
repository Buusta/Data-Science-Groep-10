import streamlit as st
import requests
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Point
import numpy as np

st.set_page_config(
    page_title="Laadpalen Nederland",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=3600)
def fetch_laadpalen(url):
    response = requests.get(url)
    data = response.json()
    df = pd.json_normalize(data)
    df.columns = df.columns.str.replace('.', '_', regex=False)
    df['kosten_text'] = df['UsageCost'].fillna("Onbekend")
    df.loc[df['UsageCost'].str.contains('Free', na=False), 'kosten_text'] = 'Gratis'
    df['aantal_laadpunten'] = df['NumberOfPoints'].fillna(0).astype(int)
    return df

@st.cache_data(ttl=3600)
def load_gemeenten():
    url = "https://cartomap.github.io/nl/wgs84/gemeente_2023.geojson"
    return gpd.read_file(url)

def prepare_gemeenten(laadpalen_df, _gemeenten_gdf):
    geometry = [Point(xy) for xy in zip(laadpalen_df.AddressInfo_Longitude, laadpalen_df.AddressInfo_Latitude)]
    laadpalen_gdf = gpd.GeoDataFrame(laadpalen_df, geometry=geometry, crs=_gemeenten_gdf.crs)

    laadpalen_met_gemeente = gpd.sjoin(laadpalen_gdf, _gemeenten_gdf, how="left", predicate="within")
    aantal_per_gemeente = laadpalen_met_gemeente.groupby("statnaam").size().reset_index(name="aantal_laadpalen")

    gemeenten_prepared = _gemeenten_gdf.merge(aantal_per_gemeente, on="statnaam", how="left")
    gemeenten_prepared["aantal_laadpalen"] = gemeenten_prepared["aantal_laadpalen"].fillna(0)
    return gemeenten_prepared

ocm_url = "https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=10000&compact=true&verbose=false&key=93b912b5-9d70-4b1f-960b-fb80a4c9c017"
laadpalen = fetch_laadpalen(ocm_url)
gemeenten = load_gemeenten()

col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    st.title("Laadpalen in Nederland")
    kaart_keuze = st.radio("Kies welke kaart je wilt zien:", ["Laadpalenkaart", "Laadpalen per gemeente"])

    num_points = min(10000, len(laadpalen))
    laadpalen_subset = laadpalen.sample(n=num_points, random_state=1)


    m = folium.Map(location=(52.379189, 5), zoom_start=8)

    if kaart_keuze == "Laadpalenkaart":
        coords = laadpalen_subset[['AddressInfo_Latitude', 'AddressInfo_Longitude']].dropna().values.tolist()
        FastMarkerCluster(coords).add_to(m)
    
    else:
        gemeenten_prepared = prepare_gemeenten(laadpalen_subset, gemeenten)

        max_laadpalen = gemeenten_prepared['aantal_laadpalen'].max()

        bins = list(np.linspace(0, max_laadpalen, num=18))

        folium.Choropleth(
            geo_data=gemeenten_prepared,
            data=gemeenten_prepared,
            columns=['statnaam', 'aantal_laadpalen'],
            key_on='feature.properties.statnaam',
            fill_color='BuGn',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name="Aantal laadpalen per gemeente",
            bins=bins,
            reset=True
        ).add_to(m)

    st_folium(m, width=900, height=1000)
