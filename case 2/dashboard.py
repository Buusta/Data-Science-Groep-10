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
player_counts = pd.read_csv("PlayerCountDB.csv")
games = pd.read_csv("steamdb_charts_250.csv")
game_details = pd.read_csv("GameDetailDB.csv")
genres = pd.read_csv("GenreIdDB.csv")

platform_names = ["Windows", "Mac", "Linux"]

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

if option == "Per Game":
    data = (total_players.merge(filtered_games[["appid"]], on="appid", how="inner")
            .sort_values("player_count", ascending=False)
            .head(top_n)
    )
    fig = px.bar(data, x="name", y="player_count", color_discrete_sequence=["darkblue"], title=f"Top {top_n} Most Played Games",
                 labels={"name":"Game","player_count":"Total Player Count"})
else:
    genre_data = (filtered_games.explode("genre_ids_list")
                  .merge(total_players[["appid","player_count"]], on="appid", how="left")
                  .merge(genres, left_on="genre_ids_list", right_on="genre_id", how="left")
                  .assign(player_count=lambda df: df["player_count"].fillna(0),
                          description=lambda df: df["description"].fillna("Unknown"))
                  .groupby("description")["player_count"].sum()
                  .reset_index()
                  .sort_values("player_count", ascending=False)
                  .head(top_n)
    )
    fig = px.bar(genre_data, x="description", y="player_count", color_discrete_sequence=["green"], title=f"Top {top_n} Most Played Genres",
                 labels={"description":"Genre","player_count":"Total Player Count"})

fig.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig)

# ======================
# Boxplot (Top 5 games = gemiddelde player count)
# ======================
st.subheader("Boxplot: Player Count per Platform")
top_n_box = st.slider("Kies Top N games voor boxplot", 5, 250, 20, 5, key="top_n_box")

if top_n_box == 5:
    boxplot_df = filtered_games.merge(avg_players_per_game, on="appid", how="left").assign(avg_player_count=lambda df: df["avg_player_count"].fillna(0)).sort_values("avg_player_count", ascending=False).head(5)
    y_col = "avg_player_count"
else:
    boxplot_df = filtered_games.merge(total_players, on="appid", how="left").assign(player_count=lambda df: df["player_count"].fillna(0)).sort_values("player_count", ascending=False).head(top_n_box)
    y_col = "player_count"

boxplot_expanded = pd.DataFrame([
    {"name": row["name"], "platform": plat, y_col: row[y_col], "genre_ids_list": row["genre_ids_list"]}
    for _, row in boxplot_df.iterrows()
    for i, plat in enumerate(platform_names) if row["platforms_list"][i]==1
])

selected_genres_box = st.multiselect("Selecteer genres voor boxplot:", genres["description"].unique(), key="boxplot_genres")
if selected_genres_box:
    genre_ids_filter = genres[genres['description'].isin(selected_genres_box)]["genre_id"].tolist()
    boxplot_expanded = boxplot_expanded[boxplot_expanded["genre_ids_list"].apply(lambda x: any(g in genre_ids_filter for g in x))]

fig = px.box(boxplot_expanded, x="platform", y=y_col, color="platform",
             color_discrete_map={"PC":"blue","Mac":"green","Linux":"red"},
             hover_data=["name", y_col], labels={y_col:"Player Count","platform":"Platform"},
             title="Player Count per Platform")
st.plotly_chart(fig)

# ======================
# Scatterplot: Gemiddelde Player Count vs Game Age
# ======================
st.subheader("Scatterplot: Gemiddelde Player Count vs Game Age")
scatter_platforms = st.multiselect("Selecteer platform(s) voor scatterplot:", platform_names, default=platform_names, key="scatter_platforms")
show_trendline = st.selectbox("Toon regressielijn?", ("Nee", "Ja"), key="trendline_toggle")

scatter_df = (
    filtered_games.merge(player_counts, on="appid", how="left")
    .merge(games[["appid","name"]], on="appid", how="left")
    .assign(
        release_date=lambda df: pd.to_datetime(df["release_date"], errors="coerce"),
        game_age=lambda df: datetime.now().year - df["release_date"].dt.year,
        player_count=lambda df: pd.to_numeric(df["player_count"], errors="coerce")
    )
    .dropna(subset=["player_count","game_age"])
)

scatter_df = scatter_df[scatter_df.apply(lambda row: any(row["platforms_list"][platform_names.index(p)]==1 for p in scatter_platforms), axis=1)]
scatter_df = scatter_df.assign(primary_platform=lambda df: df.apply(primary_platform, axis=1, args=(scatter_platforms, platform_names)))
scatter_df_avg = scatter_df.groupby(["appid","name","game_age","primary_platform"], as_index=False).agg(avg_player_count=("player_count","mean"))

corr = scatter_df_avg[["game_age","avg_player_count"]].corr().iloc[0,1]
st.write(f"Correlatie tussen game leeftijd en gemiddelde player count: **{corr:.2f}**")

trendline_param = "ols" if show_trendline == "Ja" else None
fig = px.scatter(scatter_df_avg, x="game_age", y="avg_player_count", color="primary_platform",
                 color_discrete_map={"PC":"blue","Mac":"green","Linux":"red"},
                 hover_data=["name","avg_player_count","game_age","primary_platform"],
                 labels={"game_age":"Game Age (years)","avg_player_count":"Gemiddelde Player Count","primary_platform":"Platform"},
                 title=f"Gemiddelde Player Count vs Game Age ({', '.join(scatter_platforms)})",
                 trendline=trendline_param)
fig.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>Gem. Players: %{customdata[1]:,.0f}<br>Age: %{customdata[2]} jaar<br>Platform: %{customdata[3]}<extra></extra>")
st.plotly_chart(fig, use_container_width=True, key="scatter_avg_player_count_trendline")

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
    title="Number of Players Over Time (Hourly Bins)",
    labels={"player_count":"Player Count","date":"Date","name":"Game"})
    fig.update_traces(mode="lines+markers", connectgaps=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="Player Count", legend_title_text="Game")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No data available for the selected filters.")
