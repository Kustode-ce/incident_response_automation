"""Celery application configuration for async task processing."""

import os

from celery import Celery

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Create Celery application
celery_app = Celery(
    "incident_response",
    broker=REDIS_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "src.workers.tasks.runbook_tasks",
        "src.workers.tasks.notification_tasks",
        "src.workers.tasks.ml_tasks",
        "src.workers.tasks.enrichment",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit 9 minutes
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Beat schedule for periodic tasks (if needed)
    beat_schedule={
        "cleanup-old-executions": {
            "task": "src.workers.tasks.runbook_tasks.cleanup_old_executions",
            "schedule": 3600.0,  # Every hour
        },
    },
)

# Task routes for different queues
celery_app.conf.task_routes = {
    "src.workers.tasks.runbook_tasks.*": {"queue": "runbooks"},
    "src.workers.tasks.notification_tasks.*": {"queue": "notifications"},
    "src.workers.tasks.ml_tasks.*": {"queue": "ml"},
    "src.workers.tasks.enrichment.*": {"queue": "enrichment"},
}

if __name__ == "__main__":
    celery_app.start()
