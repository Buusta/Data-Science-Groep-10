import streamlit as st
import plotly.express as px
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.dirname(BASE_DIR)

@st.cache_data
def load_and_astype_Cars():
    Cars = pd.read_pickle(os.path.join(CASE_DIR, "cars.pkl"))

    kolommen_drop = [
        'massa_ledig_voertuig',
        'massa_rijklaar',
        'catalogusprijs',
        'aantal_deuren',
        'aantal_wielen',
        'lengte',
        'breedte',
        'hoogte_voertuig',
        'volgnummer_wijziging_eu_typegoedkeuring',
        'wielbasis',
        'jaar_laatste_registratie_tellerstand',
        'vermogen_massarijklaar',
        'datum_tenaamstelling_dt'
    ]

    Cars = Cars.dropna(subset=kolommen_drop)

    Cars['vervaldatum_apk_dt'] = pd.to_datetime(Cars['vervaldatum_apk_dt'], errors='coerce')
    Cars['datum_tenaamstelling_dt'] = pd.to_datetime(Cars['datum_tenaamstelling_dt'], errors='coerce')

    Cars['massa_ledig_voertuig'] = Cars['massa_ledig_voertuig'].astype(int)
    Cars['massa_rijklaar'] = Cars['massa_rijklaar'].astype(int)
    Cars['catalogusprijs'] = Cars['catalogusprijs'].astype(int)
    Cars['aantal_deuren'] = Cars['aantal_deuren'].astype(int)
    Cars['aantal_wielen'] = Cars['aantal_wielen'].astype(int)
    Cars['lengte'] = Cars['lengte'].astype(int)
    Cars['breedte'] = Cars['breedte'].astype(int)
    Cars['hoogte_voertuig'] = Cars['hoogte_voertuig'].astype(int)
    Cars['volgnummer_wijziging_eu_typegoedkeuring'] = Cars['volgnummer_wijziging_eu_typegoedkeuring'].astype(int)
    Cars['wielbasis'] = Cars['wielbasis'].astype(int)
    Cars['jaar_laatste_registratie_tellerstand'] = Cars['jaar_laatste_registratie_tellerstand'].astype(int)

    Cars['vermogen_massarijklaar'] = Cars['vermogen_massarijklaar'].astype(float)

    Cars['export_indicator'] = Cars['export_indicator'].astype(bool)
    Cars['openstaande_terugroepactie_indicator'] = Cars['openstaande_terugroepactie_indicator'].astype(bool)
    Cars['taxi_indicator'] = Cars['taxi_indicator'].astype(bool)

    return Cars

Cars = load_and_astype_Cars()

merken = Cars['merk'].unique()





# cars per brand sold fig
Cars['maand_tenaamstelling'] = Cars['datum_tenaamstelling_dt'].dt.month
Cars['jaar_tenaamstelling'] = Cars['datum_tenaamstelling_dt'].dt.year
groupby_brand = Cars.groupby(['jaar_tenaamstelling', 'maand_tenaamstelling', 'merk']).size()

month_cum_brand = groupby_brand.groupby(level=2)
month_cum_brand = month_cum_brand.cumsum().reset_index(name='cumulatief')
month_cum_brand['yearmonth'] = pd.to_datetime(month_cum_brand['jaar_tenaamstelling'].astype(str) + ' ' + month_cum_brand['maand_tenaamstelling'].astype(str))
cum_sorted_brand = month_cum_brand.groupby('merk')['cumulatief'].max().sort_values(ascending=False)
cum_sorted_brand_list = list(cum_sorted_brand.index)

def update_gekozen_merk_line():
    if st.session_state[2]:
        st.session_state[2] = list(cum_sorted_brand[:st.session_state['month_brand_number_input']].index)


st.number_input('Top N merken', 1, len(cum_sorted_brand), key='month_brand_number_input', value=5, on_change=update_gekozen_merk_line)
gekozen_merk_line = st.multiselect("Kies een merk", merken, default=list(cum_sorted_brand[:st.session_state['month_brand_number_input']].index), key=2)


st.write(st.session_state)
month_cum_brand_filtered = month_cum_brand[month_cum_brand['merk'].isin(gekozen_merk_line)]
cars_per_brand_fig = px.line(month_cum_brand_filtered, x='yearmonth', y='cumulatief', color='merk', category_orders={'merk':cum_sorted_brand_list})
st.plotly_chart(cars_per_brand_fig)










# cars per month fig
groupby_month_brand = Cars.groupby(['jaar_tenaamstelling', 'maand_tenaamstelling', 'merk']).size()
month_brand = groupby_month_brand.reset_index(name='registraties')
month_brand['yearmonth'] = pd.to_datetime(month_brand['jaar_tenaamstelling'].astype(str) + ' ' + month_brand['maand_tenaamstelling'].astype(str), format='%Y %m')

top_n_merken_bar = st.number_input('Top N merken', 1, len(cum_sorted_brand), key=3, value=5)
st.write(top_n_merken_bar)
if top_n_merken_bar:
    gekozen_merk_bar = st.multiselect("Kies een merk", merken, default=list(cum_sorted_brand[:top_n_merken_bar].index), key=4)
    st.write(gekozen_merk_bar)

month_brand_filtered = month_brand[month_brand['merk'].isin(gekozen_merk_bar)]
month_per_brand_fig = px.histogram(month_brand_filtered, x='yearmonth', y='registraties', color='merk', category_orders={'merk':cum_sorted_brand_list})
st.plotly_chart(month_per_brand_fig)

# avg price per month box?
Cars['yearmonth'] = pd.to_datetime(Cars['jaar_tenaamstelling'].astype(str) + '-' + Cars['maand_tenaamstelling'].astype(str) + '-01')

fig = px.box(Cars, x='yearmonth', y='catalogusprijs', log_y=True, hover_name='handelsbenaming')
st.plotly_chart(fig)

# inrichting fig
inrichting_labels = {
    'stationwagen': 'Stationwagen',
    'MPV': 'MPV',
    'hatchback': 'Hatchback',
    'sedan': 'Sedan',
    'Overige': 'Overige'
}

groupby_inrichting = Cars['inrichting'].value_counts().reset_index(name='counts')
overige_labels = ['cabriolet', 'coupe', 'kampeerwagen', 'lijkwagen']

Cars_inrichting = Cars['inrichting'].replace(overige_labels, 'Overige')
groupby_inrichting = Cars_inrichting.value_counts().reset_index(name='counts')

groupby_inrichting['inrichting'] = groupby_inrichting['inrichting'].replace(inrichting_labels)

chart_type = st.radio(
    "Kies grafiektype:",
    ["Taartdiagram", "Staafdiagram"],
    horizontal=True
)

if chart_type == "Taartdiagram":
    inrichting_pie = px.pie(groupby_inrichting, values='counts', names='inrichting', labels=inrichting_labels)
    st.plotly_chart(inrichting_pie)
else:
    inrichting_hist = px.histogram(groupby_inrichting, x='inrichting' ,y='counts', color='inrichting', labels=inrichting_labels)
    st.plotly_chart(inrichting_hist)

# st.write(Cars)

# print(Cars.columns)