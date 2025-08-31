from flask import Flask, request, jsonify
from transformers import pipeline
from model import context_gen

# Initialize the Flask app
app = Flask(__name__)

# Load the AI model from Hugging Face
# This pipeline simplifies the process to a few lines of code [cite: 14]
# We'll use a pre-trained model for toxicity detection.
print("Loading AI model...")
classifier = context_gen
print("Model loaded successfully!")

# Define the API endpoint for analysis
@app.route('/analyze', methods=['POST'])
def analyze_text():
    data = request.get_json()
    print(data)
    if not data or 'text' not in data:
        return jsonify({"error": "Invalid input, 'text' field is required."}), 400

    text_to_analyze = data['text']
    
    # The entire AI logic is handled by this one line [cite: 14]
    results = classifier(text_to_analyze)
    
    # We only care about the 'toxic' label for this prototype
    toxic_result = next((item for item in results if item['label'] == 'toxic'), None)

    # The backend will respond with a JSON object [cite: 25]
    if toxic_result and toxic_result['score'] > 0.7: # Setting a confidence threshold
        return jsonify({"label": "toxic", "score": toxic_result['score']})
    else:
        return jsonify({"label": "not_toxic", "score": 0})

# This allows you to run the app directly
if __name__ == '__main__':
    app.run(debug=True, port=5000)