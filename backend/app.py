from flask import Flask, request, jsonify
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
import re


# Initialize the Flask app
app = Flask(__name__)

# Load the AI model from Hugging Face
# This pipeline simplifies the process to a few lines of code [cite: 14]
# We'll use a pre-trained model for toxicity detection.
print("Loading AI model...")
context_gen = SentenceTransformer('all-MiniLM-L6-v2') 
print("Model loaded successfully!")

# Define the API endpoint for analysis
@app.route('/analyze', methods=['POST'])
def analyze_text():
    data = request.get_json()
    print(f"\n✅ 1. RECEIVED DATA: {data}")
    if not data or 'text' not in data:
        return jsonify({"error": "Invalid input, 'text' field is required."}), 400

    tweet_text = data.get('text')
    user_input_string = data.get('keywords', '') # Get the whole string first
    
    # --- ADD THIS LOGIC ---
    # Split the string into a list of sentences. This handles cases where the string is empty.
    # It splits by periods, commas, exclamation marks, and question marks.
    
    user_input_list = [s.strip() for s in re.split(r'[.,!?]', user_input_string) if s.strip()]
     # Debugging line to check the split result
    if not user_input_list:
        print("DECISION: No keywords, not masking.")
        return jsonify({"action": "not_mask", "score": 0})
    # --- END OF NEW LOGIC ---

    # context generation
    embed_tweet_text = context_gen.encode([tweet_text])
    embed_user_input = context_gen.encode(user_input_list) # Use the new list here

    # Compute cosine similarity
    cosine_scores = util.cos_sim(embed_tweet_text, embed_user_input)

    # Find the highest similarity score
    max_score = cosine_scores.max().item() # Use .item() to get a standard Python float

    # Check if the highest score is greater than the threshold
    threshold = 0.50

    # --- Step 4: Log the result and decision ---
    print(f"🧠 3. CALCULATED SCORE: {max_score:.4f} (Threshold: {threshold})")

    
    if max_score > threshold:
        # It's good practice to send the score back to the frontend
        return jsonify({"action": "mask", "score": max_score})
    else:
        return jsonify({"action": "not_mask", "score": max_score})



    
    
    

# This allows you to run the app directly
if __name__ == '__main__':
    app.run(debug=True, port=5000)