# Import packages
import math
import numpy as np
import pandas as pd
from collections import Counter
import warnings
warnings.filterwarnings(action='once')

# Set a seed to ensure consistent results for reproductability
np.random.seed(seed=408)

# Run this code if you're getting warnings as you're modifying dataframes
# Might be want to remove if you're not
import warnings
warnings.filterwarnings(action='once')

# Load in team standings and elo dataframe
# Change this path to your own directory
team_df = pd.read_csv("nba_elo_data.csv")

# Create weighed elo value to estimate team's true ability
# Weigh between current elo value and potential full strength elo
# Use 0.5 meaning we give half credit to current and full strength
elo_weight_start_season = 0.5
# If you want to manually change a team's elo value, here's how you do it
#team_df['elo_basic'][team_df.team_abbrev == 'LAL'] = 10000.0
#team_df['elo_playoff_full'][team_df.team_abbrev == 'LAL'] = 10000.0
team_df['elo_value'] = elo_weight_start_season * team_df['elo_basic'] + (1 - elo_weight_start_season) * team_df['elo_playoff_full']
# If you want to manually change a team's elo value, here's how you do it
#team_df['elo_value'][team_df.team_abbrev == 'LAL'] = 10000.0

# Create column with list of elo values so we can append as we simulate games
team_df['elo_list'] = [[x] for x in team_df.elo_value]

#Create copies of dataframe
team_df_testing = team_df
team_df_backup = team_df

#Bring in the schedule
schedule = pd.read_csv("nba_regular_season_games_2020.csv")

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
def game_simulation_regular_season(team_a, team_b, df):
    team_a = team_a
    team_b = team_b
    input_df = df

    #Get elo values from database
    elo_a = input_df['elo_list'][input_df['team_abbrev'] == team_a].values[0][-1]
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
def simulate_regular_season(df, schedule_df):
    input_df = df
    # Simulate the season
    for index, row in schedule_df.iterrows():
        game_simulation_regular_season(row['team_a'], row['team_b'], input_df)

    # Create certain column that will be needed later on
    # Create winning percentage field for sorting
    input_df['winning_percentage'] = input_df['wins']/(input_df['wins']+input_df['losses'])
    # Get final regular season elo
    input_df['elo_final_regular_season'] = [x[-1] for x in input_df['elo_list']]
    # Get playoff elo which will be weighted between initial reg season elo and final elo to account for regression to mean
    elo_playoff_regress = 0.5
    input_df['elo_into_playoffs'] = elo_playoff_regress * input_df['elo_value'] + (1 - elo_playoff_regress) * input_df['elo_final_regular_season']
    # Add 'elo_into_playoffs' to 'elo_list'
    for row in input_df.iterrows():
        row[1]['elo_list'].append(row[1]['elo_into_playoffs'])

    # Create western conference and eastern conference dataframes
    western_df = input_df[input_df.conference == 'western'].sort_values(by=['winning_percentage', 'elo_final_regular_season'], ascending=False)
    western_df['seed'] = [x for x in range(1, len(western_df.team_abbrev)+1)]
    eastern_df = input_df[input_df.conference == 'eastern'].sort_values(by=['winning_percentage', 'elo_final_regular_season'], ascending=False)
    eastern_df['seed'] = [x for x in range(1, len(eastern_df.team_abbrev)+1)]

    return input_df, western_df, eastern_df


# Simulate play-in round
# This applies to the eight and ninth seeds in each conference
def play_in_round(df, placement_df):
    input_df = df
    input_df['ahead_wins'] = input_df['wins'].shift(1)
    input_df['ahead_losses'] = input_df['losses'].shift(1)
    input_df['games_back_of_ahead_team'] = ((input_df['ahead_wins'] - input_df['wins']) + (input_df['losses'] - input_df['ahead_losses']))/2
    eight = input_df[input_df.seed == 8]
    nine = input_df[input_df.seed == 9]
    if nine['games_back_of_ahead_team'].values > 4:
        placement_df['conference'].append(eight.conference.values[0])
        placement_df['placement'].append('FIRST_ROUND')
        placement_df['team_abbrev'].append(eight.team_abbrev.values[0])
        placement_df['conference'].append(nine.conference.values[0])
        placement_df['placement'].append('DNQ')
        placement_df['team_abbrev'].append(nine.team_abbrev.values[0])
        return eight, placement_df
    elif nine['games_back_of_ahead_team'].values <= 4:
        for i in [eight, nine]:
            placement_df['conference'].append(i.conference.values[0])
            placement_df['placement'].append('PLAY_IN')
            placement_df['team_abbrev'].append(i.team_abbrev.values[0])
        outcome1 = game_winner(eight['elo_list'].values[0][-1], nine['elo_list'].values[0][-1])
        #eight['elo_value'] = rating1_1
        #nine['elo_value'] = rating2_1
        if outcome1 == 1:
            placement_df['conference'].append(eight.conference.values[0])
            placement_df['placement'].append('FIRST_ROUND')
            placement_df['team_abbrev'].append(eight.team_abbrev.values[0])
            placement_df['conference'].append(nine.conference.values[0])
            placement_df['placement'].append('DNQ')
            placement_df['team_abbrev'].append(nine.team_abbrev.values[0])
            return eight, placement_df
        else:
            outcome2 = game_winner(eight['elo_list'].values[0][-1], nine['elo_list'].values[0][-1])
            #eight['elo_value'] = rating1_2
            #nine['elo_value'] = rating2_2
            if outcome2 == 1:
                placement_df['conference'].append(eight.conference.values[0])
                placement_df['placement'].append('FIRST_ROUND')
                placement_df['team_abbrev'].append(eight.team_abbrev.values[0])
                placement_df['conference'].append(nine.conference.values[0])
                placement_df['placement'].append('DNQ')
                placement_df['team_abbrev'].append(nine.team_abbrev.values[0])
                return eight, placement_df
            else:
                placement_df['conference'].append(nine.conference.values[0])
                placement_df['placement'].append('FIRST_ROUND')
                placement_df['team_abbrev'].append(nine.team_abbrev.values[0])
                placement_df['conference'].append(eight.conference.values[0])
                placement_df['placement'].append('DNQ')
                placement_df['team_abbrev'].append(eight.team_abbrev.values[0])
                return nine, placement_df


#Simulate a best-of-seven playoff series
def playoff_series_sim(team_one, team_two):
    team1_wins = 0
    team2_wins = 0
    while team1_wins < 4 and team2_wins < 4:
        team1_in_rating = team_one['elo_list'].values[0][-1]
        team2_in_rating = team_two['elo_list'].values[0][-1]
        rating1, rating2, outcome = elo_update(team1_in_rating, team2_in_rating)
        #team_one['elo_value'] = rating1
        #team_two['elo_value'] = rating2
        if outcome == 1:
            team1_wins += 1
        elif outcome == 2:
            team2_wins += 1
    if team1_wins == 4:
        team_one['elo_list'].values[0].append(rating1)
        return team_one
    elif team2_wins == 4:
        team_two['elo_list'].values[0].append(rating2)
        return team_two
    else:
        return None

# Simulate the entire season - regular season, play-in round, and playoffs
# Only need three parameters - team record/elo dataframe, schedule of regular season games dataframe, and number of iterations
def simulate_entire_season(input_team_df, schedule_df, iterations):
    team_df = input_team_df
    schedule_input = schedule_df
    original_team_object = team_df.copy(deep=True)
    regular_season_standings_df = pd.DataFrame({u'team_abbrev':[], u'team_nickname':[], u'elo_basic':[], u'elo_playoff_full':[],
       u'wins':[], u'losses':[], u'conference':[], u'elo_value':[], u'elo_list':[],
       u'elo_final_regular_season':[], u'winning_percentage':[],
       u'elo_into_playoffs':[], 'seed':[]})
    result_dict = {'team_abbrev':[], 'conference':[], 'placement':[]}
    for i in range(iterations):
        team_df = original_team_object.copy(deep=True)
        elo_weight_start_season = 0.5
        team_df['elo_value'] = elo_weight_start_season * team_df['elo_basic'] + (1 - elo_weight_start_season) * team_df['elo_playoff_full']
        team_df['elo_list'] = [[x] for x in team_df.elo_value]
        team_df_output, west_df_output, east_df_output = simulate_regular_season(team_df, schedule_input)
        regular_season_standings_df = regular_season_standings_df.append(west_df_output.append(east_df_output))

        for row in west_df_output[west_df_output.seed >= 10].iterrows():
            result_dict['team_abbrev'].append(row[1]['team_abbrev'])
            result_dict['conference'].append(row[1]['conference'])
            result_dict['placement'].append('DNQ')


        west_seed_eight, result_dict = play_in_round(west_df_output, result_dict)
        east_seed_eight, result_dict = play_in_round(east_df_output, result_dict)


        for row in west_df_output[west_df_output['seed'] <= 7].iterrows():
            result_dict['team_abbrev'].append(row[1]['team_abbrev'])
            result_dict['conference'].append(row[1]['conference'])
            result_dict['placement'].append('FIRST_ROUND')

        for row in east_df_output[east_df_output.seed <= 7].iterrows():
            result_dict['team_abbrev'].append(row[1]['team_abbrev'])
            result_dict['conference'].append(row[1]['conference'])
            result_dict['placement'].append('FIRST_ROUND')

        west_seed_one = west_df_output[west_df_output.seed == 1]
        west_seed_two = west_df_output[west_df_output.seed == 2]
        west_seed_three = west_df_output[west_df_output.seed == 3]
        west_seed_four = west_df_output[west_df_output.seed == 4]
        west_seed_five = west_df_output[west_df_output.seed == 5]
        west_seed_six = west_df_output[west_df_output.seed == 6]
        west_seed_seven = west_df_output[west_df_output.seed == 7]
        east_seed_one = east_df_output[east_df_output.seed == 1]
        east_seed_two = east_df_output[east_df_output.seed == 2]
        east_seed_three = east_df_output[east_df_output.seed == 3]
        east_seed_four = east_df_output[east_df_output.seed == 4]
        east_seed_five = east_df_output[east_df_output.seed == 5]
        east_seed_six = east_df_output[east_df_output.seed == 6]
        east_seed_seven = east_df_output[east_df_output.seed == 7]

        west18 = playoff_series_sim(west_seed_one, west_seed_eight)
        west45 = playoff_series_sim(west_seed_four, west_seed_five)
        west36 = playoff_series_sim(west_seed_three, west_seed_six)
        west27 = playoff_series_sim(west_seed_two, west_seed_seven)

        east18 = playoff_series_sim(east_seed_one, east_seed_eight)
        east45 = playoff_series_sim(east_seed_four, east_seed_five)
        east36 = playoff_series_sim(east_seed_three, east_seed_six)
        east27 = playoff_series_sim(east_seed_two, east_seed_seven)

        for i in [west18, west27, west36, west45, east18, east27, east36, east45]:
            result_dict['team_abbrev'].append(i.team_abbrev.values[0])
            result_dict['conference'].append(i.conference.values[0])
            result_dict['placement'].append('SECOND_ROUND')

        westsemi1 = playoff_series_sim(west18, west45)
        westsemi2 = playoff_series_sim(west36, west27)
        eastsemi1 = playoff_series_sim(east18, east45)
        eastsemi2 = playoff_series_sim(east36, east27)

        for i in [westsemi1, westsemi2, eastsemi1, eastsemi2]:
            result_dict['team_abbrev'].append(i.team_abbrev.values[0])
            result_dict['conference'].append(i.conference.values[0])
            result_dict['placement'].append('CONFERENCE_FINALS')


        west_winner = playoff_series_sim(westsemi1, westsemi2)
        east_winner = playoff_series_sim(eastsemi1, eastsemi2)

        for i in [west_winner, east_winner]:
            result_dict['team_abbrev'].append(i.team_abbrev.values[0])
            result_dict['conference'].append(i.conference.values[0])
            result_dict['placement'].append('NBA_FINALS')

        champion = playoff_series_sim(west_winner, east_winner)

        for i in [champion]:
            result_dict['team_abbrev'].append(i.team_abbrev.values[0])
            result_dict['conference'].append(i.conference.values[0])
            result_dict['placement'].append('NBA_CHAMPION')

    result_df = pd.DataFrame(result_dict)
    playoff_rounds_order = ['DNQ', 'PLAY_IN', 'FIRST_ROUND', 'SECOND_ROUND', 'CONFERENCE_FINALS', 'NBA_FINALS', 'NBA_CHAMPION']
    playoff_sort_results_columns = ['NBA_CHAMPION', 'NBA_FINALS', 'CONFERENCE_FINALS', 'SECOND_ROUND', 'FIRST_ROUND', 'PLAY_IN', 'DNQ']

    west_regular_season_outcomes = pd.pivot_table(regular_season_standings_df[['team_abbrev','seed', 'team_nickname']][regular_season_standings_df.conference == 'western'].groupby(['team_abbrev', 'seed']).count().reset_index(), values='team_nickname', index=['team_abbrev'], columns=['seed'], aggfunc=np.sum)
    west_regular_season_outcomes = west_regular_season_outcomes.reindex(west_regular_season_outcomes.sort_values(by=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0], ascending=False).index)
    west_regular_season_outcomes = west_regular_season_outcomes.fillna(0)

    east_regular_season_outcomes = pd.pivot_table(regular_season_standings_df[['team_abbrev','seed', 'team_nickname']][regular_season_standings_df.conference == 'eastern'].groupby(['team_abbrev', 'seed']).count().reset_index(), values='team_nickname', index=['team_abbrev'], columns=['seed'], aggfunc=np.sum)
    east_regular_season_outcomes = east_regular_season_outcomes.reindex(east_regular_season_outcomes.sort_values(by=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], ascending=False).index)
    east_regular_season_outcomes = east_regular_season_outcomes.fillna(0)

    playoff_result_agg = pd.pivot_table(result_df[['team_abbrev','placement', 'conference']].groupby(['team_abbrev', 'placement']).count().reset_index(), values='conference', index=['team_abbrev'], columns=['placement'], aggfunc=np.sum)
    playoff_result_agg = playoff_result_agg.reindex_axis(playoff_rounds_order, axis=1)
    playoff_result_agg = playoff_result_agg.reindex(playoff_result_agg.sort_values(by=playoff_sort_results_columns, ascending=False).index)
    playoff_result_agg = playoff_result_agg.fillna(0)

    return west_regular_season_outcomes, east_regular_season_outcomes, playoff_result_agg


# Create a variable for the number of iterations
# I choose 500 but feel free to change
iterations_count = 500

# Run our season simulator
# I choose 500 times but feel free to modify
# Get three outputs (all are aggregated across all simulations)
# The outputs are western conference standings, eastern conference standings, playoff sound results
west_standings, east_standings, playoff_results = simulate_entire_season(team_df_backup, schedule, iterations_count)


# Look at our output
west_standings
east_standings
playoff_results

# Get percentages
west_standings/iterations_count
east_standings/iterations_count
playoff_results/iterations_count
