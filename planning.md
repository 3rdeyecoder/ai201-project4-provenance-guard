# Provenance Guard Planning

## Overview
Provenance Guard is a Flask-based API that analyzes submitted text and returns a transparency label describing the estimated likelihood that the writing was AI-generated. The system combines two independent signals: an LLM-based assessment and a stylometric heuristic score. It also records each submission and appeal in a structured audit log.

## Detection Signals
### Signal 1: LLM-based classification
- Measures: semantic and stylistic coherence as judged by an LLM prompt that asks whether the passage reads as human-written or AI-generated.
- Why it helps: language models often produce text that is polished, evenly balanced, and structurally consistent in ways that differ from human writing.
- Output: a score between 0.0 and 1.0 where 0.0 means strongly human-like and 1.0 means strongly AI-like.
- Blind spots: it can overfit to surface-level fluency and may miss subtle human writing that is highly polished or heavily edited AI output that sounds casual.

### Signal 2: Stylometric heuristics
- Measures: sentence-length variance, punctuation density, and type-token ratio (vocabulary diversity) to detect structural uniformity.
- Why it helps: AI-generated writing often shows smoother, more uniform sentence structure and vocabulary usage than human writing.
- Output: a score between 0.0 and 1.0 where 0.0 means strongly human-like and 1.0 means strongly AI-like.
- Blind spots: a poem, a short informal message, or a text packed with repetition could be misread because the metrics are not semantic.

### Combination strategy
- The combined confidence score is a weighted average of the two signals: $0.6 \times \text{llm_score} + 0.4 \times \text{stylometric_score}$.
- This keeps the LLM signal slightly more influential while still grounding the result in measurable structure.

## Uncertainty Representation
- A score below 0.35 is treated as likely human-written.
- A score between 0.35 and 0.70 is treated as uncertain.
- A score above 0.70 is treated as likely AI-generated.
- A confidence score of 0.6 means the system sees mixed evidence and should present a cautious, non-definitive label rather than a categorical verdict.

## Transparency Label Design
- High-confidence AI result: "Likely AI-generated. This text appears to have characteristics associated with AI writing."
- High-confidence human result: "Likely human-written. This text appears to reflect human authorship patterns."
- Uncertain result: "Uncertain classification. The evidence is mixed, so this result should be treated as a provisional signal rather than a definitive judgment."

## Appeals Workflow
- Anyone who submits content can appeal the result by providing a `content_id` and `creator_reasoning`.
- When an appeal is received, the content status changes to `under_review`, a new audit entry is appended with the appeal reasoning, and the response confirms that the appeal was received.
- A human reviewer can inspect the audit log and see both the original classification decision and the appeal record.

## Anticipated Edge Cases
- A poem with repeated phrasing and simple vocabulary may score as AI-generated because the stylometric metrics look unusually uniform.
- A polished human essay with very consistent sentence structure may score as AI-generated because the heuristic signal is not sensitive to writer intent or domain context.
- Short texts may be unstable because both signals have limited evidence.

## Architecture
```text
POST /submit
  -> validate input
  -> Signal 1: LLM classifier -> llm_score
  -> Signal 2: stylometric heuristic -> stylometric_score
  -> combine scores -> confidence + label
  -> append audit log entry -> response with content_id

POST /appeal
  -> find submission by content_id
  -> mark status as under_review
  -> append appeal audit entry
  -> return confirmation
```

Submission flow: a request to `/submit` receives raw text and creator metadata, runs the two detection signals, combines them into a confidence score and label, writes a structured audit entry, and returns a `content_id` so the submission can be referenced later. Appeal flow: `/appeal` receives the `content_id` and a reason from the creator, updates the content status to `under_review`, and appends a new audit entry so reviewers can see the original decision and the appeal together.

## AI Tool Plan
### M3: submission endpoint + first signal
- Provide the detection signals section and the architecture diagram.
- Ask for a Flask app skeleton with a `POST /submit` route and a first-signal scoring function.
- Verify by calling the endpoint directly and checking that the response includes `content_id`, `attribution`, `confidence`, and `label`.

### M4: second signal + confidence scoring
- Provide the detection signals section, the uncertainty representation section, and the architecture diagram.
- Ask for a stylometric signal function and the scoring logic that combines both signals into a single confidence score.
- Verify by testing clearly AI-like, clearly human-like, and borderline inputs.

### M5: production layer
- Provide the label design, appeals workflow, and architecture diagram.
- Ask for label generation logic and the `/appeal` endpoint.
- Verify that all three label variants are reachable and that an appeal changes status and appears in the audit log.
