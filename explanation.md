# Project structure

The project is organized around a small FastAPI application. Service modules will own parsing, criteria extraction, scoring, and Groq client integration as those capabilities are implemented. Shared text helpers belong in `app/utils`, configuration belongs in `config`, and focused tests belong in `tests`.

This initial step intentionally contains no application implementation logic.
