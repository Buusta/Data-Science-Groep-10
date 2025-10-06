import streamlit as st
import pandas as pd
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ChargingData = pd.read_pickle(os.path.join(BASE_DIR, "Charging_data.pkl"))
LaadpaalData = pd.read_csv(os.path.join(BASE_DIR, "laadpaaldata.csv"))
Cars = pd.read_pickle(os.path.join(BASE_DIR, "cars.pkl"))

st.set_page_config(
    page_title="Laadpalen Dashboard",
    page_icon=":sunglasses"
)

st.title("This is the homepage")
st.sidebar.success('Select a page above')

if "show_text" not in st.session_state:
    st.session_state.show_text = False

def toggle():
    st.session_state.show_text = not st.session_state.show_text

st.button(label="Toggle Text", on_click=toggle)

if st.session_state.show_text:
    st.write(ChargingData)
    st.write(LaadpaalData)
    st.write(Cars)