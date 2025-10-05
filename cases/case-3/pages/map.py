import streamlit as st
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Point
import numpy as np

@st.cache_data(ttl=3600)
def load_data(source, type="csv"):
    try:
        if type == "geojson":
            gdf = gpd.read_file(source)
            gdf = gdf.to_crs(epsg=4326)
            return gdf
        elif type == "csv":
            return pd.read_csv(source)
        elif type == "pkl":
            return pd.read_pickle(source)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Fout bij het laden van data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def sample_laadpalen(laadpalen, n=2000, seed=1):
    """Return een willekeurige subset van laadpalen."""
    num_points = min(n, len(laadpalen))
    return laadpalen.sample(n=num_points, random_state=seed)

@st.cache_data(ttl=3600)
def bereken_laadpalen_per_gemeente(laadpalen_df, _gemeenten_gdf):
    # Verwijder laadpalen zonder coördinaten
    laadpalen_df = laadpalen_df.dropna(subset=['AddressInfo_Longitude', 'AddressInfo_Latitude'])

    # Maak GeoDataFrame van laadpalen
    laadpalen_gdf = gpd.GeoDataFrame(
        laadpalen_df,
        geometry=[Point(xy) for xy in zip(laadpalen_df.AddressInfo_Longitude, laadpalen_df.AddressInfo_Latitude)],
        crs=_gemeenten_gdf.crs
    )

    # Voeg elke laadpaal toe aan de gemeente waarin hij ligt
    laadpalen_met_gemeente = gpd.sjoin(laadpalen_gdf, _gemeenten_gdf, how="left", predicate="within")

    # Tel aantal laadpalen per gemeente
    aantal_per_gemeente = laadpalen_met_gemeente.groupby("statnaam").size().reset_index(name="aantal_laadpalen")

    # Voeg aantal toe aan gemeenten
    gemeenten_prepared = _gemeenten_gdf.merge(aantal_per_gemeente, on="statnaam", how="left")
    gemeenten_prepared["aantal_laadpalen"] = gemeenten_prepared["aantal_laadpalen"].fillna(0)

    return gemeenten_prepared

st.set_page_config(
    page_title="Laadpalen Nederland",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded"
)

laadpalen = load_data(
    "C:/Users/8Appe/Minor/Data-Science-Groep-10/cases/case-3/laadpalen_nederland_public.csv", 
    type="csv"
)

# Hierdoor werkt het beter met Fast Marker Cluster
laadpalen.columns = laadpalen.columns.str.replace('.', '_')

# Vul ontbrekende aantal laadpunten in
laadpalen['aantal_laadpunten'] = laadpalen['NumberOfPoints'].fillna(0).astype(int)

# Haal alle gemeentegrenzen in nederland op
geo_url = "https://cartomap.github.io/nl/wgs84/gemeente_2023.geojson"
gemeenten = load_data(geo_url, "geojson")

col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    st.title("Publieke laadpalen in Nederland")
    kaart_keuze = st.radio("Kies welke kaart je wilt zien:", ["Laadpalenkaart", "Laadpalen per gemeente"])

    # Maak lege Folium kaart van Nederland
    m = folium.Map(location=(52.379189, 5), zoom_start=8)

    if kaart_keuze == "Laadpalenkaart":
        st.header("2000 willekeurig geselecteerde laadpalen")
        laadpalen_subset = sample_laadpalen(laadpalen)
        coords = laadpalen_subset[['AddressInfo_Latitude', 'AddressInfo_Longitude']].dropna().values.tolist()
        FastMarkerCluster(coords).add_to(m)

    else:
        st.header("Aantal laadpalen per gemeente")
        gemeenten_prepared = bereken_laadpalen_per_gemeente(laadpalen, gemeenten)
        gemeenten_prepared["aantal_laadpalen_x10"] = gemeenten_prepared["aantal_laadpalen"] / 10
        max_laadpalen = gemeenten_prepared["aantal_laadpalen_x10"].max()
        stap = 25
        max_afgerond = int(np.ceil(max_laadpalen / stap) * stap)
        bins = list(range(0, max_afgerond + stap, stap))

        folium.Choropleth(
            geo_data=gemeenten_prepared,
            data=gemeenten_prepared,
            columns=["statnaam", "aantal_laadpalen_x10"],
            key_on="feature.properties.statnaam",
            fill_color="YlGnBu",
            fill_opacity=0.8,
            line_opacity=0.3,
            legend_name="Aantal laadpalen per gemeente (×10)",
            bins=bins,
            reset=True
        ).add_to(m)

    st_folium(m, width=900, height=1000)
