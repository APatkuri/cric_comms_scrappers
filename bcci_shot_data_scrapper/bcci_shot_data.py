import pandas as pd
import os
import requests
import json
import glob
import re
from bs4 import BeautifulSoup


def get_bcci_shot_data(match_id, max_overs, cat):
    # match_id = 1653
    innings = 0

    if max_overs == 20 or max_overs == 50:
        innings = 2
    else:
        innings = 4

    match_data = []
    for i in range(1, innings+1):
        BCCI_COMMS_URL = f"https://scores.bcci.tv/feeds-international/scoringfeeds/{match_id}-Innings{i}.js"
        
        try:
            response = requests.get(BCCI_COMMS_URL, timeout=100)
            response.raise_for_status()
            data = response.text
            # result = re.sub(r'onScoring\((.*?)\);', r'\1', data)
            result = data.replace("onScoring(", "").replace(");", "")
            data_json = json.loads(result)
            match_data.append(data_json[f"Innings{i}"])

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                continue

    with open(f"./bcci_shot_data/{cat}/json/{match_id}.json", 'w') as f:
        json.dump(match_data, f, indent=4)

def csv_to_json(match_id, cat):
    df = pd.read_json(f"./bcci_shot_data/{cat}/json/{match_id}.json")

    if df.empty:
        print(f"DataFrame is empty. Skipping {match_id} further processing.")
    else:
        if 'OverHistory' in df.columns:
            dfs = []
            for i in range(len(df['OverHistory'])):
                dfs.append(pd.DataFrame(df['OverHistory'][i]))
                
            final_df = pd.concat(dfs, axis=0, ignore_index=True)

            # final_df.to_csv(f"./bcci_shot_data/{match_id}.csv")
            final_df = final_df.drop(columns=['BallID', 'BallUniqueID', 'StrikerID', 'NonStrikerID', 'BowlerID', 
                                            'VideoFile', 'NewCommentry', 'Commentry', 'UPDCommentry', 'OutBatsManID',
                                            'HatCheck', 'CommentStrikers', 'OverName', 'CommentOver', 'RunsText'], errors='ignore')

            if 'ActualBallNo' in final_df.columns:
                final_df = final_df[final_df['ActualBallNo'].str.strip() != '']
            if len(final_df) > 0:
                final_df.to_csv(f"./bcci_shot_data/{cat}/csv/{match_id}.csv")
            # final_df.columns.unique()
        else:
            print(f"No OverHistory {match_id}")

def bcci_shot_data_json(cat):
    BCCI = {"BCCI_RECENT_MATCH_URL": f"https://scores2.bcci.tv/getRecentMatches?platform=international&previousMatchesCount=999&filterType={cat}&loadMore=true&archieves=true",
    "BCCI_LIVE_MATCH_URL": f"https://scores2.bcci.tv/getLiveMatches?platform=international&previousMatchesCount=999&filterType={cat}&loadMore=true&archieves=true",
    "BCCI_UPCOMING_MATCH_URL": f"https://scores2.bcci.tv/getUpcomingMatches?platform=international&previousMatchesCount=999&filterType={cat}&loadMore=true&archieves=true"}

    file_path = f"./bcci_shot_data/{cat}/bcci_match_list.json"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            existing_data = json.load(f)
            existing_data = [match for match in existing_data if match["MatchStatus"] == "Post"]
    else:
        existing_data = []

    existing_df = pd.read_csv(f"./bcci_shot_data/{cat}/bcci_match_list.csv")
    existing_df_completed = existing_df[existing_df['MatchStatus'] == "Post"]
    existing_match_ids = set(existing_df_completed['MatchID'])

    bcci_match_list = []
    for i in BCCI.values():
        response = requests.get(i, timeout=100)
        data = response.json()
        rows = list(data.keys())
        if(rows[0] == 'recentMatches'):
            for j in data[list(data.keys())[-1]]:
                bcci_match_list.extend(j)
        else:
            bcci_match_list.extend(data[list(data.keys())[0]])

    ##############

    # BCCI_ARCHIVES_URL = "https://scores.bcci.tv/feeds-international/internationalarchives.js"
    # response = requests.get(BCCI_ARCHIVES_URL, timeout=30)
    # data = response.text
    # result = data.replace("oncomptetion(", "").replace(");", "")
    # final = json.loads(result)
    # archive_df = pd.DataFrame(final['competition'])
    # archive_shot_data_match_list = archive_df[archive_df['completed'] == 1.0]
    # print(archive_shot_data_match_list.tail())
    # if(cat == "Women"):
    #     archive_shot_data_match_list = archive_shot_data_match_list[archive_shot_data_match_list['TeamType'] == "Womens Senior"]
    # elif(cat == "Men"):
    #     archive_shot_data_match_list = archive_shot_data_match_list[archive_shot_data_match_list['TeamType'] == "Mens Senior"]

    # bcci_archive_data = []
    # for comp_id in archive_shot_data_match_list['CompetitionID']:
    #     try:
    #         BCCI_SCORING_FEEDS_URL = f"https://scores.bcci.tv/feeds-international/scoringfeeds/{comp_id}-matchschedule.js"
    #         response = requests.get(BCCI_SCORING_FEEDS_URL, timeout=30)
    #         data = response.text
    #         result = data.replace("MatchSchedule(", "").replace(");", "")
    #         final = json.loads(result)
    #         bcci_archive_data.extend(final['Matchsummary'])
    #     except:
    #         print(archive_df[archive_df['CompetitionID'] == comp_id]['CompetitionName'])

    ###############
    # bcci_match_list.extend(bcci_archive_data)
    new_matches = [match for match in bcci_match_list if match["MatchID"] not in existing_match_ids]
    all_matches = existing_data + new_matches
    # bcci_match_list = sorted(bcci_match_list, key = lambda x: x["MatchDate"])
    all_matches = sorted(all_matches, key = lambda x: x["MatchDate"])

    with open(f"./bcci_shot_data/{cat}/bcci_match_list.json", 'w') as f:
        json.dump(all_matches, f, indent=4)

    return all_matches

def match_data_procees(bcci_match_list, cat):
    temp_df = pd.DataFrame(bcci_match_list)
    temp_df = temp_df.drop_duplicates(subset=['MatchID'], keep='first', inplace=False)

    live_data_file_name = f"./bcci_shot_data/{cat}/live_data_file_name.txt"
    try:
        with open(live_data_file_name, 'r') as file:
            existing_ids = set(line.strip() for line in file)
    except FileNotFoundError:
        existing_ids = set()

    data_temp_df = temp_df[temp_df['MatchStatus'] == 'Post']
    live_data_temp_df = temp_df[temp_df['MatchStatus'] == 'Live']

    for match_id ,max_overs in zip(data_temp_df['MatchID'], data_temp_df['MATCH_NO_OF_OVERS']):
        temp_file_str = f"./bcci_shot_data/{cat}/csv/{match_id}.csv"

        if temp_file_str not in glob.glob(f"./bcci_shot_data/{cat}/csv/*.csv"):
            get_bcci_shot_data(match_id, max_overs, cat)
            csv_to_json(match_id, cat)

        if str(match_id) in existing_ids:
            get_bcci_shot_data(match_id, max_overs, cat)
            csv_to_json(match_id, cat)
            existing_ids.remove(str(match_id))

    # live_match_list = []
    for match_id ,max_overs in zip(live_data_temp_df['MatchID'], live_data_temp_df['MATCH_NO_OF_OVERS']):
        # live_match_list.append(match_id)
        if match_id not in existing_ids:
            existing_ids.add(match_id)

        get_bcci_shot_data(match_id, max_overs, cat)
        csv_to_json(match_id, cat)
        
    with open(live_data_file_name, 'w') as file:
        file.write('\n'.join(str(id) for id in existing_ids))

    #####################

    # temp_df.fillna('', inplace=True)
    temp_df[temp_df.select_dtypes(include=['object']).columns] = temp_df.select_dtypes(include=['object']).fillna('')
    temp_df[temp_df.select_dtypes(include=['float64']).columns] = temp_df.select_dtypes(include=['float64']).fillna(0)
    temp_df = temp_df.drop(columns=['PreMatchCommentary', 'PostMatchCommentary', 'innings'], errors='ignore')
    temp_df.to_csv(f'./bcci_shot_data/{cat}/bcci_match_list.csv', index=False)

    ####################

    # Path to the folder containing the CSV files
    folder_path = f'./bcci_shot_data/{cat}/csv'  # Path to the 'csv' directory

    # List of numbers (in the order you want the CSV files to be combined)
    temp_list = temp_df['MatchID'].tolist()

    # List of all CSV files in the folder
    csv_files = list(f"{num}.csv" for num in temp_list)  # Set for fast lookup

    # Read and concatenate the CSVs
    df_list = []
    for file in csv_files:
        file_path = os.path.join(folder_path, file)
        if os.path.exists(file_path):  # Only process if the file exists
            df = pd.read_csv(file_path)
            df_list.append(df)

    # Concatenate all DataFrames into one
    if df_list:
        final_df = pd.concat(df_list, ignore_index=True)
        # Save the result to a new CSV
        final_df.to_csv(f'./bcci_shot_data/{cat}/combined_shot_data.csv', index=False)
        print('CSV files have been concatenated successfully!')
    else:
        print('No CSV files were found to combine.')

def hawkeye_data(cat):
    # https://www.bcci.tv/events/183/border-gavaskar-trophy-2024-25/match/1652/4th-test

    # temp_df = pd.DataFrame(bcci_match_list)
    hawkeye_file_name = f"./bcci_shot_data/{cat}/hawkeyeid_matchid.csv"
    try:
        with open(hawkeye_file_name, 'r') as file:
            next(file)
            hawkeye_ids = [tuple(map(int, line.strip().split(', '))) for line in file]
    except FileNotFoundError:
        hawkeye_ids = []

    hawkeye_match_ids = {m_id for m_id, _ in hawkeye_ids}

    temp_df = pd.read_json(f"./bcci_shot_data/{cat}/bcci_match_list.json", convert_dates=False)
    india_match_df = temp_df[(temp_df['HomeTeamName'] == 'India') | (temp_df['HomeTeamName'] == 'India (Women)')]

    india_match_df = india_match_df[~india_match_df['MatchID'].isin(hawkeye_match_ids)]

    for c_id, c_name, m_id, m_order in zip(india_match_df['CompetitionID'], india_match_df['CompetitionName'], india_match_df['MatchID'], india_match_df['MatchOrder']):

        c_name_new = re.sub(r'\s+', '-', c_name.lower())
        m_order_new = re.sub(r'\s+', '-', m_order.lower())

        match_center_str = f"https://www.bcci.tv/events/{c_id}/{c_name_new}/match/{m_id}/{m_order_new}"

        response = requests.get(match_center_str, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.find_all('embed')
        if len(text) != 0:
            hawkurl = text[0].get('src', '')
            hawkid = int(hawkurl.split("matchId=")[-1])

            if (m_id, hawkid) not in hawkeye_ids:
                hawkeye_ids.append((m_id, hawkid))

    # print(hawkeye_ids)
    hawkeye_ids = sorted(hawkeye_ids, key = lambda x: x[1])
    column_names = ['MatchID','HawkeyeID']
    with open(hawkeye_file_name, 'w') as file:
        file.write(f"{column_names[0]},{column_names[1]}\n")
        
        for i, j in hawkeye_ids:
            file.write(f"{i}, {j}\n")

def main_func():
    # category = ["Men", "Women"]
    category = ["Men", "Women"]

    for cat in category:
        bcci_match_list = bcci_shot_data_json(cat)
        match_data_procees(bcci_match_list, cat)
        hawkeye_data(cat)

if __name__ == '__main__':
    main_func()
