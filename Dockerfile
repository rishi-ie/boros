FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create runtime directories
RUN mkdir -p session logs snapshots evals/scores memory/experiences \
    memory/evolution_records memory/sessions tasks/queue tasks/active \
    tasks/completed tasks/learning commands \
    eval-generator/shared/requests eval-generator/shared/results \
    eval-generator/sandboxes eval-generator/generated-tests \
    eval-generator/logs eval-generator/scoring

# Environment variables (supply at runtime via --env-file .env)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/..

# Default: run the unified launcher
CMD ["python", "run.py"]
