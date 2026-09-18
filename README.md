# Resume to Job-Description Fit Scorer

## Objective

Resume to Job-Description Fit Scorer evaluates how well a resume matches a job description using an explainable, criterion-level workflow. Groq provides structured language analysis, while Python and Pydantic validate the results and calculate the final weighted score deterministically.

The project is a focused applied-AI system for an AI Engineer / Forward Deployed Engineer technical assessment.

## Status

Working prototype

## Walkthrough Video

A 5-minute walkthrough demonstrating the working API, an unseen input, the scoring implementation, and the LLM prompt used in the system.

[Watch the Walkthrough Video on Google Drive](https://drive.google.com/file/d/1mxMTf8YuEUN_9lLnWNdYDn9tEixKig2U/view?usp=sharing)

## Architecture / Pipeline

1. `POST /answer` receives a job description and a PDF or TXT resume.
2. PyMuPDF or UTF-8 decoding extracts resume text.
3. Groq extracts explicit required and preferred job criteria.
4. Groq evaluates each criterion against the resume using evidence-based scores.
5. Pydantic validates every structured LLM response.
6. Python applies YAML-configured weights and calculates the overall score.

The LLM does not calculate the final arithmetic score.

## Local Setup

### 1. Create and activate a Python virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

### 2. Install the project requirements

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Set the values in `.env`.

**Never commit `.env` or hardcode the API key.**

Environment variables:

- `GROQ_API_KEY`: Groq API key.
- `LLM_MODEL`: configured Groq model. The current configuration uses `openai/gpt-oss-120b`.
- `LLM_TEMPERATURE`: LLM temperature.
- `LLM_MAX_TOKENS`: maximum response tokens.

### 4. Start the FastAPI development server

```powershell
uvicorn app.main:app --reload
```

### 5. Health endpoint

Open:

[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 6. Swagger API documentation

Open:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The Swagger UI provides an interactive interface for submitting a job description and uploading a resume.

## Using `POST /answer`

In Swagger:

1. Open `POST /answer`.
2. Click **Try it out**.
3. Enter the job description.
4. Upload a `.pdf` or `.txt` resume.
5. Click **Execute**.
6. Inspect the returned overall score and criterion-level reasoning.

The response contains:

- `overall_score`
- criterion ID
- criterion name
- criterion importance
- criterion score
- evidence
- reasoning

The same endpoint can be called from PowerShell:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/answer" `
  -F "job_description=Python developer with FastAPI and REST API experience" `
  -F "resume=@samples/resume_1.txt"
```

Supported resume formats are PDF and TXT.

TXT files must be UTF-8.

PDFs with fewer than 50 non-whitespace extracted characters are rejected as unreadable.

## Scoring and Weights

Each criterion receives an evidence-based score:

- `0`: No evidence
- `1`: Weak or indirect evidence
- `2`: Partial evidence
- `3`: Strong evidence
- `4`: Direct and highly relevant evidence

Overall scoring is deterministic Python arithmetic.

Required and preferred criterion weights are loaded from [`config/scoring.yaml`](config/scoring.yaml).

Current configuration:

```yaml
weights:
  required: 2.0
  preferred: 1.0
```

The weighted overall score is normalized to a 0–100 scale.

## Error Handling

The API rejects:

- Empty job descriptions
- Missing resumes
- Unsupported file types
- Invalid TXT encoding
- Unreadable PDFs
- Malformed LLM JSON
- Invalid Pydantic output
- Provider failures
- Invalid scoring configuration

Errors are returned through controlled HTTP responses.

Secrets, stack traces, and raw provider responses are not returned to API clients.

## Current Implemented Functionality

- FastAPI application with API metadata.
- `GET /health` health endpoint.
- `POST /answer` end-to-end scoring endpoint.
- Environment-based settings for the Groq API key and LLM configuration.
- PDF and UTF-8 TXT document parsing.
- Controlled handling of unsupported, empty, invalid, or unreadable documents.
- LLM-based job-description criterion extraction.
- Pydantic validation of structured LLM responses.
- Criterion-level resume scoring using a 0–4 evidence-based rubric.
- Explicit handling of LLM failures and malformed output.
- Deterministic Python overall scoring.
- Configurable required/preferred scoring weights.
- Three-sample calibration tests.
- Interactive Swagger documentation.

The parser extracts PDF text from every page and marks PDFs with fewer than 50 non-whitespace characters as unreadable.

Criteria extraction asks the configured Groq model for explicit required and preferred criteria and rejects malformed or invalid structured output.

Resume scoring evaluates each criterion independently.

The final score is calculated in Python using weights from `config/scoring.yaml`.

## Calibration and Sample Run

The three files in `samples/` are synthetic resumes used for calibration and end-to-end testing.

An observed real Swagger/API run using the sample job description produced:

| Sample | Observed overall score |
| --- | ---: |
| `resume_1.txt` | 100 |
| `resume_2.txt` | 66 |
| `resume_3.txt` | 23 |

These are observed results for synthetic sample data. They are not claims of validated hiring accuracy or statistical validation.

The three samples provide different levels of evidence against the job requirements, allowing the scoring behavior and relative consistency to be inspected.

The real Swagger workflow was tested end-to-end.

## Tests

Run the complete deterministic test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The test suite covers parsing, LLM response validation, criterion scoring, weighted aggregation, calibration, and API behavior.

## Project Structure

```text
resume-fit-scorer/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   ├── criteria_extractor.py
│   │   ├── scorer.py
│   │   └── llm_client.py
│   └── utils/
│       ├── __init__.py
│       └── text_utils.py
├── config/
│   └── scoring.yaml
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_scoring.py
│   ├── test_api.py
│   └── test_calibration.py
├── samples/
│   ├── jd.txt
│   ├── resume_1.txt
│   ├── resume_2.txt
│   └── resume_3.txt
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── explanation.md
```