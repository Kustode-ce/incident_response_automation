"""
Prometheus Metrics for Business Intelligence Platform
Track all BI operations and ML model performance
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional


# ============================================
# Health Scoring Metrics
# ============================================

service_health_score = Gauge(
    'bi_service_health_score',
    'Service health score (0-100)',
    ['service_id', 'service_name', 'environment']
)

customer_health_score = Gauge(
    'bi_customer_health_score',
    'Customer health score (0-100)',
    ['customer_id', 'customer_name']
)

health_score_calculations_total = Counter(
    'bi_health_score_calculations_total',
    'Total health score calculations',
    ['entity_type', 'status']
)

# ============================================
# Forecasting Metrics
# ============================================

forecast_requests_total = Counter(
    'bi_forecast_requests_total',
    'Total forecasting requests',
    ['model_type', 'metric_name']
)

forecast_duration_seconds = Histogram(
    'bi_forecast_duration_seconds',
    'Time to generate forecast',
    ['model_type', 'horizon_days']
)

forecast_mae = Gauge(
    'bi_forecast_mae',
    'Mean Absolute Error of forecasts',
    ['model_type', 'metric_name', 'horizon_days']
)

forecast_mape = Gauge(
    'bi_forecast_mape_percent',
    'Mean Absolute Percentage Error',
    ['model_type', 'metric_name', 'horizon_days']
)

anomaly_detected_total = Counter(
    'bi_anomaly_detected_total',
    'Total anomalies detected',
    ['metric_name', 'severity']
)

# ============================================
# Cost Intelligence Metrics
# ============================================

cost_tracked_usd = Counter(
    'bi_cost_tracked_usd',
    'Total costs tracked',
    ['category', 'service', 'customer']
)

cost_per_unit = Gauge(
    'bi_cost_per_unit',
    'Cost per business unit',
    ['unit_type', 'period']
)

customer_roi_percent = Gauge(
    'bi_customer_roi_percent',
    'Customer ROI percentage',
    ['customer_id']
)

optimization_savings_usd = Counter(
    'bi_optimization_savings_usd',
    'Savings from optimization recommendations',
    ['optimization_type']
)

# ============================================
# Customer Success Metrics
# ============================================

customer_churn_risk_score = Gauge(
    'bi_customer_churn_risk_score',
    'Customer churn risk score (0-100)',
    ['customer_id', 'customer_name']
)

customer_nps_score = Gauge(
    'bi_customer_nps_score',
    'Customer NPS score (-100 to 100)',
    ['customer_id']
)

feature_adoption_rate = Gauge(
    'bi_feature_adoption_rate_percent',
    'Feature adoption rate',
    ['customer_id', 'feature_name']
)

expansion_opportunities_identified = Counter(
    'bi_expansion_opportunities_identified_total',
    'Expansion opportunities identified',
    ['customer_tier']
)

# ============================================
# Recommendation Metrics
# ============================================

recommendations_generated_total = Counter(
    'bi_recommendations_generated_total',
    'Total recommendations generated',
    ['recommendation_type', 'priority']
)

recommendations_acted_upon_total = Counter(
    'bi_recommendations_acted_upon_total',
    'Recommendations that were acted upon',
    ['recommendation_type', 'outcome']
)

recommendation_impact_usd = Counter(
    'bi_recommendation_impact_usd',
    'Financial impact of recommendations',
    ['recommendation_type', 'impact_type']  # impact_type: cost_savings, revenue_increase
)

# ============================================
# ML Model Performance Metrics
# ============================================

ml_model_predictions_total = Counter(
    'bi_ml_predictions_total',
    'Total ML predictions made',
    ['model_name', 'task_type']
)

ml_model_latency_seconds = Histogram(
    'bi_ml_latency_seconds',
    'ML model inference latency',
    ['model_name', 'task_type']
)

ml_model_confidence = Histogram(
    'bi_ml_confidence',
    'ML model prediction confidence',
    ['model_name', 'task_type'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
)

ml_model_calibration_ece = Gauge(
    'bi_ml_calibration_ece',
    'Expected Calibration Error',
    ['model_name', 'task_type']
)

ml_model_calibration_brier_score = Gauge(
    'bi_ml_calibration_brier_score',
    'Brier score for probability predictions',
    ['model_name', 'task_type']
)

ml_model_accuracy = Gauge(
    'bi_ml_accuracy',
    'Model prediction accuracy',
    ['model_name', 'task_type']
)

# ============================================
# Platform Metrics
# ============================================

platform_status = Gauge(
    'bi_platform_status',
    'Platform status (1=healthy, 0=unhealthy)'
)

api_requests_total = Counter(
    'bi_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status_code']
)

api_request_duration_seconds = Histogram(
    'bi_api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method']
)

active_users = Gauge(
    'bi_active_users',
    'Currently active users',
    ['time_window']  # 5min, 1hour, 1day
)

# ============================================
# Business Metrics
# ============================================

total_revenue_usd = Gauge(
    'bi_total_revenue_usd',
    'Total revenue',
    ['period', 'customer_tier']
)

total_customers = Gauge(
    'bi_total_customers',
    'Total customer count',
    ['tier', 'status']
)

customer_lifetime_value_usd = Gauge(
    'bi_customer_lifetime_value_usd',
    'Average customer lifetime value',
    ['customer_tier']
)


class BiMetrics:
    """Wrapper for all BI platform metrics"""
    
    def record_health_score(
        self,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        score: float,
        status: str
    ):
        """Record a health score calculation"""
        
        if entity_type == "service":
            service_health_score.labels(
                service_id=entity_id,
                service_name=entity_name,
                environment="production"  # TODO: Get from config
            ).set(score)
        elif entity_type == "customer":
            customer_health_score.labels(
                customer_id=entity_id,
                customer_name=entity_name
            ).set(score)
        
        health_score_calculations_total.labels(
            entity_type=entity_type,
            status=status
        ).inc()
    
    def record_forecast(
        self,
        model_type: str,
        metric_name: str,
        horizon_days: int,
        mae: float,
        mape: float,
        duration_seconds: float
    ):
        """Record a forecasting operation"""
        
        forecast_requests_total.labels(
            model_type=model_type,
            metric_name=metric_name
        ).inc()
        
        forecast_duration_seconds.labels(
            model_type=model_type,
            horizon_days=str(horizon_days)
        ).observe(duration_seconds)
        
        forecast_mae.labels(
            model_type=model_type,
            metric_name=metric_name,
            horizon_days=str(horizon_days)
        ).set(mae)
        
        forecast_mape.labels(
            model_type=model_type,
            metric_name=metric_name,
            horizon_days=str(horizon_days)
        ).set(mape)
    
    def record_anomaly(self, metric_name: str, severity: str):
        """Record detected anomaly"""
        anomaly_detected_total.labels(
            metric_name=metric_name,
            severity=severity
        ).inc()
    
    def record_cost(
        self,
        amount_usd: float,
        category: str,
        service: str = "unknown",
        customer: str = "unknown"
    ):
        """Record a cost entry"""
        cost_tracked_usd.labels(
            category=category,
            service=service,
            customer=customer
        ).inc(amount_usd)
    
    def record_churn_risk(
        self,
        customer_id: str,
        customer_name: str,
        risk_score: float
    ):
        """Record customer churn risk score"""
        customer_churn_risk_score.labels(
            customer_id=customer_id,
            customer_name=customer_name
        ).set(risk_score)
    
    def record_recommendation(
        self,
        recommendation_type: str,
        priority: str,
        acted_upon: bool = False,
        impact_usd: Optional[float] = None
    ):
        """Record a generated recommendation"""
        
        recommendations_generated_total.labels(
            recommendation_type=recommendation_type,
            priority=priority
        ).inc()
        
        if acted_upon:
            recommendations_acted_upon_total.labels(
                recommendation_type=recommendation_type,
                outcome="implemented"
            ).inc()
            
            if impact_usd:
                impact_type = "cost_savings" if impact_usd > 0 else "revenue_increase"
                recommendation_impact_usd.labels(
                    recommendation_type=recommendation_type,
                    impact_type=impact_type
                ).inc(abs(impact_usd))
    
    def set_platform_status(self, healthy: bool):
        """Set platform health status"""
        platform_status.set(1 if healthy else 0)


# Singleton instance
_metrics_instance = None

def get_metrics() -> BiMetrics:
    """Get metrics singleton"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = BiMetrics()
    return _metrics_instance
```

