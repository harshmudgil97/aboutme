from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from app.database import get_db
from app.models.tender import Tender, TenderCreate, TenderResponse, TenderUpdate
from app.services.tender_scraper import TenderScraper
from app.services.gemini_analyzer import GeminiTenderAnalyzer
from app.services.tender_monitor import TenderMonitorService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[TenderResponse])
def get_tenders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    recommended: Optional[bool] = None,
    min_score: Optional[float] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of tenders with optional filtering"""
    query = db.query(Tender)
    
    if status:
        query = query.filter(Tender.status == status)
    
    if recommended is not None:
        query = query.filter(Tender.recommended == recommended)
    
    if min_score is not None:
        query = query.filter(Tender.ai_score >= min_score)
    
    if region:
        query = query.filter(Tender.region == region)
    
    # Order by AI score descending, then by closing date
    query = query.order_by(Tender.ai_score.desc(), Tender.closing_date.asc())
    
    tenders = query.offset(skip).limit(limit).all()
    return tenders

@router.get("/recommended", response_model=List[TenderResponse])
def get_recommended_tenders(
    limit: int = 20,
    min_score: float = 0.6,
    db: Session = Depends(get_db)
):
    """Get recommended tenders for Wayground"""
    tenders = db.query(Tender).filter(
        Tender.recommended == True,
        Tender.ai_score >= min_score,
        Tender.status != "rejected"
    ).order_by(
        Tender.ai_score.desc()
    ).limit(limit).all()
    
    return tenders

@router.get("/stats")
def get_tender_stats(db: Session = Depends(get_db)):
    """Get tender statistics"""
    total_tenders = db.query(Tender).count()
    recommended_tenders = db.query(Tender).filter(Tender.recommended == True).count()
    high_score_tenders = db.query(Tender).filter(Tender.ai_score >= 0.7).count()
    
    # Tenders by status
    status_counts = {}
    statuses = ["new", "reviewed", "applied", "rejected"]
    for status in statuses:
        count = db.query(Tender).filter(Tender.status == status).count()
        status_counts[status] = count
    
    # Tenders by region
    region_counts = {}
    regions = ["UK", "EU", "APAC", "MEA"]
    for region in regions:
        count = db.query(Tender).filter(Tender.region == region).count()
        region_counts[region] = count
    
    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_tenders = db.query(Tender).filter(Tender.created_at >= week_ago).count()
    
    return {
        "total_tenders": total_tenders,
        "recommended_tenders": recommended_tenders,
        "high_score_tenders": high_score_tenders,
        "status_distribution": status_counts,
        "region_distribution": region_counts,
        "recent_activity": recent_tenders
    }

@router.get("/{tender_id}", response_model=TenderResponse)
def get_tender(tender_id: str, db: Session = Depends(get_db)):
    """Get specific tender by ID"""
    tender = db.query(Tender).filter(Tender.tender_id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender

@router.put("/{tender_id}", response_model=TenderResponse)
def update_tender(tender_id: str, tender_update: TenderUpdate, db: Session = Depends(get_db)):
    """Update tender status and notes"""
    tender = db.query(Tender).filter(Tender.tender_id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    update_data = tender_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tender, field, value)
    
    tender.updated_at = datetime.now()
    db.commit()
    db.refresh(tender)
    
    return tender

@router.post("/search")
async def search_tenders(
    background_tasks: BackgroundTasks,
    region: Optional[str] = None,
    keywords: Optional[List[str]] = None
):
    """Manually trigger tender search"""
    try:
        async with TenderScraper() as scraper:
            if region:
                # Search specific region
                portals = scraper.portals.get(region, [])
                if not portals:
                    raise HTTPException(status_code=400, detail="Invalid region")
                
                tenders = []
                for portal in portals:
                    portal_tenders = await scraper.search_portal(portal, region)
                    tenders.extend(portal_tenders)
            else:
                # Search all portals
                tenders = await scraper.search_all_portals()
        
        # Add analysis task to background
        background_tasks.add_task(analyze_new_tenders, tenders)
        
        return {
            "message": f"Found {len(tenders)} tenders. Analysis started in background.",
            "tenders_found": len(tenders)
        }
        
    except Exception as e:
        logger.error(f"Error in manual tender search: {str(e)}")
        raise HTTPException(status_code=500, detail="Error searching for tenders")

@router.post("/analyze/{tender_id}")
async def analyze_tender(tender_id: str, db: Session = Depends(get_db)):
    """Manually trigger analysis for a specific tender"""
    tender = db.query(Tender).filter(Tender.tender_id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    try:
        analyzer = GeminiTenderAnalyzer()
        
        # Convert tender to dict for analysis
        tender_data = {
            "tender_id": tender.tender_id,
            "title": tender.title,
            "description": tender.description,
            "organization": tender.organization,
            "location": tender.location,
            "country": tender.country,
            "region": tender.region,
            "value": tender.value,
            "currency": tender.currency,
            "closing_date": tender.closing_date.isoformat() if tender.closing_date else None,
            "cpv_codes": tender.cpv_codes or [],
        }
        
        analysis = await analyzer.analyze_tender(tender_data)
        
        # Update tender with analysis results
        scores = analysis.get("scores", {})
        recommendation = analysis.get("recommendation", {})
        
        tender.ai_score = scores.get("ai_score", 0.0)
        tender.relevance_score = scores.get("relevance_score", 0.0)
        tender.keyword_match_score = scores.get("keyword_match_score", 0.0)
        tender.value_score = scores.get("value_score", 0.0)
        tender.urgency_score = scores.get("urgency_score", 0.0)
        tender.geo_score = scores.get("geo_score", 0.0)
        tender.success_probability = scores.get("success_probability", 0.0)
        tender.ai_analysis = analysis.get("ai_analysis")
        tender.recommended = recommendation.get("recommendation") in ["Highly Recommended", "Recommended"]
        tender.reason = recommendation.get("reasoning", "")
        tender.updated_at = datetime.now()
        
        db.commit()
        db.refresh(tender)
        
        return {
            "message": "Analysis completed",
            "tender_id": tender_id,
            "ai_score": tender.ai_score,
            "recommended": tender.recommended,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing tender {tender_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error analyzing tender")

@router.delete("/{tender_id}")
def delete_tender(tender_id: str, db: Session = Depends(get_db)):
    """Delete a tender"""
    tender = db.query(Tender).filter(Tender.tender_id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    db.delete(tender)
    db.commit()
    
    return {"message": "Tender deleted successfully"}

async def analyze_new_tenders(tenders: List[dict]):
    """Background task to analyze newly found tenders"""
    analyzer = GeminiTenderAnalyzer()
    monitor_service = TenderMonitorService()
    
    for tender_data in tenders:
        try:
            # Save tender to database and analyze
            await monitor_service.save_and_analyze_tender(tender_data, analyzer)
        except Exception as e:
            logger.error(f"Error analyzing tender {tender_data.get('tender_id')}: {str(e)}")
            continue