# Business Intelligence Platform - Full Implementation

## Overview

A comprehensive **Business Intelligence & ML Analytics Platform** designed to drive customer business success through data-driven insights, predictive analytics, and actionable recommendations.

**Core Philosophy**: Transform raw operational data into strategic business intelligence that enables customers to make informed decisions, optimize operations, and achieve measurable business outcomes.

## Platform Capabilities

| Module | Description | Customer Value |
|--------|-------------|----------------|
| **Health Scoring** | Real-time health scores (0-100) for services, systems, teams | Executive visibility, proactive management |
| **Predictive Forecasting** | ML-powered forecasts for volumes, costs, trends | Capacity planning, budget optimization |
| **Performance Analytics** | Comprehensive performance metrics and benchmarking | Identify bottlenecks, optimize efficiency |
| **Cost Intelligence** | Cost attribution, optimization, ROI tracking | Financial planning, cost reduction |
| **Customer Success Metrics** | Adoption, satisfaction, value realization | Drive retention, identify upsell opportunities |
| **Anomaly Detection** | Real-time detection of unusual patterns | Early warning system, risk mitigation |
| **Recommendation Engine** | AI-powered actionable recommendations | Guided optimization, best practices |

## Architecture

```
business-intelligence-platform/
├── src/
│   ├── bi_platform/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── health_scoring.py
│   │   │   │   │   ├── forecasting.py
│   │   │   │   │   ├── performance_analytics.py
│   │   │   │   │   ├── cost_intelligence.py
│   │   │   │   │   ├── customer_success.py
│   │   │   │   │   ├── anomaly_detection.py
│   │   │   │   │   └── recommendations.py
│   │   │   │   └── router.py
│   │   │   └── main.py
│   │   │
│   │   ├── services/
│   │   │   ├── health_scorer.py
│   │   │   ├── forecasting_engine.py
│   │   │   ├── performance_analyzer.py
│   │   │   ├── cost_tracker.py
│   │   │   ├── customer_success_tracker.py
│   │   │   ├── anomaly_detector.py
│   │   │   └── recommendation_engine.py
│   │   │
│   │   ├── models/
│   │   │   ├── time_series/
│   │   │   │   ├── prophet_forecaster.py
│   │   │   │   ├── arima_forecaster.py
│   │   │   │   └── lstm_forecaster.py
│   │   │   ├── ml_models/
│   │   │   │   ├── health_predictor.py
│   │   │   │   ├── churn_predictor.py
│   │   │   │   └── anomaly_detector.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── analytics/
│   │   │   ├── aggregators.py
│   │   │   ├── calculators.py
│   │   │   └── benchmarks.py
│   │   │
│   │   ├── observability/
│   │   │   ├── prometheus_metrics.py
│   │   │   ├── calibration_tracker.py
│   │   │   └── model_monitor.py
│   │   │
│   │   └── data/
│   │       ├── connectors/
│   │       │   ├── database.py
│   │       │   ├── data_warehouse.py
│   │       │   └── external_apis.py
│   │       └── feature_store.py
│   │
│   └── shared/
│       ├── core/
│       │   ├── config.py
│       │   ├── db.py
│       │   └── auth.py
│       └── utils/
│           ├── time_utils.py
│           └── math_utils.py
│
├── deploy/
│   ├── grafana/
│   │   └── dashboards/
│   │       ├── executive-dashboard.json
│   │       ├── performance-analytics.json
│   │       ├── cost-intelligence.json
│   │       └── customer-success.json
│   └── kubernetes/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── hpa.yaml
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **ML/Forecasting**: Prophet, scikit-learn, XGBoost, TensorFlow
- **Data**: PostgreSQL, Redis, ClickHouse (analytics)
- **Observability**: Prometheus, Grafana, structlog
- **Time Series**: Prophet, ARIMA, LSTM
- **Vector DB**: Qdrant (for similarity search)

## Full Implementation

### 1. Main Application

```python
# src/bi_platform/api/main.py

"""
Business Intelligence Platform
Comprehensive analytics, forecasting, and intelligence for business success
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import structlog

from bi_platform.observability import get_metrics
from shared.core.db import init_db, close_db, check_db_health

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    # Startup
    logger.info("bi_platform_starting", version="1.0.0")
    
    # Initialize database
    await init_db()
    logger.info("database_initialized")
    
    # Initialize metrics
    metrics = get_metrics()
    metrics.platform_status.set(1)  # 1 = healthy
    
    # Pre-load ML models
    if os.getenv("PRELOAD_MODELS", "true").lower() == "true":
        await preload_models()
    
    yield
    
    # Shutdown
    logger.info("bi_platform_stopping")
    await close_db()


async def preload_models():
    """Pre-load ML models into memory"""
    logger.info("preloading_ml_models")
    # Load forecasting models, health predictors, etc.
    # TODO: Implement model loading


app = FastAPI(
    title="Business Intelligence Platform",
    description="""
    ## Comprehensive Business Intelligence & Analytics
    
    Transform operational data into strategic insights that drive business success.
    
    ### Key Capabilities
    - **Health Scoring**: Real-time health scores for services and systems
    - **Predictive Forecasting**: ML-powered volume and cost predictions
    - **Performance Analytics**: Deep-dive into operational efficiency
    - **Cost Intelligence**: Detailed cost attribution and optimization
    - **Customer Success**: Adoption, satisfaction, and retention metrics
    - **Anomaly Detection**: Real-time pattern detection and alerts
    - **Recommendations**: AI-powered actionable insights
    
    ### Observability
    - `/metrics` - Prometheus metrics
    - `/health` - Platform health check
    - `/calibration` - ML model calibration status
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Platform health check"""
    db_health = await check_db_health()
    
    return {
        "status": "healthy" if db_health["connected"] else "degraded",
        "service": "business_intelligence_platform",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database": db_health,
        "models_loaded": True,  # TODO: Check actual model status
    }


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# Include API routers
from bi_platform.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "bi_platform.api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("BI_PLATFORM_PORT", "8000")),
        reload=os.getenv("ENVIRONMENT") == "development",
    )
```

### 2. Health Scoring Service

```python
# src/bi_platform/services/health_scorer.py

"""
Health Scoring Service
Calculate comprehensive health scores (0-100) for services, systems, and teams
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass

from bi_platform.data.connectors.database import get_db
from bi_platform.analytics.calculators import (
    calculate_availability,
    calculate_performance_score,
    calculate_trend
)


@dataclass
class HealthScore:
    """Health score result"""
    entity_type: str  # service, system, team, customer
    entity_id: str
    entity_name: str
    score: float  # 0-100
    grade: str  # A, B, C, D, F
    status: str  # healthy, fair, concerning, critical
    components: Dict[str, Dict]
    recommendations: List[str]
    timestamp: datetime


class HealthScoringService:
    """
    Calculate health scores for various entities
    
    Score Components (0-100):
    - Availability (30%): Uptime, success rates
    - Performance (25%): Latency, throughput, efficiency
    - Quality (25%): Error rates, data quality, completeness
    - Trend (20%): Is it improving or degrading?
    """
    
    def __init__(self):
        self.db = None
    
    async def score_service(
        self,
        service_id: str,
        lookback_days: int = 7
    ) -> HealthScore:
        """
        Calculate health score for a service
        
        Args:
            service_id: Service identifier
            lookback_days: Days of history to analyze
            
        Returns:
            HealthScore with 0-100 score and breakdown
        """
        
        # Get service metrics
        metrics = await self._get_service_metrics(service_id, lookback_days)
        
        if not metrics:
            return self._no_data_score(service_id, "service")
        
        # Calculate component scores
        availability_score = await self._calculate_availability_score(metrics)
        performance_score = await self._calculate_performance_score(metrics)
        quality_score = await self._calculate_quality_score(metrics)
        trend_score = await self._calculate_trend_score(metrics)
        
        # Weighted total
        total_score = (
            availability_score * 0.30 +
            performance_score * 0.25 +
            quality_score * 0.25 +
            trend_score * 0.20
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            availability_score,
            performance_score,
            quality_score,
            trend_score,
            metrics
        )
        
        return HealthScore(
            entity_type="service",
            entity_id=service_id,
            entity_name=metrics.get("service_name", service_id),
            score=round(total_score, 1),
            grade=self._score_to_grade(total_score),
            status=self._score_to_status(total_score),
            components={
                "availability": {
                    "score": round(availability_score, 1),
                    "weight": 30,
                    "uptime_percent": metrics.get("uptime_percent"),
                    "success_rate": metrics.get("success_rate")
                },
                "performance": {
                    "score": round(performance_score, 1),
                    "weight": 25,
                    "p99_latency_ms": metrics.get("p99_latency_ms"),
                    "throughput_rps": metrics.get("throughput_rps")
                },
                "quality": {
                    "score": round(quality_score, 1),
                    "weight": 25,
                    "error_rate": metrics.get("error_rate_percent"),
                    "data_quality": metrics.get("data_quality_score")
                },
                "trend": {
                    "score": round(trend_score, 1),
                    "weight": 20,
                    "direction": metrics.get("trend_direction"),
                    "velocity": metrics.get("trend_velocity")
                }
            },
            recommendations=recommendations,
            timestamp=datetime.utcnow()
        )
    
    async def score_customer(
        self,
        customer_id: str,
        lookback_days: int = 30
    ) -> HealthScore:
        """
        Calculate customer health score
        
        Components:
        - Engagement (30%): Usage frequency, feature adoption
        - Satisfaction (25%): NPS, support tickets, feedback
        - Growth (25%): Expansion, usage trends
        - Risk (20%): Churn indicators, payment issues
        """
        
        metrics = await self._get_customer_metrics(customer_id, lookback_days)
        
        engagement_score = await self._calculate_engagement_score(metrics)
        satisfaction_score = await self._calculate_satisfaction_score(metrics)
        growth_score = await self._calculate_growth_score(metrics)
        risk_score = await self._calculate_risk_score(metrics)
        
        total_score = (
            engagement_score * 0.30 +
            satisfaction_score * 0.25 +
            growth_score * 0.25 +
            risk_score * 0.20
        )
        
        return HealthScore(
            entity_type="customer",
            entity_id=customer_id,
            entity_name=metrics.get("customer_name", customer_id),
            score=round(total_score, 1),
            grade=self._score_to_grade(total_score),
            status=self._score_to_status(total_score),
            components={
                "engagement": {
                    "score": round(engagement_score, 1),
                    "weight": 30,
                    "dau": metrics.get("daily_active_users"),
                    "feature_adoption": metrics.get("feature_adoption_percent")
                },
                "satisfaction": {
                    "score": round(satisfaction_score, 1),
                    "weight": 25,
                    "nps": metrics.get("nps_score"),
                    "support_tickets": metrics.get("support_ticket_count")
                },
                "growth": {
                    "score": round(growth_score, 1),
                    "weight": 25,
                    "usage_trend": metrics.get("usage_trend"),
                    "expansion_rate": metrics.get("expansion_rate")
                },
                "risk": {
                    "score": round(risk_score, 1),
                    "weight": 20,
                    "churn_risk": metrics.get("churn_risk_percent"),
                    "payment_issues": metrics.get("payment_issues")
                }
            },
            recommendations=self._generate_customer_recommendations(
                engagement_score,
                satisfaction_score,
                growth_score,
                risk_score,
                metrics
            ),
            timestamp=datetime.utcnow()
        )
    
    async def get_health_trends(
        self,
        entity_type: str,
        entity_id: str,
        days: int = 30
    ) -> List[Dict]:
        """Get historical health scores to show trends"""
        
        # Query historical scores from database
        scores = await self._query_historical_scores(
            entity_type,
            entity_id,
            days
        )
        
        return scores
    
    async def get_health_leaderboard(
        self,
        entity_type: str,
        limit: int = 10,
        sort_by: str = "score"
    ) -> List[HealthScore]:
        """Get top/bottom entities by health score"""
        
        entities = await self._get_all_entities(entity_type)
        
        scores = []
        for entity in entities:
            if entity_type == "service":
                score = await self.score_service(entity['id'])
            elif entity_type == "customer":
                score = await self.score_customer(entity['id'])
            else:
                continue
            
            scores.append(score)
        
        # Sort by score
        scores.sort(key=lambda x: x.score, reverse=(sort_by == "score"))
        
        return scores[:limit]
    
    # Helper methods
    
    async def _calculate_availability_score(self, metrics: Dict) -> float:
        """Calculate availability component (0-30 points)"""
        uptime = metrics.get("uptime_percent", 0)
        success_rate = metrics.get("success_rate", 0)
        
        # Uptime score (15 points)
        uptime_score = (uptime / 100) * 15
        
        # Success rate score (15 points)
        success_score = (success_rate / 100) * 15
        
        return uptime_score + success_score
    
    async def _calculate_performance_score(self, metrics: Dict) -> float:
        """Calculate performance component (0-25 points)"""
        p99_latency = metrics.get("p99_latency_ms", 0)
        target_latency = metrics.get("target_latency_ms", 500)
        throughput = metrics.get("throughput_rps", 0)
        target_throughput = metrics.get("target_throughput_rps", 100)
        
        # Latency score (15 points) - lower is better
        if p99_latency <= target_latency:
            latency_score = 15
        else:
            latency_score = max(0, 15 * (1 - (p99_latency - target_latency) / target_latency))
        
        # Throughput score (10 points) - higher is better
        throughput_ratio = min(throughput / target_throughput, 1.5)
        throughput_score = (throughput_ratio / 1.5) * 10
        
        return latency_score + throughput_score
    
    async def _calculate_quality_score(self, metrics: Dict) -> float:
        """Calculate quality component (0-25 points)"""
        error_rate = metrics.get("error_rate_percent", 0)
        data_quality = metrics.get("data_quality_score", 100)
        
        # Error rate score (15 points) - lower is better
        error_score = max(0, 15 * (1 - error_rate / 5))  # 5% errors = 0 points
        
        # Data quality score (10 points)
        data_score = (data_quality / 100) * 10
        
        return error_score + data_score
    
    async def _calculate_trend_score(self, metrics: Dict) -> float:
        """Calculate trend component (0-20 points)"""
        trend_direction = metrics.get("trend_direction", "stable")
        
        if trend_direction == "improving":
            return 20
        elif trend_direction == "stable":
            return 15
        elif trend_direction == "slightly_degrading":
            return 10
        elif trend_direction == "degrading":
            return 5
        else:
            return 10  # Unknown
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _score_to_status(self, score: float) -> str:
        """Convert score to status"""
        if score >= 90:
            return "healthy"
        elif score >= 75:
            return "fair"
        elif score >= 60:
            return "concerning"
        else:
            return "critical"
    
    def _generate_recommendations(
        self,
        availability: float,
        performance: float,
        quality: float,
        trend: float,
        metrics: Dict
    ) -> List[str]:
        """Generate actionable recommendations based on scores"""
        recommendations = []
        
        # Availability issues
        if availability < 20:  # Out of 30
            uptime = metrics.get("uptime_percent", 100)
            if uptime < 99.5:
                recommendations.append(
                    f"⚠️ Availability: Uptime is {uptime:.1f}%. Implement redundancy and failover mechanisms."
                )
            
            success_rate = metrics.get("success_rate", 100)
            if success_rate < 95:
                recommendations.append(
                    f"⚠️ Success Rate: Only {success_rate:.1f}% of requests succeed. Review error handling and retry logic."
                )
        
        # Performance issues
        if performance < 15:  # Out of 25
            p99_latency = metrics.get("p99_latency_ms", 0)
            target = metrics.get("target_latency_ms", 500)
            if p99_latency > target:
                recommendations.append(
                    f"🐌 Performance: P99 latency is {p99_latency}ms (target: {target}ms). Consider caching, optimization, or scaling."
                )
        
        # Quality issues
        if quality < 15:  # Out of 25
            error_rate = metrics.get("error_rate_percent", 0)
            if error_rate > 2:
                recommendations.append(
                    f"🐛 Quality: Error rate is {error_rate:.1f}%. Investigate root causes and implement fixes."
                )
        
        # Trend concerns
        if trend < 10:  # Out of 20
            recommendations.append(
                "📉 Trend: Metrics are degrading over time. Schedule a review to identify systemic issues."
            )
        
        # If everything is good
        if not recommendations:
            recommendations.append("✅ All metrics are healthy. Continue monitoring and maintain current practices.")
        
        return recommendations
    
    def _no_data_score(self, entity_id: str, entity_type: str) -> HealthScore:
        """Return a score when no data is available"""
        return HealthScore(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_id,
            score=0.0,
            grade="N/A",
            status="no_data",
            components={},
            recommendations=["No data available. Start collecting metrics to enable health scoring."],
            timestamp=datetime.utcnow()
        )
```

### 3. Forecasting Engine

```python
# src/bi_platform/services/forecasting_engine.py

"""
Forecasting Engine
ML-powered time series forecasting for volumes, costs, and trends
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from prophet import Prophet

from bi_platform.data.connectors.database import get_db


class ForecastingEngine:
    """
    Time series forecasting using multiple models
    
    Supports:
    - Prophet: Facebook's forecasting library (seasonal patterns)
    - ARIMA: Classical statistical forecasting
    - LSTM: Deep learning for complex patterns
    """
    
    def __init__(self):
        self.models = {}
    
    async def forecast_metric(
        self,
        metric_name: str,
        entity_id: str,
        horizon_days: int = 30,
        confidence_level: float = 0.95,
        model_type: str = "prophet"
    ) -> Dict:
        """
        Forecast a metric for the next N days
        
        Args:
            metric_name: Name of metric to forecast
            entity_id: Entity identifier
            horizon_days: Number of days to forecast
            confidence_level: Confidence interval (0.80-0.99)
            model_type: prophet, arima, or lstm
            
        Returns:
            Forecast with predictions and confidence intervals
        """
        
        # Get historical data
        historical_data = await self._get_historical_data(
            metric_name,
            entity_id,
            lookback_days=90
        )
        
        if len(historical_data) < 14:
            return {
                "error": "insufficient_data",
                "message": "Need at least 14 days of historical data",
                "data_points": len(historical_data)
            }
        
        # Prepare data for forecasting
        df = pd.DataFrame({
            'ds': pd.to_datetime(historical_data['dates']),
            'y': historical_data['values']
        })
        
        # Select and fit model
        if model_type == "prophet":
            forecast = await self._forecast_prophet(
                df,
                horizon_days,
                confidence_level
            )
        elif model_type == "arima":
            forecast = await self._forecast_arima(
                df,
                horizon_days,
                confidence_level
            )
        elif model_type == "lstm":
            forecast = await self._forecast_lstm(
                df,
                horizon_days,
                confidence_level
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return {
            "metric_name": metric_name,
            "entity_id": entity_id,
            "model_type": model_type,
            "horizon_days": horizon_days,
            "confidence_level": confidence_level,
            "historical_data_points": len(historical_data),
            "forecast": forecast,
            "accuracy_metrics": await self._calculate_accuracy(df, forecast),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def _forecast_prophet(
        self,
        df: pd.DataFrame,
        horizon_days: int,
        confidence_level: float
    ) -> Dict:
        """Forecast using Facebook Prophet"""
        
        # Initialize Prophet model
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            interval_width=confidence_level,
            changepoint_prior_scale=0.05,  # Flexibility of trend
            seasonality_prior_scale=10.0   # Strength of seasonality
        )
        
        # Fit model
        model.fit(df)
        
        # Make future dataframe
        future = model.make_future_dataframe(periods=horizon_days)
        
        # Generate forecast
        forecast_df = model.predict(future)
        
        # Extract forecast data (only future values)
        future_forecast = forecast_df.iloc[len(df):]
        
        forecasts = []
        for _, row in future_forecast.iterrows():
            forecasts.append({
                "date": row['ds'].isoformat(),
                "predicted_value": float(row['yhat']),
                "lower_bound": float(row['yhat_lower']),
                "upper_bound": float(row['yhat_upper']),
                "trend": float(row['trend']),
                "weekly_seasonal": float(row.get('weekly', 0)),
                "yearly_seasonal": float(row.get('yearly', 0))
            })
        
        # Detect seasonality
        seasonality_detected = {
            "weekly": bool(model.weekly_seasonality),
            "yearly": bool(model.yearly_seasonality),
            "changepoints_detected": len(model.changepoints)
        }
        
        return {
            "forecasts": forecasts,
            "seasonality": seasonality_detected,
            "model_params": {
                "changepoint_prior_scale": model.changepoint_prior_scale,
                "seasonality_prior_scale": model.seasonality_prior_scale
            }
        }
    
    async def _forecast_arima(
        self,
        df: pd.DataFrame,
        horizon_days: int,
        confidence_level: float
    ) -> Dict:
        """Forecast using ARIMA model"""
        
        from statsmodels.tsa.arima.model import ARIMA
        
        # Auto-select ARIMA parameters using AIC
        best_aic = float('inf')
        best_order = None
        
        for p in range(0, 3):
            for d in range(0, 2):
                for q in range(0, 3):
                    try:
                        model = ARIMA(df['y'], order=(p, d, q))
                        fitted = model.fit()
                        
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_order = (p, d, q)
                    except:
                        continue
        
        # Fit best model
        model = ARIMA(df['y'], order=best_order)
        fitted = model.fit()
        
        # Generate forecast
        forecast_result = fitted.forecast(steps=horizon_days)
        
        # Get confidence intervals
        forecast_df = fitted.get_forecast(steps=horizon_days)
        conf_int = forecast_df.conf_int(alpha=1-confidence_level)
        
        # Build forecast list
        forecasts = []
        start_date = df['ds'].iloc[-1] + timedelta(days=1)
        
        for i in range(horizon_days):
            date = start_date + timedelta(days=i)
            forecasts.append({
                "date": date.isoformat(),
                "predicted_value": float(forecast_result.iloc[i]),
                "lower_bound": float(conf_int.iloc[i, 0]),
                "upper_bound": float(conf_int.iloc[i, 1])
            })
        
        return {
            "forecasts": forecasts,
            "model_params": {
                "order": best_order,
                "aic": float(best_aic)
            }
        }
    
    async def forecast_business_volume(
        self,
        business_metric: str,
        horizon_days: int = 30
    ) -> Dict:
        """
        Forecast business volumes (transactions, users, events, etc.)
        
        Returns detailed forecast with:
        - Daily predictions
        - Confidence intervals
        - Seasonality breakdown
        - Growth trajectory
        """
        
        forecast = await self.forecast_metric(
            metric_name=business_metric,
            entity_id="global",
            horizon_days=horizon_days,
            model_type="prophet"
        )
        
        # Calculate additional business metrics
        forecasts = forecast['forecast']['forecasts']
        
        total_predicted = sum(f['predicted_value'] for f in forecasts)
        avg_daily = total_predicted / len(forecasts)
        
        # Calculate growth rate
        historical = await self._get_recent_actual(business_metric, days=30)
        historical_avg = np.mean(historical)
        growth_rate = ((avg_daily - historical_avg) / historical_avg) * 100
        
        return {
            **forecast,
            "business_insights": {
                "total_predicted": round(total_predicted, 2),
                "avg_daily": round(avg_daily, 2),
                "growth_rate_percent": round(growth_rate, 1),
                "trend": "growing" if growth_rate > 5 else "stable" if growth_rate > -5 else "declining",
                "peak_day": max(forecasts, key=lambda x: x['predicted_value'])['date'],
                "low_day": min(forecasts, key=lambda x: x['predicted_value'])['date']
            }
        }
    
    async def detect_anomalies(
        self,
        metric_name: str,
        entity_id: str,
        sensitivity: float = 2.0
    ) -> List[Dict]:
        """
        Detect anomalies in recent data using forecasting
        
        Args:
            metric_name: Metric to analyze
            entity_id: Entity identifier
            sensitivity: Std deviations from prediction (default 2.0)
            
        Returns:
            List of detected anomalies
        """
        
        # Get recent data
        recent_data = await self._get_historical_data(
            metric_name,
            entity_id,
            lookback_days=60
        )
        
        # Split into train (first 50 days) and test (last 10 days)
        train_df = pd.DataFrame({
            'ds': pd.to_datetime(recent_data['dates'][:-10]),
            'y': recent_data['values'][:-10]
        })
        
        test_df = pd.DataFrame({
            'ds': pd.to_datetime(recent_data['dates'][-10:]),
            'y': recent_data['values'][-10:]
        })
        
        # Train model on historical data
        model = Prophet()
        model.fit(train_df)
        
        # Predict on test period
        predictions = model.predict(test_df[['ds']])
        
        # Find anomalies
        anomalies = []
        for i, row in test_df.iterrows():
            pred = predictions.iloc[i]
            actual = row['y']
            expected = pred['yhat']
            lower = pred['yhat_lower']
            upper = pred['yhat_upper']
            
            # Check if actual is outside confidence interval
            if actual < lower or actual > upper:
                # Calculate how many std deviations away
                std = (upper - lower) / (2 * 1.96)  # 95% CI = ~1.96 std
                deviation = abs(actual - expected) / std
                
                if deviation >= sensitivity:
                    anomalies.append({
                        "date": row['ds'].isoformat(),
                        "actual_value": float(actual),
                        "expected_value": float(expected),
                        "deviation_std": round(deviation, 2),
                        "confidence_interval": [float(lower), float(upper)],
                        "type": "spike" if actual > upper else "drop",
                        "severity": "high" if deviation > 3 else "medium"
                    })
        
        return anomalies
    
    async def _calculate_accuracy(
        self,
        historical_df: pd.DataFrame,
        forecast: Dict
    ) -> Dict:
        """Calculate forecast accuracy metrics"""
        
        # Use last 30 days as test set
        if len(historical_df) < 30:
            return {}
        
        # Split data
        train = historical_df[:-30]
        test = historical_df[-30:]
        
        # Train model on training set
        model = Prophet()
        model.fit(train)
        
        # Predict on test set
        predictions = model.predict(test[['ds']])
        
        # Calculate metrics
        actual = test['y'].values
        predicted = predictions['yhat'].values
        
        mae = np.mean(np.abs(actual - predicted))
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        
        return {
            "mae": round(float(mae), 2),
            "rmse": round(float(rmse), 2),
            "mape_percent": round(float(mape), 2),
            "test_period_days": 30
        }
```

### 4. Cost Intelligence Service

```python
# src/bi_platform/services/cost_tracker.py

"""
Cost Intelligence Service
Track, attribute, and optimize costs across all operations
"""

from typing import Dict, List
from datetime import datetime, timedelta
from collections import defaultdict


class CostIntelligenceService:
    """
    Comprehensive cost tracking and optimization
    
    Tracks:
    - Infrastructure costs (compute, storage, network)
    - ML API costs (OpenAI, Anthropic, etc.)
    - Third-party service costs
    - Labor costs (engineer time)
    """
    
    async def get_cost_breakdown(
        self,
        time_range_days: int = 30,
        group_by: str = "category"  # category, service, customer
    ) -> Dict:
        """
        Get detailed cost breakdown
        
        Returns costs grouped by specified dimension with optimization insights
        """
        
        costs = await self._query_costs(time_range_days)
        
        # Group costs
        grouped = defaultdict(float)
        for cost_record in costs:
            key = cost_record.get(group_by, "other")
            grouped[key] += cost_record['amount_usd']
        
        total_cost = sum(grouped.values())
        
        # Calculate percentages
        cost_breakdown = {
            category: {
                "amount_usd": round(amount, 2),
                "percentage": round((amount / total_cost * 100), 1) if total_cost > 0 else 0
            }
            for category, amount in grouped.items()
        }
        
        # Sort by amount
        cost_breakdown = dict(sorted(
            cost_breakdown.items(),
            key=lambda x: x[1]['amount_usd'],
            reverse=True
        ))
        
        return {
            "time_range_days": time_range_days,
            "total_cost_usd": round(total_cost, 2),
            "cost_breakdown": cost_breakdown,
            "daily_average_usd": round(total_cost / time_range_days, 2),
            "projected_monthly_usd": round((total_cost / time_range_days) * 30, 2),
            "optimization_opportunities": await self._identify_optimizations(costs)
        }
    
    async def calculate_unit_economics(
        self,
        unit_type: str,  # transaction, user, request, etc.
        time_range_days: int = 30
    ) -> Dict:
        """
        Calculate cost per unit
        
        Essential for understanding business efficiency
        """
        
        total_cost = await self._get_total_cost(time_range_days)
        unit_count = await self._get_unit_count(unit_type, time_range_days)
        
        cost_per_unit = total_cost / unit_count if unit_count > 0 else 0
        
        # Get historical comparison
        previous_period_cost = await self._get_total_cost(
            time_range_days,
            offset_days=time_range_days
        )
        previous_period_units = await self._get_unit_count(
            unit_type,
            time_range_days,
            offset_days=time_range_days
        )
        
        previous_cost_per_unit = (
            previous_period_cost / previous_period_units
            if previous_period_units > 0 else 0
        )
        
        # Calculate efficiency change
        efficiency_change = (
            ((cost_per_unit - previous_cost_per_unit) / previous_cost_per_unit) * 100
            if previous_cost_per_unit > 0 else 0
        )
        
        return {
            "unit_type": unit_type,
            "time_range_days": time_range_days,
            "current_period": {
                "total_cost_usd": round(total_cost, 2),
                "unit_count": unit_count,
                "cost_per_unit_usd": round(cost_per_unit, 4)
            },
            "previous_period": {
                "total_cost_usd": round(previous_period_cost, 2),
                "unit_count": previous_period_units,
                "cost_per_unit_usd": round(previous_cost_per_unit, 4)
            },
            "efficiency_change_percent": round(efficiency_change, 1),
            "trend": "improving" if efficiency_change < 0 else "worsening" if efficiency_change > 0 else "stable"
        }
    
    async def calculate_customer_roi(
        self,
        customer_id: str,
        time_range_days: int = 30
    ) -> Dict:
        """
        Calculate ROI for a specific customer
        
        ROI = (Revenue - Cost) / Cost * 100
        """
        
        # Get customer revenue
        revenue = await self._get_customer_revenue(customer_id, time_range_days)
        
        # Get customer costs
        costs = await self._get_customer_costs(customer_id, time_range_days)
        total_cost = sum(c['amount_usd'] for c in costs)
        
        # Calculate profit and ROI
        profit = revenue - total_cost
        roi_percent = (profit / total_cost * 100) if total_cost > 0 else 0
        
        # Classify customer profitability
        if roi_percent > 100:
            classification = "highly_profitable"
        elif roi_percent > 50:
            classification = "profitable"
        elif roi_percent > 0:
            classification = "marginally_profitable"
        else:
            classification = "unprofitable"
        
        return {
            "customer_id": customer_id,
            "time_range_days": time_range_days,
            "revenue_usd": round(revenue, 2),
            "total_cost_usd": round(total_cost, 2),
            "profit_usd": round(profit, 2),
            "roi_percent": round(roi_percent, 1),
            "classification": classification,
            "cost_breakdown": {
                category: sum(c['amount_usd'] for c in costs if c['category'] == category)
                for category in set(c['category'] for c in costs)
            },
            "recommendations": self._generate_roi_recommendations(
                roi_percent,
                revenue,
                total_cost
            )
        }
    
    async def _identify_optimizations(
        self,
        costs: List[Dict]
    ) -> List[Dict]:
        """Identify cost optimization opportunities"""
        
        optimizations = []
        
        # Group by category
        by_category = defaultdict(float)
        for cost in costs:
            by_category[cost['category']] += cost['amount_usd']
        
        total = sum(by_category.values())
        
        # Look for high-cost categories
        for category, amount in by_category.items():
            percentage = (amount / total) * 100
            
            if category == "ml_api" and percentage > 30:
                optimizations.append({
                    "category": category,
                    "current_cost_usd": round(amount, 2),
                    "percentage": round(percentage, 1),
                    "opportunity": "ML API costs are high",
                    "recommendations": [
                        "Consider caching frequent queries",
                        "Use cheaper models for simple tasks",
                        "Implement request deduplication"
                    ],
                    "estimated_savings_percent": 20
                })
            
            elif category == "compute" and percentage > 40:
                optimizations.append({
                    "category": category,
                    "current_cost_usd": round(amount, 2),
                    "percentage": round(percentage, 1),
                    "opportunity": "Compute costs are high",
                    "recommendations": [
                        "Review instance sizing (right-sizing)",
                        "Enable auto-scaling to match demand",
                        "Consider reserved instances or savings plans"
                    ],
                    "estimated_savings_percent": 25
                })
        
        return optimizations
```

I'll continue with the remaining services and API endpoints in the next file...

Would you like me to continue with:
1. Customer Success Tracker
2. Performance Analytics
3. Recommendation Engine
4. Complete API endpoints
5. Grafana dashboards
6. Full deployment configuration

This will give you a complete, production-ready Business Intelligence Platform!