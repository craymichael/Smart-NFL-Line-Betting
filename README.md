# NFL Line Betting "AI"
This system uses an automated approach to betting on NFL game lines. Kelly criterion is used
to determine the proportion of money that should be bet on each game, if any. Currently, the
forecasts from Five Thirty Eight (QB-adjusted elo probabilities) are used to determine odds.

# Installation

You will first need to ensure you have Python 3 installed. You can then use pip to install
the dependencies as follows:

```shell
pip install -r requirements.txt
```

# Basic Usage

Example usage:

```python
python gamble.py 200 week4_lines.csv --week-start 10/1
```

The program will spit out some recommended wagers to place.

Currently, lines CSVs must be of the format:
```
Away Team, Money Line, Home Team, Money Line
DEN,      -110,        NYJ,       -110
IND,      -145,        CHI,        125
JAX,       150,        CIN,       -170
...
```
Other columns will be ignored, case matters for teams and column headers.

# License

See LICENSE.md. I am not responsible for your losses.
