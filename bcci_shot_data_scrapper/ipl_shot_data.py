import pandas as pd
import os
import requests
import json
import glob
import re
from bs4 import BeautifulSoup
from line_profiler import LineProfiler
# from bcci_hawkeye_scrapper import hawkeye_main


def get_bcci_shot_data(match_id, max_overs):
    innings = 0

    if max_overs == 20 or max_overs == 50:
        innings = 2
    else:
        innings = 4

    match_data = []
    for i in range(1, innings+1):
        IPL_COMMS_URL = f"https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/feeds/{match_id}-Innings{i}.js"
        
        try:
            response = requests.get(IPL_COMMS_URL, timeout=100)
            response.raise_for_status()
            data = response.text
            result = data.replace("onScoring(", "").replace(");", "")
            data_json = json.loads(result)
            match_data.append(data_json[f"Innings{i}"])

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                continue

    os.makedirs(f"./bcci_shot_data_scrapper/ipl_shot_data/json", exist_ok=True)    
    with open(f"./bcci_shot_data_scrapper/ipl_shot_data/json/{match_id}.json", 'w') as f:
        json.dump(match_data, f, indent=4)

def csv_to_json(match_id):
    df = pd.read_json(f"./bcci_shot_data_scrapper/ipl_shot_data/json/{match_id}.json")

    if df.empty:
        print(f"DataFrame is empty. Skipping {match_id} further processing.")
    else:
        if 'OverHistory' in df.columns:
            dfs = []
            for i in range(len(df['OverHistory'])):
                dfs.append(pd.DataFrame(df['OverHistory'][i]))
                
            final_df = pd.concat(dfs, axis=0, ignore_index=True)

            final_df = final_df.drop(columns=['BallID', 'BallUniqueID', 'StrikerID', 'NonStrikerID', 'BowlerID', 
                                            'VideoFile', 'NewCommentry', 'Commentry', 'UPDCommentry', 'OutBatsManID',
                                            'HatCheck', 'CommentStrikers', 'OverName', 'CommentOver', 'RunsText'], errors='ignore')

            if 'ActualBallNo' in final_df.columns:
                final_df = final_df[final_df['ActualBallNo'].str.strip() != '']
            if len(final_df) > 0:
                os.makedirs(f"./bcci_shot_data_scrapper/ipl_shot_data/csv", exist_ok=True)
                final_df.to_csv(f"./bcci_shot_data_scrapper/ipl_shot_data/csv/{match_id}.csv")

        else:
            print(f"No OverHistory {match_id}")

def ipl_shot_data_json():
    # ipl_comp_list = [10000,10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,10011,10012,10013, 60, 107, 148, 203]
    ipl_comp_list = [60, 107, 148, 203]
    # BCCI = {"IPL_MATCH_URL": f"https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/feeds/{ipl_comp_id}-matchschedule.js"}

    file_path = f"./bcci_shot_data_scrapper/ipl_shot_data/ipl_match_list.json"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            existing_data = json.load(f)
            existing_data = [match for match in existing_data if match["MatchStatus"] == "Post"]
    else:
        existing_data = []

    if os.path.exists(f"./bcci_shot_data_scrapper/ipl_shot_data/ipl_match_list.csv"):
        existing_df = pd.read_csv(f"./bcci_shot_data_scrapper/ipl_shot_data/ipl_match_list.csv")
        existing_df_completed = existing_df[existing_df['MatchStatus'] == "Post"]
        existing_match_ids = set(existing_df_completed['MatchID'])
    else:
        existing_match_ids = set()


    ipl_match_list = []

    for j in ipl_comp_list:
        ipl_comp_id = j
        response = requests.get(f"https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/feeds/{ipl_comp_id}-matchschedule.js", timeout=100)
        data = response.text
        result = data.replace("MatchSchedule(", "").replace(");", "")
        data_json = json.loads(result)
        ipl_match_list.extend(data_json['Matchsummary'])

    new_matches = [match for match in ipl_match_list if match["MatchID"] not in existing_match_ids]
    all_matches = existing_data + new_matches
    all_matches = sorted(all_matches, key = lambda x: x["MatchDate"])

    os.makedirs(f"./bcci_shot_data_scrapper/ipl_shot_data", exist_ok=True)

    with open(f"./bcci_shot_data_scrapper/ipl_shot_data/ipl_match_list.json", 'w') as f:
        json.dump(all_matches, f, indent=4)

    return all_matches, new_matches

def match_data_procees(ipl_match_list, new_match_list):
    temp_df = pd.DataFrame(ipl_match_list)
    temp_df = temp_df.drop_duplicates(subset=['MatchID'])

    new_match_df = pd.DataFrame(new_match_list).drop_duplicates(subset=['MatchID'], keep='first', inplace=False)

    live_data_file_name = f"./bcci_shot_data_scrapper/ipl_shot_data/live_data_file_name.txt"
    # live_data_file_name = f"./bcci_shot_data/{cat}/live_data_file.csv"
    try:
        with open(live_data_file_name, 'r') as file:
            existing_ids = set(line.strip() for line in file)
        # existing_df = pd.read_csv(live_data_file_name)
        # existing_ids = set(existing_df['MatchID'].astype(str))
    except FileNotFoundError:
        existing_ids = set()

    # data_temp_df = temp_df[temp_df['MatchStatus'] == 'Post']
    # live_data_temp_df = temp_df[temp_df['MatchStatus'] == 'Live']

    data_temp_df = new_match_df[new_match_df['MatchStatus'] == 'Post']
    live_data_temp_df = new_match_df[new_match_df['MatchStatus'] == 'Live']

    for match_id ,max_overs in zip(data_temp_df['MatchID'], data_temp_df['MATCH_NO_OF_OVERS']):
        temp_file_str = f"./bcci_shot_data_scrapper/ipl_shot_data/csv/{match_id}.csv"

        # if temp_file_str not in glob.glob(f"./bcci_shot_data/{cat}/csv/*.csv"):
        if not os.path.exists(temp_file_str):
            get_bcci_shot_data(match_id, max_overs)
            csv_to_json(match_id)

        if str(match_id) in existing_ids:
            get_bcci_shot_data(match_id, max_overs)
            csv_to_json(match_id)
            existing_ids.remove(str(match_id))

    # live_match_list = []
    for match_id ,max_overs in zip(live_data_temp_df['MatchID'], live_data_temp_df['MATCH_NO_OF_OVERS']):
        # live_match_list.append(match_id)
        if match_id not in existing_ids:
            existing_ids.add(match_id)

        get_bcci_shot_data(match_id, max_overs)
        csv_to_json(match_id)
        
        # updated_df = pd.DataFrame({'MatchID': list(existing_ids)})
        # updated_df.to_csv(live_data_file_name, index=False)
    with open(live_data_file_name, 'w') as file:
        file.write('\n'.join(str(id) for id in existing_ids))

    #####################

    # temp_df.fillna('', inplace=True)
    temp_df[temp_df.select_dtypes(include=['object']).columns] = temp_df.select_dtypes(include=['object']).fillna('')
    temp_df[temp_df.select_dtypes(include=['float64']).columns] = temp_df.select_dtypes(include=['float64']).fillna(0)
    temp_df = temp_df.drop(columns=['PreMatchCommentary', 'PostMatchCommentary', 'innings'], errors='ignore')
    temp_df.to_csv(f'./bcci_shot_data_scrapper/ipl_shot_data/ipl_match_list.csv', index=False)

    ####################

    # Path to the folder containing the CSV files
    folder_path = f'./bcci_shot_data_scrapper/ipl_shot_data/csv'  # Path to the 'csv' directory

    # List of numbers (in the order you want the CSV files to be combined)
    # temp_list = temp_df['MatchID'].tolist()

    # List of all CSV files in the folder
    csv_files = [os.path.join(folder_path, f"{match_id}.csv") for match_id in temp_df['MatchID']]
    # csv_files = list(f"{num}.csv" for num in temp_list)  # Set for fast lookup

    existing_csv_files = list(filter(os.path.exists, csv_files)) 

    if existing_csv_files:
        df_list = [pd.read_csv(file) for file in existing_csv_files]
        final_df = pd.concat(df_list, ignore_index=True)
        final_df.to_csv(f'./bcci_shot_data_scrapper/ipl_shot_data/combined_shot_data.csv', index=False)
        print('CSV files have been concatenated successfully!')
    else:
        print('No CSV files were found to combine.')

def hawkeye_data():
    # https://www.bcci.tv/events/183/border-gavaskar-trophy-2024-25/match/1652/4th-test

    # temp_df = pd.DataFrame(bcci_match_list)
    hawkeye_file_name = f"./bcci_shot_data_scrapper/ipl_shot_data/hawkeyeid_matchid.csv"
    try:
        with open(hawkeye_file_name, 'r') as file:
            next(file)
            hawkeye_ids = [tuple(map(int, line.strip().split(', '))) for line in file]
    except FileNotFoundError:
        hawkeye_ids = []

    hawkeye_match_ids = {m_id for m_id, _ in hawkeye_ids}

    if hawkeye_ids:
        last_hawkeye_match_id = hawkeye_ids[-1][0]
    else:
        last_hawkeye_match_id = None

    temp_df = pd.read_json(f"./bcci_shot_data_scrapper/ipl_shot_data/ipl_match_list.json", convert_dates=False)

    if last_hawkeye_match_id is not None:
        last_match_index = temp_df[temp_df['MatchID'] == last_hawkeye_match_id].index.max()
        india_match_df = temp_df.loc[last_match_index + 1:]
    else:
        india_match_df = temp_df
    # india_match_df = temp_df[(temp_df['HomeTeamName'] == 'India') | (temp_df['HomeTeamName'] == 'India (Women)')]
    # india_match_df = india_match_df[india_match_df['HomeTeamName'].isin(['India', 'India (Women)'])]

    # india_match_df = india_match_df[~india_match_df['MatchID'].isin(hawkeye_match_ids)]
    india_match_df['MatchDate'] = pd.to_datetime(india_match_df['MatchDate'])
    india_match_df = india_match_df[india_match_df['MatchDate'].dt.year >= 2022]

    for m_date, m_id in zip(india_match_df['MatchDate'].dt.year, india_match_df['MatchID']):

        # c_name_new = re.sub(r'\s+', '-', c_name.lower())
        # m_order_new = re.sub(r'\s+', '-', m_order.lower())

        # match_center_str = f"https://www.bcci.tv/events/{c_id}/{c_name_new}/match/{m_id}/{m_order_new}"
        match_center_str = f"https://www.iplt20.com/match/{m_date}/{m_id}"

        response = requests.get(match_center_str, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.find_all('embed')
        if len(text) != 0:
            hawkurl = text[0].get('src', '')
            hawkid = hawkurl.split("matchId=")[-1]
            hawkid = int(hawkid.split("&ipl=1")[0])

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
    all_ipl_match_list, new_match_list = ipl_shot_data_json()
    match_data_procees(all_ipl_match_list, new_match_list)
    hawkeye_data()

if __name__ == '__main__':
    main_func()

    # with open('./bcci_shot_data_scrapper/ipl_shot_data/hawkeyeid_matchid.csv', 'r') as f:
    #     next(f)
    #     for l in f:
    #         hawk_match_pair = l.replace(' ', '').strip().split(',')

    #         if int(hawk_match_pair[0]) > 1855:
    #             hawkeye_main('Test', hawk_match_pair[0], hawk_match_pair[1], 'ipl')
