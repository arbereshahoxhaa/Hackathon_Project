from pydantic import BaseModel
from typing import Optional


class NormalizedFailure(BaseModel):
    tool: str
    job_name: str
    error_message: str
    log_excerpt: str
    timestamp: str
    run_id: Optional[str] = None
    environment: str = "production"


class DiagnosisResult(BaseModel):
    # Flattened — includes all NormalizedFailure fields plus diagnosis fields
    tool: str
    job_name: str
    error_message: str
    log_excerpt: str
    timestamp: str
    run_id: Optional[str] = None
    environment: str = "production"
    root_cause: str
    suggested_fix: str
    severity: str   # "low" | "medium" | "high"
    confidence: str # "low" | "medium" | "high"


class OwnerInfo(BaseModel):
    name: str
    slack_handle: str
    team: Optional[str] = None
