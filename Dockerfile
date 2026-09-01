# Use official Python lightweight image
FROM python:3.12-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally
RUN pip install --no-cache-dir uv

# Copy root requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container (including GoogleAdsMCP and comment_analyzer)
COPY . .

# Pre-build and sync the MCP virtual environment at build time
RUN cd GoogleAdsMCP && uv sync --frozen

EXPOSE 6161

# Command to run the FastAPI application
CMD ["uvicorn", "main_mcp:app", "--host", "0.0.0.0", "--port", "6161"]