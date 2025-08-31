import json
import numpy as np
import pandas as pd


with open('dataset.json', 'r') as f:
    dataset = json.load(f)

with open('post_id_divisions.json', 'r') as f:
    post_id_divisions = json.load(f)

# Create a list of dictionaries to build the DataFrame
data_list = []
for post_id, data in dataset.items():
    source = post_id.split('_')[-1]

    # The 'annotators' list can be empty, handle this case
    if not data['annotators']:
        continue

    data_list.append({
        'post_id': post_id,
        'text': " ".join(data['post_tokens']),
        'source': source,
        'annotations': data['annotators'] # Changed key name for clarity
    })



# Create the DataFrame
df = pd.DataFrame(data_list)
df_exploded = df.explode('annotations')
annotations_df = df_exploded['annotations'].apply(pd.Series)
df_final = pd.concat([
    df_exploded.drop(['annotations'], axis=1).reset_index(drop=True), 
    annotations_df.reset_index(drop=True)
], axis=1)
df_final = df_final[['post_id', 'text', 'source', 'label', 'target']]

# Display the first 5 rows
print(df_final.sample(50))



# convert to parquet
df_final.to_parquet('Data.parquet', index=False)

print("\nSuccessfully exported DataFrame to 'Data.parquet'")

# To prove it worked, you can read it back
df_read = pd.read_parquet('Data.parquet')

print("\nDataFrame read back from Parquet file:")
print(df_read)