#!/usr/bin/env python
import random
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('money', type=float)
parser.add_argument('--n-games', '-n', type=int, default=16)
args = parser.parse_args()

n_games = args.n_games
money = args.money
min_bets = 3
bet_money_pct = 0.3
offset = 3  # spreadsheet offset

#
bet_on = random.randint(min_bets, max(min_bets, round(2 / 3 * n_games)))
bet_games = random.sample(range(offset, n_games + offset), k=bet_on)
bet_teams = random.choices(range(2), k=bet_on)
#
bet_pcts = [random.random() for _ in range(bet_on)]

ez_data = {'home': [''] * n_games, 'away': [''] * n_games}
for bet_pct, game, team in zip(bet_pcts, bet_games, bet_teams):
    bet = bet_pct / sum(bet_pcts) * money * bet_money_pct
    team = 'home' if team else 'away'
    print(f'Game row {game} bet of {bet:.2f} on {team} team')
    ez_data[team][game - offset] = bet

import pandas as pd

print(pd.DataFrame(ez_data))
