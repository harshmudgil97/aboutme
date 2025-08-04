import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/wayground_tenders")
    
    # Google Gemini API
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # Redis for Celery
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Wayground company profile
    company_name: str = "Wayground"
    company_description: str = """
    Wayground is an innovative education technology company specializing in:
    - AI-based Education Tools and Learning Solutions
    - Learning Management Systems (LMS)
    - Digital Learning Solutions and Online Teaching Tools
    - Interactive Learning Tools and Educational Software
    - ICT Services for Education
    - Distance Learning Technology and eLearning Solutions
    - EdTech Software as a Service (SaaS)
    - Curriculum and Pedagogy Support
    - AI Solutions for Learning and Education Innovation
    - School Software Solutions and Education System Integration
    - Technology solutions for K-12 Education
    - Educational procurement and tender services
    """
    
    # Tender search keywords
    tender_keywords: List[str] = [
        "Online Learning Tools", "Educational Software", "ICT Services Scheme",
        "AI-based Education Tools", "Learning Management System", "LMS",
        "Digital Learning Solutions", "Education Technology", "EdTech Tender",
        "Software as a Service", "SaaS", "Education", "Curriculum and Pedagogy",
        "Functional Requirements in EdTech", "Online Teaching Tools",
        "Interactive Learning Tools", "Distance Learning Technology",
        "eLearning Tender", "Procurement for Education Software",
        "Education Tools Panel", "Procurement of Learning Solutions",
        "Education Procurement", "Tenders for Educational Software",
        "Technology in Education", "Digital Tools for Schools",
        "Education System Integration", "School Software Solutions",
        "Procurement for ICT Services in Education", "AI Solutions for Learning",
        "Education Innovation Tenders", "Software for K-12 Education",
        "AI and Education Technology", "Education Procurement Framework",
        "Learning Tools Integration", "Education Services Panel"
    ]
    
    # Government tender portals (EUK, APAC, MEA regions)
    tender_portals: dict = {
        "UK": [
            "https://www.find-tender.service.gov.uk/",
            "https://www.contractsfinder.service.gov.uk/",
            "https://etendersni.gov.uk/",
            "https://www.sell2wales.gov.uk/",
            "https://www.publiccontractsscotland.gov.uk/"
        ],
        "EU": [
            "https://ted.europa.eu/",
            "https://www.vergabe.de/",
            "https://www.boamp.fr/",
            "https://www.gazzettaufficiale.it/",
            "https://www.boe.es/"
        ],
        "APAC": [
            "https://www.tenders.gov.au/",
            "https://www.gebiz.gov.sg/",
            "https://eprocure.gov.in/",
            "https://www.etender.up.nic.in/",
            "https://tender.gov.my/"
        ],
        "MEA": [
            "https://www.etenders.gov.za/",
            "https://www.tenders.gov.ae/",
            "https://www.almanaaqh.gov.sa/",
            "https://www.etenders.gov.eg/",
            "https://www.tender.gov.qa/"
        ]
    }
    
    # AI scoring weights for tender analysis
    scoring_weights: dict = {
        "keyword_match": 0.3,
        "value_range": 0.2,
        "deadline_urgency": 0.15,
        "geographical_preference": 0.1,
        "past_success_probability": 0.25
    }

    class Config:
        env_file = ".env"

settings = Settings()