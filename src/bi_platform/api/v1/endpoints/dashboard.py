"""
Dashboard API Endpoints
Comprehensive endpoints for business intelligence dashboards
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import datetime

from bi_platform.services.health_scorer import HealthScoringService
from bi_platform.services.forecasting_engine import ForecastingEngine
from bi_platform.services.cost_tracker import CostIntelligenceService
from bi_platform.services.customer_success_tracker import CustomerSuccessTracker
from bi_platform.services.recommendation_engine import RecommendationEngine
from shared.core.auth import get_current_user

router = APIRouter()

# Initialize services
health_scorer = HealthScoringService()
forecaster = ForecastingEngine()
cost_tracker = CostIntelligenceService()
customer_tracker = CustomerSuccessTracker()
recommender = RecommendationEngine()


@router.get("/executive")
async def get_executive_dashboard(
    time_range_days: int = Query(30, ge=1, le=90),
    current_user = Depends(get_current_user)
):
    """
    Executive Dashboard
    
    High-level overview for executives with key metrics and trends
    """
    
    # Get key metrics
    total_customers = await _get_total_customers()
    total_revenue = await _get_total_revenue(time_range_days)
    active_users = await _get_active_users()
    
    # Health scores
    platform_health = await health_scorer.score_service("platform", time_range_days)
    
    # Top customers by health
    top_customers = await health_scorer.get_health_leaderboard("customer", limit=5)
    
    # At-risk customers
    at_risk = await customer_tracker.get_at_risk_customers(limit=5)
    
    # Cost summary
    costs = await cost_tracker.get_cost_breakdown(time_range_days)
    
    # Top recommendations
    recommendations = await recommender.generate_recommendations("platform")
    top_recommendations = recommendations[:5]
    
    return {
        "dashboard_type": "executive",
        "time_range_days": time_range_days,
        "generated_at": datetime.utcnow().isoformat(),
        "key_metrics": {
            "total_customers": total_customers,
            "total_revenue_usd": total_revenue,
            "active_users": active_users,
            "platform_health_score": platform_health.score,
            "platform_health_status": platform_health.status
        },
        "health": {
            "platform_score": platform_health.score,
            "top_services": top_customers[:5],
            "at_risk_customers": len(at_risk),
            "at_risk_revenue_usd": sum(c.health_score for c in at_risk)  # Placeholder
        },
        "costs": {
            "total_usd": costs['total_cost_usd'],
            "daily_average_usd": costs['daily_average_usd'],
            "projected_monthly_usd": costs['projected_monthly_usd'],
            "top_categories": list(costs['cost_breakdown'].items())[:3]
        },
        "top_recommendations": top_recommendations,
        "alerts": await _get_critical_alerts()
    }


@router.get("/operations")
async def get_operations_dashboard(
    time_range_days: int = Query(7, ge=1, le=30),
    current_user = Depends(get_current_user)
):
    """
    Operations Dashboard
    
    Detailed operational metrics for engineering and ops teams
    """
    
    # Service health scores
    services = await _get_all_services()
    service_scores = []
    for service_id in services:
        score = await health_scorer.score_service(service_id, time_range_days)
        service_scores.append({
            'service_id': service_id,
            'service_name': score.entity_name,
            'health_score': score.score,
            'status': score.status,
            'availability': score.components['availability']['uptime_percent'],
            'performance': score.components['performance']['p99_latency_ms']
        })
    
    # Sort by health score (lowest first - needs attention)
    service_scores.sort(key=lambda x: x['health_score'])
    
    # Performance recommendations
    perf_recommendations = await recommender.generate_recommendations(
        "platform",
        recommendation_types=[RecommendationType.PERFORMANCE]
    )
    
    return {
        "dashboard_type": "operations",
        "time_range_days": time_range_days,
        "generated_at": datetime.utcnow().isoformat(),
        "services": {
            "total_count": len(service_scores),
            "healthy_count": sum(1 for s in service_scores if s['status'] == 'healthy'),
            "needs_attention_count": sum(1 for s in service_scores if s['status'] in ['concerning', 'critical']),
            "details": service_scores
        },
        "performance": {
            "avg_health_score": sum(s['health_score'] for s in service_scores) / len(service_scores) if service_scores else 0,
            "services_below_threshold": [s for s in service_scores if s['health_score'] < 75]
        },
        "recommendations": perf_recommendations[:10]
    }


@router.get("/customer-success")
async def get_customer_success_dashboard(
    time_range_days: int = Query(30, ge=1, le=90),
    current_user = Depends(get_current_user)
):
    """
    Customer Success Dashboard
    
    Customer health, engagement, and success metrics
    """
    
    # Get customer metrics
    total_customers = await _get_total_customers()
    
    # At-risk customers
    at_risk = await customer_tracker.get_at_risk_customers(limit=20)
    
    # Expansion candidates
    expansion = await customer_tracker.get_expansion_candidates(limit=20)
    
    # Cohort analysis
    cohorts = await customer_tracker.get_customer_cohort_analysis()
    
    # CS recommendations
    cs_recommendations = await recommender.generate_recommendations(
        "platform",
        recommendation_types=[RecommendationType.CUSTOMER_SUCCESS, RecommendationType.GROWTH]
    )
    
    return {
        "dashboard_type": "customer_success",
        "time_range_days": time_range_days,
        "generated_at": datetime.utcnow().isoformat(),
        "overview": {
            "total_customers": total_customers,
            "healthy_customers": sum(1 for c in at_risk if c.health_score >= 75),
            "at_risk_customers": len(at_risk),
            "expansion_candidates": len(expansion)
        },
        "at_risk": {
            "count": len(at_risk),
            "total_revenue_at_risk_usd": sum(c.health_score for c in at_risk),  # Placeholder
            "top_risks": [
                {
                    'customer_id': c.customer_id,
                    'customer_name': c.customer_name,
                    'health_score': c.health_score,
                    'churn_risk_score': c.churn_risk_score,
                    'days_until_renewal': c.days_until_renewal
                }
                for c in at_risk[:10]
            ]
        },
        "expansion": {
            "count": len(expansion),
            "potential_revenue_usd": sum(e['estimated_expansion_value'] for e in expansion),
            "top_opportunities": expansion[:10]
        },
        "cohorts": cohorts,
        "recommendations": cs_recommendations[:10]
    }


@router.get("/financial")
async def get_financial_dashboard(
    time_range_days: int = Query(30, ge=1, le=90),
    current_user = Depends(get_current_user)
):
    """
    Financial Dashboard
    
    Cost intelligence, unit economics, and ROI tracking
    """
    
    # Cost breakdown
    costs = await cost_tracker.get_cost_breakdown(time_range_days, group_by="category")
    
    # Unit economics
    unit_economics = await cost_tracker.calculate_unit_economics("transaction", time_range_days)
    
    # Customer profitability
    customers = await _get_all_customers()
    customer_roi = []
    for customer_id in customers[:20]:  # Top 20 customers
        roi = await cost_tracker.calculate_customer_roi(customer_id, time_range_days)
        customer_roi.append(roi)
    
    # Sort by ROI
    customer_roi.sort(key=lambda x: x['roi_percent'], reverse=True)
    
    # Cost recommendations
    cost_recommendations = await recommender.generate_recommendations(
        "platform",
        recommendation_types=[RecommendationType.COST]
    )
    
    return {
        "dashboard_type": "financial",
        "time_range_days": time_range_days,
        "generated_at": datetime.utcnow().isoformat(),
        "costs": costs,
        "unit_economics": unit_economics,
        "customer_profitability": {
            "highly_profitable": [c for c in customer_roi if c['classification'] == 'highly_profitable'],
            "profitable": [c for c in customer_roi if c['classification'] == 'profitable'],
            "marginally_profitable": [c for c in customer_roi if c['classification'] == 'marginally_profitable'],
            "unprofitable": [c for c in customer_roi if c['classification'] == 'unprofitable']
        },
        "optimization_opportunities": cost_recommendations[:10]
    }


@router.get("/predictive")
async def get_predictive_dashboard(
    horizon_days: int = Query(30, ge=7, le=90),
    current_user = Depends(get_current_user)
):
    """
    Predictive Analytics Dashboard
    
    Forecasts, predictions, and forward-looking metrics
    """
    
    # Revenue forecast
    revenue_forecast = await forecaster.forecast_business_volume("revenue", horizon_days)
    
    # User growth forecast
    user_forecast = await forecaster.forecast_business_volume("active_users", horizon_days)
    
    # Transaction volume forecast
    transaction_forecast = await forecaster.forecast_business_volume("transactions", horizon_days)
    
    # Anomaly detection
    anomalies = await forecaster.detect_anomalies("revenue", "global")
    
    return {
        "dashboard_type": "predictive",
        "horizon_days": horizon_days,
        "generated_at": datetime.utcnow().isoformat(),
        "forecasts": {
            "revenue": {
                "total_predicted_usd": revenue_forecast['business_insights']['total_predicted'],
                "growth_rate_percent": revenue_forecast['business_insights']['growth_rate_percent'],
                "trend": revenue_forecast['business_insights']['trend'],
                "daily_forecast": revenue_forecast['forecast']['forecasts'][:30]
            },
            "users": {
                "total_predicted": user_forecast['business_insights']['total_predicted'],
                "growth_rate_percent": user_forecast['business_insights']['growth_rate_percent'],
                "daily_forecast": user_forecast['forecast']['forecasts'][:30]
            },
            "transactions": {
                "total_predicted": transaction_forecast['business_insights']['total_predicted'],
                "growth_rate_percent": transaction_forecast['business_insights']['growth_rate_percent'],
                "daily_forecast": transaction_forecast['forecast']['forecasts'][:30]
            }
        },
        "anomalies": {
            "count": len(anomalies),
            "recent_anomalies": anomalies
        },
        "confidence": {
            "revenue_forecast": revenue_forecast['accuracy_metrics'],
            "user_forecast": user_forecast['accuracy_metrics']
        }
    }


# Service-specific endpoints

@router.get("/service/{service_id}/health")
async def get_service_health(
    service_id: str,
    lookback_days: int = Query(7, ge=1, le=30),
    current_user = Depends(get_current_user)
):
    """Get detailed health metrics for a specific service"""
    
    health_score = await health_scorer.score_service(service_id, lookback_days)
    
    # Get historical trend
    health_trends = await health_scorer.get_health_trends("service", service_id, days=30)
    
    # Get recommendations
    recommendations = await recommender.generate_recommendations("service", service_id)
    
    return {
        "service_id": service_id,
        "current_health": {
            "score": health_score.score,
            "grade": health_score.grade,
            "status": health_score.status,
            "components": health_score.components,
            "recommendations": health_score.recommendations
        },
        "trends": health_trends,
        "actionable_recommendations": recommendations[:5]
    }


@router.get("/customer/{customer_id}/metrics")
async def get_customer_metrics(
    customer_id: str,
    lookback_days: int = Query(30, ge=1, le=90),
    current_user = Depends(get_current_user)
):
    """Get comprehensive metrics for a specific customer"""
    
    metrics = await customer_tracker.get_customer_metrics(customer_id, lookback_days)
    roi = await cost_tracker.calculate_customer_roi(customer_id, lookback_days)
    recommendations = await recommender.generate_recommendations("customer", customer_id)
    
    return {
        "customer_id": customer_id,
        "customer_name": metrics.customer_name,
        "health_score": metrics.health_score,
        "engagement": {
            "daily_active_users": metrics.daily_active_users,
            "monthly_active_users": metrics.monthly_active_users,
            "feature_adoption_rate": metrics.feature_adoption_rate
        },
        "satisfaction": {
            "nps_score": metrics.nps_score,
            "csat_score": metrics.csat_score,
            "support_tickets": metrics.support_tickets_count
        },
        "growth": {
            "usage_growth_rate": metrics.usage_growth_rate,
            "revenue_growth_rate": metrics.revenue_growth_rate,
            "expansion_opportunities": metrics.expansion_opportunities
        },
        "risk": {
            "churn_risk_score": metrics.churn_risk_score,
            "payment_issues": metrics.payment_issues,
            "days_until_renewal": metrics.days_until_renewal
        },
        "financial": roi,
        "recommendations": recommendations
    }


@router.get("/forecast/{metric_name}")
async def get_metric_forecast(
    metric_name: str,
    entity_id: str = Query("global"),
    horizon_days: int = Query(30, ge=7, le=90),
    model_type: str = Query("prophet", regex="^(prophet|arima|lstm)$"),
    current_user = Depends(get_current_user)
):
    """Forecast a specific metric"""
    
    forecast = await forecaster.forecast_metric(
        metric_name=metric_name,
        entity_id=entity_id,
        horizon_days=horizon_days,
        model_type=model_type
    )
    
    return forecast


@router.get("/recommendations")
async def get_recommendations(
    context: str = Query("platform", regex="^(platform|customer|service)$"),
    entity_id: Optional[str] = None,
    recommendation_types: Optional[List[str]] = Query(None),
    current_user = Depends(get_current_user)
):
    """Get prioritized recommendations"""
    
    if recommendation_types:
        rec_types = [RecommendationType(t) for t in recommendation_types]
    else:
        rec_types = None
    
    recommendations = await recommender.generate_recommendations(
        context=context,
        entity_id=entity_id,
        recommendation_types=rec_types
    )
    
    return {
        "context": context,
        "entity_id": entity_id,
        "total_recommendations": len(recommendations),
        "by_priority": {
            "critical": [r for r in recommendations if r['priority'] == 'critical'],
            "high": [r for r in recommendations if r['priority'] == 'high'],
            "medium": [r for r in recommendations if r['priority'] == 'medium'],
            "low": [r for r in recommendations if r['priority'] == 'low']
        },
        "recommendations": recommendations
    }


# Helper functions (these would query actual databases)

async def _get_total_customers() -> int:
    # Query database for total customers
    return 150  # Placeholder

async def _get_total_revenue(days: int) -> float:
    # Query database for revenue in time period
    return 50000.0  # Placeholder

async def _get_active_users() -> int:
    # Query database for active users
    return 5000  # Placeholder

async def _get_all_services() -> List[str]:
    # Query database for all service IDs
    return ["api-gateway", "auth-service", "data-processor", "notification-service"]

async def _get_all_customers() -> List[str]:
    # Query database for all customer IDs
    return [f"cust-{i}" for i in range(1, 51)]  # Placeholder

async def _get_critical_alerts() -> List[Dict]:
    # Query for critical alerts that need attention
    return []  # Placeholder
```

