# syntax=docker/dockerfile:1
#
# Example Dockerfile for Prefect deployments using git-based code retrieval.
#
# This image installs only the runtime dependencies defined in pyproject.toml.
# Code is NOT baked in — Prefect pulls it from GitHub at runtime via the
# `pull` step in prefect.yaml (prefect.deployments.steps.git_clone).
#
# Build (date-based tag):
#   docker buildx build --platform linux/amd64 -t <your-registry>/mm2-sanbox:$(date +%Y-%m-%d) .
#
# Pin the Prefect version to match the project requirement (prefect>=3.6.4).
# Update this tag when you bump the version in pyproject.toml.
FROM --platform=linux/amd64 prefecthq/prefect:3.6.24-python3.12

WORKDIR /app

# Copy only the files uv needs to resolve and install dependencies.
# The project source is intentionally excluded — it is retrieved from GitHub
# at flow run time via the git_clone pull step in prefect.yaml.
COPY pyproject.toml uv.lock ./

# Install runtime dependencies into the system Python.
# uv export produces a pinned requirements.txt from the lockfile, then
# uv pip install --system puts packages where Prefect's runner can find them
# (/usr/local/lib/python3.12/site-packages) rather than a project venv.
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt \
    && uv pip install --system --no-cache-dir -r /tmp/requirements.txt
