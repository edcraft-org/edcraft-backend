# EdCraft Backend

FastAPI backend for the **EdCraft**, providing APIs for question generation and content management.

## 🚀 Overview

EdCraft Backend exposes the EdCraft Engine via a REST API and handles database operations. It handles authentication, data management, and async job processing for question generation.

## 🧱 Tech Stack

* Python 3.12+
* FastAPI
* PostgreSQL
* SQLAlchemy
* Alembic
* Nomad
* Docker

## ⚡ Quick Start

### 1. Clone & install

```bash
git clone https://github.com/edcraft-org/edcraft-backend.git
cd edcraft-backend
uv sync
```

Requires [`uv`](https://github.com/astral-sh/uv)


### 2. Setup environment

```bash
cp .env.example .env.development
```

Update database and secrets in `.env.development`.


### 3. Start services

```bash
# Start database
make db-up

# Start Nomad
make nomad

# Run backend
make dev
```


### 4. Access API

* API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 🧪 Testing

```bash
# Start test db
make db-test

# Run tests
make test
```

## 📁 Project Structure

```
edcraft_backend/
├── routers/        # API endpoints
├── services/       # Business logic
├── repositories/   # DB access layer
├── models/         # SQLAlchemy models
├── schemas/        # Pydantic schemas
├── config/         # Settings
├── security/       # Auth utilities
├── oauth/          # OAuth integration
├── executors/      # External jobs (Nomad)
├── main.py         # App entrypoint
alembic/            # DB migrations
tests/              # Test suite
worker/             # Nomad job worker
```

## 🗄️ Database

Run migrations:

```bash
uv run alembic upgrade head
```

Create a migration:

```bash
uv run alembic revision --autogenerate -m "message"
```

Access database (dev):

```bash
docker exec -it edcraft-postgres psql -U edcraft_dev -d edcraft
```

For details about the schema, see: [Database Documentation](docs/database.md)

## 🔐 Authentication

* JWT (access and refresh tokens in httpOnly cookies)
* OAuth via GitHub

### Basic flow

1. `POST /auth/signup`
2. `POST /auth/login`
3. Use authenticated endpoints
4. `POST /auth/refresh` (token rotation)

## ⚙️ Async Jobs (Nomad)

Long-running endpoints (e.g. question generation) are **asynchronous**.

### 🧠 How it works

1. Client sends request

2. Backend:
   * generates a callback token
   * submits a Nomad job

3. API responds immediately:

```json
{ "job_id": "...", "status_url": "/jobs/{id}" }
```

4. Nomad:

   * spins up a worker container
   * injects worker code at runtime
   * executes the task

5. Worker sends result back:

```
POST /jobs/callback/{token}
```

6. Client polls:

```
GET /jobs/{job_id}
```

### Example response

```json
{
  "status": "completed",
  "result": {...}
}
```

## 🖥️ WSL2 Nomad Setup

If you're using **WSL2**, if you are facing issues using nomad, follow the instructions in this section.

Docker containers cannot access `localhost` on the host.

### One-time setup

```bash
docker network create --subnet 192.168.100.0/24 edcraft-network
docker tag edcraft-backend:latest edcraft-backend:local
```

Set in `.env.development`:

```
NOMAD_CONTAINER_IMAGE=edcraft-backend:local
```

---

### Each session

1. Start Nomad:

```bash
make nomad
```

2. Update Nomad host IP (if not working):

```bash
sed -i "s/NOMAD_HOST=.*/NOMAD_HOST=$(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)/" .env.development
```

3. Start backend:

```bash
make docker-up
```

## Enhancements

* Add rate limiting to protect APIs and improve system stability
* Add pagination support for data retrieval endpoints
* Add caching to improve performance and reduce repeated computations
* Add unit tests to improve test coverage alongside existing integration tests
* Implement proper logging for debugging, monitoring, and error tracking

## 📄 License

MIT License © 2025 EdCraft Team
