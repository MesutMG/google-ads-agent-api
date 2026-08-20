### 1. Root Workspace README (`project/README.md`)

```markdown
# Google Ads AI Agent & Analytics Platform

An end-to-end full-stack analytics platform combining a Laravel & Vue.js web portal with a containerized Python/FastAPI backend powered by OpenAI and the Google Ads Model Context Protocol (MCP).

---

## Architecture Overview

```text
project/
├── laravel/               # Web Application (PHP 8.2+, Laravel 11, Vue 3, Inertia/Vite)
│   ├── app/               # API Controllers, Models, Console Commands
│   ├── resources/         # Vue frontend components & Tailwind/CSS
│   └── routes/            # Web & API route definitions
│
└── python/                # AI Agent & MCP Microservice (Python 3.12, FastAPI, Docker)
    ├── GoogleAdsMCP/      # Model Context Protocol stdio server
    ├── Dockerfile         # Production container definition
    ├── docker-compose.yml # Compose orchestrator
    └── main_mcp.py        # Persistent MCP client & OpenAI tool router

```

---

## Quick Start Guide

### Step 1: Start the Python AI Microservice (Port 6161)

Navigate to the `python/` directory and spin up the Docker container:

```bash
cd python
cp config_example.json config.json
# Fill in your Google Ads and OpenAI credentials in config.json
docker compose up -d --build

```

### Step 2: Start the Laravel Application (Port 8000)

In a separate terminal, navigate to the `laravel/` directory:

```bash
cd laravel
cp .env.example .env
composer install
npm install
php artisan key:generate
php artisan migrate

# Ensure .env contains: PYTHON_ADS_URL=[http://127.0.0.1:6161](http://127.0.0.1:6161)
php artisan serve

```

### Step 3: Start the Frontend Asset Bundler

In another terminal, start the Vite development server:

```bash
cd laravel
npm run dev

```

Visit **`http://127.0.0.1:8000`** in your browser to interact with the platform.

---

## Sub-Project Documentation

* [Laravel Web App Setup & Scheduling Guide](https://www.google.com/search?q=./laravel/README.md)
* [Python Google Ads Agent & Docker Deployment Guide](https://www.google.com/search?q=./python/README.md)
