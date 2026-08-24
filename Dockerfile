# Use official Python lightweight image
FROM python:3.12-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies (build-essential + git are required for pip git installs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally
RUN pip install --no-cache-dir uv

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install FastAPI dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Expose the port Uvicorn runs on
RUN pip install --no-cache-dir -e ./GoogleAdsMCP
EXPOSE 6161

# Command to run the FastAPI application
CMD ["uvicorn", "main_mcp:app", "--host", "0.0.0.0", "--port", "6161"]