# Google Ads MCP Agent API & Comment Analyzer

A containerized microservice running **FastAPI**, wrapping the **Google Ads Model Context Protocol (MCP)** server over `stdio` and integrating **Ollama** for local comment moderation and analysis alongside OpenAI GPT-4o for ad queries.



## System Requirements

* **Docker & Docker Compose** (Recommended)
* *OR* **Python 3.12+**, **[`uv`](https://docs.astral.sh/uv/)**, and local **[Ollama](https://ollama.ai/)** (for local development)



## Credentials Configuration

You must create `config.json` **before** starting the Docker containers to prevent Docker from mounting an empty directory.

1. Create a configuration file from the template:
```bash
cp config_example.json config.json
```

2. Open `config.json` and insert your credentials:
```json
{
  "developer_token": "YOUR_DEVELOPER_TOKEN",
  "client_id": "YOUR_OAUTH_CLIENT_ID",
  "client_secret": "YOUR_OAUTH_CLIENT_SECRET",
  "refresh_token": "YOUR_OAUTH_REFRESH_TOKEN",
  "login_customer_id": "YOUR_MCC_ID_IF_APPLICABLE",
  "google_ads_customer_id": "YOUR_TARGET_CUSTOMER_ID",
  "openai_api_key": "sk-proj-..."
}
```



## Deployment (Docker Compose)

### 1. Build and Start the Services

Run Docker Compose in detached mode:
```bash
docker compose up -d --build
```

**What this does:**

1. `ollama` starts on port `11434`.
2. `ollama-pull` waits for Ollama to become healthy, downloads `qwen2.5:3b`, and exits cleanly.
3. `google-ads-agent-api` starts on port `6161` once the model pull completes successfully.

### 2. View Live Logs

Monitor all services or track individual containers:

```bash
# All service logs
docker compose logs -f

# Watch model download progress
docker compose logs -f ollama-pull

# API application logs
docker compose logs -f google-ads-agent-api
```

### 3. Stop or Reset

Stop containers:
```bash
docker compose down
```

Wipe containers, cached models, images, and volumes:

```bash
# Clean deinstallation from scratch including the model:
docker compose down -v

# Or use the uninstall script:
chmod +x uninstall.bash
./uninstall.bash
```



## Local Development (Without Docker)

1. Ensure Ollama is installed locally and pull the model:

```bash
ollama run qwen2.5:3b
```

2. Create a virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

3. Start the Uvicorn development server:
```bash
uvicorn main_mcp:app --host 0.0.0.0 --port 6161 --reload
```



## API Reference

The service runs on port `6161`. Interactive Swagger documentation is available at `http://localhost:6161/docs`.

* **`POST /comments/analyze`**: Batch moderation and sentiment analysis for customer comments via Ollama (`qwen2.5:3b`).
* **`POST /chat`**: OpenAI agent querying Google Ads data via MCP tools.
* **`POST /execute-tool`**: Direct execution of a Google Ads MCP tool without LLM interpretation.
* **`GET /tools`**: Lists all exposed Google Ads MCP tools and JSON parameter schemas.