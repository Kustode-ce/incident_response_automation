"""
Customer Success Tracking Service
Track customer engagement, satisfaction, adoption, and churn risk
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np


@dataclass
class CustomerMetrics:
    """Customer health and engagement metrics"""
    customer_id: str
    customer_name: str
    
    # Engagement
    daily_active_users: int
    monthly_active_users: int
    feature_adoption_rate: float  # 0-100
    session_duration_avg_mins: float
    
    # Satisfaction
    nps_score: Optional[float]  # -100 to 100
    csat_score: Optional[float]  # 0-100
    support_tickets_count: int
    support_satisfaction: Optional[float]  # 0-100
    
    # Growth
    usage_growth_rate: float  # Percent
    revenue_growth_rate: float
    expansion_opportunities: List[str]
    
    # Risk
    churn_risk_score: float  # 0-100 (higher = more risk)
    payment_issues: int
    contract_renewal_date: Optional[datetime]
    days_until_renewal: Optional[int]
    
    # Overall
    health_score: float  # 0-100
    last_updated: datetime


class CustomerSuccessTracker:
    """Track and analyze customer success metrics"""
    
    async def get_customer_metrics(
        self,
        customer_id: str,
        lookback_days: int = 30
    ) -> CustomerMetrics:
        """Get comprehensive customer metrics"""
        
        # Fetch raw data
        usage_data = await self._get_usage_data(customer_id, lookback_days)
        satisfaction_data = await self._get_satisfaction_data(customer_id, lookback_days)
        financial_data = await self._get_financial_data(customer_id, lookback_days)
        support_data = await self._get_support_data(customer_id, lookback_days)
        
        # Calculate engagement metrics
        dau = usage_data.get('daily_active_users', 0)
        mau = usage_data.get('monthly_active_users', 0)
        feature_adoption = self._calculate_feature_adoption(usage_data)
        session_duration = usage_data.get('avg_session_duration_mins', 0)
        
        # Calculate growth metrics
        usage_growth = self._calculate_growth_rate(
            usage_data.get('current_usage', 0),
            usage_data.get('previous_usage', 0)
        )
        revenue_growth = self._calculate_growth_rate(
            financial_data.get('current_revenue', 0),
            financial_data.get('previous_revenue', 0)
        )
        
        # Calculate churn risk
        churn_risk = await self._calculate_churn_risk(
            usage_data,
            satisfaction_data,
            financial_data,
            support_data
        )
        
        # Calculate overall health score
        health_score = await self._calculate_customer_health_score(
            dau,
            mau,
            feature_adoption,
            satisfaction_data.get('nps'),
            churn_risk
        )
        
        return CustomerMetrics(
            customer_id=customer_id,
            customer_name=financial_data.get('customer_name', customer_id),
            daily_active_users=dau,
            monthly_active_users=mau,
            feature_adoption_rate=feature_adoption,
            session_duration_avg_mins=session_duration,
            nps_score=satisfaction_data.get('nps'),
            csat_score=satisfaction_data.get('csat'),
            support_tickets_count=support_data.get('ticket_count', 0),
            support_satisfaction=support_data.get('satisfaction'),
            usage_growth_rate=usage_growth,
            revenue_growth_rate=revenue_growth,
            expansion_opportunities=await self._identify_expansion_opportunities(usage_data),
            churn_risk_score=churn_risk,
            payment_issues=financial_data.get('payment_issues', 0),
            contract_renewal_date=financial_data.get('renewal_date'),
            days_until_renewal=financial_data.get('days_until_renewal'),
            health_score=health_score,
            last_updated=datetime.utcnow()
        )
    
    async def get_at_risk_customers(
        self,
        risk_threshold: float = 70.0,
        limit: int = 20
    ) -> List[CustomerMetrics]:
        """Identify customers at risk of churning"""
        
        all_customers = await self._get_all_customers()
        at_risk = []
        
        for customer_id in all_customers:
            metrics = await self.get_customer_metrics(customer_id)
            
            if metrics.churn_risk_score >= risk_threshold:
                at_risk.append(metrics)
        
        # Sort by churn risk (highest first)
        at_risk.sort(key=lambda x: x.churn_risk_score, reverse=True)
        
        return at_risk[:limit]
    
    async def get_expansion_candidates(
        self,
        health_threshold: float = 80.0,
        limit: int = 20
    ) -> List[Dict]:
        """Identify customers ready for upsell/expansion"""
        
        all_customers = await self._get_all_customers()
        candidates = []
        
        for customer_id in all_customers:
            metrics = await self.get_customer_metrics(customer_id)
            
            # Healthy customers with expansion opportunities
            if (metrics.health_score >= health_threshold and 
                len(metrics.expansion_opportunities) > 0):
                
                candidates.append({
                    'customer_id': customer_id,
                    'customer_name': metrics.customer_name,
                    'health_score': metrics.health_score,
                    'usage_growth_rate': metrics.usage_growth_rate,
                    'expansion_opportunities': metrics.expansion_opportunities,
                    'estimated_expansion_value': await self._estimate_expansion_value(
                        customer_id,
                        metrics.expansion_opportunities
                    )
                })
        
        # Sort by health score and expansion potential
        candidates.sort(
            key=lambda x: (x['health_score'], len(x['expansion_opportunities'])),
            reverse=True
        )
        
        return candidates[:limit]
    
    async def get_customer_cohort_analysis(
        self,
        cohort_by: str = "signup_month"
    ) -> Dict:
        """Analyze customer retention by cohort"""
        
        cohorts = await self._get_cohorts(cohort_by)
        
        cohort_data = []
        for cohort in cohorts:
            retention = await self._calculate_cohort_retention(cohort)
            revenue = await self._calculate_cohort_revenue(cohort)
            
            cohort_data.append({
                'cohort_period': cohort['period'],
                'initial_customers': cohort['initial_count'],
                'retention_rates': retention,
                'revenue_per_customer': revenue,
                'churn_rate': 100 - retention[-1] if retention else 0
            })
        
        return {
            'cohort_by': cohort_by,
            'cohorts': cohort_data,
            'overall_retention': await self._calculate_overall_retention(),
            'analysis_date': datetime.utcnow().isoformat()
        }
    
    async def _calculate_churn_risk(
        self,
        usage_data: Dict,
        satisfaction_data: Dict,
        financial_data: Dict,
        support_data: Dict
    ) -> float:
        """
        Calculate churn risk score (0-100, higher = more risk)
        
        Risk factors:
        - Declining usage
        - Low satisfaction scores
        - High support ticket volume
        - Payment issues
        - No contract renewal yet
        """
        
        risk_score = 0.0
        
        # Usage decline (30 points)
        usage_trend = usage_data.get('usage_trend', 'stable')
        if usage_trend == 'declining':
            decline_rate = abs(usage_data.get('usage_growth_rate', 0))
            risk_score += min(30, decline_rate)
        elif usage_trend == 'sharply_declining':
            risk_score += 30
        
        # Low engagement (20 points)
        dau_mau_ratio = usage_data.get('dau_mau_ratio', 0)
        if dau_mau_ratio < 0.2:  # Less than 20% daily engagement
            risk_score += 20
        elif dau_mau_ratio < 0.4:
            risk_score += 10
        
        # Satisfaction issues (25 points)
        nps = satisfaction_data.get('nps', 0)
        if nps < 0:  # Detractors
            risk_score += 25
        elif nps < 30:  # Passives
            risk_score += 15
        
        # Support issues (15 points)
        ticket_count = support_data.get('ticket_count', 0)
        if ticket_count > 10:
            risk_score += 15
        elif ticket_count > 5:
            risk_score += 10
        
        # Financial issues (10 points)
        payment_issues = financial_data.get('payment_issues', 0)
        risk_score += min(10, payment_issues * 3)
        
        return min(100, risk_score)
    
    async def _calculate_customer_health_score(
        self,
        dau: int,
        mau: int,
        feature_adoption: float,
        nps: Optional[float],
        churn_risk: float
    ) -> float:
        """Calculate overall customer health score (0-100)"""
        
        # Engagement (40 points)
        dau_mau_ratio = (dau / mau) if mau > 0 else 0
        engagement_score = (dau_mau_ratio * 40)
        
        # Adoption (30 points)
        adoption_score = (feature_adoption / 100) * 30
        
        # Satisfaction (20 points)
        if nps is not None:
            # Convert NPS (-100 to 100) to 0-20 scale
            nps_normalized = ((nps + 100) / 200) * 20
        else:
            nps_normalized = 10  # Neutral if no data
        
        # Risk (10 points) - inverse of churn risk
        risk_score = (1 - (churn_risk / 100)) * 10
        
        total = engagement_score + adoption_score + nps_normalized + risk_score
        
        return min(100, max(0, total))
    
    def _calculate_feature_adoption(self, usage_data: Dict) -> float:
        """Calculate percentage of features adopted by customer"""
        
        total_features = usage_data.get('total_features_available', 1)
        features_used = usage_data.get('features_used_count', 0)
        
        return (features_used / total_features) * 100
    
    def _calculate_growth_rate(
        self,
        current: float,
        previous: float
    ) -> float:
        """Calculate growth rate percentage"""
        
        if previous == 0:
            return 0.0 if current == 0 else 100.0
        
        return ((current - previous) / previous) * 100
    
    async def _identify_expansion_opportunities(
        self,
        usage_data: Dict
    ) -> List[str]:
        """Identify upsell/cross-sell opportunities"""
        
        opportunities = []
        
        # Check feature usage patterns
        features_used = usage_data.get('features_used', [])
        
        # High usage of certain features suggests need for higher tier
        if 'api_calls' in features_used:
            api_usage = usage_data.get('api_usage_percent', 0)
            if api_usage > 80:
                opportunities.append("API usage near limit - recommend higher tier plan")
        
        # Features in current plan but not used yet
        unused_features = usage_data.get('unused_features', [])
        if len(unused_features) > 0:
            opportunities.append(f"Not using {len(unused_features)} features - training opportunity")
        
        # Adjacent products/features they don't have
        adjacent_products = usage_data.get('adjacent_products_not_purchased', [])
        if adjacent_products:
            opportunities.append(f"Cross-sell opportunity: {', '.join(adjacent_products)}")
        
        return opportunities
```

