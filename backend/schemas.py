"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Any
from datetime import date, datetime
from uuid import UUID


# ========== AUTH SCHEMAS ==========

class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    """Token response with officer information"""
    access_token: str
    token_type: str = "bearer"
    officer_id: str
    officer_name: str
    officer_name_tamil: Optional[str] = None
    employee_id: str
    jurisdiction_type: str
    jurisdiction_name: str


class OfficerContext(BaseModel):
    """Officer context used in JWT payload and dependencies"""
    officer_id: UUID
    employee_id: str
    name: str
    email: str
    jurisdiction_type: str
    jurisdiction_name: str
    jurisdiction_ids: List[UUID]
    
    model_config = ConfigDict(from_attributes=True)


class StandardResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    data: Optional[Any] = None
    message: str
    timestamp: str  # ISO8601
    
    @staticmethod
    def success_response(data: Any = None, message: str = "Success") -> "StandardResponse":
        """Create a success response"""
        return StandardResponse(
            success=True,
            data=data,
            message=message,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    
    @staticmethod
    def error_response(message: str, data: Any = None) -> "StandardResponse":
        """Create an error response"""
        return StandardResponse(
            success=False,
            data=data,
            message=message,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


# ========== OFFICER SCHEMAS ==========

class OfficerBase(BaseModel):
    employee_id: str
    name: str
    name_tamil: Optional[str] = None
    email: EmailStr
    mobile: Optional[str] = None
    designation: str = "Sub Inspector Surveyor"


class OfficerCreate(OfficerBase):
    password: str = Field(min_length=6)


class OfficerResponse(OfficerBase):
    id: UUID
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OfficerProfileResponse(BaseModel):
    """Officer profile with jurisdiction information"""
    officer_id: str
    employee_id: str
    name: str
    name_tamil: Optional[str] = None
    email: str
    mobile: Optional[str] = None
    designation: str
    is_active: bool
    last_login: Optional[str] = None
    jurisdiction: dict
    
    model_config = ConfigDict(from_attributes=True)


# ========== APPLICATION SCHEMAS ==========

class ApplicationBase(BaseModel):
    application_number: str
    application_type: str  # ISD, NISD, MERGE
    submission_channel: Optional[str] = None
    submission_date: date
    declared_reason: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    applicant_id: UUID
    survey_number_id: UUID


class ApplicationResponse(ApplicationBase):
    id: UUID
    current_stage: str
    current_status: str
    field_visit_scheduled: bool
    is_overdue: bool
    priority_flag: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationResponse]
    total: int


# ========== SURVEY SCHEMAS ==========

class SurveyNumberBase(BaseModel):
    survey_no: str
    total_area_sqm: float = Field(gt=0)
    land_type: Optional[str] = None
    patta_number: Optional[str] = None


class SurveyNumberResponse(SurveyNumberBase):
    id: UUID
    block_id: UUID
    has_encroachment: bool
    has_litigation: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ========== CHAT SCHEMAS ==========

class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1)
    session_token: Optional[str] = None


class ChatMessageResponse(BaseModel):
    message: str
    session_token: str
    detected_language: str = "en"
    response_time_ms: Optional[int] = None


# ========== PLACEHOLDER SCHEMAS ==========
# Add more schemas as needed for different endpoints
