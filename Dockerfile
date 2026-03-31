FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements/base.txt requirements/base.txt
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r requirements/base.txt -r backend/requirements.txt

# Source
COPY . .
RUN pip install --no-cache-dir -e .

# Migrate + seed on first run
RUN python -m alembic upgrade head && python backend/seed.py

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
