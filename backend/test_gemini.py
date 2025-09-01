import google.generativeai as genai
import os

# Get API key from environment
GOOGLE_API_KEY = 'AIzaSyAd1dtQobqAV21ohT1ZLSlAeWOxaubsBog'
os.environ['GOOGLE_API_KEY'] = GOOGLE_API_KEY

# Configure the library
genai.configure(api_key=GOOGLE_API_KEY)

print(f"Using google.generativeai version: {genai.__version__}")

# Test API connectivity
import requests
print("\nTesting API connectivity:")
try:
    r = requests.get('https://generativelanguage.googleapis.com/v1beta/models', 
                    params={'key': GOOGLE_API_KEY})
    print(f"API Status Code: {r.status_code}")
    print(f"API Response: {r.text[:200]}...")  # Show first 200 chars
except Exception as e:
    print(f"Connection Error: {str(e)}")

# List all available models
print("\nAvailable Models:")
try:
    for m in genai.list_models():
        print(f"- Name: {m.name}")
        print(f"  Supported methods: {m.supported_generation_methods}")
        print()
except Exception as e:
    print(f"Error listing models: {str(e)}")

# Test with a simple prompt
test_prompt = "Give me a three-word response about safety"

try:
    # Try different model names
    model_names = [
        'models/gemini-2.5-pro',
        'models/gemini-1.5-pro',
        'models/gemini-2.0-pro-exp',
        'models/gemini-1.5-pro-002'
    ]
    
    print("\nTrying different model names:")
    for model_name in model_names:
        try:
            print(f"\nTesting model name: {model_name}")
            model = genai.GenerativeModel(model_name)
            # Just try to initialize, don't generate yet
            print("✓ Model initialized successfully")
        except Exception as model_error:
            print(f"✗ Failed: {str(model_error)}")
            continue

    # Define generation config
    generation_config = genai.types.GenerationConfig(
        temperature=0.9,
        top_p=1,
        top_k=1,
        max_output_tokens=2048,
    )

    # Define safety settings
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE"
        },
    ]

    # Initialize model with both configs
    model = genai.GenerativeModel('models/gemini-2.5-pro',
                                generation_config=generation_config,
                                safety_settings=safety_settings)
    
    # Generate response
    response = model.generate_content(test_prompt)
    
    print("\n✅ API Connection Success!")
    print(f"Response: {response.text}")
    
except Exception as e:
    print("\n❌ API Error:")
    print(str(e))
