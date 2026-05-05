"""
Pydantic Schemas
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class LicenseInfo(BaseModel):
    ip_address: str
    total_limit: int
    used_count: int
    remaining: int
    is_expired: bool
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UploadResponse(BaseModel):
    success: bool
    message: str
    session_id: Optional[str] = None
    file_type: Optional[str] = None
    sheets_processed: int = 0
    records_count: int = 0
    filename: Optional[str] = None
    license: Optional[LicenseInfo] = None
    remaining: Optional[int] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
    license_expired: bool = False
    remaining: int = 0