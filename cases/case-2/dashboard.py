import pandas as pd
import streamlit as st
import ast
from datetime import datetime
import plotly.express as px
import os

# Get the folder where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Build paths relative to the script
db_path = os.path.join(BASE_DIR, "Databases")

player_counts = pd.read_csv(os.path.join(db_path, "PlayerCountDB.csv"))
games = pd.read_csv(os.path.join(db_path, "steamdb_charts_250.csv"))
game_details = pd.read_csv(os.path.join(db_path, "GameDetailDB.csv"))
genres = pd.read_csv(os.path.join(db_path, "GenreIdDB.csv"))


avg_player_counts = player_counts.groupby("appid")["player_count"].mean()
games["avg_player_count"] = games["appid"].map(avg_player_counts).fillna(0).round().astype(int)

merged_game_details = games.merge(game_details, how='left').dropna()

merged_game_details = merged_game_details[merged_game_details['appid'] != 914690]

platform_names = ["Windows", "Mac", "Linux"]
genres['cum_player_count'] = 0

merged_game_details['genre_ids'] = merged_game_details['genre_ids'].apply(ast.literal_eval)

genres['cum_player_count'] = genres['genre_id'].apply(lambda id: merged_game_details[merged_game_details['genre_ids'].apply(lambda g: str(id) in g)]['avg_player_count'].sum())

total_players = (
    player_counts.groupby("appid")["player_count"].sum()
    .reset_index()
    .merge(games[["appid","name"]], on="appid", how="left")
    .assign(name=lambda df: df["name"].fillna("Unknown"))
)

avg_players_per_game = (
    player_counts.groupby("appid", as_index=False)
    .agg(avg_player_count=("player_count","mean"))
    .merge(games[["appid","name"]], on="appid", how="left")
)

# ======================
# Pagina titel
# ======================
st.title("Steam Games")

# ======================
# KPI's & Top Genres
# ======================

st.subheader("KPI's")
total_games = len(game_details)
st.metric("Totaal aantal games", total_games)

# Top genres met cumulatieve player count (rechtstreeks uit genres)
genre_cum = (
    genres.rename(columns={"description": "genre_name"})[["genre_name", "cum_player_count"]]
    .sort_values("cum_player_count", ascending=False)
)

top_n_genres = 10
top_genres = genre_cum.head(top_n_genres)
other_genres = genre_cum.tail(len(genre_cum) - top_n_genres)

if not other_genres.empty:
    other_sum = pd.DataFrame({
        "genre_name": ["Overig"],
        "cum_player_count": [other_genres["cum_player_count"].sum()]
    })
    pie_data = pd.concat([top_genres, other_sum], ignore_index=True)
else:
    pie_data = top_genres

fig = px.pie(
    pie_data,
    names="genre_name",
    values="cum_player_count",
    title=f"Verdeling van cumulatieve hoeveelheid spelers per genre (Top {top_n_genres})",
    hole=0.3
)
st.plotly_chart(fig, use_container_width=True)


# ======================
# Leaderboards (Top 5 games = gemiddelde player count)
# ======================
st.subheader("Leaderboards")
option = st.selectbox("Kies leaderboard type:", ("Per Game", "Per Genre"), key="leaderboard_type")


is_genre = True if option == "Per Genre" else False
min_slider_val = 3 if is_genre else 6
max_slider_val = len(genres) if is_genre else len(games)
default_slider_val = 6 if is_genre else 25
step_slider_val = 1 if is_genre else 5

top_n = st.slider("Kies Top N games/genres", min_slider_val, max_slider_val, default_slider_val, step_slider_val, key="top_n_games")

if option == 'Per Game':
    game_count_data = games.sort_values('avg_player_count', ascending=False)[:top_n]
    fig = px.bar(game_count_data, 'name', 'avg_player_count', labels={'name': 'Game', 'avg_player_count': 'Aantal spelers'})
elif option == 'Per Genre':
    genre_count_data = genres.sort_values('cum_player_count', ascending=False)[:top_n]
    fig = px.bar(genre_count_data, 'description', 'cum_player_count', labels={'description': 'Genre', 'avg_player_count': 'Aantal spelers'})
st.plotly_chart(fig)


# ======================
# Boxplot (Top 5 games = gemiddelde player count)
# ======================

platforms_dict = {'[1, 0, 0]':'Windows',
                  '[1, 0, 1]': 'Windows, Linux',
                  '[1, 1, 0]': 'Windows, Mac',
                  '[1, 1, 1]': 'All'}

merged_game_details['platform_label'] = merged_game_details['platforms'].map(platforms_dict)

fig = px.histogram(merged_game_details, 'platform_label', labels=platforms_dict, 
                   color='platform_label',
                   category_orders=dict(platform_label=['Windows', 'Windows, Mac', 'Windows, Linux', 'All'],
                   labels={'platform_label': 'Ondersteunde platforms', 'count': 'Aantal games'}
                   ))

fig.update_layout(yaxis_title="Aantal games", showlegend=False,
                  xaxis_title='Ondersteunde platforms')
st.plotly_chart(fig)


# ======================
# Scatterplot: Gemiddelde Player Count vs Game Age
# ======================

# merged_game_details is assumed to already exist in the environment
df = merged_game_details.copy()
show_trendline = st.selectbox("Toon regressielijn?", ("Nee", "Ja"), key="trendline_toggle")
# Parse release_date en game_age
df['release_date_parsed'] = pd.to_datetime(df['release_date'], errors='coerce')
df['game_age'] = datetime.now().year - df['release_date_parsed'].dt.year

# Drop NA en filter log issues
df = df.dropna(subset=['avg_player_count', 'game_age', 'platform_label'])
df = df[df['avg_player_count'] > 0]

# Selecteer platforms
platforms_dict = {
    '[1, 0, 0]':'Windows',
    '[1, 0, 1]': 'Windows, Linux',
    '[1, 1, 0]': 'Windows, Mac',
    '[1, 1, 1]': 'All'
}
category_order = ['Windows', 'Windows, Mac', 'Windows, Linux', 'All']

trendline_param = "ols" if show_trendline == "Ja" else None

# Scatterplot met regressielijn
fig = px.scatter(
    df,
    x='game_age',
    y='avg_player_count',
    opacity=0.5,
    color='platform_label',
    trendline=trendline_param,
    category_orders={'platform_label': category_order},
    custom_data=['name', 'avg_player_count', 'game_age', 'platform_label', 'appid'],
    labels={
        'game_age': 'Leeftijd game (jaren)',
        'avg_player_count': 'Gemiddelde hoeveelheid spelers',
        'platform_label': 'Platform'
    },
    title=f"Gemiddelde Player Count vs Game Age"
)

fig.update_yaxes(type='log')
fig.update_traces(
    marker=dict(size=8),
    hovertemplate="<b>%{customdata[0]}</b><br>"
                  "Gem. Players: %{customdata[1]:,.0f}<br>"
                  "Leeftijd: %{customdata[2]} jaar<br>"
                  "Platform: %{customdata[3]}<extra></extra>"
)

st.plotly_chart(fig, use_container_width=True)


if show_trendline == 'Ja':
# Bereken correlaties per platform
    correlations = df.groupby('platform_label').apply(
        lambda g: g['game_age'].corr(g['avg_player_count'])
    ).reindex(category_order)

    st.write("### Correlaties tussen game leeftijd en gemiddelde player count")
    st.dataframe(correlations.apply(lambda x: f"{x:.2f}"))

# ======================
# Histogram: Genre Distribution
# ======================

st.subheader("Genreverdeling in de top 250")

# Parse genre_ids naar een lijst
game_details['genre_ids_list'] = game_details['genre_ids'].apply(
    lambda x: ast.literal_eval(x) if isinstance(x, str) else []
)

# Explode naar losse genre_id's
df_genres = game_details.explode("genre_ids_list").copy()

# Zorg dat genre_ids_list hetzelfde type heeft als genres['genre_id']
df_genres["genre_ids_list"] = pd.to_numeric(df_genres["genre_ids_list"], errors="coerce").astype("Int64")

# Merge met genres
df_genres = (
    df_genres.merge(
        genres.rename(columns={"description": "genre_name"}),
        left_on="genre_ids_list",
        right_on="genre_id",
        how="left"
    )
    .dropna(subset=["genre_name"])
)

# Genre filter
selected_genres_hist = st.multiselect(
    "Selecteer genres:",
    sorted(df_genres["genre_name"].unique()),
    default=sorted(df_genres["genre_name"].unique())
)
df_genres = df_genres[df_genres["genre_name"].isin(selected_genres_hist)]

# Aantal per genre
genre_count = (
    df_genres["genre_name"]
    .value_counts()
    .rename_axis("genre")
    .reset_index(name="count")
)

# Plot
fig = px.bar(
    genre_count.sort_values("count"),
    x="count",
    y="genre",
    orientation="h",
    title="Verdeling van genres binnen de top 250 Steam-games",
    labels={"count": "Aantal games", "genre": ""},
)

fig.update_xaxes(dtick=20, showgrid=True, gridcolor="lightgrey", gridwidth=1)
fig.update_traces(marker_line_width=1.5, marker_line_color="white")
fig.update_layout(height=30 * len(genre_count) + 100)
st.plotly_chart(fig, use_container_width=True)



# ======================
# Time Series
# ======================
st.subheader("Spelertrends over de tijd heen")
player_count_df = (player_counts.merge(games[["appid","name"]], on="appid", how="left")
                   .assign(date=lambda df: pd.to_datetime(df["date"], errors="coerce"),
                           player_count=lambda df: pd.to_numeric(df["player_count"], errors="coerce"))
                   .dropna(subset=["date","player_count"])
                   .drop_duplicates(["appid","date"])
)

default_games_selection = ['PEAK', 'Counter-Strike 2', 'Dota 2', 'PUBG: BATTLEGROUNDS', 'Hollow Knight: Silksong']

game_names = sorted(player_count_df["name"].dropna().unique())
selected_games_ts = st.multiselect("Selecteer games om te laten zien", game_names, default=default_games_selection)

date_range = st.date_input(
    "Selecteer een periode",
    [datetime(2025, 9, 22), datetime(2025, 9, 26)],
    min_value=datetime(2025, 9, 22),
    max_value=datetime(2025, 9, 27),
)


ts_df = player_count_df[player_count_df["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))]
if selected_games_ts: ts_df = ts_df[ts_df["name"].isin(selected_games_ts)]

if not ts_df.empty:
    ts_df = ts_df.set_index("date").groupby("name").resample("1h").mean(numeric_only=True).reset_index()
    fig = px.line(ts_df, x="date", y="player_count", color="name",
    title="Aantal spelers over de tijd heen",
    labels={"player_count":"Aantal spelers","date":"Datum","name":"Spel"})
    fig.update_traces(mode="lines+markers", connectgaps=True)
    fig.update_layout(xaxis_title="Datum", yaxis_title="Aantal spelers", legend_title_text="Spel")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Niks geselecteerd")
