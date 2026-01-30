"""
Pydantic models for FastAPI Platform API
"""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict
from datetime import datetime


class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: str
    is_admin: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class AdminSettingsUpdate(BaseModel):
    allow_signups: bool


class AppCreate(BaseModel):
    name: str
    code: str
    env_vars: Optional[Dict[str, str]] = None


class AppUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None


class DraftUpdate(BaseModel):
    code: str


class AppResponse(BaseModel):
    id: str
    app_id: str
    name: str
    status: str
    created_at: str
    last_activity: Optional[str]
    deployment_url: str
    error_message: Optional[str] = None
    deploy_stage: Optional[str] = None
    last_error: Optional[str] = None
    last_deploy_at: Optional[str] = None


class AppDetailResponse(AppResponse):
    code: str
    env_vars: Optional[Dict[str, str]] = None
    draft_code: Optional[str] = None
    deployed_code: Optional[str] = None
    deployed_at: Optional[str] = None
    has_unpublished_changes: bool = False


class VersionEntry(BaseModel):
    code: str
    deployed_at: str
    code_hash: str


class VersionHistoryResponse(BaseModel):
    app_id: str
    versions: List[VersionEntry]
    current_deployed_hash: Optional[str] = None


class AppStatusResponse(BaseModel):
    status: str
    pod_status: Optional[str] = None
    error_message: Optional[str] = None
    deployment_ready: bool = False
    deploy_stage: Optional[str] = None
    last_error: Optional[str] = None


class AppDeployStatusResponse(BaseModel):
    status: str
    deploy_stage: Optional[str] = None
    deployment_ready: bool = False
    pod_status: Optional[str] = None
    last_error: Optional[str] = None
    last_deploy_at: Optional[str] = None


class ValidateRequest(BaseModel):
    code: str


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    code: str
    complexity: str
    is_global: bool
    created_at: str


class ViewerResponse(BaseModel):
    url: str
    username: str
    password: Optional[str] = None
    password_provided: bool = False
    ready: bool = False
    pod_status: Optional[str] = None


class CollectionStats(BaseModel):
    name: str
    document_count: int
    size_bytes: int
    avg_doc_size: Optional[int] = None


class DatabaseStatsResponse(BaseModel):
    database_name: str
    total_collections: int
    total_documents: int
    total_size_bytes: int
    total_size_mb: float
    collections: List[CollectionStats]


class LogLine(BaseModel):
    timestamp: Optional[str] = None
    message: str


class AppLogsResponse(BaseModel):
    app_id: str
    pod_name: Optional[str] = None
    container: str = "runner"
    logs: List[LogLine]
    truncated: bool = False
    error: Optional[str] = None


class K8sEvent(BaseModel):
    timestamp: str
    type: str
    reason: str
    message: str
    involved_object: str
    count: int = 1


class AppEventsResponse(BaseModel):
    app_id: str
    events: List[K8sEvent]
    deployment_phase: str
    error: Optional[str] = None


# Observability models (Phase 1e)

class AppMetricsResponse(BaseModel):
    app_id: str
    request_count: int = 0
    error_count: int = 0
    avg_response_time_ms: float = 0
    min_response_time_ms: float = 0
    max_response_time_ms: float = 0
    period_hours: int = 24


class AppErrorEntry(BaseModel):
    timestamp: str
    status_code: int
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    error_type: str  # "client_error" or "server_error"


class AppErrorsResponse(BaseModel):
    app_id: str
    errors: List[AppErrorEntry]
    total_count: int = 0


class HealthStatus(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    last_check: Optional[str] = None
    response_time_ms: Optional[float] = None
    checks_passed: int = 0
    checks_failed: int = 0
    uptime_percent: Optional[float] = None


class AppHealthStatusResponse(BaseModel):
    app_id: str
    health: HealthStatus


class AppWithMetrics(AppResponse):
    """Extended AppResponse with metrics summary for Dashboard"""
    metrics: Optional[AppMetricsResponse] = None
    health_status: Optional[str] = None  # "healthy", "degraded", "unhealthy", "unknown"
