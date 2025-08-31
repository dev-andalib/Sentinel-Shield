import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans


print("Loading the Sentence Transformer model ")
model = SentenceTransformer('all-MiniLM-L6-v2') # context analysis
print("Model loaded.")


df = pd.read_parquet('D:/Projects/SAFEGUARD/Data/Final_Trauma_Data.parquet')
df = df.drop('post_id', axis=1)
df = df.drop('source', axis=1)


# --- 3. Generate Embeddings ---
print("Generating embeddings for all texts...")
# The .encode() method converts our text into numerical vectors
embeddings = model.encode(df['text'].tolist())
print(f"Generated {len(embeddings)} embeddings.")

# --- 4. Perform Clustering ---
# We will group the texts into 4 clusters, since we have 4 distinct topics.
num_clusters = 20
kmeans = KMeans(n_clusters=num_clusters, random_state=42)

# Fit the model to our embeddings
kmeans.fit(embeddings)

# Get the cluster assignment for each text
cluster_labels = kmeans.labels_

# --- 5. Analyze the Results ---
# Add the cluster labels to our original DataFrame
df['cluster'] = cluster_labels

print("\n--- Analyzing Cluster Results ---")

# Loop through each unique cluster and print the texts belonging to it
for i in range(num_clusters):
    print(f"\n--- Cluster {i} ---")
    
    # Get all rows from the DataFrame that belong to the current cluster
    cluster_texts = df[df['cluster'] == i]['text'].tolist()
    
    # Print each text in the cluster
    count = 0
    for text in cluster_texts:
        if count <= 10:
            print(f"- {text}")
        count += 1
    
    print(f"Total texts in this cluster: {len(cluster_texts)}")