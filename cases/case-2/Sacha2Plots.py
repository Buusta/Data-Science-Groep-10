import pandas as pd
import streamlit as st
import ast
from datetime import datetime
import plotly.express as px

# Converteert string x veilig naar een Python lijst.
def safe_evaluation(x, default=list()):
    if pd.isna(x) or not str(x).strip(): return default
    try: return list(ast.literal_eval(x))
    except: return default

# Controleert of een game beschikbaar is op een van de geselecteerde platforms.
def filter_platforms(row, selected, names): 
    return any(row["platforms_list"][i] for i, plat in enumerate(names) if plat in selected)

# Geeft het eerste platform terug waarop het spel beschikbaar is uit de geselecteerde lijst.
def primary_platform(row, selected, names): 
    return next((plat for i, plat in enumerate(names) if row["platforms_list"][i] and plat in selected), "PC")

# Importeer de benodigde datasets
player_counts = pd.read_csv("PlayerCountDB.csv")
games = pd.read_csv("steamdb_charts_250.csv")
game_details = pd.read_csv("GameDetailDB.csv")
genres = pd.read_csv("GenreIdDB.csv")

# Beschikbare platforms in deze datasets
platform_names = ["Windows", "Mac", "Linux"]

# Opschonen van data; zorgt Ensure genre_ids_list is a list of ints
game_details = game_details.assign(
    genre_ids_list=game_details["genre_ids"].apply(lambda x: [int(g) for g in safe_evaluation(x)]),
    platforms_list=game_details["platforms"].apply(lambda x: safe_evaluation(x, [0,0,0]))
)

# Ensure genres['genre_id'] is int
genres = genres.astype({"genre_id": int})

total_players = (player_counts.groupby("appid")["player_count"].sum()
    .reset_index()
    .merge(games[["appid","name"]], on="appid", how="left")
    .assign(name=lambda df: df["name"].fillna("Unknown"))
)

# ============================================================
# Title & Top 5 Games
# ============================================================
st.title("Top 250 Steam Games")
st.subheader("Top 5 Games Overzicht")

top5 = (game_details.explode("genre_ids_list")
        .merge(genres, left_on="genre_ids_list", right_on="genre_id", how="left")
        .assign(description=lambda df: df["description"].fillna("Unknown"))
        .merge(total_players, on="appid", how="left")
        .assign(player_count=lambda df: df["player_count"].fillna(0),
                release_date=lambda df: pd.to_datetime(df["release_date"], errors="coerce"),
                game_age=lambda df: datetime.now().year - df["release_date"].dt.year)
        .sort_values("player_count", ascending=False)
        .head(5)
)
st.table(top5[["name","player_count","description","game_age"]]
         .rename(columns={"name":"Game","player_count":"Player Count","description":"Genre","game_age":"Game Age"}))

# ============================================================
# Filters
# ============================================================
selected_platforms = st.multiselect("Selecteer platform(s):", platform_names, default=platform_names)
filtered_games = game_details[game_details.apply(filter_platforms, axis=1, args=(selected_platforms, platform_names))]
top_n = st.slider("Kies Top N games/genres", 5, 250, 20, 5)

# ============================================================
# KPIs
# ============================================================
st.subheader("KPI's")
total_games = len(game_details)
platform_counts = {plat: sum(g[plat_idx] for g, plat_idx in zip(game_details["platforms_list"], range(len(platform_names)))) 
                   for plat, plat_idx in zip(platform_names, range(len(platform_names)))}

genre_totals = (game_details.explode("genre_ids_list")
                .merge(total_players[["appid","player_count"]], on="appid", how="left")
                .merge(genres, left_on="genre_ids_list", right_on="genre_id", how="left")
                .assign(player_count=lambda df: df["player_count"].fillna(0),
                        description=lambda df: df["description"].fillna("Unknown"))
                .groupby("description")["player_count"].sum()
                .reset_index()
)
top_genre = genre_totals.sort_values("player_count", ascending=False).iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Totaal aantal games", total_games)
col2.metric("Games per platform", " | ".join(f"{plat}: {cnt} ({cnt/total_games*100:.1f}%)" for plat, cnt in platform_counts.items()))
col3.metric("Meest gespeelde genre", f"{top_genre['description']} ({top_genre['player_count']/genre_totals['player_count'].sum()*100:.1f}%)")

# ============================================================
# Leaderboards
# ============================================================
st.subheader("Leaderboards")
option = st.selectbox("Kies leaderboard type:", ("Per Game", "Per Genre"))

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

# ============================================================
# Boxplot
# ============================================================
st.subheader("Boxplot: Player Count per Platform")
top_n_box = st.slider("Kies Top N games voor boxplot", 5, 250, 20, 5)

boxplot_df = (filtered_games.merge(total_players, on="appid", how="left")
              .assign(player_count=lambda df: df["player_count"].fillna(0))
              .sort_values("player_count", ascending=False)
              .head(top_n_box)
)
boxplot_expanded = pd.DataFrame([
    {"name": row["name"], "platform": plat, "player_count": row["player_count"], "genre_ids_list": row["genre_ids_list"]}
    for _, row in boxplot_df.iterrows()
    for i, plat in enumerate(platform_names) if row["platforms_list"][i]==1
])

selected_genres_box = st.multiselect("Selecteer genres voor boxplot:", genres["description"].unique())
if selected_genres_box:
    genre_ids_filter = genres[genres['description'].isin(selected_genres_box)]["genre_id"].tolist()
    boxplot_expanded = boxplot_expanded[boxplot_expanded["genre_ids_list"].apply(lambda x: any(g in genre_ids_filter for g in x))]

fig = px.box(boxplot_expanded, x="platform", y="player_count", color="platform",
             color_discrete_map={"PC":"blue","Mac":"green","Linux":"red"},
             hover_data=["name","player_count"], labels={"player_count":"Player Count","platform":"Platform"},
             title="Player Count per Platform")
st.plotly_chart(fig)

# ============================================================
# Scatterplot
# ============================================================
st.subheader("Scatterplot: Gemiddelde Player Count vs Game Age")

# Selecteer platforms voor scatterplot
scatter_platforms = st.multiselect("Selecteer platform(s) voor scatterplot:", platform_names, default=platform_names)

# Bereid dataframe voor
scatter_df = (filtered_games.merge(player_counts, on="appid", how="left")
              .merge(games[["appid","name"]], on="appid", how="left")  # Voeg 'name' toe
              .assign(
                  release_date=lambda df: pd.to_datetime(df["release_date"], errors="coerce"),
                  game_age=lambda df: datetime.now().year - df["release_date"].dt.year,
                  player_count=lambda df: pd.to_numeric(df["player_count"], errors="coerce")
              )
              .dropna(subset=["player_count","game_age"])
)

# Filter op geselecteerde platforms
scatter_df = scatter_df[scatter_df.apply(
    lambda row: any(row["platforms_list"][platform_names.index(p)]==1 for p in scatter_platforms),
    axis=1
)]

# Bereken het eerste platform waarop het spel beschikbaar is
scatter_df = scatter_df.assign(
    primary_platform=lambda df: df.apply(primary_platform, axis=1, args=(scatter_platforms, platform_names))
)

# Gemiddelde player count per game
scatter_df_avg = scatter_df.groupby(["appid","name","game_age","primary_platform"], as_index=False).agg(
    avg_player_count=("player_count", "mean")
)

# Plot
fig = px.scatter(
    scatter_df_avg,
    x="game_age",
    y="avg_player_count",
    color="primary_platform",
    color_discrete_map={"PC":"blue","Mac":"green","Linux":"red"},
    hover_data=["name","avg_player_count","game_age","primary_platform"],
    labels={
        "game_age":"Game Age (years)",
        "avg_player_count":"Gemiddelde Player Count",
        "primary_platform":"Platform"
    },
    title=f"Gemiddelde Player Count vs Game Age ({', '.join(scatter_platforms)})"
)

# Hover template
fig.update_traces(
    hovertemplate="<b>%{customdata[0]}</b><br>Gem. Players: %{customdata[1]:,.0f}<br>Age: %{customdata[2]} jaar<br>Platform: %{customdata[3]}<extra></extra>"
)

st.plotly_chart(fig)


# ============================================================
# Time Series
# ============================================================
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

# ============================================================
# Histogram: Genre Distribution
# ============================================================
st.subheader("Genreverdeling in de top 250")
df_genres = (game_details.explode("genre_ids_list")
    .merge(genres.rename(columns={"description":"genre_name"}), left_on="genre_ids_list", right_on="genre_id", how="left")
    .dropna(subset=["genre_name"])
)
selected_genres_hist = st.multiselect("Selecteer genres:", df_genres["genre_name"].unique(), default=df_genres["genre_name"].unique())
df_genres = df_genres[df_genres["genre_name"].isin(selected_genres_hist)]

# Corrected genre_count
genre_count = (df_genres["genre_name"]
    .value_counts()
    .rename_axis("genre")        # index name
    .reset_index(name="count")   # column with counts
)

fig = px.bar(
    genre_count.sort_values("count"), x="count", y="genre", orientation="h",
    title="Verdeling van genres binnen de top 250 Steam-games",
    labels={"count":"Aantal spellen","genre":""},
    
)

fig.update_xaxes(
    dtick=20,
    showgrid=True,      # gridlines aanzetten
    gridcolor="lightgrey",  # kleur van gridlines
    gridwidth=1             # dikte van gridlines
)

fig.update_traces(marker_line_width=1.5, marker_line_color='white')
fig.update_layout(height=30*len(genre_count)+100)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Correlatie: Game Age vs Avg Player Count")

scatter_df_avg = (scatter_df.groupby(["appid","name","game_age"])
                  .agg(avg_player_count=("player_count","mean"))
                  .reset_index()
)

corr = scatter_df_avg[["game_age","avg_player_count"]].corr().iloc[0,1]
st.write(f"Correlatie tussen game leeftijd en gemiddelde player count: **{corr:.2f}**")

fig = px.scatter(scatter_df_avg, x="game_age", y="avg_player_count", hover_data=["name"],
                 trendline="ols", labels={"game_age":"Game Age (years)", "avg_player_count":"Average Player Count"},
                 title="Gemiddelde Player Count vs Game Age met Regressielijn")
st.plotly_chart(fig)

# ============================================================
# Scatterplot: Gemiddelde Player Count vs Game Age
# ============================================================
st.subheader("Scatterplot: Gemiddelde Player Count vs Game Age")

# Selecteer platforms voor scatterplot
scatter_platforms = st.multiselect(
    "Selecteer platform(s) voor scatterplot:",
    platform_names,
    default=platform_names,
    key="scatter_platforms"
)

# Kies of regressielijn zichtbaar moet zijn
show_trendline = st.selectbox(
    "Toon regressielijn?",
    ("Nee", "Ja"),
    key="trendline_toggle"
)

# Bereid dataframe voor
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

# Filter op geselecteerde platforms
scatter_df = scatter_df[scatter_df.apply(
    lambda row: any(row["platforms_list"][platform_names.index(p)]==1 for p in scatter_platforms),
    axis=1
)]

# Bereken het eerste platform waarop het spel beschikbaar is
scatter_df = scatter_df.assign(
    primary_platform=lambda df: df.apply(primary_platform, axis=1, args=(scatter_platforms, platform_names))
)

# Gemiddelde player count per game
scatter_df_avg = scatter_df.groupby(["appid","name","game_age","primary_platform"], as_index=False).agg(
    avg_player_count=("player_count", "mean")
)

# Bereken correlatie
corr = scatter_df_avg[["game_age","avg_player_count"]].corr().iloc[0,1]
st.write(f"Correlatie tussen game leeftijd en gemiddelde player count: **{corr:.2f}**")

# Trendline parameter
trendline_param = "ols" if show_trendline == "Ja" else None

# Plot
fig = px.scatter(
    scatter_df_avg,
    x="game_age",
    y="avg_player_count",
    color="primary_platform",
    color_discrete_map={"PC":"blue","Mac":"green","Linux":"red"},
    hover_data=["name","avg_player_count","game_age","primary_platform"],
    labels={
        "game_age":"Game Age (years)",
        "avg_player_count":"Gemiddelde Player Count",
        "primary_platform":"Platform"
    },
    title=f"Gemiddelde Player Count vs Game Age ({', '.join(scatter_platforms)})",
    trendline=trendline_param
)

# Hover template
fig.update_traces(
    hovertemplate="<b>%{customdata[0]}</b><br>Gem. Players: %{customdata[1]:,.0f}<br>Age: %{customdata[2]} jaar<br>Platform: %{customdata[3]}<extra></extra>"
)

# Unieke key toegevoegd
st.plotly_chart(fig, use_container_width=True, key="scatter_avg_player_count_trendline")

# ============================================================
# KPI's & Top Genres met correcte gemiddelde player count
# ============================================================
st.subheader("KPI's")

# Bereken gemiddelde player_count per game
avg_players_per_game = (player_counts.groupby("appid", as_index=False)
                        .agg(avg_player_count=("player_count","mean"))
                        .merge(games[["appid","name"]], on="appid", how="left")
                       )

# Totaal aantal games
total_games = len(game_details)
st.metric("Totaal aantal games", total_games)

# ----------------------------
# Top genres (Top 10) met 'Overig'
# ----------------------------
# Explode genres en merge met gemiddelde player_count
genres_expanded = (filtered_games.explode("genre_ids_list")
                   .merge(genres.rename(columns={"description":"genre_name"}), 
                          left_on="genre_ids_list", right_on="genre_id", how="left")
                   .dropna(subset=["genre_name"])
                   .merge(avg_players_per_game[["appid","avg_player_count"]], on="appid", how="left")
                   .assign(avg_player_count=lambda df: df["avg_player_count"].fillna(0))
)

# Gemiddelde player_count per genre
genre_avg = (genres_expanded.groupby("genre_name", as_index=False)
             .agg(avg_player_count=("avg_player_count","mean"))
             .sort_values("avg_player_count", ascending=False)
)

# Top 10 genres, rest als 'Overig'
top_n_genres = 10
top_genres = genre_avg.head(top_n_genres)
other_genres = genre_avg.tail(len(genre_avg)-top_n_genres)
if not other_genres.empty:
    other_sum = pd.DataFrame({"genre_name":["Overig"], 
                              "avg_player_count":[other_genres["avg_player_count"].mean()]})
    pie_data = pd.concat([top_genres, other_sum], ignore_index=True)
else:
    pie_data = top_genres

# Plot taartdiagram
fig = px.pie(pie_data, names="genre_name", values="avg_player_count",
             title=f"Verdeling van gemiddelde player count per genre (Top {top_n_genres})",
             hole=0.3)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Meest gespeelde game per geselecteerde genres
# ----------------------------
selected_genres = st.multiselect(
    "Selecteer genres voor meest gespeelde game:", 
    genre_avg["genre_name"].tolist(), 
    default=top_genres["genre_name"].tolist()
)

if selected_genres:
    # Merge opnieuw om 'name' mee te nemen
    filtered_genres_df = (genres_expanded
                          .merge(games[["appid","name"]], on="appid", how="left")
                          .loc[lambda df: df["genre_name"].isin(selected_genres)]
                         )

    most_played_games = (filtered_genres_df.groupby(["genre_name","name"], as_index=False)
                         .agg(avg_player_count=("avg_player_count","mean"))
                         .sort_values(["genre_name","avg_player_count"], ascending=[True,False])
                         .groupby("genre_name").first().reset_index()
                         [["genre_name","name","avg_player_count"]]
    )

    st.subheader("Meest gespeelde game per geselecteerd genre")
    st.table(most_played_games.rename(
        columns={"genre_name":"Genre","name":"Game","avg_player_count":"Gemiddelde Player Count"}
    ))
