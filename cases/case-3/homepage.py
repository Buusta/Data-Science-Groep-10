import streamlit as st
import pickle
import pandas as pd

loaded_data = pd.read_pickle("Charging_data.pkl")
loaded_data2 = pd.read_csv('laadpaaldata.csv')

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
    st.write(loaded_data)
    st.write(loaded_data2)