"""
Business Intelligence Platform API Router
Aggregates all BI endpoints
"""

from fastapi import APIRouter

from bi_platform.api.v1.endpoints import dashboard

api_router = APIRouter()

# Dashboard endpoints
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboards"]
)
