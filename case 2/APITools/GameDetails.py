import pandas as pd
import requests
from time import sleep

def get_steam_game_info(appid: int):
    url = f'https://store.steampowered.com/api/appdetails?appids={appid}'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        app_info = data.get(str(appid), {})
        
        # Check if Steam returned success: False
        if not app_info.get('success', False):
            return None  # indicate failure
        
        app_data = app_info['data']

        # Genres
        genres = app_data.get('genres', [])
        genre_ids = [g['id'] for g in genres]
        genre_descriptions = [g['description'] for g in genres]

        # Release date
        release_date = app_data.get('release_date', {}).get('date')

        # Platforms
        platforms_data = app_data.get('platforms', {})
        platforms_list = [
            int(platforms_data.get('windows', False)),
            int(platforms_data.get('mac', False)),
            int(platforms_data.get('linux', False))
        ]

        return genre_ids, release_date, platforms_list, genre_descriptions

    except Exception as e:
        print(f"Error fetching {appid}: {e}")
        return None


# --- Main loop ---
num_games = 248
GameDB = pd.read_csv('steamdb_charts_250.csv')[0:num_games]

GameDetailDB = pd.DataFrame(columns=['appid', 'genre_ids', 'release_date', 'platforms'])
GenreIdDB = pd.DataFrame(columns=['genre_id', 'description'])
failed_apps = []

for i in range(len(GameDB)):
    appid, name = GameDB.iloc[i]

    print(f"Processing {i+1}/{len(GameDB)}: AppID {appid} ({name})")
    result = get_steam_game_info(appid)

    if result is None:
        failed_apps.append(appid)
        continue

    genre_ids, release_date, platforms, genre_descriptions = result

    # Save game details
    GameDetailDB.loc[len(GameDetailDB)] = [appid, genre_ids, release_date, platforms]

    # Save unique genres
    for gid, desc in zip(genre_ids, genre_descriptions):
        if gid not in GenreIdDB['genre_id'].values:
            GenreIdDB.loc[len(GenreIdDB)] = [gid, desc]

    sleep(3)  # rate-limit

# --- Save CSVs at the end ---
GameDetailDB.to_csv('GameDetailDB.csv', index=False)
GenreIdDB.to_csv('GenreIdDB.csv', index=False)

# --- Print failed apps ---
if failed_apps:
    print("Failed to fetch the following AppIDs:")
    print(failed_apps)
else:
    print("All apps fetched successfully!")
