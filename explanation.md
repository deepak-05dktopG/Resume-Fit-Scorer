# Design and Evaluation Notes

## 1. Design Parameter Chosen

Required and preferred criteria use configurable weights in `config/scoring.yaml` (`2.0` and `1.0` in the current configuration). Keeping these values outside Python makes the importance policy easy to inspect and change without rewriting the scoring formula.

The LLM performs criterion extraction and evidence-based criterion scoring. Python and Pydantic validate those results, while Python performs deterministic weighted aggregation. This prevents the LLM from controlling the final arithmetic score.

## 2. One Failure Actually Observed

The initial Groq model, `llama-3.3-70b-versatile`, produced a real `404 model_not_found` error. This was a model availability/provider configuration issue, not a valid scoring failure. The configured model was changed to `openai/gpt-oss-120b`, after which the real extraction and scoring flow worked.

## 3. One Metric Tracked

The tracked metric is end-to-end API latency: the practical time from submitting a job description and resume to receiving the final response.

Latency was observed during real API and Swagger runs to understand practical response time, but no persistent numeric latency dataset was collected. A useful future improvement would be persistent latency tracking across multiple runs, alongside request-level cost tracking.

## 4. What Was Not Finished + Next Step

Production deployment, authentication, a frontend, and a database were not implemented because they were outside the assignment's required scope.

The meaningful next step is to evaluate calibration on a larger labeled resume/JD dataset and track latency and cost across repeated runs.