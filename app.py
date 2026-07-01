import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from groq import Groq

load_dotenv()

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

AUDIT_LOG: List[Dict[str, Any]] = []
SUBMISSIONS: Dict[str, Dict[str, Any]] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.lower())


def stylometric_score(text: str) -> float:
    if not text or not text.strip():
        return 0.5

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return 0.5

    word_counts = [len(_tokenize(sentence)) for sentence in sentences]
    avg_len = sum(word_counts) / len(word_counts)
    variance = sum((count - avg_len) ** 2 for count in word_counts) / len(word_counts)
    sentence_variance_score = min(1.0, variance / 200.0)

    words = _tokenize(text)
    if not words:
        return 0.5
    type_token_ratio = len(set(words)) / len(words)
    ttr_score = max(0.0, min(1.0, 1.0 - type_token_ratio))

    punctuation_density = len(re.findall(r"[.!?,;:-]", text)) / max(1, len(words))
    punctuation_score = min(1.0, punctuation_density * 2.5)

    combined = (sentence_variance_score * 0.4) + (ttr_score * 0.3) + (punctuation_score * 0.3)
    return round(max(0.0, min(1.0, combined)), 4)


def llm_signal(text: str) -> float:
    if not os.getenv("GROQ_API_KEY"):
        return 0.5

    prompt = (
        "You are evaluating whether a passage reads as human-written or AI-generated. "
        "Return ONLY a JSON object with keys 'score' and 'reason'. "
        "The score should be a number between 0.0 and 1.0 where 0.0 means strongly human-like and 1.0 means strongly AI-like."
        f"\n\nText:\n{text}"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            messages=[{"role": "system", "content": prompt}],
        )
        content = response.choices[0].message.content
        if isinstance(content, str):
            import json as json_module

            parsed = json_module.loads(content)
            score = float(parsed.get("score", 0.5))
            return round(max(0.0, min(1.0, score)), 4)
    except Exception:
        return 0.5

    return 0.5


def combine_scores(llm_score: float, stylometric_score: float) -> float:
    return round(max(0.0, min(1.0, (0.6 * llm_score) + (0.4 * stylometric_score))), 4)


def classify_text(text: str) -> Dict[str, Any]:
    llm_score = llm_signal(text)
    stylometric = stylometric_score(text)
    combined = combine_scores(llm_score, stylometric)

    if combined < 0.35:
        attribution = "likely_human"
        label = "Likely human-written. This text appears to reflect human authorship patterns."
    elif combined > 0.70:
        attribution = "likely_ai"
        label = "Likely AI-generated. This text appears to have characteristics associated with AI writing."
    else:
        attribution = "uncertain"
        label = "Uncertain classification. The evidence is mixed, so this result should be treated as a provisional signal rather than a definitive judgment."

    return {
        "attribution": attribution,
        "confidence": combined,
        "label": label,
        "llm_score": llm_score,
        "stylometric_score": stylometric,
    }


def append_log(entry: Dict[str, Any]) -> None:
    AUDIT_LOG.append(entry)


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    creator_id = payload.get("creator_id") or "anonymous"

    if not text:
        return jsonify({"error": "text is required"}), 400

    content_id = str(uuid.uuid4())
    result = classify_text(text)
    entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": _utc_now(),
        "attribution": result["attribution"],
        "confidence": result["confidence"],
        "llm_score": result["llm_score"],
        "stylometric_score": result["stylometric_score"],
        "status": "classified",
        "appeal_reasoning": None,
    }
    append_log(entry)
    SUBMISSIONS[content_id] = {
        "content_id": content_id,
        "creator_id": creator_id,
        "text": text,
        "status": "classified",
        "result": result,
    }

    return jsonify(
        {
            "content_id": content_id,
            "attribution": result["attribution"],
            "confidence": result["confidence"],
            "label": result["label"],
        }
    )


@app.route("/appeal", methods=["POST"])
def appeal():
    payload = request.get_json(silent=True) or {}
    content_id = payload.get("content_id")
    creator_reasoning = payload.get("creator_reasoning") or ""

    if not content_id:
        return jsonify({"error": "content_id is required"}), 400

    submission = SUBMISSIONS.get(content_id)
    if not submission:
        return jsonify({"error": "content_id not found"}), 404

    submission["status"] = "under_review"
    submission["appeal_reasoning"] = creator_reasoning

    entry = {
        "content_id": content_id,
        "creator_id": submission["creator_id"],
        "timestamp": _utc_now(),
        "attribution": submission["result"]["attribution"],
        "confidence": submission["result"]["confidence"],
        "llm_score": submission["result"]["llm_score"],
        "stylometric_score": submission["result"]["stylometric_score"],
        "status": "under_review",
        "appeal_reasoning": creator_reasoning,
    }
    append_log(entry)

    return jsonify({"content_id": content_id, "status": "under_review", "received": True})


@app.route("/log", methods=["GET"])
def log_entries():
    return jsonify({"entries": AUDIT_LOG[-10:]})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)
