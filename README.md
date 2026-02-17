# Incident Response Automation

A Kubernetes-native incident response automation platform that detects, manages, and automatically responds to incidents using configurable runbooks and ML-powered analysis.

## Features

- **Incident Management**: Full lifecycle management from detection to resolution
- **Runbook Engine**: Automated response execution with configurable steps
- **ML Integration**: Classification, root cause analysis, and runbook generation
- **Integrations**: Slack, PagerDuty, Kubernetes, Prometheus, Grafana, Loki
- **Observability**: Structured logging, Prometheus metrics, OpenTelemetry tracing

## Quick Start (Local Development)

### Prerequisites

- Docker & Docker Compose
- (Optional) Python 3.11+ for running without Docker

### 1. Clone and Setup

```bash
cd incident-response-automation

# Review/modify environment variables
cp .env .env.local  # For personal overrides (gitignored)
```

### 2. Start Services with Docker Compose

```bash
# Start all services (API, DB, Redis, Worker)
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f api
docker-compose logs -f worker
```

### 3. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:8000 | Main API |
| Swagger UI | http://localhost:8000/docs | Interactive API docs |
| ReDoc | http://localhost:8000/redoc | API documentation |
| Health Check | http://localhost:8000/health | Health endpoint |
| Metrics | http://localhost:8000/metrics | Prometheus metrics |
| Flower | http://localhost:5555 | Celery monitoring (optional) |

### 4. Verify Services

```bash
# Check health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs
```

## Docker Services

| Service | Dockerfile | Description |
|---------|------------|-------------|
| `api` | `deploy/docker/Dockerfile.api` | FastAPI application server |
| `worker` | `deploy/docker/Dockerfile.worker` | Celery background worker |
| `beat` | `deploy/docker/Dockerfile.worker` | Celery scheduled tasks |
| `db` | `deploy/docker/Dockerfile.db` | PostgreSQL database |
| `redis` | `deploy/docker/Dockerfile.redis` | Redis cache/broker |
| `flower` | `deploy/docker/Dockerfile.worker` | Celery monitoring (optional) |

### Starting with Monitoring

```bash
# Include Flower for Celery monitoring
docker-compose --profile monitoring up --build
```

## Development

### Running Without Docker

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (via Docker or locally)
docker-compose up -d db redis

# Run database migrations
alembic upgrade head

# Start the API server
python -m src.main

# In another terminal, start Celery worker
celery -A src.workers.celery_app worker --loglevel=info
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test files
pytest tests/unit/ -v
pytest tests/integration/ -v
```

### Code Quality

```bash
# Format code
black src tests
ruff check src tests --fix

# Type checking
mypy src
```

## Configuration

### Environment Variables

Key environment variables (see `.env` for full list):

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment (development/staging/production) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `OPENAI_API_KEY` | - | OpenAI API key for ML features |
| `ANTHROPIC_API_KEY` | - | Anthropic API key for ML features |
| `ENABLE_ML_CLASSIFICATION` | `false` | Enable ML incident classification |

### Enabling ML Features

To enable ML-powered features, add your API keys to `.env.local`:

```bash
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
ENABLE_ML_CLASSIFICATION=true
ENABLE_ML_ROOT_CAUSE=true
```

## API Endpoints

### Core Endpoints

- `POST /api/v1/incidents` - Create incident
- `GET /api/v1/incidents` - List incidents
- `GET /api/v1/incidents/{id}` - Get incident
- `PATCH /api/v1/incidents/{id}` - Update incident
- `POST /api/v1/runbooks` - Create runbook
- `POST /api/v1/runbooks/{id}/execute` - Execute runbook
- `POST /webhooks/prometheus` - Prometheus alert webhook
- `POST /webhooks/alertmanager` - AlertManager webhook

See http://localhost:8000/docs for complete API documentation.

## Project Structure

```
incident-response-automation/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings and configuration
│   ├── models/              # SQLAlchemy models
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   │   ├── integrations/    # External integrations
│   │   ├── ml/              # ML orchestrator
│   │   └── runbook/         # Runbook engine
│   ├── repositories/        # Data access layer
│   ├── workers/             # Celery tasks
│   └── observability/       # Logging, metrics, tracing
├── tests/
│   ├── unit/
│   └── integration/
├── deploy/
│   └── docker/              # Dockerfiles and configs
├── alembic/                 # Database migrations
├── docs/                    # Documentation
├── docker-compose.yml       # Local development stack
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and components
- [Data Schema](docs/DATA_SCHEMA.md) - Data models and schemas
- [ML Orchestrator](docs/ML_ORCHESTRATOR.md) - ML/AI integration
- [System Flow](docs/SYSTEM_FLOW.md) - Incident lifecycle
- [Service Interactions](docs/SERVICE_INTERACTIONS.md) - Service communication

## Troubleshooting

### Common Issues

**Database connection failed:**
```bash
# Check if PostgreSQL is running
docker-compose ps db
docker-compose logs db
```

**Redis connection refused:**
```bash
# Check if Redis is running
docker-compose ps redis
docker-compose logs redis
```

**API not starting:**
```bash
# Check API logs
docker-compose logs api
# Rebuild if needed
docker-compose up --build api
```

### Reset Everything

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Rebuild and start fresh
docker-compose up --build
```

## License

[Add your license here]
