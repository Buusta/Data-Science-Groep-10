import streamlit as st
import pickle
import pandas as pd

st.set_page_config(
    page_title="Laadpalen Dashboard",
    page_icon=":sunglasses"
)

st.title("This is the homepage")
st.sidebar.success('Select a page above')

with open("cars.pkl", "rb") as f:
    loaded_data = pickle.load(f)

if "show_text" not in st.session_state:
    st.session_state.show_text = False

def toggle():
    st.session_state.show_text = not st.session_state.show_text

st.button(label="Toggle Text", on_click=toggle)

if st.session_state.show_text:
    st.write(loaded_data)