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
    labels={"count": "Aantal spellen", "genre": ""},
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

game_names = sorted(player_count_df["name"].dropna().unique())
selected_games_ts = st.multiselect("Select games om te laten zien", game_names)
min_date, max_date = player_count_df["date"].min(), player_count_df["date"].max()
date_range = st.date_input("Selecteer een periode", [min_date, max_date])

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
