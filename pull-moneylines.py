#!/usr/bin/env python
import pandas as pd

import requests
from bs4 import BeautifulSoup

URL = 'https://www.espn.com/nfl/lines'

response = requests.get(URL)

soup = BeautifulSoup(response.content, 'html.parser')

# gather data
table = soup.select('section.Card > div.Wrapper')[0]
header = table.select('h1.headline')[0]
print(header.text)
print('-' * len(header.text))

data = []
date = None
game_id = 0
for game in table.select('div.margin-date'):
    date_ = game.select('div.Table__Title')
    if date_:
        assert len(date_) == 1
        date = date_[0].text

    for game_table in game.select('div.margin-wrapper table'):
        data_header = game_table.select('thead > tr > th')
        time = data_header[0].text
        data_headers = [dh.text for dh in data_header[1:]]

        data_game = {
            'date': date,
            'time': time,
            'game': game_id,
        }
        game_id += 1

        teams = game_table.select('tbody > tr')
        assert len(teams) == 2, teams

        for team, flag in zip(teams, ('away', 'home')):
            data_game_ = data_game.copy()
            team_data = team.select('td')
            assert len(team_data) - 1 == len(data_headers)
            team_el = team_data[0].select('a')[-1]
            data_game_['team_long'] = team_el.text
            data_game_['team'] = team_el['href'].split('/')[-2].upper()
            data_game_['flag'] = flag
            for dh, dv in zip(data_headers, team_data[1:]):
                data_game_[dh.lower()] = dv.text

            data.append(data_game_)

df = pd.DataFrame(data)
df.sort_values(by='game', inplace=True)
home_mask = df.flag == 'home'
df_home = df[home_mask]
df_away = df[~home_mask]
print('Away')
print(df_away[['team', 'ml']])
print('Home')
print(df_home[['team', 'ml']])
