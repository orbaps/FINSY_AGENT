"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class InvoiceParseRequest(BaseModel):
    """Request schema for invoice parsing"""
    invoice_text: Optional[str] = Field(None, description="Raw invoice text")
    amount: Optional[float] = Field(None, ge=0, description="Invoice amount")
    vendor: Optional[str] = Field(None, description="Vendor name")
    po_number: Optional[str] = Field(None, description="Purchase order number")
    date: Optional[str] = Field(None, description="Invoice date")
    currency: Optional[str] = Field("USD", description="Currency code")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('Amount must be non-negative')
        return v


class InvoiceParseResponse(BaseModel):
    """Response schema for invoice parsing"""
    invoice_id: str
    vendor: Optional[str]
    date: str
    total: Optional[float]
    currency: Optional[str]
    po_number: Optional[str]
    confidence: Optional[float] = Field(None, ge=0, le=1)
    parsed: bool
    text: Optional[str] = None
    created_at: Optional[str] = None


class RiskScoreRequest(BaseModel):
    """Request schema for risk scoring"""
    invoice_id: Optional[str] = None
    amount: float = Field(..., ge=0, description="Invoice amount")
    vendor: str = Field(..., min_length=1, description="Vendor name")
    po_number: Optional[str] = None
    has_po: Optional[bool] = None
    date: Optional[str] = None
    invoice_text: Optional[str] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v < 0:
            raise ValueError('Amount must be non-negative')
        return v


class RiskScoreResponse(BaseModel):
    """Response schema for risk scoring"""
    risk_score: float = Field(..., ge=0, le=1)
    risk_level: str = Field(..., pattern="^(low|medium|high)$")
    reasons: List[str] = []
    requires_approval: bool
    invoice_id: Optional[str] = None
    model_score: Optional[float] = None
    rule_score: Optional[float] = None


class ApprovalCreateRequest(BaseModel):
    """Request schema for creating approval"""
    invoice_id: str = Field(..., min_length=1)
    amount: float = Field(..., ge=0)
    vendor: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    requester: Optional[str] = None
    approver: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    """Request schema for approval action"""
    action: str = Field(..., pattern="^(approve|reject)$")
    comment: Optional[str] = ""
    approver: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Response schema for approval"""
    approval_id: str
    invoice_id: str
    amount: float
    vendor: str
    reason: str
    status: str = Field(..., pattern="^(pending|approved|rejected)$")
    created_at: str
    approver: Optional[str] = None
    approved_at: Optional[str] = None
    comment: Optional[str] = None
    requester: Optional[str] = None
    updated_at: Optional[str] = None


class HealthResponse(BaseModel):
    """Response schema for health check"""
    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$")
    version: str
    database: str
    model_loaded: bool
    services: dict = {}
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    message: str
    code: Optional[int] = None


