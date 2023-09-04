#!/usr/bin/env python
import argparse
import random
from datetime import datetime, timedelta
import pandas as pd
import nfl_data_py as nfl

parser = argparse.ArgumentParser()
parser.add_argument('money', type=float)
args = parser.parse_args()

money = args.money
money_pct = .3
k = 3
streak_thresh = 3

season_year = (datetime.now() - timedelta(weeks=29)).year
df_orig = nfl.import_schedules([season_year])
df = df_orig[['week', 'away_team', 'home_team', 'away_score', 'home_score']]
df = df.dropna()
df['away_win'] = df['away_score'] > df['home_score']
# don't negate in case there was a cringe tie
df['home_win'] = df['home_score'] > df['away_score']

df_away = df.loc[:, ['week', 'away_team', 'home_team', 'away_win']]
df_away.rename(
    columns={'away_team': 'team', 'home_team': 'other_team',
             'away_win': 'win'}, inplace=True
)
df_home = df.loc[:, ['week', 'home_team', 'away_team', 'home_win']]
df_home.rename(
    columns={'home_team': 'team', 'away_team': 'other_team',
             'home_win': 'win'}, inplace=True
)
df = pd.concat([df_away, df_home], ignore_index=True)
standings = {
    # team: df_team.sort_values(by='week').iloc[-avg_last:]['win'].mean()
    team: df_team.sort_values(by='week')['win'].ewm(com=.5).mean().iloc[-1]
    for team, df_team in df.groupby(['team'], sort=False)
}

print(standings)

ss = sorted(standings.items(), key=lambda x: x[1])
worst = ss[:k]
best = ss[-k:]

tot = sum(x[1] for x in best)
tot += sum(1 - x[1] for x in worst)
n_rand = 2 * k - len(worst) - len(best)
rand_bets = []
for _ in range(n_rand):
    pct = random.random()
    tot += pct
    while True:
        rand_team = df_orig['home_team'].sample().values[0]
        if rand_team not in standings:
            break
    rand_bets.append((rand_team, pct))

money_tot = money * money_pct

print('S&P Bet')
for team, pct in best:
    bet = money_tot * pct / tot
    print(f'best bet (for): {team} ${bet:.2f}')
for team, pct in worst:
    bet = money_tot * (1 - pct) / tot
    print(f'worst bet (against): {team} ${bet:.2f}')
for team, pct in rand_bets:
    bet = money_tot * pct / tot
    print(f'random bet (for): {team} ${bet:.2f}')

print()

streaks = {}
for team, df_team in df.groupby(['team'], sort=False):
    wins = -1 + 2 * df_team.sort_values('week')['win']
    streak = wins.groupby((wins != wins.shift()).cumsum()).cumsum().iloc[-1]
    if abs(streak) >= streak_thresh:
        streaks[team] = streak

print('Daunte Bet')
ss = sorted(streaks.items(), key=lambda x: x[1])
worst = [sss for sss in ss[:k] if sss[1] < 0]
best = [sss for sss in ss[-k:] if sss[1] > 0]

tot = sum(x[1] for x in best)
tot += sum(-x[1] for x in worst)
n_rand = 2 * k - len(worst) - len(best)
rand_bets = []
for _ in range(n_rand):
    pct = random.randint(1, streak_thresh)
    tot += pct
    while True:
        rand_team = df_orig['home_team'].sample().values[0]
        if rand_team not in streaks:
            break
    rand_bets.append((rand_team, pct))

for team, pct in best:
    bet = money_tot * pct / tot
    print(f'best bet streak={pct} (for): {team} ${bet:.2f}')
for team, pct in worst:
    bet = money_tot * (-pct) / tot
    print(f'worst bet streak={pct} (against): {team} ${bet:.2f}')
for team, pct in rand_bets:
    bet = money_tot * pct / tot
    print(f'random bet streak={pct} (for): {team} ${bet:.2f}')
