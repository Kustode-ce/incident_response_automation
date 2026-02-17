from enum import Enum


class IncidentSeverity(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, Enum):
    new = "new"
    investigating = "investigating"
    identified = "identified"
    monitoring = "monitoring"
    resolved = "resolved"
    closed = "closed"


class IncidentCategory(str, Enum):
    infrastructure = "infrastructure"
    application = "application"
    database = "database"
    network = "network"
    security = "security"
    other = "other"


class AlertStatus(str, Enum):
    firing = "firing"
    resolved = "resolved"


class ExecutionStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    skipped = "skipped"
    waiting_approval = "waiting_approval"


class MLTaskType(str, Enum):
    classification = "classification"
    severity_prediction = "severity_prediction"
    root_cause_analysis = "root_cause_analysis"
    runbook_generation = "runbook_generation"
    post_mortem_generation = "post_mortem_generation"

