# AI201 Project 4 - Provenance Guard

## Overview

Provenance Guard is a Flask API that estimates whether a submitted passage looks more like AI-generated text or human-written text. It combines two independent signals: an LLM-based assessment and a stylometric heuristic score. The service returns a transparency label, records submissions and appeals in a structured audit log, and applies rate limiting to protect the endpoint from abuse.

## Architecture

The submission flow begins at `/submit`, where the API validates the incoming JSON payload and extracts the writer's text. The text is scored by two independent signals:

1. A Groq-backed LLM judge that evaluates whether the passage reads as human or AI-like.
2. A stylometric heuristic that looks at sentence-length variance, punctuation density, and type-token ratio.

The two scores are combined into a single confidence value from 0.0 to 1.0. The service then maps that confidence to one of three transparency labels and writes an audit entry containing the classification details and a new `content_id`. The appeal flow uses the same `content_id` to update the record to `under_review` and append a second entry describing the appeal.

## Features

- LLM-as-Judge classification
- Stylometric analysis
- Confidence scoring
- Audit logging
- Flask API
- Transparency labels
- Appeals workflow
- Rate limiting

## Technologies

- Python
- Flask
- Groq API
- Flask-Limiter
- JSON
- Python-dotenv

## Project Structure

- planning.md
- app.py
- requirements.txt
- .env
- test_app.py

## Detection Signals

- LLM-based classification: measures semantic and stylistic coherence by asking an LLM to score the text from 0.0 (human-like) to 1.0 (AI-like).
- Stylometric heuristics: measures structural regularity through sentence-length variance, punctuation density, and vocabulary diversity.
- Confidence scoring: uses a weighted average of $0.6 \times \text{llm_score} + 0.4 \times \text{stylometric_score}$.

## Transparency Labels

- High-confidence AI: "Likely AI-generated. This text appears to have characteristics associated with AI writing."
- High-confidence human: "Likely human-written. This text appears to reflect human authorship patterns."
- Uncertain: "Uncertain classification. The evidence is mixed, so this result should be treated as a provisional signal rather than a definitive judgment."

## Appeals Workflow

A creator can submit an appeal by posting to `/appeal` with a `content_id` and `creator_reasoning`. The system updates the content status to `under_review`, appends a new audit log entry with the appeal reasoning, and returns a confirmation payload.

## Rate Limiting

The submission endpoint is rate limited to 10 requests per minute and 100 requests per day per client address. This keeps the service practical for a single writer while reducing the chance of automated abuse.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Add a `.env` file with a `GROQ_API_KEY` value.
4. Run the app with `python app.py`.

## API Examples

### Submit text

```bash
curl -s -X POST http://localhost:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "The sun dipped below the horizon, painting the sky in hues of amber and rose.", "creator_id": "demo-user"}' | python -m json.tool
```

### Appeal a submission

```bash
curl -s -X POST http://localhost:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "PASTE_CONTENT_ID", "creator_reasoning": "I wrote this myself."}' | python -m json.tool
```

## Verification Evidence

- `pytest -q` -> `1 passed in 0.51s`
- Sample log entries are available via `GET /log`.
- Rate-limit behavior was checked by sending 12 rapid requests; the first 10 returned `200` and the later ones returned `429`.
- Example scores from the live classifier:
  - AI-like passage: `confidence = 0.5525`, label = `Uncertain classification...`
  - Human-like passage: `confidence = 0.1321`, label = `Likely human-written...`

## Known Limitations

A short poem or a highly repetitive passage may be misclassified because the stylometric signal is sensitive to uniform structure and repetition rather than meaning. The system is also not calibrated for production use without more data and human review.

## Spec Reflection

The planning document helped keep the API contract and label design consistent. The main divergence from the initial plan is that the Groq integration is intentionally graceful: when no API key is present, the service falls back to a neutral score so the app still runs locally.

## AI Usage

- I used the planning document to guide the Flask skeleton and endpoint contract.
- I also used the architecture notes to shape the audit log format and the appeal workflow.
- The implementation was then reviewed and adjusted to match the regression test and the required API behavior.

## Author

Darryl Jack
