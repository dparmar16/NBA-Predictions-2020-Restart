# Import packages
import math
import numpy as np
import pandas as pd
from collections import Counter
import warnings
warnings.filterwarnings(action='once')

# Set a seed to ensure consistent results for reproductability
np.random.seed(seed=408)

# Load in team standings and elo dataframe
# Change this path to your own directory
team_df = pd.read_csv("C:\\Users\\Divya Parmar's PC\\Documents\\NBA-Predictions-2020-Restart\\nba_elo_data.csv")

# Create weighed elo value to estimate team's true ability
# Weigh between current elo value and potential full strength elo
# Use 0.5 meaning we give half credit to current and full strength
elo_weight_start_season = 0.5
team_df['elo_value'] = elo_weight_start_season * team_df['elo_basic'] + (1 - elo_weight_start_season) * team_df['elo_playoff_full']

# Create column with list of elo values so we can append as we simulate games
team_df['elo_list'] = [[x] for x in team_df.elo_value]

#Bring in the schedule
schedule = pd.read_csv("C:\\Users\\Divya Parmar's PC\\Documents\\NBA-Predictions-2020-Restart\\nba_regular_season_games_2020.csv")

# Create regular season standings dictionary that we'll fill in later
regular_season_standings = {'team': [], 'seed':[], 'conference':[]}

# First let's write a function to calculate elo
# Thankfully it's  already been done
# https://www.geeksforgeeks.org/elo-rating-algorithm/
def elo_probability(rating1, rating2):
    return 1.0 * 1.0 / (1 + 1.0 * math.pow(10, 1.0 * (rating2 - rating1)/400))

# Test elo_probability function
# Validate that the probabilities add up to 1 for a given matchup
print(elo_probability(1200, 2000))
print(elo_probability(2000, 1200))
print(elo_probability(2000, 1200) + elo_probability(1200, 2000))

# K-Factor determines how quickly elo score reacts to new events
# FiveThirtyEight recommends k-factor of 20 for NBA games
k = 20

# Define game winner function that takes in two elo values and generates a winner
def game_winner(rating1, rating2):
    prob = elo_probability(rating1, rating2)
    random_value = np.random.uniform(0,1)
    if random_value <= prob:
        return 1
    else:
        return 2

# Test of game_winner function
# Ensure value is 1 or 2
print(game_winner(1800, 1700))
print(game_winner(1800, 1700))
print(game_winner(1800, 1700))

# Define function to update elo values after a game occurs
def elo_update(rating_a, rating_b):
    Pa = elo_probability(rating_a, rating_b)
    Pb = elo_probability(rating_b, rating_a)

    game_winner_output = game_winner(rating_a, rating_b)

    if game_winner_output == 1:
        rating_a_updated = rating_a + 20 * (1-Pa)
        rating_b_updated = rating_b + 20 * (0-Pb)

    elif game_winner_output == 2:
        rating_a_updated = rating_a + 20 * (0-Pa)
        rating_b_updated = rating_b + 20 * (1-Pb)

    else:
        rating_a_updated = rating_a
        rating_b_updated = rating_b
    return rating_a_updated, rating_b_updated, game_winner_output



# Define function to take in team elo values, simulate game, update elo values, and update wins/losses
def game_simulation_regular_season(team_a, team_b, input_df):
    #Get first team's elo values from database
    elo_a = input_df['elo_list'][input_df['team_abbrev'] == team_a].values[0][-1]

    #Get second team's elo values from database
    elo_b = input_df['elo_list'][input_df['team_abbrev'] == team_b].values[0][-1]

    # Run elo update and game winner functions
    new_elo_a, new_elo_b, game_winner_output = elo_update(elo_a, elo_b)

    # Update elo for first team
    input_df['elo_list'][input_df['team_abbrev'] == team_a].values[0].append(new_elo_a)

    # Update elo for second team
    input_df['elo_list'][input_df['team_abbrev'] == team_b].values[0].append(new_elo_b)

    # Add wins and losses to respective teams
    if game_winner_output == 1:
        input_df['wins'][input_df['team_abbrev'] == team_a] += 1
        input_df['losses'][input_df['team_abbrev'] == team_b] += 1
    elif game_winner_output == 2:
        input_df['wins'][input_df['team_abbrev'] == team_b] += 1
        input_df['losses'][input_df['team_abbrev'] == team_a] += 1
    else:
        pass
    return input_df

# Define function to simulate all regular season games and return a final dataframe at the end of the regular season
def simulate_regular_season(input_df, schedule_df):
    # Simulate the season
    for index, row in schedule_df.iterrows():
        game_simulation_regular_season(row['team_a'], row['team_b'], input_df)

    # Create certain column that will be needed later on
    input_df['elo_final_regular_season'] = [x[-1] for x in input_df['elo_list']]
    input_df['winning_percentage'] = input_df['wins']/(input_df['wins']+input_df['losses'])
    input_df['elo_into_playoffs'] = 0.5 * input_df['elo_value'] + 0.5 * input_df['elo_final_regular_season']

    # Create western conference and eastern conference dataframes
    western_df = input_df[input_df.conference == 'western']
    eastern_df = input_df[input_df.conference == 'eastern']

    return input_df, western_df, eastern_df
