import streamlit as st
import pandas as pd
import plotly.express as px
import ast

PlayerCountDB = pd.read_csv('Databases\\PlayerCountDB.csv', parse_dates=['date']).dropna()
AppidDB = pd.read_csv('Databases\\steamdb_charts_250.csv')
GameDetailDB = pd.read_csv('Databases\\GameDetailDB.csv')
GenreIdDB = pd.read_csv('Databases\\GenreIdDB.csv')

# Change Gamedetail column types
GameDetailDB['genre_ids'] = GameDetailDB['genre_ids'].apply(ast.literal_eval)
GameDetailDB['platforms'] = GameDetailDB['platforms'].apply(ast.literal_eval)
GameDetailDB['release_date'] = pd.to_datetime(GameDetailDB['release_date'])


# Player count plot
names = AppidDB['name']
selected_app = st.sidebar.selectbox("Choose a game:", names)
selected_appid = AppidDB.loc[AppidDB['name'] == selected_app, 'appid'].iloc[0]
player_count = PlayerCountDB[PlayerCountDB['appid'] == selected_appid]
pc_fig = px.line(player_count, 'date', 'player_count')
st.plotly_chart(pc_fig)

# Get min and max years
min_year = GameDetailDB['release_date'].dt.year.min()
max_year = GameDetailDB['release_date'].dt.year.max()


# Genre release date plot
genres = GenreIdDB['description']
selected_genre = st.sidebar.selectbox("Choos:", genres)
selected_genre_id = str(GenreIdDB.loc[GenreIdDB['description'] == selected_genre, 'genre_id'].iloc[0])
selected_games = GameDetailDB[GameDetailDB['genre_ids'].apply(lambda g: selected_genre_id in g)]

# Get min and max years
min_year = selected_games['release_date'].dt.year.min()
max_year = selected_games['release_date'].dt.year.max()

# Make a list of bin edges (one per year)
bins = pd.date_range(start=f'{min_year}-01-01', end=f'{max_year+1}-01-01', freq='YS')

# Histogram
gd_fig = px.histogram(
    selected_games,
    x='release_date',
    nbins=len(bins)-1
)
gd_fig.update_xaxes(dtick="M12")  # show 1 tick per year
gd_fig.update_layout(bargap=0.2)

st.plotly_chart(gd_fig)



