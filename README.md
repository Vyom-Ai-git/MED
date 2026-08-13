# Vyoma LabOS — Phase 0 Foundation

Vyoma LabOS is a reusable, multi-tenant Medical Laboratory Management Platform. It is designed around the core laboratory workflow:
**Patient Registration → Test Selection → Order → Sample Collection → Processing → Result Entry → Verification → Final Report**

This repository contains the core platform services (FastAPI, SQLAlchemy, Alembic, PostgreSQL) and the laboratory manager interface (Next.js, TypeScript, Tailwind CSS).

---

## 📁 Project Structure

* **`backend/`**: Python FastAPI app implementing REST endpoints, JWT authentication, tenant isolation, DB schemas/repositories/services, and Alembic migrations.
* **`frontend/`**: Next.js App Router app implementing the design system primitives, sidebar shell layout, and pages for dashboard analytics, patient records, test catalog, and order workflow logs.
* **`docker-compose.yml`**: Docker-ready configurations.
* **`.env`**: Global environment variables.

---

## 🚀 Setup & Local Execution

### 1. Prerequisites
* **Node.js** (v18+)
* **Python** (3.11+)
* **PostgreSQL** (14+)

### 2. Configure Database & Environment
Copy the example environment settings:
```bash
cp .env.example .env
```
Create a local PostgreSQL database named `labos_db`.

### 3. Run Backend Migrations & Seed
Set up the python virtual environment, run migrations, and load the development seed data:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations and seed DB
alembic upgrade head
python seed.py
```

### 4. Start Servers

**Start Backend (FastAPI):**
```bash
# From MED/backend
uvicorn app.main:app --reload --port 8000
```
* Swagger API Docs served at: `http://localhost:8000/api/v1/docs`
* Health Check Endpoint: `http://localhost:8000/api/v1/health`

**Start Frontend (Next.js):**
```bash
cd ../frontend
npm install
npm run dev
```
* Dashboard web app served at: `http://localhost:3000`

---

## 🧪 Testing

Run backend unit and integration tests (isolated in SQLite):
```bash
cd backend
python -m pytest tests/
```

---

## 🔑 Demo Access Credentials

The development database contains the following pre-seeded credentials:
* **Administrator**: `admin@vyoma.com` / `admin123`
* **Pathologist**: `anand@vyoma.com` / `pathologist123`
* **Technician**: `sarah@vyoma.com` / `tech123`
