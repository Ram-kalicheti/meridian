FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY extractor/ ./extractor/
COPY quality/ ./quality/
COPY telemetry/ ./telemetry/

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
