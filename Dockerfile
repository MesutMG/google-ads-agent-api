FROM python:3.12-slim

WORKDIR /app

<<<<<<< HEAD
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

=======
# Set environment variables for Python & UV
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=0

# Install system dependencies
>>>>>>> 62bccee (Analyze and Dockerfile optimizations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY requirements.txt .
COPY GoogleAdsMCP/ GoogleAdsMCP/

RUN uv pip install --system --no-cache -r requirements.txt

<<<<<<< HEAD
COPY . .

EXPOSE 6161

=======
# Pre-cache GoogleAdsMCP environment before full codebase copy
COPY GoogleAdsMCP/pyproject.toml GoogleAdsMCP/uv.lock GoogleAdsMCP/
RUN cd GoogleAdsMCP && uv sync --frozen --no-install-project

# Copy application codebase
COPY . .

# Finalize MCP environment with source files
RUN cd GoogleAdsMCP && uv sync --frozen

EXPOSE 6161

# Run FastAPI via Uvicorn
>>>>>>> 62bccee (Analyze and Dockerfile optimizations)
CMD ["uvicorn", "main_mcp:app", "--host", "0.0.0.0", "--port", "6161"]