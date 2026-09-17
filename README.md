# Resume to Job-Description Fit Scorer

## Objective

Resume to Job-Description Fit Scorer will evaluate how well a resume matches a job description using an explainable scoring workflow supported by Groq's Llama 3.3 70B model. The project is designed as a focused applied-AI system for an AI Engineer / Forward Deployed Engineer technical assessment.

## Status

Under development

## Planned capabilities

- Parse resume and job-description text, including PDF input.
- Extract and organize job criteria.
- Score resume fit against explicit criteria.
- Use Groq's Llama 3.3 70B for structured language analysis.
- Return explainable scores, strengths, gaps, and supporting evidence through a FastAPI API.

## Local setup

1. Create and activate a Python virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   On macOS or Linux, activate it with:

   ```bash
   source .venv/bin/activate
   ```

2. Install the project requirements:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Create a local environment file from the example:

   ```powershell
   Copy-Item .env.example .env
   ```

   Set `GROQ_API_KEY` in `.env` when LLM functionality is added. Never commit the `.env` file or hardcode the key.

4. Start the FastAPI development server:

   ```powershell
   uvicorn app.main:app --reload
   ```

5. Access the health endpoint at [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

## Current implemented functionality

- FastAPI application with basic title and description.
- `GET /health` endpoint returning the service status.
- Environment-based settings for the Groq API key and LLM configuration.
- PDF and UTF-8 TXT document parsing with controlled errors for unsupported, empty, invalid, or unreadable documents.
- LLM-based job-description criterion extraction with Pydantic validation of the structured response.

The parser extracts PDF text from every page and marks PDFs with fewer than 50 non-whitespace characters as unreadable. Criteria extraction asks Groq's configured Llama model for explicit required and preferred criteria and rejects malformed or invalid structured output. Resume scoring will be added incrementally in later steps.
