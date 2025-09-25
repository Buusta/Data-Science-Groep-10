import pandas as pd
import requests
from time import sleep
from datetime import datetime

num_games = 250

GameDB = pd.read_csv('steamdb_charts_250.csv')[0:num_games]

checks_per_hour = 2
sleep_time = checks_per_hour * 3600 / num_games

PlayerCountDB = pd.read_csv('PlayerCountDB.csv', index_col=0)

def get_player_count(appid):
    url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
    params = {"appid": appid}

    while True:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Handle "success": false cases
            if "response" in data and "player_count" in data["response"]:
                return data["response"]["player_count"]
            else:
                return None  # existing appid but no count available

        except Exception:
            return None

while True:
    for i in range(len(GameDB)):
        appid, name = GameDB.iloc[i]
        player_count = get_player_count(appid)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        PlayerCountDB.loc[len(PlayerCountDB)] = [appid, player_count, now]

        PlayerCountDB.to_csv('PlayerCountDB2.csv')

        sleep(sleep_time)