# Google Ads MCP Agent API & Comment Analyzer

A containerized microservice running **FastAPI**, wrapping the **Google Ads Model Context Protocol (MCP)** server over `stdio` and integrating **Ollama** for local comment moderation and analysis alongside OpenAI GPT-4o for ad queries.



## System Requirements

* **Git**
* **Docker & Docker Compose** (Recommended)
* *OR* **Python 3.12+**, **[`uv`](https://docs.astral.sh/uv/)**, and local **[Ollama](https://ollama.ai/)** (for local development)



## 1. Clone the Repository (With Submodules)

This project contains Git submodules (`GoogleAdsMCP` and `comment_analyzer`). You must clone with the `--recurse-submodules` flag so the dependencies are populated:

```bash
git clone --recurse-submodules <REPOSITORY_URL>
cd <PROJECT_DIR>
```

If you already cloned the repository without submodules, initialize and fetch them before proceeding:

```bash
git submodule update --init --recursive
```

To pull the latest changes alongside submodule updates later:

```bash
git pull --recurse-submodules
```



## 2. Credentials Configuration

Create `config.json` in the root directory before starting the containers:

1. Copy the example configuration:

```bash
cp config_example.json config.json
```

2. Add your credentials to `config.json`:

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



## 3. Deployment (Docker Compose)

### Build and Start

Run Docker Compose in detached mode:
```bash
docker compose up -d --build
```

**Automated Lifecycle:**

1. `ollama` starts on port `11434`.
2. `ollama-pull` waits for Ollama to become healthy, pulls `qwen2.5:3b`, and exits.
3. `google-ads-agent-api` installs the local submodule dependency (`GoogleAdsMCP`) and starts on port `6161` once model provisioning completes.

### View Live Logs

Monitor all services or track individual containers:

```bash
# All service logs
docker compose logs -f

# Track model download progress
docker compose logs -f ollama-pull

# API application logs
docker compose logs -f google-ads-agent-api
```

### Stop or Reset

Stop containers:
```bash
docker compose down
```

Wipe containers, cached models, volumes, and temporary local files:

```bash
# Clean deinstallation from scratch (clears models and volumes):
docker compose down -v

# Or run the cleanup script:
chmod +x uninstall.bash
./uninstall.bash
```



## 4. Local Development (Without Docker)

1. Ensure Ollama is running locally and pull the target model:

```bash
ollama run qwen2.5:3b
```

2. Verify submodules are populated:

```bash
git submodule update --init --recursive

```

3. Create a virtual environment and install dependencies:

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

4. Start the development server:

```bash
uvicorn main_mcp:app --host 0.0.0.0 --port 6161 --reload
```

---

## API Reference

The service runs on port `6161`. Interactive Swagger documentation is available at `http://localhost:6161/docs`.

* **`POST /comments/analyze`**: Batch moderation and sentiment analysis for customer comments via Ollama (`qwen2.5:3b`).
* **`POST /chat`**: OpenAI agent querying Google Ads data via MCP tools.
* **`POST /execute-tool`**: Direct execution of a Google Ads MCP tool without LLM interpretation.
* **`GET /tools`**: Lists all exposed Google Ads MCP tools and JSON parameter schemas.