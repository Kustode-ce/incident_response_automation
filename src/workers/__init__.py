"""Celery workers for async task processing."""

from src.workers.celery_app import celery_app

__all__ = ["celery_app"]
