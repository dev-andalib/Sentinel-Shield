from flask import Flask, request, jsonify
from transformers import pipeline
from typing import Any, Dict
import time

app = Flask(__name__)

print("Loading AI models...")
classifier_toxicity = pipeline(
    "text-classification",
    model="unitary/toxic-bert",
    return_all_scores=True
)
classifier_hate = pipeline(
    "text-classification",
    model="cardiffnlp/twitter-roberta-base-hate",
    return_all_scores=True
)
classifier_suicide = pipeline(
    "text-classification", 
    model='j-hartmann/emotion-english-distilroberta-base',
    return_all_scores=True
)
print("Models loaded successfully!")

# Thresholds for each label
thresholds = {
    'toxic': 0.7,
    'severe_toxic': 0.9,
    'obscene': 0.7,
    'threat': 0.7,
    'insult': 0.7,
    'hate': 0.7,
    'offensive': 0.7,
    'suicide': 0.7
}

positive_labels_model1 = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult']
positive_labels_model2 = ['hate', 'offensive']
positive_labels_model3 = ['suicide']
risk_emotions = {"sadness", "fear", "anger", "disgust"}
protective_emotions = {"joy", "love", "neutral", "surprise"}
emotion_threshold = 0.8 



def _normalize_result_item(raw: Any) -> Dict[str, Any]:
    """
    Ensure a result item has {'label': ..., 'score': ...}.
    Handles dicts and (label, score) or [label, score] pairs.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            label = raw[0]
            score = raw[1]
            return {"label": label, "score": score}
        except Exception:
            pass
    return {"label": None, "score": 0.0}

@app.route('/analyze', methods=['POST'])
def analyze_text():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Invalid input, 'text' field is required."}), 400

    text_to_analyze = data['text']
    flagged = []

    # time measure for inference
    start = time.perf_counter()
    # Model 1: Toxicity
    results1 = classifier_toxicity(text_to_analyze)
    for raw_item in results1[0]:
        item = _normalize_result_item(raw_item)
        label = item.get('label')
        score = float(item.get('score', 0.0))
        if label in positive_labels_model1 and score > thresholds.get(label, 0.7):
            flagged.append({
                "type": "Toxicity/Insult",
                "label": label,
                "score": round(score, 4)
            })

    # Model 2: Hate speech
    results2 = classifier_hate(text_to_analyze)
    for raw_item in results2[0]:
        item = _normalize_result_item(raw_item)
        label = item.get('label')
        score = float(item.get('score', 0.0))
        if label in positive_labels_model2 and score > thresholds.get(label, 0.7):
            flagged.append({
                "type": "Hate/Offensive",
                "label": label,
                "score": round(score, 4)
            })

    # Model 3: Suicide
    results_em = classifier_suicide(text_to_analyze)
    normalized_em = [_normalize_result_item(r) for r in (results_em[0] if results_em and isinstance(results_em[0], (list, tuple)) else results_em)]
    top_em = max(normalized_em, key=lambda x: x.get("score", 0.0))
    em_label = str(top_em.get("label", "")).lower()
    em_score = float(top_em.get("score", 0.0))

    # flag if high-risk emotion above threshold (adjust logic to your needs)
    if em_label in risk_emotions and em_score >= emotion_threshold:
        flagged.append({
            "type": "Emotion",
            "label": em_label,
            "score": round(em_score, 4)
        })

    # time end
    elapsed = time.perf_counter() - start
    print(f"inference took {elapsed:.4f}s")


    # flagging logic
    if flagged:
        sorted_flags = sorted(flagged, key=lambda x: x['score'], reverse=True)
        return jsonify({
            "status": "flagged",
            "details": sorted_flags
        })
    else:
        return jsonify({"status": "not_flagged"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)