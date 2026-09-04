# Dockerfile
#
# Builds the FastAPI backend for deployment (Cloud Run, Render, or any
# container platform). Installs the full requirements.txt for simplicity
# rather than maintaining a separate slimmed-down backend-only requirements
# file — a reasonable simplification for a hackathon deadline, at the cost
# of a somewhat larger image (xgboost/scikit-learn/streamlit aren't needed
# by the API itself, only by the offline pipeline and the frontend).
FROM python:3.12-slim

WORKDIR /app

# System deps needed to build psycopg2 and a few scientific packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application code and the small precomputed data artifacts
# committed to the repo (see .gitignore — clusters_full.parquet,
# scored_clusters.parquet, etc.). The raw dataset and large intermediate
# artifacts are intentionally NOT copied here; the API only ever reads the
# small serving-ready files.
COPY backend/ backend/
COPY data/ data/
COPY policy/ policy/
COPY agents/ agents/

# Cloud Run sets $PORT itself; default to 8080 for local/other-platform runs.
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn backend.api:app --host 0.0.0.0 --port ${PORT}
