# =============================================================================
# IMPORTS
# =============================================================================
import streamlit as st
import requests
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Point
import numpy as np
import matplotlib.pyplot as plt

# =============================================================================
# METHODS
# =============================================================================
@st.cache_data(ttl=3600)
def load_data(source, type="csv"):
    try:
        if type == "json":
            response = requests.get(source)
            response.raise_for_status()
            return pd.json_normalize(response.json())
        elif type == "geojson":
            return gpd.read_file(source)
        elif type == "csv":
            return pd.read_csv(source)
        elif type == "pkl":
            return pd.read_pickle(source)
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def prepare_gemeenten(laadpalen_df, gemeenten_gdf):
    geometry = [Point(xy) for xy in zip(laadpalen_df.AddressInfo_Longitude, laadpalen_df.AddressInfo_Latitude)]
    laadpalen_gdf = gpd.GeoDataFrame(laadpalen_df, geometry=geometry, crs=gemeenten_gdf.crs)

    laadpalen_met_gemeente = gpd.sjoin(laadpalen_gdf, gemeenten_gdf, how="left", predicate="within")
    aantal_per_gemeente = laadpalen_met_gemeente.groupby("statnaam").size().reset_index(name="aantal_laadpalen")

    gemeenten_prepared = gemeenten_gdf.merge(aantal_per_gemeente, on="statnaam", how="left")
    gemeenten_prepared["aantal_laadpalen"] = gemeenten_prepared["aantal_laadpalen"].fillna(0)
    
    return gemeenten_prepared

# =============================================================================
# STREAMLIT CONFIG
# =============================================================================
st.set_page_config(
    page_title="Laadpalen Nederland",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# MAPS
# =============================================================================
ocm_url = "https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=10000&compact=true&verbose=false&key=93b912b5-9d70-4b1f-960b-fb80a4c9c017"
laadpalen = load_data(ocm_url, "json")
laadpalen.columns = laadpalen.columns.str.replace('.', '_')
laadpalen['aantal_laadpunten'] = laadpalen['NumberOfPoints'].fillna(0).astype(int)

geo_url = "https://cartomap.github.io/nl/wgs84/gemeente_2023.geojson"
gemeenten = load_data(geo_url, "geojson")

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

# =============================================================================
# HEATMAP
# =============================================================================

