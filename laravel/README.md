# Google Ads Analyzer - Laravel Web Portal

The frontend interface and operational backend for the Google Ads AI platform, built with **Laravel 11**, **Vue.js 3**, and **Tailwind CSS**.

---

## Prerequisites

* **PHP 8.2+** with `pdo_sqlite` or `pdo_mysql`, `curl`, and `mbstring` extensions
* **Composer**
* **Node.js 18+** and **npm**
* Running instance of the Python Agent API (default: `http://127.0.0.1:6161`)

---

## Installation & Setup

1. **Install Dependencies:**
```bash
composer install
npm install
```

2. **Configure Environment:**
```bash
cp .env.example .env
php artisan key:generate
```
3. **Run Database Migrations:**
```bash
php artisan migrate
```



---

## Development & Execution

Run the backend server and frontend compiler concurrently:

```bash
# Terminal 1: Laravel Backend
php artisan serve

# Terminal 2: Vite Dev Server
npm run dev
```

Alternatively, use the starter script:

```bash
chmod +x start.sh
./start.sh
```

---

## Automated Background Tasks

To execute the daily automated account analysis command manually:

```bash
php artisan ads:run-daily-analysis
```

To run scheduled tasks continuously via cron, add this entry to your server's crontab (`crontab -e`):

```bash
* * * * * cd /path-to-project/laravel && php artisan schedule:run >> /dev/null 2>&1
```
