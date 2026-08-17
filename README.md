# Google Ads AI Analyzer

A web application built with Laravel, Vue.js, and FastAPI that leverages OpenAI and the Google Ads Model Context Protocol (MCP) to query, analyze, and summarize Google Ads campaign data using natural language.

## Prerequisites

Ensure you have the following installed on your system before proceeding:

* **PHP 8.2+** & **Composer**
* **Node.js** & **npm**
* **Python 3.12+**
* **[`uv`](https://docs.astral.sh/uv/)** (Python package manager)
* Google Ads API Credentials (OAuth2 Client ID, Secret, and Refresh Token)
* OpenAI API Key

---

## Installation

### 1. Laravel Frontend/Backend Setup

1. Clone the repository and navigate to the project root:
```bash
git clone <your-repository-url>
cd googleAdsAnalyzer-bertramdev

```


2. Install PHP and Node.js dependencies:
```bash
composer install
npm install

```


3. Set up the Laravel environment file:
```bash
cp .env.example .env
php artisan key:generate

```


4. Configure the Python service URL in your `.env` file to ensure Laravel can communicate with the FastAPI backend:
```env
PYTHON_ADS_URL=http://127.0.0.1:6161

```



### 2. Python & Google Ads MCP Setup

1. Navigate to the Python directory:


```bash
cd python

```


2. Clone the Google Ads MCP Server into this directory:
```bash
git clone https://github.com/bertramdev/GoogleAdsMCP.git

```


3. Create a virtual environment and install the required dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
uv pip install -r requirements.txt

```


4. Configure your API credentials by copying the example configuration file:


```bash
cp config_example.json config.json

```


5. Open `config.json` and fill in your Google Ads and OpenAI details:


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

## Running the Application

You will need three separate terminal windows to run all services simultaneously.

**Terminal 1: Laravel Backend**

```bash
# From the project root (googleAdsAnalyzer-bertramdev)
php artisan serve

```

**Terminal 2: Vue.js Frontend (Vite)**

```bash
# From the project root (googleAdsAnalyzer-bertramdev)
npm run dev

```

**Terminal 3: Python AI Agent Server**

```bash
# From the python directory (googleAdsAnalyzer-bertramdev/python)
source .venv/bin/activate
uvicorn main_mcp:app --reload --host 0.0.0.0 --port 6161

```

---

## Usage

1. Open your browser and navigate to the local Laravel server (usually `[http://127.0.0.1:8000](http://127.0.0.1:8000)`).
2. Use the UI to interact with the agent. You can ask natural language questions like: *"Ağustos ayındaki kampanyalarımın performansı nasıldı?"*
3. The Laravel backend routes your prompt to the FastAPI server, which uses OpenAI to determine the correct Google Ads MCP tools to call.
4. The AI iteratively queries your Google Ads account, fetches the live data, and returns a summarized markdown response to the frontend.

## Endpoints (FastAPI)

* `POST /chat`: Main entry point for the OpenAI agent. Handles multi-turn tool execution.


* `POST /execute-tool`: Direct execution of an MCP tool without passing through the AI (useful for raw data pulls).


* `GET /tools`: Lists all available Google Ads MCP tools and their required parameter schemas.