import pandas as pd
import requests
from time import sleep
from datetime import datetime

def get_player_count(appid: int):
    url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
    params = {"appid": appid}
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get("response", {}).get("player_count", 0)
    else:
        print("Error:", response.status_code, response.text)
        return None

num_games = 250

GameDB = pd.read_csv('steamdb_charts_250.csv')[0:num_games]

checks_per_hour = 2
sleep_time = checks_per_hour * 3600 / num_games

PlayerCountDB = pd.DataFrame(columns=["appid", "player_count", "date"])

while True:
    for i in range(len(GameDB)):
        appid, name = GameDB.iloc[i]
        player_count = get_player_count(appid)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        PlayerCountDB.loc[len(PlayerCountDB)] = [appid, player_count, now]

        PlayerCountDB.to_csv('PlayerCountDB.csv')

        sleep(sleep_time)