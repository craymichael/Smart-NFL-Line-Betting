import argparse
import dateutil
import json
import math
import os
import re
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from dateutil.relativedelta import TH
from textwrap import indent
from time import sleep

import openai
import pandas as pd

today = datetime.now()
today = datetime(today.year, today.month, today.day)

parser = argparse.ArgumentParser()
parser.add_argument('money', type=float)
parser.add_argument('lines')
parser.add_argument('--week-start', '-w', default=today)
parser.add_argument('--bet-pct', '-p', default=0.06, type=float)

args = parser.parse_args()

money = args.money
bet_pct = args.bet_pct

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
year = start_date.year

# Mascots
with open('chatgpt_data/mascot_mapping.json') as fp:
    mascots = json.load(fp)

# Load the lines
lines_df = pd.read_csv(args.lines)
n_named = sum(1 for k in lines_df if not k.startswith('Unnamed'))
if n_named < 4:
    lines_df = pd.read_csv(args.lines, skiprows=1)
lines_df.rename(
    columns=lambda c: re.sub(' +', ' ', c.replace('\n', ' ').strip()),
    inplace=True
)
# lines_df = lines_df[['Away Team', 'Money Line', 'Home Team', 'Money Line.1']]
lines_df = lines_df[['Away Team', 'Home Team']]
idx = -1
for team in lines_df['Away Team']:
    if team not in mascots:
        break
    idx += 1

lines_df = lines_df.iloc[:idx + 1]
# lines_df['Money Line'] = lines_df['Money Line'].astype(float)
# lines_df['Money Line.1'] = lines_df['Money Line.1'].astype(float)


def fetch_chatgpt_data():
    client = openai.OpenAI()

    TEMPLATE = ('Who would win in a fight: a {A} or a {B}? Answer either '
                '"{A}" or "{B}" and your level of confidence as a percentage.')

    results = []
    for _, row in lines_df.iterrows():
        message = TEMPLATE.format(
            A=mascots[row['Away Team']],
            B=mascots[row['Home Team']],
        )

        messages = [
            {'role': 'user', 'content': message},
        ]
        chat = client.chat.completions.create(
            model='gpt-4o',
            # model='gpt-3.5-turbo',
            messages=messages,
        )

        for choice in chat.choices:
            reply = choice.message.content
            print(f'ChatGPT: {reply}')
            results.append({
                'Away Team': row['Away Team'],
                'Home Team': row['Home Team'],
                'Response': reply,
            })
            break
        # Don't rate limit me!!!
        sleep(.15)
    return pd.DataFrame(results)


# Check cache if data already computed
cache_dir = os.path.join('chatgpt_data', str(year))
cache_file = os.path.join(cache_dir,
                          str(start_date.date()) + '.csv')
if os.path.isfile(cache_file):
    print('Loading from cache:', cache_file)
    df = pd.read_csv(cache_file)
else:
    os.makedirs(cache_dir, exist_ok=True)
    df = fetch_chatgpt_data()
    df.to_csv(cache_file, index=False)


def str_distance(mascot, string, start, end):
    """Number of characters away mascot is from span (start, end)"""
    dist = float('inf')
    for m in re.finditer(mascot.lower(), string.lower()):
        a, b = m.span()
        dist = min(dist, 
                   abs(a - start), abs(a - end),
                   abs(b - start), abs(b - end))
    return dist


# Parse data, make bets
ez_data = []
for i, (_, row) in enumerate(df.iterrows()):
    m = re.search(r'\d+(?:\.d+)?%', row['Response'])
    bet = away = None
    if m is None:
        conf = None
        team = None
    else:
        start, end = m.span()
        conf = float(m.string[start:end - 1])
        bet = conf / 100 * bet_pct * money
        # Find the closest mascot
        dist_home = str_distance(mascots[row['Home Team']], row['Response'],
                                 start, end)
        dist_away = str_distance(mascots[row['Away Team']], row['Response'],
                                 start, end)
        if math.isinf(dist_home) and math.isinf(dist_away):
            team = None
        elif dist_home < dist_away:
            team = row['Home Team']
            away = False
        else:
            team = row['Away Team']
            away = True
    print(f'PARSED: {team} @ {conf}%\n{indent(row["Response"], "\t")}')

    ez_data.append({
        'Away Team': row['Away Team'],
        'Away Bet': '' if team is None or not away else bet,
        'Home Team': row['Home Team'],
        'Home Bet': '' if team is None or away else bet,
    })

print(pd.DataFrame(ez_data))
