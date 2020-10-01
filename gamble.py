import os
import tempfile
import zipfile
import argparse
from urllib import request
from datetime import datetime
from datetime import timedelta

import dateutil
from dateutil.relativedelta import relativedelta
from dateutil.relativedelta import TH

import pandas as pd
import numpy as np

# Five Thirty Eight NFL forecasts
ELO_URL = ('https://projects.fivethirtyeight.com/'
           'data-webpage-data/datasets/nfl-elo.zip')
ELO_FILE = 'nfl_elo_latest.csv'


parser = argparse.ArgumentParser()
parser.add_argument('money', type=float)
today = datetime.now()
today = datetime(today.year, today.month, today.day)
parser.add_argument('--week-start', '-w', default=today)
args = parser.parse_args()

money = args.money
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

print('Using Kelly criterion to place bets with ${:.2f}.'.format(money))

# Grab winning teams and probabilities
winner_idx = data.loc[:, ELO1] > data.loc[:, ELO2]
winners = np.where(winner_idx,
                   data.loc[:, TEAM1], data.loc[:, TEAM2])
probs = np.where(winner_idx,
                 data.loc[:, ELO1], data.loc[:, ELO2])
print(probs)
# EOF
