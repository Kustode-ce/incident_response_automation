"""
Recommendation Engine
AI-powered actionable recommendations based on analytics and ML insights
"""

from typing import Dict, List
from datetime import datetime
from enum import Enum


class RecommendationType(str, Enum):
    PERFORMANCE = "performance"
    COST = "cost"
    CUSTOMER_SUCCESS = "customer_success"
    RISK = "risk"
    GROWTH = "growth"


class RecommendationPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationEngine:
    """Generate actionable recommendations based on BI data"""
    
    async def generate_recommendations(
        self,
        context: str = "platform",  # platform, customer, service
        entity_id: Optional[str] = None,
        recommendation_types: Optional[List[RecommendationType]] = None
    ) -> List[Dict]:
        """
        Generate prioritized list of recommendations
        
        Analyzes all available data and provides actionable insights
        """
        
        recommendations = []
        
        # Get relevant data based on context
        if context == "platform":
            data = await self._get_platform_wide_data()
        elif context == "customer":
            data = await self._get_customer_data(entity_id)
        elif context == "service":
            data = await self._get_service_data(entity_id)
        else:
            raise ValueError(f"Unknown context: {context}")
        
        # Generate recommendations by type
        if not recommendation_types:
            recommendation_types = list(RecommendationType)
        
        for rec_type in recommendation_types:
            if rec_type == RecommendationType.PERFORMANCE:
                recs = await self._generate_performance_recommendations(data)
                recommendations.extend(recs)
            
            elif rec_type == RecommendationType.COST:
                recs = await self._generate_cost_recommendations(data)
                recommendations.extend(recs)
            
            elif rec_type == RecommendationType.CUSTOMER_SUCCESS:
                recs = await self._generate_customer_success_recommendations(data)
                recommendations.extend(recs)
            
            elif rec_type == RecommendationType.RISK:
                recs = await self._generate_risk_recommendations(data)
                recommendations.extend(recs)
            
            elif rec_type == RecommendationType.GROWTH:
                recs = await self._generate_growth_recommendations(data)
                recommendations.extend(recs)
        
        # Score and prioritize recommendations
        for rec in recommendations:
            rec['priority_score'] = self._calculate_priority_score(rec)
        
        # Sort by priority score
        recommendations.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return recommendations
    
    async def _generate_performance_recommendations(
        self,
        data: Dict
    ) -> List[Dict]:
        """Generate performance optimization recommendations"""
        
        recommendations = []
        
        # Check latency
        if data.get('p99_latency_ms', 0) > 500:
            impact = self._calculate_latency_impact(data['p99_latency_ms'])
            recommendations.append({
                'type': RecommendationType.PERFORMANCE,
                'priority': self._latency_to_priority(data['p99_latency_ms']),
                'title': 'High Latency Detected',
                'description': f"P99 latency is {data['p99_latency_ms']}ms, above target of 500ms",
                'impact': impact,
                'actions': [
                    {
                        'action': 'Enable caching for frequently accessed data',
                        'estimated_improvement': '30-50% latency reduction'
                    },
                    {
                        'action': 'Review database query performance',
                        'estimated_improvement': '20-40% latency reduction'
                    },
                    {
                        'action': 'Implement CDN for static assets',
                        'estimated_improvement': '40-60% reduction for static content'
                    }
                ],
                'estimated_effort': 'medium',
                'metrics_to_track': ['p99_latency_ms', 'cache_hit_rate'],
                'created_at': datetime.utcnow()
            })
        
        # Check error rates
        if data.get('error_rate_percent', 0) > 1.0:
            recommendations.append({
                'type': RecommendationType.PERFORMANCE,
                'priority': RecommendationPriority.HIGH,
                'title': 'High Error Rate',
                'description': f"Error rate is {data['error_rate_percent']}%, target is <1%",
                'impact': {
                    'affected_requests_per_day': data.get('requests_per_day', 0) * (data['error_rate_percent'] / 100),
                    'customer_impact': 'high',
                    'revenue_at_risk': 'medium'
                },
                'actions': [
                    {
                        'action': 'Implement retry logic with exponential backoff',
                        'estimated_improvement': '50-70% error reduction'
                    },
                    {
                        'action': 'Add circuit breakers for failing dependencies',
                        'estimated_improvement': 'Prevent cascading failures'
                    },
                    {
                        'action': 'Improve error handling and logging',
                        'estimated_improvement': 'Better debugging'
                    }
                ],
                'estimated_effort': 'high',
                'metrics_to_track': ['error_rate_percent', 'retry_success_rate'],
                'created_at': datetime.utcnow()
            })
        
        # Check throughput
        current_throughput = data.get('throughput_rps', 0)
        peak_throughput = data.get('peak_throughput_rps', 0)
        
        if peak_throughput > current_throughput * 1.5:
            recommendations.append({
                'type': RecommendationType.PERFORMANCE,
                'priority': RecommendationPriority.MEDIUM,
                'title': 'Throughput Headroom Available',
                'description': f"Current: {current_throughput} RPS, Peak: {peak_throughput} RPS",
                'impact': {
                    'capacity_utilization': f"{(current_throughput / peak_throughput * 100):.1f}%",
                    'opportunity': 'Can handle more load without scaling'
                },
                'actions': [
                    {
                        'action': 'Right-size infrastructure to match actual demand',
                        'estimated_improvement': '20-30% cost savings'
                    }
                ],
                'estimated_effort': 'low',
                'metrics_to_track': ['throughput_rps', 'cpu_utilization'],
                'created_at': datetime.utcnow()
            })
        
        return recommendations
    
    async def _generate_cost_recommendations(
        self,
        data: Dict
    ) -> List[Dict]:
        """Generate cost optimization recommendations"""
        
        recommendations = []
        
        # ML API costs
        ml_costs = data.get('ml_api_costs_usd', 0)
        total_costs = data.get('total_costs_usd', 1)
        ml_cost_percent = (ml_costs / total_costs) * 100
        
        if ml_cost_percent > 30:
            recommendations.append({
                'type': RecommendationType.COST,
                'priority': RecommendationPriority.HIGH,
                'title': 'High ML API Costs',
                'description': f"ML APIs represent {ml_cost_percent:.1f}% of total costs (${ml_costs:.2f}/month)",
                'impact': {
                    'current_cost_usd_per_month': ml_costs,
                    'potential_savings_usd_per_month': ml_costs * 0.3,
                    'roi': 'high'
                },
                'actions': [
                    {
                        'action': 'Implement aggressive caching for ML predictions',
                        'estimated_improvement': '20-30% cost reduction',
                        'implementation': 'Cache predictions for 1 hour, deduplicate similar queries'
                    },
                    {
                        'action': 'Use cheaper models for simple classification tasks',
                        'estimated_improvement': '15-25% cost reduction',
                        'implementation': 'Route low-complexity queries to GPT-3.5 instead of GPT-4'
                    },
                    {
                        'action': 'Batch API requests where possible',
                        'estimated_improvement': '10-15% cost reduction',
                        'implementation': 'Batch up to 10 requests per API call'
                    }
                ],
                'estimated_effort': 'medium',
                'metrics_to_track': ['ml_api_cost_usd', 'cache_hit_rate', 'cost_per_prediction'],
                'created_at': datetime.utcnow()
            })
        
        # Compute over-provisioning
        avg_cpu = data.get('avg_cpu_utilization', 0)
        if avg_cpu < 40:
            recommendations.append({
                'type': RecommendationType.COST,
                'priority': RecommendationPriority.MEDIUM,
                'title': 'Compute Under-Utilized',
                'description': f"Average CPU utilization is {avg_cpu}%, instances may be over-provisioned",
                'impact': {
                    'current_cost_usd_per_month': data.get('compute_costs_usd', 0),
                    'potential_savings_usd_per_month': data.get('compute_costs_usd', 0) * 0.25,
                    'roi': 'medium'
                },
                'actions': [
                    {
                        'action': 'Right-size instances to match actual usage',
                        'estimated_improvement': '20-30% cost savings',
                        'implementation': 'Downgrade to smaller instance types'
                    },
                    {
                        'action': 'Enable auto-scaling to scale down during low traffic',
                        'estimated_improvement': '15-25% cost savings',
                        'implementation': 'Scale to min instances during off-peak hours'
                    }
                ],
                'estimated_effort': 'low',
                'metrics_to_track': ['compute_costs_usd', 'avg_cpu_utilization'],
                'created_at': datetime.utcnow()
            })
        
        return recommendations
    
    async def _generate_customer_success_recommendations(
        self,
        data: Dict
    ) -> List[Dict]:
        """Generate customer success recommendations"""
        
        recommendations = []
        
        # At-risk customers
        at_risk_count = data.get('at_risk_customers_count', 0)
        if at_risk_count > 0:
            recommendations.append({
                'type': RecommendationType.CUSTOMER_SUCCESS,
                'priority': RecommendationPriority.CRITICAL,
                'title': 'Customers At Risk',
                'description': f"{at_risk_count} customers showing churn risk indicators",
                'impact': {
                    'customers_affected': at_risk_count,
                    'revenue_at_risk_usd': data.get('at_risk_revenue_usd', 0),
                    'urgency': 'immediate_action_required'
                },
                'actions': [
                    {
                        'action': 'Schedule executive business reviews with at-risk accounts',
                        'timeline': 'This week'
                    },
                    {
                        'action': 'Conduct usage analysis to identify friction points',
                        'timeline': 'Within 3 days'
                    },
                    {
                        'action': 'Offer proactive support and training',
                        'timeline': 'Immediately'
                    }
                ],
                'estimated_effort': 'high',
                'metrics_to_track': ['churn_risk_score', 'customer_engagement'],
                'created_at': datetime.utcnow()
            })
        
        # Low feature adoption
        avg_adoption = data.get('avg_feature_adoption_percent', 0)
        if avg_adoption < 50:
            recommendations.append({
                'type': RecommendationType.CUSTOMER_SUCCESS,
                'priority': RecommendationPriority.HIGH,
                'title': 'Low Feature Adoption',
                'description': f"Average feature adoption is {avg_adoption}%, indicating under-utilization",
                'impact': {
                    'customer_value_realization': 'low',
                    'expansion_opportunity': 'limited',
                    'churn_risk': 'elevated'
                },
                'actions': [
                    {
                        'action': 'Launch in-app feature tours and tooltips',
                        'estimated_improvement': 'Increase adoption by 20-30%'
                    },
                    {
                        'action': 'Create targeted email campaigns for unused features',
                        'estimated_improvement': 'Increase awareness'
                    },
                    {
                        'action': 'Offer personalized onboarding sessions',
                        'estimated_improvement': 'Improve time-to-value'
                    }
                ],
                'estimated_effort': 'medium',
                'metrics_to_track': ['feature_adoption_percent', 'time_to_value_days'],
                'created_at': datetime.utcnow()
            })
        
        # Expansion opportunities
        expansion_count = data.get('expansion_candidates_count', 0)
        if expansion_count > 0:
            recommendations.append({
                'type': RecommendationType.GROWTH,
                'priority': RecommendationPriority.HIGH,
                'title': 'Expansion Opportunities',
                'description': f"{expansion_count} healthy customers ready for upsell/expansion",
                'impact': {
                    'customers': expansion_count,
                    'estimated_expansion_revenue_usd': data.get('expansion_revenue_potential_usd', 0),
                    'confidence': 'high'
                },
                'actions': [
                    {
                        'action': 'Reach out to expansion candidates with upgrade offers',
                        'timeline': 'This month'
                    },
                    {
                        'action': 'Highlight ROI and value delivered in current tier',
                        'timeline': 'Ongoing'
                    },
                    {
                        'action': 'Offer incentives for annual commitments',
                        'timeline': 'During renewal discussions'
                    }
                ],
                'estimated_effort': 'medium',
                'metrics_to_track': ['expansion_revenue', 'upgrade_conversion_rate'],
                'created_at': datetime.utcnow()
            })
        
        return recommendations
    
    async def _generate_risk_recommendations(
        self,
        data: Dict
    ) -> List[Dict]:
        """Generate risk mitigation recommendations"""
        
        recommendations = []
        
        # Single point of failure
        if data.get('has_single_point_of_failure', False):
            recommendations.append({
                'type': RecommendationType.RISK,
                'priority': RecommendationPriority.CRITICAL,
                'title': 'Single Point of Failure Detected',
                'description': 'Critical components lack redundancy',
                'impact': {
                    'risk_level': 'critical',
                    'potential_downtime': 'extended_outage_possible',
                    'business_impact': 'severe'
                },
                'actions': [
                    {
                        'action': 'Implement multi-region deployment',
                        'estimated_improvement': 'Eliminate SPOF'
                    },
                    {
                        'action': 'Add database replication',
                        'estimated_improvement': 'Data redundancy'
                    },
                    {
                        'action': 'Set up automated failover',
                        'estimated_improvement': 'Reduce recovery time'
                    }
                ],
                'estimated_effort': 'high',
                'metrics_to_track': ['uptime_percent', 'failover_time'],
                'created_at': datetime.utcnow()
            })
        
        return recommendations
    
    async def _generate_growth_recommendations(
        self,
        data: Dict
    ) -> List[Dict]:
        """Generate growth opportunity recommendations"""
        
        recommendations = []
        
        # Positive usage trends
        if data.get('usage_growth_rate', 0) > 20:
            recommendations.append({
                'type': RecommendationType.GROWTH,
                'priority': RecommendationPriority.MEDIUM,
                'title': 'Strong Growth Trajectory',
                'description': f"Usage growing at {data['usage_growth_rate']}% month-over-month",
                'impact': {
                    'growth_momentum': 'strong',
                    'scaling_needed': 'proactive_planning_required'
                },
                'actions': [
                    {
                        'action': 'Plan infrastructure scaling for projected growth',
                        'timeline': 'Next quarter'
                    },
                    {
                        'action': 'Invest in automation to maintain efficiency at scale',
                        'timeline': 'Ongoing'
                    },
                    {
                        'action': 'Prepare customer success for increased onboarding',
                        'timeline': 'Next month'
                    }
                ],
                'estimated_effort': 'high',
                'metrics_to_track': ['usage_growth_rate', 'capacity_headroom'],
                'created_at': datetime.utcnow()
            })
        
        return recommendations
    
    def _calculate_priority_score(self, recommendation: Dict) -> float:
        """Calculate priority score for sorting recommendations"""
        
        # Priority weights
        priority_weights = {
            RecommendationPriority.CRITICAL: 100,
            RecommendationPriority.HIGH: 75,
            RecommendationPriority.MEDIUM: 50,
            RecommendationPriority.LOW: 25
        }
        
        base_score = priority_weights.get(
            recommendation.get('priority'),
            25
        )
        
        # Adjust based on impact
        impact = recommendation.get('impact', {})
        
        if 'revenue_at_risk' in impact:
            base_score += 20
        
        if 'potential_savings_usd_per_month' in impact:
            savings = impact['potential_savings_usd_per_month']
            if savings > 1000:
                base_score += 15
            elif savings > 500:
                base_score += 10
        
        if impact.get('urgency') == 'immediate_action_required':
            base_score += 25
        
        # Adjust based on effort
        effort = recommendation.get('estimated_effort', 'medium')
        if effort == 'low':
            base_score += 10  # Easy wins
        elif effort == 'high':
            base_score -= 5  # Harder to implement
        
        return base_score
    
    def _calculate_latency_impact(self, latency_ms: float) -> Dict:
        """Calculate business impact of latency"""
        
        # Every 100ms of latency costs ~1% conversion (Amazon study)
        latency_over_target = max(0, latency_ms - 500)
        conversion_impact = (latency_over_target / 100) * 1
        
        return {
            'latency_ms': latency_ms,
            'latency_over_target_ms': latency_over_target,
            'estimated_conversion_loss_percent': round(conversion_impact, 2),
            'user_experience': 'poor' if latency_ms > 1000 else 'degraded',
            'severity': 'high' if latency_ms > 1000 else 'medium'
        }
    
    def _latency_to_priority(self, latency_ms: float) -> RecommendationPriority:
        """Convert latency to priority level"""
        if latency_ms > 2000:
            return RecommendationPriority.CRITICAL
        elif latency_ms > 1000:
            return RecommendationPriority.HIGH
        elif latency_ms > 500:
            return RecommendationPriority.MEDIUM
        else:
            return RecommendationPriority.LOW
```

