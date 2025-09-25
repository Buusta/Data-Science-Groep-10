import pandas as pd
import streamlit as st
import ast
from datetime import datetime
import plotly.express as px

st.title("Meest gespeelde games")

# ----------------------------
# 1. Data inlezen
# ----------------------------
player_counts = pd.read_csv("PlayerCountDB.csv")
games = pd.read_csv("steamdb_charts_250.csv")
game_details = pd.read_csv("GameDetailDB.csv")
genres = pd.read_csv("GenreIdDB.csv")

# ----------------------------
# 1b. Parse genre_ids in game_details zodat KPI's werken
# ----------------------------
def parse_genre_ids(x):
    if pd.isna(x) or x.strip() == "":
        return []
    try:
        return [int(g) for g in ast.literal_eval(x)]
    except:
        return []

game_details["genre_ids_list"] = game_details["genre_ids"].apply(parse_genre_ids)

# ----------------------------
# 2. Player count per game optellen
# ----------------------------
total_players = player_counts.groupby("appid")["player_count"].sum().reset_index()
total_players = total_players.merge(games[["appid","name"]], on="appid", how="left")
total_players["name"] = total_players["name"].fillna("Unknown").astype(str)

# ----------------------------
# 3. Platformfilter
# ----------------------------
platform_names = ["PC","Mac","Linux"]

def parse_platforms(x):
    try:
        return ast.literal_eval(x)
    except:
        return [0,0,0]

game_details["platforms_list"] = game_details["platforms"].apply(parse_platforms)

selected_platforms = st.multiselect("Selecteer platform(s):", platform_names, default=platform_names)

def filter_platform(row):
    for i, plat in enumerate(platform_names):
        if plat in selected_platforms and row["platforms_list"][i] == 1:
            return True
    return False

filtered_games = game_details[game_details.apply(filter_platform, axis=1)]

# ----------------------------
# 4. Top N filter
# ----------------------------
top_n = st.slider("Kies Top N games/genres", min_value=5, max_value=250, value=20, step=5)

# ----------------------------
# 8. KPI's
# ----------------------------
st.subheader("KPI's")

# Totaal aantal games
total_games = len(game_details)

# % games per platform
platform_counts = {plat: game_details["platforms_list"].apply(lambda x, i=i: x[i]==1).sum() for i, plat in enumerate(platform_names)}

# Meest gespeelde genre
genre_players_all = game_details.explode("genre_ids_list").merge(total_players[["appid","player_count"]], on="appid", how="left")
genre_players_all["player_count"] = genre_players_all["player_count"].fillna(0)
genre_players_all = genre_players_all.merge(genres, left_on="genre_ids_list", right_on="genre_id", how="left")
genre_players_all["description"] = genre_players_all["description"].fillna("Unknown")
genre_total_all = genre_players_all.groupby("description")["player_count"].sum().reset_index()
top_genre = genre_total_all.sort_values(by="player_count", ascending=False).iloc[0]
top_genre_name = top_genre["description"]
top_genre_pct = top_genre["player_count"] / genre_total_all["player_count"].sum() * 100

# Toon KPI's
col1, col2, col3 = st.columns(3)
col1.metric("Totaal aantal games", total_games)
col2.metric(
    "Games per platform",
    f"PC: {platform_counts['PC']} ({platform_counts['PC']/total_games*100:.1f}%) | "
    f"Mac: {platform_counts['Mac']} ({platform_counts['Mac']/total_games*100:.1f}%) | "
    f"Linux: {platform_counts['Linux']} ({platform_counts['Linux']/total_games*100:.1f}%)"
)
col3.metric("Meest gespeelde genre", f"{top_genre_name} ({top_genre_pct:.1f}%)")

# ----------------------------
# 5. Leaderboard per Game / Genre
# ----------------------------
option = st.selectbox("Kies leaderboard type:", ("Per Game", "Per Genre"))

if option == "Per Game":
    game_data = total_players.merge(filtered_games[["appid"]], on="appid", how="inner")
    game_data_sorted = game_data.sort_values(by="player_count", ascending=False).head(top_n)
    
    fig = px.bar(game_data_sorted, x="name", y="player_count", title=f"Top {top_n} Most Played Games",
                 labels={"name":"Game", "player_count":"Total Player Count"},
                 color_discrete_sequence=["darkblue"])
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig)

elif option == "Per Genre":
    genre_players = filtered_games.explode("genre_ids_list")
    genre_players = genre_players.merge(total_players[["appid","player_count"]], on="appid", how="left")
    genre_players["player_count"] = genre_players["player_count"].fillna(0)
    genres["genre_id"] = genres["genre_id"].astype(int)
    genre_players = genre_players.merge(genres, left_on="genre_ids_list", right_on="genre_id", how="left")
    genre_players["description"] = genre_players["description"].fillna("Unknown")
    genre_total = genre_players.groupby("description")["player_count"].sum().reset_index()
    genre_total = genre_total.sort_values(by="player_count", ascending=False).head(top_n)

    fig = px.bar(genre_total, x="description", y="player_count", title=f"Top {top_n} Most Played Genres",
                 labels={"description":"Genre", "player_count":"Total Player Count"},
                 color_discrete_sequence=["green"])
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig)

# ----------------------------
# 6. Boxplot: Platform vs Player Count
# ----------------------------
st.subheader("Boxplot: Player Count per Platform")

top_n_box = st.slider("Kies Top N games voor boxplot", min_value=5, max_value=250, value=20, step=5)

boxplot_df = filtered_games.merge(total_players, on="appid", how="left")
top_games = boxplot_df.sort_values(by="player_count", ascending=False).head(top_n_box)

rows = []
for _, row in top_games.iterrows():
    for i, plat in enumerate(platform_names):
        if row["platforms_list"][i] == 1:
            rows.append({"name": row["name"], "platform": plat, "player_count": row["player_count"], "genre_ids_list": row["genre_ids_list"]})

boxplot_expanded = pd.DataFrame(rows)

# Genre filter voor boxplot
selected_genres = st.multiselect("Selecteer genres voor boxplot:", genres["description"].unique(), key="boxplot_genres")
if selected_genres:
    genre_ids_filter = genres[genres['description'].isin(selected_genres)]["genre_id"].tolist()
    boxplot_expanded = boxplot_expanded[
        boxplot_expanded["genre_ids_list"].apply(lambda x: any(g in genre_ids_filter for g in x))
    ]

color_map = {"PC":"blue","Mac":"green","Linux":"red"}
fig = px.box(boxplot_expanded, x="platform", y="player_count", color="platform", 
             color_discrete_map=color_map,
             hover_data=["name", "player_count"],
             labels={"player_count":"Player Count", "platform":"Platform"},
             title="Player Count per Platform")
st.plotly_chart(fig)

# ----------------------------
# 7. Scatterplot: Game Age vs Player Count
# ----------------------------
st.subheader("Scatterplot: Game Age vs Player Count")

filtered_games["release_date"] = pd.to_datetime(filtered_games["release_date"], errors="coerce")
current_year = datetime.now().year
filtered_games["game_age"] = current_year - filtered_games["release_date"].dt.year

scatter_df = filtered_games.merge(total_players, on="appid", how="left")
scatter_df = scatter_df[scatter_df["game_age"].notna()]
scatter_df["player_count"] = scatter_df["player_count"].fillna(0)

# Multi-select platform filter voor scatterplot
scatter_platforms = st.multiselect("Selecteer platform(s) voor scatterplot:", platform_names, default=platform_names, key="scatter_platforms")
scatter_df = scatter_df[
    scatter_df.apply(lambda row: any(row["platforms_list"][platform_names.index(p)]==1 for p in scatter_platforms), axis=1)
]

# Bepaal primary platform voor kleur
def primary_platform(row):
    for i, plat in enumerate(platform_names):
        if row["platforms_list"][i]==1 and plat in scatter_platforms:
            return plat
    return "PC"  # fallback

scatter_df["primary_platform"] = scatter_df.apply(primary_platform, axis=1)

color_map_scatter = {"PC":"blue","Mac":"green","Linux":"red"}

fig = px.scatter(
    scatter_df,
    x="game_age",
    y="player_count",
    color="primary_platform",
    color_discrete_map=color_map_scatter,
    hover_data=["name", "player_count", "game_age", "primary_platform"],
    labels={"game_age":"Game Age (years)", "player_count":"Player Count", "primary_platform":"Platform"},
    title=f"Player Count vs Game Age ({', '.join(scatter_platforms)})"
)

# Custom hover template
fig.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>Players: %{customdata[1]}<br>Age: %{customdata[2]} jaar<br>Platform: %{customdata[3]}<extra></extra>")
st.plotly_chart(fig)
