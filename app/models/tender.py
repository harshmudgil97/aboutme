from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel

Base = declarative_base()

class Tender(Base):
    __tablename__ = "tenders"
    
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(String, unique=True, index=True)  # External tender ID
    title = Column(String, index=True)
    description = Column(Text)
    organization = Column(String)
    location = Column(String)
    country = Column(String)
    region = Column(String)  # EUK, APAC, MEA
    value = Column(Float)
    currency = Column(String)
    publication_date = Column(DateTime)
    closing_date = Column(DateTime)
    tender_url = Column(String)
    source_portal = Column(String)
    cpv_codes = Column(JSON)  # List of CPV codes
    keywords = Column(JSON)  # Extracted keywords
    
    # AI Analysis fields
    ai_score = Column(Float, default=0.0)
    relevance_score = Column(Float, default=0.0)
    keyword_match_score = Column(Float, default=0.0)
    value_score = Column(Float, default=0.0)
    urgency_score = Column(Float, default=0.0)
    geo_score = Column(Float, default=0.0)
    success_probability = Column(Float, default=0.0)
    
    # Analysis details
    ai_analysis = Column(JSON)  # Detailed AI analysis
    recommended = Column(Boolean, default=False)
    reason = Column(Text)  # Why recommended/not recommended
    
    # Status tracking
    status = Column(String, default="new")  # new, reviewed, applied, rejected
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_checked = Column(DateTime, server_default=func.now())


class TenderAnalysis(Base):
    __tablename__ = "tender_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(String, index=True)
    analysis_date = Column(DateTime, server_default=func.now())
    gemini_response = Column(JSON)
    score_breakdown = Column(JSON)
    recommendations = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# Pydantic models for API
class TenderBase(BaseModel):
    tender_id: str
    title: str
    description: str
    organization: str
    location: str
    country: str
    region: str
    value: Optional[float] = None
    currency: Optional[str] = None
    publication_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    tender_url: Optional[str] = None
    source_portal: str
    cpv_codes: Optional[List[str]] = []
    keywords: Optional[List[str]] = []

class TenderCreate(TenderBase):
    pass

class TenderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    recommended: Optional[bool] = None

class TenderResponse(TenderBase):
    id: int
    ai_score: float
    relevance_score: float
    keyword_match_score: float
    value_score: float
    urgency_score: float
    geo_score: float
    success_probability: float
    ai_analysis: Optional[Dict] = None
    recommended: bool
    reason: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_checked: datetime

    class Config:
        from_attributes = True

class TenderAnalysisResponse(BaseModel):
    id: int
    tender_id: str
    analysis_date: datetime
    gemini_response: Dict
    score_breakdown: Dict
    recommendations: str
    created_at: datetime

    class Config:
        from_attributes = True