import pandas as pd
import streamlit as st
import ast
from datetime import datetime
import plotly.express as px

# ======================
# Helper functies
# ======================
def safe_evaluation(x, default=None):
    if default is None:
        default = []
    if pd.isna(x) or not str(x).strip(): 
        return default
    try: 
        return list(ast.literal_eval(x))
    except: 
        return default

def filter_platforms(row, selected, names): 
    return any(row["platforms_list"][i] for i, plat in enumerate(names) if plat in selected)

def primary_platform(row, selected, names): 
    return next((plat for i, plat in enumerate(names) if row["platforms_list"][i] and plat in selected), "PC")

# ======================
# Data importeren
# ======================
player_counts = pd.read_csv("Databases\\PlayerCountDB.csv")
games = pd.read_csv("Databases\\steamdb_charts_250.csv")
game_details = pd.read_csv("Databases\\GameDetailDB.csv")
genres = pd.read_csv("Databases\\GenreIdDB.csv")

avg_player_counts = player_counts.groupby("appid")["player_count"].mean()
games["avg_player_count"] = games["appid"].map(avg_player_counts).fillna(0).round().astype(int)

merged_game_details = games.merge(game_details, how='left').dropna()

merged_game_details = merged_game_details[merged_game_details['appid'] != 914690]

platform_names = ["Windows", "Mac", "Linux"]
genres['cum_player_count'] = 0

# unique genre_ids

# sum player counts for genre_ids
#loop over merged_game_details
#locate genre ids in genres
#add player count

merged_game_details['genre_ids'] = merged_game_details['genre_ids'].apply(ast.literal_eval)

genres['cum_player_count'] = genres['genre_id'].apply(lambda id: merged_game_details[merged_game_details['genre_ids'].apply(lambda g: str(id) in g)]['avg_player_count'].sum())

game_details["genre_ids_list"] = game_details["genre_ids"].apply(lambda x: [int(g) for g in safe_evaluation(x)])
game_details["platforms_list"] = game_details["platforms"].apply(lambda x: safe_evaluation(x, [0,0,0]))

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
st.title("Top 250 Steam Games")

# ======================
# Filters
# ======================
selected_platforms = st.multiselect(
    "Selecteer platform(s):", 
    platform_names, 
    default=platform_names,
    key="platforms_top_n"
)
filtered_games = game_details[game_details.apply(filter_platforms, axis=1, args=(selected_platforms, platform_names))]

# ======================
# KPI's & Top Genres
# ======================
st.subheader("KPI's")
total_games = len(game_details)
st.metric("Totaal aantal games", total_games)

# Top genres
genres_expanded = (
    filtered_games.explode("genre_ids_list")
    .merge(genres.rename(columns={"description":"genre_name"}), left_on="genre_ids_list", right_on="genre_id", how="left")
    .dropna(subset=["genre_name"])
    .merge(avg_players_per_game[["appid","avg_player_count"]], on="appid", how="left")
    .assign(avg_player_count=lambda df: df["avg_player_count"].fillna(0))
)
genre_avg = (
    genres_expanded.groupby("genre_name", as_index=False)
    .agg(avg_player_count=("avg_player_count","mean"))
    .sort_values("avg_player_count", ascending=False)
)
top_n_genres = 10
top_genres = genre_avg.head(top_n_genres)
other_genres = genre_avg.tail(len(genre_avg)-top_n_genres)
if not other_genres.empty:
    other_sum = pd.DataFrame({"genre_name":["Overig"], "avg_player_count":[other_genres["avg_player_count"].mean()]})
    pie_data = pd.concat([top_genres, other_sum], ignore_index=True)
else:
    pie_data = top_genres

fig = px.pie(pie_data, names="genre_name", values="avg_player_count",
             title=f"Verdeling van gemiddelde player count per genre (Top {top_n_genres})", hole=0.3)
st.plotly_chart(fig, use_container_width=True)

# Meest gespeelde game per geselecteerd genre
selected_genres = st.multiselect(
    "Selecteer genres voor meest gespeelde game:", 
    genre_avg["genre_name"].tolist(), 
    default=top_genres["genre_name"].tolist(),
    key="most_played_genres"
)
if selected_genres:
    filtered_genres_df = (
        genres_expanded
        .merge(games[["appid","name"]], on="appid", how="left")
        .loc[lambda df: df["genre_name"].isin(selected_genres)]
    )
    most_played_games = (
        filtered_genres_df.groupby(["genre_name","name"], as_index=False)
        .agg(avg_player_count=("avg_player_count","mean"))
        .sort_values(["genre_name","avg_player_count"], ascending=[True,False])
        .groupby("genre_name").first().reset_index()[["genre_name","name","avg_player_count"]]
    )
    st.subheader("Meest gespeelde game per geselecteerd genre")
    st.table(most_played_games.rename(columns={"genre_name":"Genre","name":"Game","avg_player_count":"Gemiddelde Player Count"}))

# ======================
# Leaderboards (Top 5 games = gemiddelde player count)
# ======================
st.subheader("Leaderboards")
top_n = st.slider("Kies Top N games/genres", 5, 250, 20, 5, key="top_n_games")
option = st.selectbox("Kies leaderboard type:", ("Per Game", "Per Genre"), key="leaderboard_type")

if option == 'Per Game':
    game_count_data = games.sort_values('avg_player_count', ascending=False)[:top_n]
    fig = px.bar(game_count_data, 'name', 'avg_player_count')
elif option == 'Per Genre':
    genre_count_data = genres.sort_values('cum_player_count', ascending=False)[:top_n]
    fig = px.bar(genre_count_data, 'description', 'cum_player_count')
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
                   ))

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
        'game_age': 'Game Age (years)',
        'avg_player_count': 'Gemiddelde Player Count',
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
df_genres = (game_details.explode("genre_ids_list")
    .merge(genres.rename(columns={"description":"genre_name"}), left_on="genre_ids_list", right_on="genre_id", how="left")
    .dropna(subset=["genre_name"])
)
selected_genres_hist = st.multiselect("Selecteer genres:", df_genres["genre_name"].unique(), default=df_genres["genre_name"].unique())
df_genres = df_genres[df_genres["genre_name"].isin(selected_genres_hist)]

genre_count = (df_genres["genre_name"]
    .value_counts()
    .rename_axis("genre")
    .reset_index(name="count")
)

fig = px.bar(
    genre_count.sort_values("count"), x="count", y="genre", orientation="h",
    title="Verdeling van genres binnen de top 250 Steam-games",
    labels={"count":"Aantal spellen","genre":""},
)
fig.update_xaxes(dtick=20, showgrid=True, gridcolor="lightgrey", gridwidth=1)
fig.update_traces(marker_line_width=1.5, marker_line_color='white')
fig.update_layout(height=30*len(genre_count)+100)
st.plotly_chart(fig, use_container_width=True)

# ======================
# Time Series
# ======================
st.subheader("Spelertrends over tijd")
player_count_df = (player_counts.merge(games[["appid","name"]], on="appid", how="left")
                   .assign(date=lambda df: pd.to_datetime(df["date"], errors="coerce"),
                           player_count=lambda df: pd.to_numeric(df["player_count"], errors="coerce"))
                   .dropna(subset=["date","player_count"])
                   .drop_duplicates(["appid","date"])
)

game_names = sorted(player_count_df["name"].dropna().unique())
selected_games_ts = st.multiselect("Select games to display", game_names)
min_date, max_date = player_count_df["date"].min(), player_count_df["date"].max()
date_range = st.date_input("Select date range", [min_date, max_date])

ts_df = player_count_df[player_count_df["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))]
if selected_games_ts: ts_df = ts_df[ts_df["name"].isin(selected_games_ts)]

if not ts_df.empty:
    ts_df = ts_df.set_index("date").groupby("name").resample("1h").mean(numeric_only=True).reset_index()
    fig = px.line(ts_df, x="date", y="player_count", color="name",
    title="Number of Players Over Time",
    labels={"player_count":"Player Count","date":"Date","name":"Game"})
    fig.update_traces(mode="lines+markers", connectgaps=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="Player Count", legend_title_text="Game")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No data available for the selected filters.")
