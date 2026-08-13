# VYOMA LABOS — Production Deployment & Configuration Guide

## 1. Prerequisites

- **Python**: 3.10+ (Recommended Python 3.11–3.14)
- **Node.js**: 18.0+ or 20.0+ LTS
- **Database**: PostgreSQL 14+ (Development/Testing supports SQLite)
- **Object Storage**: S3 / Google Cloud Storage / Azure Blob (Development supports local filesystem storage)

---

## 2. Environment Configuration Reference

Create `.env` based on `.env.example`:

```ini
# Environment Configuration
ENVIRONMENT=production
LOG_LEVEL=info
PORT=8000

# Database (Production requires PostgreSQL)
DATABASE_URL=postgresql://labos_user:SecurePassword123@db.example.com:5432/labos_production

# Security Secrets
JWT_SECRET=a_very_strong_random_jwt_secret_key_at_least_32_chars_long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# CORS & Frontend URLs
FRONTEND_URL=https://labos.example.com
CORS_ALLOWED_ORIGINS=https://labos.example.com

# File Storage Path
STORAGE_PATH=storage/reports

# n8n Webhook & Integration Security
N8N_WEBHOOK_URL=https://n8n.example.com/webhook/report-available
N8N_WEBHOOK_SECRET=strong_hmac_webhook_secret_key_999
N8N_INTEGRATION_KEY=strong_m2m_integration_key_888
INTEGRATION_TIMEOUT_SECONDS=15
INTEGRATION_MAX_RETRIES=3
```

---

## 3. Backend Deployment Steps

```bash
# 1. Navigate to backend directory
cd backend

# 2. Setup Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run Alembic Database Migrations
alembic upgrade head

# 5. Start Production Server (Uvicorn / Gunicorn)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 4. Frontend Deployment Steps

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install Dependencies
npm install

# 3. Create Production Build
npm run build

# 4. Start Next.js Production Server
npm start
```

---

## 5. Database & Storage Production Recommendations

### Database (PostgreSQL)
- **POC vs Production**: The local test environment uses SQLite. Production MUST use PostgreSQL with SSL (`sslmode=require`), automated daily backups, and point-in-time recovery (PITR).
- **Pooling**: Configure PgBouncer or SQLAlchemy connection pool options (`pool_size=20`, `max_overflow=10`).

### Object Storage (S3 / GCS / Azure)
- **POC vs Production**: The POC uses local filesystem storage (`storage/reports/`). Production MUST configure object storage (e.g. AWS S3 bucket with private ACLs and server-side encryption enabled).

### Database Backup Requirements
- **Frequency**: Daily full backup + hourly WAL archiving.
- **Retention**: Retain clinical database backups in accordance with healthcare regulatory requirements.
