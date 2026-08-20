# Google Ads MCP Agent API (`google-ads-agent-api`)

A containerized **FastAPI** microservice that wraps the **Google Ads Model Context Protocol (MCP)** server over `stdio` and connects to **OpenAI GPT-4o** for multi-turn conversational querying, performance analysis, and automated insights.

---

## System Requirements

* **Docker & Docker Compose** (Recommended for production/server)
* *OR* **Python 3.12+** and **[`uv`](https://docs.astral.sh/uv/)** (for local development)

---

## Credentials Configuration

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



---

## Production Deployment (Docker Compose)

### 1. Build and Run

```bash
docker compose up -d --build
```

### 2. View Live Logs

```bash
docker compose logs -f
```

### 3. Stop or Uninstall

To stop the service and wipe the container, image, and cache:

```bash
chmod +x uninstall.bash
./uninstall.bash
```

---

## Local Development (Without Docker)

1. Create a virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```


2. Start the Uvicorn development server:
```bash
uvicorn main_mcp:app --host 0.0.0.0 --port 6161 --reload
```



---

## API Reference

The service runs on port `6161`. Interactive Swagger documentation is available at `http://localhost:6161/docs`.

* **`POST /chat`**: Main OpenAI iterative agent endpoint.
* **Payload:** `{"prompt": "Ağustos ayında en çok harcama yapan kampanyalar hangileri?"}`


* **`POST /execute-tool`**: Direct execution of a Google Ads MCP tool without AI interpretation.
* **Payload:** `{"tool_name": "list_campaigns", "arguments": {}}`


* **`GET /tools`**: Lists all exposed Google Ads MCP tools and JSON parameter schemas.
