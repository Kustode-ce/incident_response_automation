# Business Intelligence Platform

## Overview

A comprehensive **Business Intelligence & ML Analytics Platform** that transforms operational data into strategic insights, enabling data-driven decision making and business success.

### Key Features

- 🎯 **Health Scoring**: Real-time 0-100 health scores for services, customers, and systems
- 📈 **Predictive Forecasting**: ML-powered forecasts using Prophet, ARIMA, and LSTM
- 💰 **Cost Intelligence**: Detailed cost attribution, unit economics, and ROI tracking
- 🚀 **Customer Success**: Churn prediction, expansion opportunities, cohort analysis
- 📊 **Performance Analytics**: Comprehensive metrics, benchmarking, and trends
- 🔮 **Anomaly Detection**: Real-time pattern detection and early warnings
- 💡 **AI Recommendations**: Prioritized, actionable insights based on data analysis

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- (Optional) Qdrant for vector search

### Installation

```bash
# Clone repository
git clone https://github.com/yourorg/bi-platform.git
cd bi-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-bi-platform.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the application
cd src
uvicorn bi_platform.api.main:app --reload --port 8000
```

### Docker Setup

```bash
# Build image
docker build -t bi-platform:latest -f Dockerfile.bi-platform .

# Run with Docker Compose
docker-compose -f docker-compose.bi.yml up -d
```

## API Documentation

Once running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Executive Dashboard
```bash
GET /api/v1/dashboard/executive?time_range_days=30
```
High-level overview with key metrics for executives.

#### Operations Dashboard
```bash
GET /api/v1/dashboard/operations?time_range_days=7
```
Detailed operational metrics for engineering teams.

#### Customer Success Dashboard
```bash
GET /api/v1/dashboard/customer-success?time_range_days=30
```
Customer health, engagement, and retention metrics.

#### Financial Dashboard
```bash
GET /api/v1/dashboard/financial?time_range_days=30
```
Cost intelligence and unit economics.

#### Predictive Dashboard
```bash
GET /api/v1/dashboard/predictive?horizon_days=30
```
Forecasts and forward-looking analytics.

#### Health Scoring
```bash
# Service health
GET /api/v1/dashboard/service/{service_id}/health?lookback_days=7

# Customer metrics
GET /api/v1/dashboard/customer/{customer_id}/metrics?lookback_days=30
```

#### Forecasting
```bash
GET /api/v1/dashboard/forecast/{metric_name}?entity_id=global&horizon_days=30&model_type=prophet
```
Supported models: `prophet`, `arima`, `lstm`

#### Recommendations
```bash
GET /api/v1/dashboard/recommendations?context=platform&recommendation_types=cost,performance
```

## Architecture

### Services

| Service | Purpose | Key Features |
|---------|---------|-------------|
| Health Scorer | Calculate health scores | 0-100 scoring, component breakdown, trends |
| Forecasting Engine | Time series predictions | Prophet, ARIMA, LSTM models |
| Cost Tracker | Cost intelligence | Attribution, unit economics, ROI |
| Customer Success Tracker | Customer health | Churn risk, NPS, engagement |
| Recommendation Engine | AI insights | Prioritized actions, impact analysis |

### Data Flow

```
Operational Data (DB, APIs, Logs)
          ↓
    Data Connectors
          ↓
    Feature Store
          ↓
    ML Services (Health, Forecast, Cost)
          ↓
    Analytics Engine
          ↓
    API Layer (FastAPI)
          ↓
    Dashboards (Grafana, Custom UI)
```

## Configuration

### Environment Variables

```bash
# Application
ENVIRONMENT=production  # development, staging, production
BI_PLATFORM_PORT=8000
PRELOAD_MODELS=true

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bi_db
SQL_ECHO=false

# Redis
REDIS_URL=redis://localhost:6379/0

# Vector DB (Optional)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# Observability
ENABLE_METRICS=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SERVICE_NAME=bi-platform

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Model Configuration

Models are configured in `src/bi_platform/models/config.yaml`:

```yaml
forecasting:
  prophet:
    yearly_seasonality: true
    weekly_seasonality: true
    changepoint_prior_scale: 0.05
    
  arima:
    auto_select: true
    max_p: 3
    max_d: 2
    max_q: 3

health_scoring:
  weights:
    availability: 0.30
    performance: 0.25
    quality: 0.25
    trend: 0.20
  
  thresholds:
    healthy: 90
    fair: 75
    concerning: 60
    critical: 0
```

## Dashboards

### Grafana Dashboards

Pre-built dashboards are available in `deploy/grafana/dashboards/`:

1. **Executive Dashboard** (`executive-dashboard.json`)
   - Key business metrics
   - Health scores
   - Revenue trends
   - Top recommendations

2. **Performance Analytics** (`performance-analytics.json`)
   - Service health scores
   - Latency trends
   - Error rates
   - Throughput metrics

3. **Cost Intelligence** (`cost-intelligence.json`)
   - Cost breakdown by category
   - Unit economics
   - ROI tracking
   - Optimization opportunities

4. **Customer Success** (`customer-success.json`)
   - Customer health scores
   - Churn risk
   - Cohort analysis
   - Expansion opportunities

### Custom UI

Build your own dashboard using the API:

```typescript
// Example: Fetch executive dashboard data
const response = await fetch('/api/v1/dashboard/executive?time_range_days=30');
const data = await response.json();

console.log('Platform Health:', data.key_metrics.platform_health_score);
console.log('At-Risk Customers:', data.health.at_risk_customers);
console.log('Total Costs:', data.costs.total_usd);
```

## ML Models

### Forecasting Models

#### Prophet (Default)
- Best for: Data with strong seasonality
- Strengths: Handles missing data, outliers, holidays
- Use case: Revenue, user growth, transaction volume

#### ARIMA
- Best for: Stationary time series
- Strengths: Classical, interpretable
- Use case: Short-term predictions, stable metrics

#### LSTM
- Best for: Complex patterns, long sequences
- Strengths: Deep learning, captures non-linear patterns
- Use case: High-dimensional data, complex seasonality

### Health Scoring Algorithm

```python
# Health Score = Weighted sum of components
score = (
    availability_score * 0.30 +  # Uptime, success rate
    performance_score * 0.25 +   # Latency, throughput
    quality_score * 0.25 +       # Error rates, data quality
    trend_score * 0.20           # Improving/degrading
)
```

### Churn Risk Model

```python
# Churn Risk = Sum of risk factors
risk = (
    usage_decline_risk +      # 30 points max
    engagement_risk +         # 20 points max
    satisfaction_risk +       # 25 points max
    support_issues_risk +     # 15 points max
    financial_issues_risk     # 10 points max
)
```

## Deployment

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f deploy/kubernetes/

# Check status
kubectl get pods -l app=bi-platform

# View logs
kubectl logs -l app=bi-platform --tail=100 -f
```

### Docker Compose

```yaml
# docker-compose.bi.yml
version: '3.8'

services:
  bi-platform:
    build:
      context: .
      dockerfile: Dockerfile.bi-platform
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/bi_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=bi_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./deploy/grafana:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  grafana_data:
```

## Monitoring

### Prometheus Metrics

The platform exposes metrics at `/metrics`:

```
# Health Scores
service_health_score{service="api-gateway",environment="production"} 87.5
customer_health_score{customer="acme-corp"} 92.3

# Forecasting Accuracy
forecast_mae{model="prophet",metric="revenue",horizon_days="30"} 0.08
forecast_mape{model="prophet",metric="users",horizon_days="30"} 5.2

# Costs
total_cost_usd{category="ml_api"} 1250.50
cost_per_unit{unit_type="transaction"} 0.05

# Recommendations
recommendations_generated_total{type="cost",priority="high"} 15
recommendations_acted_upon_total{type="performance"} 8
```

### Logging

Structured JSON logging with `structlog`:

```json
{
  "event": "health_score_calculated",
  "service_id": "api-gateway",
  "health_score": 87.5,
  "components": {
    "availability": 28.5,
    "performance": 22.0,
    "quality": 20.0,
    "trend": 17.0
  },
  "timestamp": "2026-01-23T10:00:00Z",
  "level": "info"
}
```

## Best Practices

### Data Collection

1. **Real-time metrics**: Collect at 1-5 minute intervals
2. **Historical data**: Retain at least 90 days for accurate forecasting
3. **Data quality**: Validate and clean data before analysis
4. **Sampling**: Use appropriate sampling for high-volume metrics

### Forecasting

1. **Model selection**: Start with Prophet for most use cases
2. **Validation**: Always check accuracy metrics (MAE, MAPE, RMSE)
3. **Retraining**: Retrain models monthly or when accuracy degrades
4. **Confidence intervals**: Use wide intervals (95%) for business planning

### Health Scoring

1. **Consistent thresholds**: Define and document scoring thresholds
2. **Component weights**: Adjust weights based on business priorities
3. **Trend analysis**: Look at trends over time, not just point-in-time scores
4. **Action triggers**: Define automated actions for low scores

### Cost Intelligence

1. **Tagging**: Tag all resources for proper cost attribution
2. **Regular reviews**: Review cost reports weekly/monthly
3. **Budget alerts**: Set alerts at 80% of budget
4. **ROI tracking**: Track ROI for all optimization initiatives

## API Examples

### Python Client

```python
import httpx

class BIPlatformClient:
    def __init__(self, base_url: str, api_key: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def get_executive_dashboard(self, days: int = 30):
        response = await self.client.get(
            f"/api/v1/dashboard/executive?time_range_days={days}"
        )
        return response.json()
    
    async def get_service_health(self, service_id: str):
        response = await self.client.get(
            f"/api/v1/dashboard/service/{service_id}/health"
        )
        return response.json()
    
    async def forecast_metric(self, metric_name: str, horizon_days: int = 30):
        response = await self.client.get(
            f"/api/v1/dashboard/forecast/{metric_name}",
            params={"horizon_days": horizon_days, "model_type": "prophet"}
        )
        return response.json()

# Usage
client = BIPlatformClient("http://localhost:8000", "your-api-key")
dashboard = await client.get_executive_dashboard(days=30)
print(f"Platform Health: {dashboard['key_metrics']['platform_health_score']}")
```

### JavaScript/TypeScript Client

```typescript
class BIPlatformClient {
  constructor(private baseUrl: string, private apiKey: string) {}

  async getExecutiveDashboard(days: number = 30) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/dashboard/executive?time_range_days=${days}`,
      {
        headers: { 'Authorization': `Bearer ${this.apiKey}` }
      }
    );
    return response.json();
  }

  async getRecommendations(context: string = 'platform') {
    const response = await fetch(
      `${this.baseUrl}/api/v1/dashboard/recommendations?context=${context}`,
      {
        headers: { 'Authorization': `Bearer ${this.apiKey}` }
      }
    );
    return response.json();
  }
}

// Usage
const client = new BIPlatformClient('http://localhost:8000', 'your-api-key');
const dashboard = await client.getExecutiveDashboard(30);
console.log('Total Revenue:', dashboard.key_metrics.total_revenue_usd);
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bi_platform --cov-report=html

# Run specific test file
pytest tests/unit/test_health_scorer.py

# Run integration tests
pytest tests/integration/

# Run E2E tests
pytest tests/e2e/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linting: `ruff check . && black --check .`
6. Submit a pull request

## License

Proprietary - All Rights Reserved

## Support

For support, email support@yourcompany.com or open an issue in the repository.

## Roadmap

### Q1 2026
- ✅ Core health scoring
- ✅ Forecasting (Prophet, ARIMA)
- ✅ Cost intelligence
- ✅ Customer success metrics

### Q2 2026
- 🔄 Advanced ML models (LSTM, XGBoost)
- 🔄 Real-time streaming analytics
- 🔄 Custom dashboard builder
- 🔄 Mobile app

### Q3 2026
- 📅 Prescriptive analytics (automated actions)
- 📅 What-if scenario modeling
- 📅 Benchmarking against industry standards
- 📅 Advanced anomaly detection (isolation forest)

### Q4 2026
- 📅 Natural language queries
- 📅 Automated report generation
- 📅 ML model marketplace
- 📅 Multi-tenancy support
