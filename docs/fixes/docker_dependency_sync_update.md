# Docker Dependency Sync Update

Date: 2025-01-08

Added missing runtime dependencies to `backend/requirements.txt` so Docker builds include the same critical packages as the dev environment:

Added:
- python-dotenv>=0.21.0
- asyncssh>=2.14.2
- google-generativeai>=0.8.0
- openai-agents>=0.0.6

Reason: Dockerfile currently installs only `requirements.txt`. These packages existed only in `pyproject.toml`, causing import failures in the container (OpenAIAgent, Hop SSH, Imagen tool).

Also marked `requirements-agentic.txt` as deprecated to reduce fragmentation.

Next Step (preferred long-term): Modify Dockerfile to install from `pyproject.toml` instead of `requirements.txt`.
