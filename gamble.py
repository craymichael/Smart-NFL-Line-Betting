#!/usr/bin/env python
import os
import tempfile
import zipfile
import argparse
import re
from urllib import request
from datetime import datetime
from datetime import timedelta
from pprint import pprint

import dateutil
from dateutil.relativedelta import relativedelta
from dateutil.relativedelta import TH

import pandas as pd
import numpy as np

# Five Thirty Eight NFL forecasts
# https://projects.fivethirtyeight.com/2020-nfl-predictions/games/
ELO_URL = ('https://projects.fivethirtyeight.com/'
           'data-webpage-data/datasets/nfl-elo.zip')
ELO_FILE = 'nfl_elo_latest.csv'


parser = argparse.ArgumentParser()
parser.add_argument('money', type=float)
parser.add_argument('lines')  # .csv file containing lines

today = datetime.now()
today = datetime(today.year, today.month, today.day)
parser.add_argument('--week-start', '-w', default=today)

parser.add_argument('--min-bets', '-b', default=4, type=int)
parser.add_argument('--top-k', '-k', action='store_true',
                    help='Top k good bets instead of all good bets '
                         'normalized')

parser.add_argument('--lines-only', action='store_true',
                    help='Use lines only to make bets')
parser.add_argument('--tyAI', action='store_true')

args = parser.parse_args()

money = args.money * .6
print(f'Bet 60% of ${args.money:.2f} = ${money:.2f}')
min_bets = args.min_bets
start_date = args.week_start
if isinstance(start_date, str):
    start_date = dateutil.parser.parse(start_date)
# Find the closest thursday
next_thurs = start_date + relativedelta(weekday=TH(+1))
prev_thurs = start_date + relativedelta(weekday=TH(-1))
start_date = (next_thurs
              if (next_thurs - start_date).days <
                 (start_date - prev_thurs).days
              else prev_thurs)
end_date = start_date + timedelta(days=6)
print('Gambling for week starting on %s and ending %s.' %
      (str(start_date.date()), str(end_date.date())))

# read in lines
lines_df = pd.read_csv(args.lines)
n_named = sum(1 for k in lines_df if not k.startswith('Unnamed'))
if n_named < 4:
    lines_df = pd.read_csv(args.lines, skiprows=1)
lines_df.rename(
    columns=lambda c: re.sub(' +', ' ', c.replace('\n', ' ').strip()),
    inplace=True
)
lines_df.dropna(subset=['Money Line', 'Money Line.1',
                        'Away Team', 'Home Team'],
                how='any', axis=0, inplace=True)
lines_df.reset_index(inplace=True, drop=True)
teams = list(lines_df.loc[:, 'Away Team'])
teams.extend(list(lines_df.loc[:, 'Home Team']))
lines = list(lines_df.loc[:, 'Money Line'].astype(int))
lines.extend(list(lines_df.loc[:, 'Money Line.1'].astype(int)))

lines = dict(zip(teams, lines))
if '0' in lines:
    # idk why this happens
    del lines['0']

if not (args.lines_only or args.tyAI):
    with tempfile.TemporaryDirectory() as dirname:
        elo_zip = os.path.join(dirname, 'nfl-elo.zip')
        print('Downloading %s to %s.' % (ELO_URL, elo_zip))
        request.urlretrieve(ELO_URL, elo_zip)

        elo_dir = os.path.join(dirname, 'nfl-elo')
        print('Extracting to %s.' % elo_dir)
        with zipfile.ZipFile(elo_zip, 'r') as zip_file:
            zip_file.extractall(elo_dir)

        # Grab the contents of ELO_FILE
        zip_contents = os.listdir(elo_dir)
        elo_file = ELO_FILE
        if (len(zip_contents) == 1 and
                os.path.isdir(os.path.join(elo_dir, zip_contents[0]))):
            elo_file = os.path.join(zip_contents[0], elo_file)
        elo_file = os.path.join(elo_dir, elo_file)

        print('Reading content of %s.' % elo_file)
        data = pd.read_csv(elo_file)

    # Quarterback-adjusted elo probability of winning
    ELO1 = 'qbelo_prob1'
    ELO2 = 'qbelo_prob2'
    TEAM1 = 'team1'
    TEAM2 = 'team2'
    DATE = 'date'

    # Filter data for date range
    data.loc[:, DATE] = pd.to_datetime(data.loc[:, DATE])
    data = data.loc[(data.loc[:, DATE] >= start_date) &
                    (data.loc[:, DATE] <= end_date)]
    data.reset_index(inplace=True, drop=True)
    # Rename teams
    RENAME = {
        'OAK': 'LV',
        'JAC': 'JAX',
    }
    data.loc[:, TEAM1].replace(RENAME, inplace=True)
    data.loc[:, TEAM2].replace(RENAME, inplace=True)

    # Grab winning teams and probabilities
    winner_idx = data.loc[:, ELO1] > data.loc[:, ELO2]
    winners = np.where(winner_idx,
                       data.loc[:, TEAM1], data.loc[:, TEAM2])
    losers = np.where(winner_idx,
                      data.loc[:, TEAM2], data.loc[:, TEAM1])
    probs = np.where(winner_idx,
                     data.loc[:, ELO1], data.loc[:, ELO2])
else:
    # Dummies, TODO hacky...
    winners = lines_df.loc[:, 'Home Team']
    losers = lines_df.loc[:, 'Away Team']
    probs = len(winners) * [None]

print('Using Kelly criterion to place bets with ${:.2f}.'.format(money))


def kelly(p, b):
    """
    p: probability of win
    b: net fractional odds received on wager
    https://en.wikipedia.org/wiki/Kelly_criterion
    """
    return (p * (b + 1) - 1) / b


def line_odds(line):
    if line > 0:
        return line / 100
    else:
        return -100 / line


bets = []
if args.tyAI:
    print('Explicitly going out of the way to ignore the statistical model '
          'and say every game is 50/50 odds.')
for winner, loser, prob in zip(winners, losers, probs):
    if winner not in lines or np.isnan(lines[winner]):
        continue

    if args.tyAI:
        prob_w = prob_l = 0.5
    elif args.lines_only:
        against = lines[winner] / 100
        prob_w = against / (abs(against) + 1)
        if prob_w < 0:
            prob_w += 1

        against = lines[loser] / 100
        prob_l = against / (abs(against) + 1)
        if prob_l < 0:
            prob_l += 1
    else:
        prob_w = prob
        prob_l = 1. - prob

    payout_w = line_odds(lines[winner])
    wager_w = kelly(prob_w, payout_w)

    payout_l = line_odds(lines[loser])
    wager_l = kelly(prob_l, payout_l)

    bets.append([winner, wager_w, payout_w, prob_w])
    bets.append([loser, wager_l, payout_l, prob_l])

bets = sorted(bets, key=lambda r: r[1], reverse=True)
print('Team, Kelly wager, Net payout, Win prob')
pprint(bets)

MIN_KELLY = 0
BAD_BET_WAGER = 0.69  # cents

good_bets = list(filter(lambda r: r[1] > MIN_KELLY, bets))

if args.top_k:
    print('Using top k bets that sum to 1')
    total = 0
    n_bets = 1
    for i, bet in enumerate(good_bets):
        total += bet[1]
        if total > 1:
            print('Full money exceeded after %d bets' % (i + 1))
            break
        n_bets += 1
    good_bets = good_bets[:n_bets]

if len(good_bets) < min_bets:
    print('Minimum bets not exceeded. Adding more bets...')
    good_bets = bets[:min_bets]
    bad_bet_frac = BAD_BET_WAGER / money
    for bet in good_bets:
        if bet[1] < 0:
            bet[1] = bad_bet_frac

bet_total = sum(r[1] for r in good_bets)
if bet_total > 1:
    bet_scalar = bet_total
    bet_total = 1
    print('Total bets over 100%%, reducing bets by %.2f%%' %
          ((bet_scalar - 1) * 100))
else:
    bet_scalar = 1

print('Betting on %d teams with %.2f%% of $%.2f ($%.2f).' %
      (len(good_bets), bet_total * 100, money, money * bet_total))
final_bets = {}
for team, wager, _, _ in good_bets:
    bet = wager / bet_scalar * money
    print('%3s $%.2f' % (team, bet))
    final_bets[team] = bet

teams_clean = []
for team in teams:
    if team not in teams_clean and team != '0':
        teams_clean.append(team)
teams = teams_clean
away = teams[:len(teams) // 2]
home = teams[len(teams) // 2:]
ez_data = [
    {
        'Away Team': ta,
        'Away Bet': final_bets.get(ta, ''),
        'Home Team': th,
        'Home Bet': final_bets.get(th, ''),
    }
    for ta, th in zip(away, home)
]
print(pd.DataFrame(ez_data))
