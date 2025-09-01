from flask import Flask, request, jsonify
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
import re
from flask_cors import CORS
import os
from typing import Dict, List, Optional

# Gemini imports
import google.generativeai as genai
import time
import threading
from datetime import datetime, timedelta
print(genai.__version__)

class RateLimiter:
    def __init__(self, requests_per_minute=59):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if we've exceeded our rate limit"""
        with self.lock:
            now = datetime.now()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < timedelta(minutes=1)]
            
            if len(self.requests) >= self.requests_per_minute:
                # Calculate how long to wait
                oldest_request = self.requests[0]
                wait_time = 60 - (now - oldest_request).total_seconds()
                if wait_time > 0:
                    print(f"⏳ Rate limit approached, waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                # Clear old requests after waiting
                self.requests = [req_time for req_time in self.requests 
                               if now - req_time < timedelta(minutes=1)]
            
            # Add current request
            self.requests.append(now)
            return True

# Initialize rate limiter
gemini_limiter = RateLimiter()

# Configure Gemini with API key
GOOGLE_API_KEY = 'AIzaSyAd1dtQobqAV21ohT1ZLSlAeWOxaubsBog'
os.environ['GOOGLE_API_KEY'] = GOOGLE_API_KEY
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")
print("API Key found, configuring Gemini client.")

# Configure the client
genai.configure(api_key=GOOGLE_API_KEY)

# Model configuration
generation_config = genai.types.GenerationConfig(
    temperature=0.9,
    top_p=1,
    top_k=1,
    max_output_tokens=2048,
)

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# Model configurations
base_config = genai.types.GenerationConfig(
    temperature=0.9,
    top_p=1,
    top_k=1,
    max_output_tokens=2048,
)

focused_config = genai.types.GenerationConfig(
    temperature=0.7,
    top_p=0.8,
    top_k=40,
    max_output_tokens=1024,
)

balanced_config = genai.types.GenerationConfig(
    temperature=0.8,
    top_p=0.9,
    top_k=20,
    max_output_tokens=1536,
)

# Initialize model pools with different versions and configurations
TRIGGER_MODELS = [
    genai.GenerativeModel('models/gemini-2.5-pro', generation_config=base_config, safety_settings=safety_settings),
    genai.GenerativeModel('models/gemini-1.5-pro-latest', generation_config=base_config, safety_settings=safety_settings),
    genai.GenerativeModel('models/gemini-1.5-pro-002', generation_config=base_config, safety_settings=safety_settings)
]

EXPLANATION_MODELS = [
    genai.GenerativeModel('models/gemini-2.5-pro', generation_config=focused_config, safety_settings=safety_settings),
    genai.GenerativeModel('models/gemini-1.5-pro-latest', generation_config=balanced_config, safety_settings=safety_settings),
    genai.GenerativeModel('models/gemini-1.5-pro-002', generation_config=focused_config, safety_settings=safety_settings)
]

# Model selection counters for round-robin
trigger_model_index = 0
explanation_model_index = 0

def get_next_trigger_model():
    global trigger_model_index
    model = TRIGGER_MODELS[trigger_model_index]
    trigger_model_index = (trigger_model_index + 1) % len(TRIGGER_MODELS)
    return model

def get_next_explanation_model():
    global explanation_model_index
    model = EXPLANATION_MODELS[explanation_model_index]
    explanation_model_index = (explanation_model_index + 1) % len(EXPLANATION_MODELS)
    return model

# Concept and explanation caching
CONCEPT_CACHE_SIZE = 100
concept_cache: Dict[str, List[str]] = {}
explanation_cache: Dict[str, str] = {}



# Text cleaning utilities
CHAT_WORDS = {
    "AFAIK": "As Far As I Know", "AFK": "Away From Keyboard",
    "ASAP": "As Soon As Possible", "ATM": "At The Moment",
    "BTW": "By The Way", "CU": "See You", "FYI": "For Your Information",
    "GN": "Good Night", "IDC": "I don't care", "ILY": "I love you",
    "IMU": "I miss you", "ADIH": "Another day in hell",
    "WYWH": "Wish you were here", "TIME": "Tears in my eyes",
    "FIMH": "Forever in my heart", "BFF": "Best friends forever"
}

CONTRACTION_MAP = {
    "dont": "don't", "isnt": "isn't", "arent": "aren't", "wasnt": "wasn't",
    "cant": "can't", "wont": "won't", "im": "i'm", "youre": "you're",
    "hes": "he's", "shes": "she's", "its": "it's", "theyre": "they're",
    "ive": "i've", "ill": "i'll", "yall": "you all"
}

def remove_urls(text):
    """Remove URLs from text"""
    return re.sub(r'https?://\S+|www\.\S+', '', text)

def remove_html_tags(text):
    """Remove HTML tags from text"""
    return re.sub(r'<.*?>', ' ', text)

def expand_chat_words(text):
    """Expand common chat abbreviations"""
    words = text.split()
    expanded = []
    for word in words:
        expanded_word = CHAT_WORDS.get(word.upper(), word)
        if expanded_word is not None:  # Handle potential None values
            expanded.append(str(expanded_word))
        else:
            expanded.append(word)
    return ' '.join(expanded)

def expand_contractions(text):
    """Expand contractions like dont to don't"""
    for word, expansion in CONTRACTION_MAP.items():
        text = re.sub(r'\b' + re.escape(word) + r'\b', expansion, text)
    return text

def normalize_text(text):
    """Normalize quotes and apostrophes"""
    return text.replace("'", "'").replace("`", "'").replace(""", '"').replace(""", '"')

def clean_text(text):
    """Master function to clean text"""
    text = remove_urls(text)
    text = remove_html_tags(text)
    text = expand_chat_words(text)
    text = text.lower()
    text = normalize_text(text)
    text = expand_contractions(text)
    return ' '.join(text.split())  # normalize whitespace

# Initialize the Flask app
app = Flask(__name__)
CORS(app) # Enable CORS for all routes


# Load the AI model from Hugging Face
# This pipeline simplifies the process to a few lines of code [cite: 14]
# We'll use a pre-trained model for toxicity detection.
print("Loading AI model...")
context_gen = SentenceTransformer('BAAI/bge-large-en-v1.5') 
print("Model loaded successfully!")



def get_or_generate_concepts(user_input: str) -> List[str]:
    """Get concepts from cache or generate new ones"""
    if not user_input.strip():
        return []
        
    # Check cache first
    if user_input in concept_cache:
        print("📎 Using cached concepts")
        return concept_cache[user_input]
    
    concepts = generate_trigger_concepts_gemini(user_input)
    
    # Basic LRU cache management
    if len(concept_cache) >= CONCEPT_CACHE_SIZE:
        concept_cache.pop(next(iter(concept_cache)))
    concept_cache[user_input] = concepts
    
    return concepts

def generate_content_explanation(content: str, user_story: str) -> str:
    """
    Generate a personalized explanation of why content might be triggering
    based on the user's background.
    """
    try:
        # Cache key combines content and user story
        cache_key = f"{content[:100]}:{user_story[:100]}"  # Use first 100 chars of each as key
        if cache_key in explanation_cache:
            print("📎 Using cached explanation")
            return explanation_cache[cache_key]

        prompt = (
            "You are an empathetic AI assistant specializing in trauma-informed care. "
            "Your task is to explain why specific content might be triggering for someone "
            "based on their personal experience. Be gentle and supportive in your explanation. "
            "Focus on the psychological connection between the content and potential triggers. "
            "Maintain privacy by not repeating specific details.\n\n"
            f"User's background context: '{user_story}'\n"
            f"Content to analyze: '{content}'\n\n"
            "Explain in 2-3 sentences why this content might be difficult for the user "
            "and why it might be better to avoid it. Be supportive and focus on wellbeing."
        )

        # Try each model in the pool until successful
        rate_limit_hit = False
        for model in EXPLANATION_MODELS:
            try:
                # Use rate limiter
                gemini_limiter.wait_if_needed()
                
                print(f"Generating explanation with model: {model.model_name}")
                response = model.generate_content(prompt)
                explanation = response.text.strip()
                
                # Cache the explanation
                explanation_cache[cache_key] = explanation
                return explanation
            except Exception as e:
                error_msg = str(e).lower()
                if "quota" in error_msg or "rate" in error_msg:
                    print(f"⚠️ Rate limit hit with {model.model_name}")
                    rate_limit_hit = True
                else:
                    print(f"❌ Model error with {model.model_name}: {str(e)}")
                continue  # Try next model

        # If all models failed
        if rate_limit_hit:
            return "This content contains themes or concepts that align with your specified triggers. Taking a moment to prepare yourself before viewing may be helpful."
        return "This content may be triggering based on your personal experience. Consider avoiding it for your wellbeing."

    except Exception as e:
        print(f"❌ Explanation generation error: {str(e)}")
        return "This content may be triggering based on your personal experience. Consider avoiding it for your wellbeing."

def generate_trigger_concepts_gemini(user_story: str) -> List[str]:
    """
    Uses a pool of Gemini models to extract and broaden 
    trigger concepts from a user's story.
    """
    if not user_story.strip():
        return []
        
    try:
        concepts_string = ""
        last_error = None
        
        # Try each model in the pool with retries
        for _ in range(len(TRIGGER_MODELS) * 2):  # Allow two full rotations through models
            try:
                # Check rate limit before making the request
                gemini_limiter.wait_if_needed()
                
                # Get next model from pool
                model = get_next_trigger_model()
                print(f"Trying model: {model.model_name}")
                
                # Careful prompt to extract triggers while preserving privacy
                prompt = (
                    "You are an expert AI assistant specializing in psychological triggers. "
                    "Your task is to analyze a user's description of a traumatic experience. "
                    "From this description, extract a list of generalized, abstract themes, "
                    "objects, and concepts that could be triggering. Do not include any of the user's "
                    "personal details. Output ONLY a comma-separated list of these concepts. "
                    f"Here is the user's experience: '{user_story}'"
                )

                response = model.generate_content(prompt)
                print(f"Response from model: \n")
                print(response)
                concepts_string = response.text.strip()
                break  # If successful, break the retry loop
                
            except Exception as e:
                last_error = e
                print(f"Model failed: {str(e)}")
                if _ == len(TRIGGER_MODELS) * 2 - 1:  # If this was the last attempt
                    print(f"❌ All trigger models failed. Last error: {str(last_error)}")
                continue  # Try next model
        
        # Validate and clean the response
        if not concepts_string:
            print("⚠️ Gemini returned empty response, using fallback")
            return [user_story]
            
        trigger_list = [
            concept.strip() 
            for concept in concepts_string.split(',') 
            if concept.strip()
        ]
        
        # Ensure we got something useful
        if not trigger_list:
            print("⚠️ No valid concepts extracted, using fallback")
            return [user_story]
            
        print(f"✅ Generated {len(trigger_list)} trigger concepts")
        return trigger_list

    except Exception as e:
        print(f"❌ Gemini API error: {str(e)}")
        return [user_story]  # Fallback to original input



# Define the API endpoint for analysis
@app.route('/analyze', methods=['POST'])
def analyze_text():
    data = request.get_json()
    print(f"\n✅ 1. RECEIVED DATA: {data}")
    if not data or 'text' not in data:
        return jsonify({"error": "Invalid input, 'text' field is required."}), 400

    # Clean and preprocess the input text
    input_text = data.get('text', '')
    clean_content = clean_text(input_text)
    print(f"🧹 2. CLEANED TEXT: {clean_content}")
    



    user_input_string = data.get('keywords', '') # Get the whole string first

    if user_input_string.strip() == '':
        print("DECISION: No keywords, not masking.")
        return jsonify({"action": "not_mask", "score": 0})


    # Get or generate trigger concepts with caching
    trigger_concepts = get_or_generate_concepts(user_input_string)
    print(f"🎯 Using trigger concepts: {trigger_concepts}")
    
    if not trigger_concepts:
        print("DECISION: No valid trigger concepts generated.")
        return jsonify({"action": "not_mask", "score": 0})

    # Use embedding similarity for scoring
    embed_input_text = context_gen.encode([clean_content])
    clean_keywords = [clean_text(keyword) for keyword in trigger_concepts]
    embed_user_input = context_gen.encode(clean_keywords)
    cosine_scores = util.cos_sim(embed_input_text, embed_user_input)
    max_score = cosine_scores.max().item()

    # Check if the score is greater than the threshold
    threshold = 0.5

    # --- Step 4: Log the result and decision ---
    print(f"🧠 3. CALCULATED SCORE: {max_score:.4f} (Threshold: {threshold})")

    if max_score > threshold:
        # Only generate explanation for content that exceeds threshold
        explanation = generate_content_explanation(clean_content, user_input_string)
        print(f"Generated explanation: {explanation}")  # Debug log
        response_data = {
            "status": "flagged",
            "action": "mask",
            "reason": f"Content matches your triggers (confidence: {max_score:.2f})",
            "explanation": explanation,
            "details": [{
                "type": "Trigger",
                "score": round(max_score, 4),
                "matched": True
            }]
        }
        print(f"Sending response: {response_data}")  # Debug log
        return jsonify(response_data)
    else:
        # For content below threshold, return without explanation
        return jsonify({
            "status": "not_flagged",
            "action": "not_mask",
            "score": max_score
        })



    
    
    

# This allows you to run the app directly
if __name__ == '__main__':
    app.run(debug=True, port=5000)