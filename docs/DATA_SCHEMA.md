# Data Schema Documentation

## Overview

This document defines all data schemas used throughout the Incident Response Automation platform. The schemas are designed to be:
- **Consistent**: Unified structure across different data sources
- **Extensible**: Easy to add new fields without breaking existing code
- **Type-safe**: Validated using Pydantic models
- **ML-ready**: Structured for optimal ML model consumption

## Schema Categories

1. **Observability Schemas**: Data from monitoring systems
2. **Internal Schemas**: Application domain models
3. **ML Context Schemas**: Data structures for ML model prompting
4. **Integration Schemas**: External system data formats

---

## 1. Observability Data Schemas

### 1.1 Prometheus Alert Schema

Schema for alerts received from Prometheus AlertManager.

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class AlertStatus(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"

class PrometheusAlert(BaseModel):
    """Schema for Prometheus/AlertManager webhook payload"""
    
    # Alert identification
    alert_name: str = Field(..., alias="alertname", description="Name of the alert rule")
    fingerprint: str = Field(..., description="Unique fingerprint for deduplication")
    
    # Status and timing
    status: AlertStatus
    starts_at: datetime = Field(..., alias="startsAt")
    ends_at: Optional[datetime] = Field(None, alias="endsAt")
    
    # Labels (identifying dimensions)
    labels: Dict[str, str] = Field(default_factory=dict, description="Alert labels")
    
    # Annotations (descriptive information)
    annotations: Dict[str, str] = Field(default_factory=dict, description="Alert annotations")
    
    # Metrics data
    metrics: Optional["AlertMetrics"] = Field(None, description="Associated metric values")
    
    # Source information
    generator_url: str = Field(..., alias="generatorURL", description="Link to Prometheus expression")
    
    class Config:
        populate_by_name = True

class AlertMetrics(BaseModel):
    """Metric values associated with an alert"""
    current_value: float = Field(..., description="Current metric value")
    threshold: float = Field(..., description="Alert threshold value")
    query: str = Field(..., description="PromQL query that triggered alert")
    unit: Optional[str] = Field(None, description="Metric unit (percent, bytes, etc)")

# Example JSON
"""
{
  "alert_name": "HighCPUUsage",
  "fingerprint": "abc123def456",
  "status": "firing",
  "starts_at": "2026-01-22T10:00:00Z",
  "labels": {
    "severity": "critical",
    "namespace": "production",
    "pod": "api-server-xyz",
    "cluster": "us-west-2",
    "service": "api-gateway"
  },
  "annotations": {
    "summary": "High CPU usage detected",
    "description": "Pod api-server-xyz CPU usage is 95%, above threshold of 90%",
    "runbook_url": "https://wiki.company.com/runbooks/high-cpu"
  },
  "metrics": {
    "current_value": 95.2,
    "threshold": 90.0,
    "query": "rate(container_cpu_usage_seconds_total[5m]) * 100",
    "unit": "percent"
  },
  "generator_url": "http://prometheus:9090/graph?g0.expr=..."
}
"""
```

### 1.2 Loki Logs Schema

Schema for log data fetched from Grafana Loki.

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogEntry(BaseModel):
    """Individual log entry"""
    timestamp: datetime
    level: LogLevel
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    # Structured fields (from JSON logs)
    fields: Dict[str, any] = Field(default_factory=dict)
    
    # Stack trace for errors
    stack_trace: Optional[str] = None

class LokiStream(BaseModel):
    """Log stream with labels"""
    labels: Dict[str, str] = Field(..., description="Stream labels (namespace, pod, container)")
    entries: List[LogEntry] = Field(..., description="Log entries in this stream")

class LokiLogsContext(BaseModel):
    """Complete log context for an incident"""
    
    # Query parameters
    query: str = Field(..., description="LogQL query used")
    time_range: "TimeRange" = Field(..., description="Time window queried")
    
    # Results
    streams: List[LokiStream] = Field(default_factory=list)
    total_entries: int = Field(..., description="Total log entries found")
    
    # Statistics
    error_count: int = Field(0, description="Number of ERROR level logs")
    warning_count: int = Field(0, description="Number of WARNING level logs")
    
    # Common patterns found
    common_errors: List[str] = Field(default_factory=list, description="Frequently occurring errors")

class TimeRange(BaseModel):
    start: datetime
    end: datetime
    
    @property
    def duration_seconds(self) -> float:
        return (self.end - self.start).total_seconds()

# Example JSON
"""
{
  "query": "{namespace=\"production\",pod=~\"api-server-.*\"}",
  "time_range": {
    "start": "2026-01-22T09:45:00Z",
    "end": "2026-01-22T10:00:00Z"
  },
  "streams": [
    {
      "labels": {
        "namespace": "production",
        "pod": "api-server-xyz",
        "container": "app"
      },
      "entries": [
        {
          "timestamp": "2026-01-22T09:55:23Z",
          "level": "ERROR",
          "message": "Database connection timeout after 30s",
          "trace_id": "abc-123-def",
          "fields": {
            "database": "postgres-primary",
            "timeout_seconds": 30,
            "retry_count": 3
          },
          "stack_trace": "Traceback (most recent call last):\n  ..."
        }
      ]
    }
  ],
  "total_entries": 1250,
  "error_count": 47,
  "warning_count": 128,
  "common_errors": [
    "Database connection timeout",
    "HTTP 503 Service Unavailable",
    "Circuit breaker opened"
  ]
}
"""
```

### 1.3 Grafana Dashboard Schema

Schema for Grafana dashboard context and snapshots.

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Optional

class GrafanaPanel(BaseModel):
    """Individual dashboard panel"""
    id: int
    title: str
    type: str = Field(..., description="Panel type: graph, stat, table, etc")
    
    # Data
    targets: List[Dict] = Field(default_factory=list, description="Prometheus/Loki queries")
    
    # Visualization
    snapshot_url: Optional[HttpUrl] = Field(None, description="URL to panel snapshot image")
    current_value: Optional[float] = Field(None, description="Current metric value")
    
    # Alert status
    alert_state: Optional[str] = Field(None, description="ok, alerting, no_data")

class GrafanaDashboard(BaseModel):
    """Dashboard context for incident"""
    uid: str = Field(..., description="Dashboard UID")
    title: str
    url: HttpUrl = Field(..., description="Link to dashboard")
    
    # Panels
    panels: List[GrafanaPanel] = Field(default_factory=list)
    
    # Snapshot
    snapshot_url: Optional[HttpUrl] = Field(None, description="Full dashboard snapshot")
    
    # Tags
    tags: List[str] = Field(default_factory=list)
    
    # Time range
    time_from: str = Field("now-15m", description="Dashboard time range start")
    time_to: str = Field("now", description="Dashboard time range end")

# Example JSON
"""
{
  "uid": "incident-overview-v2",
  "title": "Production API Monitoring",
  "url": "https://grafana.company.com/d/incident-overview-v2",
  "panels": [
    {
      "id": 1,
      "title": "CPU Usage",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(container_cpu_usage_seconds_total[5m]) * 100"
        }
      ],
      "snapshot_url": "https://grafana.company.com/render/d-solo/...png",
      "current_value": 95.2,
      "alert_state": "alerting"
    },
    {
      "id": 2,
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total[5m])"
        }
      ],
      "current_value": 1234.5
    }
  ],
  "snapshot_url": "https://grafana.company.com/dashboard/snapshot/abc123",
  "tags": ["production", "api"],
  "time_from": "now-30m",
  "time_to": "now"
}
"""
```

### 1.4 Kubernetes State Schema

Schema for Kubernetes cluster and resource state.

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class PodPhase(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"

class ContainerState(BaseModel):
    """Container state information"""
    name: str
    ready: bool
    restart_count: int
    state: str = Field(..., description="running, waiting, terminated")
    reason: Optional[str] = None
    message: Optional[str] = None

class PodInfo(BaseModel):
    """Pod information"""
    name: str
    namespace: str
    phase: PodPhase
    node: str
    
    # Container info
    containers: List[ContainerState]
    
    # Resource usage
    cpu_usage: Optional[float] = Field(None, description="Current CPU usage (cores)")
    memory_usage: Optional[float] = Field(None, description="Current memory usage (bytes)")
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    
    # Events
    recent_events: List["KubernetesEvent"] = Field(default_factory=list)

class DeploymentInfo(BaseModel):
    """Deployment information"""
    name: str
    namespace: str
    replicas: int
    ready_replicas: int
    available_replicas: int
    unavailable_replicas: int
    
    # Image
    image: str
    
    # Status
    conditions: List[Dict[str, str]] = Field(default_factory=list)

class KubernetesEvent(BaseModel):
    """Kubernetes event"""
    type: str = Field(..., description="Normal, Warning")
    reason: str
    message: str
    timestamp: datetime
    count: int = 1
    source: Dict[str, str] = Field(default_factory=dict)

class KubernetesState(BaseModel):
    """Complete K8s state for incident context"""
    cluster: str
    namespace: str
    
    # Resources
    pods: List[PodInfo] = Field(default_factory=list)
    deployments: List[DeploymentInfo] = Field(default_factory=list)
    
    # Events
    events: List[KubernetesEvent] = Field(default_factory=list)
    
    # Node health
    node_status: Dict[str, str] = Field(default_factory=dict, description="Node name -> status")

# Example JSON
"""
{
  "cluster": "us-west-2-prod",
  "namespace": "production",
  "pods": [
    {
      "name": "api-server-xyz-7d8f9",
      "namespace": "production",
      "phase": "Running",
      "node": "node-123",
      "containers": [
        {
          "name": "app",
          "ready": false,
          "restart_count": 3,
          "state": "waiting",
          "reason": "CrashLoopBackOff",
          "message": "Back-off restarting failed container"
        }
      ],
      "cpu_usage": 0.95,
      "memory_usage": 2147483648,
      "created_at": "2026-01-22T09:00:00Z",
      "started_at": "2026-01-22T09:00:15Z",
      "recent_events": [
        {
          "type": "Warning",
          "reason": "BackOff",
          "message": "Back-off restarting failed container",
          "timestamp": "2026-01-22T09:55:00Z",
          "count": 5
        }
      ]
    }
  ],
  "deployments": [
    {
      "name": "api-server",
      "namespace": "production",
      "replicas": 5,
      "ready_replicas": 4,
      "available_replicas": 4,
      "unavailable_replicas": 1,
      "image": "company/api-server:v1.2.3"
    }
  ],
  "events": [],
  "node_status": {
    "node-123": "Ready",
    "node-124": "Ready"
  }
}
"""
```

---

## 2. Internal Application Schemas

### 2.1 Incident Schema

Core incident model.

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class IncidentSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentStatus(str, Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"

class IncidentCategory(str, Enum):
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    DATABASE = "database"
    NETWORK = "network"
    SECURITY = "security"
    OTHER = "other"

class Incident(BaseModel):
    """Core incident model"""
    
    # Identification
    id: str = Field(..., description="INC-YYYY-NNNN format")
    fingerprint: str = Field(..., description="For deduplication")
    
    # Basic information
    title: str
    description: str
    category: IncidentCategory
    severity: IncidentSeverity
    status: IncidentStatus
    
    # Labels and metadata
    labels: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, any] = Field(default_factory=dict)
    
    # Assignment
    assigned_to: Optional[str] = None
    created_by: str = Field("system", description="User or 'system'")
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Related data
    alert_ids: List[str] = Field(default_factory=list)
    runbook_execution_ids: List[str] = Field(default_factory=list)
    
    # ML insights
    ml_classification: Optional["MLClassification"] = None
    ml_root_cause: Optional["MLRootCause"] = None
    
    # SLA tracking
    time_to_acknowledge_seconds: Optional[float] = None
    time_to_resolve_seconds: Optional[float] = None
    
    # Communication
    slack_thread_ts: Optional[str] = None
    pagerduty_incident_id: Optional[str] = None

class MLClassification(BaseModel):
    """ML classification results"""
    category: str
    subcategory: Optional[str] = None
    affected_components: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_version: str
    timestamp: datetime

class MLRootCause(BaseModel):
    """ML root cause analysis"""
    probable_causes: List["ProbableCause"]
    recommended_investigation: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_version: str
    timestamp: datetime

class ProbableCause(BaseModel):
    cause: str
    confidence: float
    evidence: List[str]
    supporting_logs: Optional[List[str]] = None
    supporting_metrics: Optional[List[str]] = None
```

### 2.2 Runbook Schema

Runbook definition and execution models.

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Union
from datetime import datetime
from enum import Enum

class RunbookStepType(str, Enum):
    HTTP_REQUEST = "http_request"
    KUBERNETES_ACTION = "kubernetes_action"
    SCRIPT_EXECUTION = "script_execution"
    NOTIFICATION = "notification"
    WAIT = "wait"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    QUERY_METRICS = "query_metrics"
    QUERY_LOGS = "query_logs"
    MANUAL_APPROVAL = "manual_approval"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"

class RunbookStep(BaseModel):
    """Individual runbook step"""
    id: str
    name: str
    type: RunbookStepType
    description: Optional[str] = None
    
    # Parameters (vary by type)
    params: Dict[str, any] = Field(default_factory=dict)
    
    # Conditions
    condition: Optional[str] = Field(None, description="Jinja2 expression")
    
    # Error handling
    retry_count: int = Field(3, ge=0)
    retry_delay_seconds: int = Field(5, ge=0)
    timeout_seconds: int = Field(300, ge=1)
    continue_on_failure: bool = False
    
    # Safety
    risk_level: str = Field("low", description="low, medium, high")
    requires_approval: bool = False
    
    # Nested steps (for conditional/parallel)
    on_success: Optional[List["RunbookStep"]] = None
    on_failure: Optional[List["RunbookStep"]] = None
    steps: Optional[List["RunbookStep"]] = None  # For parallel

class TriggerCondition(BaseModel):
    """Conditions that trigger a runbook"""
    alert_names: Optional[List[str]] = None
    severities: Optional[List[IncidentSeverity]] = None
    categories: Optional[List[IncidentCategory]] = None
    labels: Optional[Dict[str, str]] = None
    
    # Custom condition (Jinja2 expression)
    custom_condition: Optional[str] = None

class Runbook(BaseModel):
    """Runbook definition"""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    
    # Activation
    enabled: bool = True
    trigger_conditions: Optional[TriggerCondition] = None
    
    # Steps
    steps: List[RunbookStep]
    
    # Rollback
    rollback_steps: Optional[List[RunbookStep]] = None
    
    # Metadata
    created_by: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = Field(default_factory=list)
    
    # Safety
    auto_execute: bool = Field(False, description="Execute without approval")
    max_concurrent_executions: int = Field(1, ge=1)

class RunbookExecution(BaseModel):
    """Runbook execution instance"""
    id: str
    runbook_id: str
    runbook_version: str
    incident_id: Optional[str] = None
    
    # Status
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # Step results
    step_results: List["StepResult"] = Field(default_factory=list)
    
    # Context
    execution_context: Dict[str, any] = Field(default_factory=dict)
    
    # Logs
    logs: List[str] = Field(default_factory=list)
    
    # Metrics
    total_steps: int
    successful_steps: int
    failed_steps: int
    skipped_steps: int

class StepResult(BaseModel):
    """Result of a single step execution"""
    step_id: str
    step_name: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Output
    output: Optional[Dict[str, any]] = None
    error: Optional[str] = None
    
    # Retry info
    attempt: int = 1
    max_attempts: int = 1

# Example Runbook YAML (converted to JSON for storage)
"""
{
  "id": "rb-001",
  "name": "Scale Pod on High CPU",
  "description": "Automatically scale deployment when CPU usage is high",
  "version": "1.0.0",
  "enabled": true,
  "auto_execute": true,
  "trigger_conditions": {
    "alert_names": ["HighCPUUsage"],
    "severities": ["critical", "high"]
  },
  "steps": [
    {
      "id": "step-1",
      "name": "Notify team",
      "type": "notification",
      "params": {
        "channel": "#incidents",
        "message": "High CPU detected on {{ incident.labels.pod }}, initiating auto-scaling"
      },
      "risk_level": "low"
    },
    {
      "id": "step-2",
      "name": "Scale deployment",
      "type": "kubernetes_action",
      "params": {
        "action": "scale_deployment",
        "namespace": "{{ incident.labels.namespace }}",
        "deployment": "{{ incident.labels.deployment }}",
        "replicas": 5
      },
      "risk_level": "medium",
      "timeout_seconds": 60
    },
    {
      "id": "step-3",
      "name": "Wait for scaling",
      "type": "wait",
      "params": {
        "duration_seconds": 30
      }
    },
    {
      "id": "step-4",
      "name": "Check if resolved",
      "type": "query_metrics",
      "params": {
        "query": "rate(container_cpu_usage_seconds_total{pod=~\"{{ incident.labels.pod }}.*\"}[5m]) * 100"
      }
    },
    {
      "id": "step-5",
      "name": "Conditional notification",
      "type": "conditional",
      "condition": "{{ step_4_result.value < 80 }}",
      "on_success": [
        {
          "id": "step-5a",
          "name": "Success notification",
          "type": "notification",
          "params": {
            "channel": "#incidents",
            "message": "✅ Auto-scaling successful, CPU normalized"
          }
        }
      ],
      "on_failure": [
        {
          "id": "step-5b",
          "name": "Escalate",
          "type": "notification",
          "params": {
            "channel": "#incidents",
            "message": "⚠️ Auto-scaling did not resolve issue, escalating to on-call",
            "mention": "@oncall"
          }
        }
      ]
    }
  ]
}
"""
```

---

## 3. ML Context Schema

Schema for data passed to ML models.

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class MLTaskType(str, Enum):
    CLASSIFICATION = "classification"
    SEVERITY_PREDICTION = "severity_prediction"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    RUNBOOK_GENERATION = "runbook_generation"
    POST_MORTEM_GENERATION = "post_mortem_generation"

class MLContext(BaseModel):
    """Complete context for ML model inference"""
    
    # Task information
    task: MLTaskType
    incident_id: Optional[str] = None
    
    # Observability data
    alerts: List[PrometheusAlert] = Field(default_factory=list)
    logs: Optional[LokiLogsContext] = None
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Recent metric values")
    dashboards: List[GrafanaDashboard] = Field(default_factory=list)
    
    # System state
    kubernetes_state: Optional[KubernetesState] = None
    infrastructure_state: Dict[str, Any] = Field(default_factory=dict)
    
    # Historical context
    similar_incidents: List["HistoricalIncident"] = Field(default_factory=list)
    
    # Metadata
    timestamp: datetime
    environment: str = Field("production", description="Environment name")
    cluster: str = Field(..., description="Cluster identifier")
    
    # Additional context
    custom_context: Dict[str, Any] = Field(default_factory=dict)

class HistoricalIncident(BaseModel):
    """Historical incident for RAG context"""
    id: str
    title: str
    category: str
    severity: str
    
    # What happened
    description: str
    root_cause: str
    
    # How it was resolved
    resolution_summary: str
    resolution_steps: List[str]
    
    # Similarity score (from vector search)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    
    # When
    occurred_at: datetime
    resolved_at: datetime
    resolution_time_seconds: float

class MLPrompt(BaseModel):
    """Structured prompt for LLM"""
    system_message: str
    user_message: str
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    
    # Context for prompt building
    context: MLContext
    
    # Few-shot examples
    examples: List[Dict[str, str]] = Field(default_factory=list)

class MLResponse(BaseModel):
    """Structured response from ML model"""
    task: MLTaskType
    
    # Model information
    model_name: str
    model_version: str
    provider: str  # openai, anthropic, local
    
    # Result
    result: Dict[str, Any]
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Metadata
    timestamp: datetime
    latency_ms: float
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    
    # Raw response (for debugging)
    raw_response: Optional[str] = None

# Example ML Context JSON
"""
{
  "task": "root_cause_analysis",
  "incident_id": "INC-2026-001",
  "alerts": [
    {
      "alert_name": "HighCPUUsage",
      "status": "firing",
      "labels": {
        "severity": "critical",
        "namespace": "production",
        "pod": "api-server-xyz"
      },
      "metrics": {
        "current_value": 95.2,
        "threshold": 90.0
      }
    }
  ],
  "logs": {
    "query": "{namespace=\"production\",pod=~\"api-server-.*\"}",
    "total_entries": 1250,
    "error_count": 47,
    "common_errors": [
      "Database connection timeout",
      "HTTP 503 Service Unavailable"
    ]
  },
  "metrics": {
    "cpu_usage": 95.2,
    "memory_usage": 85.3,
    "request_rate": 1234.5,
    "error_rate": 12.3,
    "database_connections": 100
  },
  "kubernetes_state": {
    "cluster": "us-west-2-prod",
    "namespace": "production",
    "pods": [
      {
        "name": "api-server-xyz-7d8f9",
        "phase": "Running",
        "containers": [
          {
            "name": "app",
            "ready": false,
            "restart_count": 3,
            "state": "waiting",
            "reason": "CrashLoopBackOff"
          }
        ]
      }
    ]
  },
  "similar_incidents": [
    {
      "id": "INC-2026-  042",
      "title": "High CPU due to database connection leak",
      "category": "infrastructure",
      "severity": "high",
      "root_cause": "Application not closing database connections properly",
      "resolution_summary": "Restarted pods and applied connection pool fix",
      "resolution_steps": [
        "Identified connection leak in application code",
        "Rolled back to previous version",
        "Applied hotfix to close connections",
        "Redeployed application"
      ],
      "similarity_score": 0.87,
      "resolution_time_seconds": 1800
    }
  ],
  "timestamp": "2026-01-22T10:00:00Z",
  "environment": "production",
  "cluster": "us-west-2-prod"
}
"""
```

---

## 4. Integration Schemas

### 4.1 AWS EC2 Integration

Schema for AWS EC2 instance and Auto Scaling Group data.

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class EC2InstanceState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    SHUTTING_DOWN = "shutting-down"
    TERMINATED = "terminated"

class EC2Instance(BaseModel):
    """EC2 instance information"""
    instance_id: str
    instance_type: str
    state: EC2InstanceState
    availability_zone: str
    
    # Network
    private_ip_address: Optional[str] = None
    public_ip_address: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    
    # Metadata
    launch_time: datetime
    platform: Optional[str] = Field(None, description="windows or linux")
    
    # Tags
    tags: Dict[str, str] = Field(default_factory=dict)
    
    # Monitoring
    monitoring_state: str = Field("disabled", description="enabled or disabled")
    
    # Status checks
    instance_status: Optional[str] = Field(None, description="ok, impaired, insufficient-data")
    system_status: Optional[str] = Field(None, description="ok, impaired, insufficient-data")

class AutoScalingGroup(BaseModel):
    """Auto Scaling Group information"""
    name: str
    min_size: int
    max_size: int
    desired_capacity: int
    
    # Current state
    current_instances: int
    healthy_instances: int
    unhealthy_instances: int
    
    # Configuration
    availability_zones: List[str]
    launch_template: Optional[str] = None
    
    # Health check
    health_check_type: str = Field("EC2", description="EC2 or ELB")
    health_check_grace_period: int = Field(300, description="seconds")
    
    # Cooldown
    default_cooldown: int = Field(300, description="seconds")

class EC2CloudWatchMetric(BaseModel):
    """CloudWatch metric data for EC2"""
    instance_id: str
    metric_name: str
    namespace: str = "AWS/EC2"
    
    # Datapoints
    datapoints: List[Dict] = Field(default_factory=list)
    
    # Latest value
    latest_value: Optional[float] = None
    latest_timestamp: Optional[datetime] = None
    
    # Statistics
    average: Optional[float] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None

class EC2StateContext(BaseModel):
    """Complete EC2 state for incident context"""
    
    # Instances
    instances: List[EC2Instance] = Field(default_factory=list)
    
    # Auto Scaling Groups
    auto_scaling_groups: List[AutoScalingGroup] = Field(default_factory=list)
    
    # Metrics
    metrics: Dict[str, EC2CloudWatchMetric] = Field(default_factory=dict)
    
    # Console output (logs)
    console_output: Optional[str] = None
    
    # Region
    region: str

# Example JSON
"""
{
  "instances": [
    {
      "instance_id": "i-1234567890abcdef0",
      "instance_type": "t3.large",
      "state": "running",
      "availability_zone": "us-west-2a",
      "private_ip_address": "10.0.1.50",
      "public_ip_address": "54.123.45.67",
      "vpc_id": "vpc-12345",
      "subnet_id": "subnet-67890",
      "launch_time": "2026-01-20T10:00:00Z",
      "platform": "linux",
      "tags": {
        "Name": "api-server-1",
        "Environment": "production",
        "Service": "api-gateway"
      },
      "monitoring_state": "enabled",
      "instance_status": "ok",
      "system_status": "ok"
    }
  ],
  "auto_scaling_groups": [
    {
      "name": "api-gateway-asg",
      "min_size": 2,
      "max_size": 10,
      "desired_capacity": 3,
      "current_instances": 3,
      "healthy_instances": 2,
      "unhealthy_instances": 1,
      "availability_zones": ["us-west-2a", "us-west-2b"],
      "launch_template": "lt-0123456789abcdef",
      "health_check_type": "ELB",
      "health_check_grace_period": 300,
      "default_cooldown": 300
    }
  ],
  "metrics": {
    "CPUUtilization": {
      "instance_id": "i-1234567890abcdef0",
      "metric_name": "CPUUtilization",
      "namespace": "AWS/EC2",
      "datapoints": [
        {
          "Timestamp": "2026-01-22T10:00:00Z",
          "Average": 75.5,
          "Unit": "Percent"
        },
        {
          "Timestamp": "2026-01-22T10:05:00Z",
          "Average": 92.3,
          "Unit": "Percent"
        }
      ],
      "latest_value": 92.3,
      "latest_timestamp": "2026-01-22T10:05:00Z",
      "average": 83.9,
      "minimum": 75.5,
      "maximum": 92.3
    }
  },
  "console_output": "Linux version 5.10.0-1057-aws...",
  "region": "us-west-2"
}
"""
```

### 4.2 Slack Integration

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class SlackMessage(BaseModel):
    """Slack message payload"""
    channel: str = Field(..., description="#channel or user ID")
    text: str
    thread_ts: Optional[str] = Field(None, description="Thread timestamp for replies")
    
    # Rich formatting
    blocks: Optional[List[Dict]] = None
    attachments: Optional[List[Dict]] = None
    
    # Mentions
    mentions: List[str] = Field(default_factory=list, description="@username or @channel")

class SlackInteraction(BaseModel):
    """Slack button/interaction response"""
    action_id: str
    value: str
    user_id: str
    response_url: str
```

### 4.2 PagerDuty Integration

```python
from pydantic import BaseModel, Field
from typing import Optional

class PagerDutyIncident(BaseModel):
    """PagerDuty incident payload"""
    title: str
    service_id: str
    urgency: str = Field(..., description="high or low")
    incident_key: str = Field(..., description="Deduplication key")
    body: Dict[str, str]
    
    # Assignment
    escalation_policy_id: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
```

---

## Schema Validation

All schemas are validated using Pydantic v2 with:
- Type checking
- Field validation
- Custom validators
- Serialization/deserialization
- JSON Schema generation

## Schema Evolution

When evolving schemas:
1. **Add fields**: New optional fields are safe
2. **Deprecate fields**: Mark as deprecated, remove after 2 versions
3. **Rename fields**: Use aliases for backward compatibility
4. **Change types**: Requires major version bump

## Usage in Code

```python
# Parsing incoming webhook
alert = PrometheusAlert.model_validate(webhook_payload)

# Building ML context
ml_context = MLContext(
    task=MLTaskType.ROOT_CAUSE_ANALYSIS,
    alerts=[alert],
    logs=logs_context,
    kubernetes_state=k8s_state,
    timestamp=datetime.utcnow(),
    cluster="us-west-2-prod"
)

# Serialize to JSON
json_str = ml_context.model_dump_json()

# Generate JSON Schema
schema = MLContext.model_json_schema()
```

## Conclusion

These schemas provide a robust, type-safe foundation for the entire incident response platform. They ensure data consistency across components and enable ML models to receive well-structured, comprehensive context for intelligent decision-making.
