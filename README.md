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

2. Install the foundation dependencies:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Create a local environment file and add your Groq API key:

   ```powershell
   Copy-Item .env.example .env
   ```

   Set `GROQ_API_KEY` in `.env`. Never commit the `.env` file or hardcode the key.

The application and tests will be added incrementally in later development steps.
