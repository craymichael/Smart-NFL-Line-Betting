#!/usr/bin/env python
import random

n_games = 16
money = 38.06
min_bets = 3
bet_money_pct = 0.9

#
bet_on = random.randint(min_bets, n_games)
bet_games = random.sample(range(n_games), k=bet_on)
bet_teams = random.choices(range(2), k=bet_on)
#
bet_pcts = [random.random() for _ in range(bet_on)]

for bet_pct, game, team in zip(bet_pcts, bet_games, bet_teams):
    bet = bet_pct / sum(bet_pcts) * money * bet_money_pct
    team = 'home' if team else 'away'
    print(f'Game {game} bet of {bet:.2f} on {team} team')
