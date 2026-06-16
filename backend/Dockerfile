FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY src/ ./src/
COPY ../ppt_engine ./ppt_engine

# Install backend deps (skip uv_build, use pip directly)
RUN pip install --no-cache-dir \
    fastapi>=0.115.0 \
    httpx>=0.27.0 \
    pydantic>=2.8.0 \
    python-pptx>=1.0.2 \
    python-multipart>=0.0.9 \
    "uvicorn[standard]>=0.30.0" \
    "psycopg[binary]>=3.1.0" \
    "Pillow>=10.0.0"

# Install ppt_engine as local package
RUN pip install --no-cache-dir ./ppt_engine

EXPOSE 8010

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
