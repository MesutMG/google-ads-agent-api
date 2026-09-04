FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY requirements.txt .
COPY GoogleAdsMCP/ GoogleAdsMCP/

RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

EXPOSE 6161

CMD ["uvicorn", "main_mcp:app", "--host", "0.0.0.0", "--port", "6161"]