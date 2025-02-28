import requests
import json
import os
import datetime
import pandas as pd

def raw_data():

    def reshape_scores(scores):
        """Reshape scores data into a flattened dictionary format"""
        single_row = {}
        if not scores:
            return single_row
            
        for inning in scores:
            inning_no = inning['inning_no']
            for key, value in inning.items():
                if key != 'inning_no':  # Exclude 'inning_no' from the column names
                    column_name = f"inning_{inning_no}_{key}"
                    single_row[column_name] = value
        return single_row

    def reshape_other_info(info):
        """Reshape other match information into a flattened dictionary format"""
        # Check if the info is a dictionary
        if isinstance(info, dict):
            # Flatten the dictionary into key-value pairs
            return info
        elif isinstance(info, list):
            # If the info is a list, create a dictionary with indexes
            return {f"item_{i}": item for i, item in enumerate(info)}
        else:
            # If it's neither a dictionary nor a list, return it as a single value
            return {0: info}

    current_date = datetime.datetime.now()

    total_data = []
    for start_year in range(1800, 2100, 100):
        
        if start_year == 2000:
            end_year = start_year + int(current_date.strftime('%y'))
        else:
            end_year = start_year + 100

        ICC_SCHEDULE_URL = f"https://assets-icc.sportz.io/cricket/v1/schedule?client_id=tPZJbRgIub3Vua93%2FDWtyQ%3D%3D&feed_format=json&from_date={start_year}0101&competition_type_ids=2&lang=en&league_ids=1%2C9&pagination=false&timezone=0530&to_date={end_year}0101&timezone=0530"

        response = requests.get(ICC_SCHEDULE_URL, timeout=100)
        data = response.json()
        total_data.extend(data['data']['matches']) 


    df = pd.DataFrame(total_data)

    reshaped_data = df['scores'].apply(reshape_scores)
    reshaped_df = pd.DataFrame(reshaped_data.tolist())
    df = pd.concat([df.drop(columns='scores'), reshaped_df], axis=1)

    reshaped_other_info = df['other_info'].apply(reshape_other_info)
    reshaped_other_df = pd.DataFrame(reshaped_other_info.tolist())
    df = pd.concat([df.drop(columns='other_info'), reshaped_other_df], axis=1)

    # Reshape scores and other info from the raw data
    # reshaped_scores = []
    # reshaped_other_info = []
    # if not total_data:
    #     print("No data was retrieved from the API")
    #     return
        
    # # Convert list items to dictionaries if they're not already
    # total_data = [match if isinstance(match, dict) else match._asdict() for match in total_data]


    # for match in total_data:
    #     # Reshape scores
    #     scores_data = reshape_scores(match.get('scores', []))
    #     scores_data['match_id'] = match.get('match_id')
    #     reshaped_scores.append(scores_data)

    #     # Reshape other info
    #     other_info = reshape_other_info(match.get('other_info', {}))
    #     other_info['match_id'] = match.get('match_id')
    #     reshaped_other_info.append(other_info)

    # # Convert to DataFrames
    # scores_df = pd.DataFrame(reshaped_scores)
    # other_info_df = pd.DataFrame(reshaped_other_info)

    # # Merge the DataFrames if needed
    # df = pd.merge(scores_df, other_info_df, on='match_id', how='outer')

    # os.makedirs("icc", exist_ok=True)
    
    df.to_csv("./icc_odi_match_list.csv", index=False)
    with open(f"./icc_odi_match_list.json", 'w') as f:
        json.dump(total_data, f, indent=4)

# def 

if __name__ == '__main__':
    raw_data()
    # process_match_data()