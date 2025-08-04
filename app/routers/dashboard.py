from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, List
import logging
from datetime import datetime, timedelta

from app.database import get_db
from app.models.tender import Tender

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    """Get dashboard overview statistics"""
    
    # Basic counts
    total_tenders = db.query(Tender).count()
    recommended_tenders = db.query(Tender).filter(Tender.recommended == True).count()
    new_tenders = db.query(Tender).filter(Tender.status == "new").count()
    applied_tenders = db.query(Tender).filter(Tender.status == "applied").count()
    
    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_tenders = db.query(Tender).filter(Tender.created_at >= week_ago).count()
    
    # High value opportunities (over £100K)
    high_value_tenders = db.query(Tender).filter(
        Tender.value >= 100000,
        Tender.recommended == True
    ).count()
    
    # Urgent tenders (closing within 14 days)
    two_weeks = datetime.now() + timedelta(days=14)
    urgent_tenders = db.query(Tender).filter(
        Tender.closing_date <= two_weeks,
        Tender.closing_date >= datetime.now(),
        Tender.recommended == True
    ).count()
    
    # Average AI score
    all_scores = [t.ai_score for t in db.query(Tender).all() if t.ai_score]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    
    return {
        "total_tenders": total_tenders,
        "recommended_tenders": recommended_tenders,
        "new_tenders": new_tenders,
        "applied_tenders": applied_tenders,
        "recent_activity": recent_tenders,
        "high_value_opportunities": high_value_tenders,
        "urgent_opportunities": urgent_tenders,
        "average_ai_score": round(avg_score, 2),
        "recommendation_rate": round(recommended_tenders / total_tenders, 2) if total_tenders > 0 else 0
    }

@router.get("/recent-activity")
def get_recent_activity(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent tender activity"""
    
    recent_tenders = db.query(Tender).order_by(
        Tender.created_at.desc()
    ).limit(limit).all()
    
    activities = []
    for tender in recent_tenders:
        activity = {
            "tender_id": tender.tender_id,
            "title": tender.title,
            "organization": tender.organization,
            "country": tender.country,
            "ai_score": round(tender.ai_score, 2),
            "recommended": tender.recommended,
            "created_at": tender.created_at.isoformat(),
            "closing_date": tender.closing_date.isoformat() if tender.closing_date else None,
            "value": tender.value,
            "currency": tender.currency,
            "status": tender.status
        }
        activities.append(activity)
    
    return {"recent_activities": activities}

@router.get("/urgent-tenders")
def get_urgent_tenders(db: Session = Depends(get_db)):
    """Get tenders closing soon that are recommended"""
    
    # Tenders closing within 2 weeks
    two_weeks = datetime.now() + timedelta(days=14)
    
    urgent_tenders = db.query(Tender).filter(
        Tender.closing_date <= two_weeks,
        Tender.closing_date >= datetime.now(),
        Tender.recommended == True
    ).order_by(Tender.closing_date.asc()).all()
    
    urgent_list = []
    for tender in urgent_tenders:
        days_remaining = (tender.closing_date - datetime.now()).days if tender.closing_date else 0
        
        urgent_list.append({
            "tender_id": tender.tender_id,
            "title": tender.title,
            "organization": tender.organization,
            "country": tender.country,
            "ai_score": round(tender.ai_score, 2),
            "value": tender.value,
            "currency": tender.currency,
            "closing_date": tender.closing_date.isoformat() if tender.closing_date else None,
            "days_remaining": days_remaining,
            "urgency_level": "critical" if days_remaining <= 3 else "high" if days_remaining <= 7 else "medium",
            "status": tender.status
        })
    
    return {"urgent_tenders": urgent_list}

@router.get("/top-opportunities")
def get_top_opportunities(limit: int = 5, db: Session = Depends(get_db)):
    """Get top recommended opportunities"""
    
    top_tenders = db.query(Tender).filter(
        Tender.recommended == True,
        Tender.status != "rejected"
    ).order_by(
        Tender.ai_score.desc()
    ).limit(limit).all()
    
    opportunities = []
    for tender in top_tenders:
        opportunity = {
            "tender_id": tender.tender_id,
            "title": tender.title,
            "organization": tender.organization,
            "country": tender.country,
            "region": tender.region,
            "ai_score": round(tender.ai_score, 3),
            "value": tender.value,
            "currency": tender.currency,
            "closing_date": tender.closing_date.isoformat() if tender.closing_date else None,
            "keywords": tender.keywords or [],
            "reason": tender.reason,
            "success_probability": round(tender.success_probability, 2),
            "status": tender.status
        }
        opportunities.append(opportunity)
    
    return {"top_opportunities": opportunities}

@router.get("/performance-metrics")
def get_performance_metrics(db: Session = Depends(get_db)):
    """Get performance metrics over time"""
    
    # Metrics for different time periods
    periods = {
        "last_7_days": datetime.now() - timedelta(days=7),
        "last_30_days": datetime.now() - timedelta(days=30),
        "last_90_days": datetime.now() - timedelta(days=90)
    }
    
    metrics = {}
    
    for period_name, start_date in periods.items():
        period_tenders = db.query(Tender).filter(Tender.created_at >= start_date).all()
        
        if period_tenders:
            total = len(period_tenders)
            recommended = sum(1 for t in period_tenders if t.recommended)
            avg_score = sum(t.ai_score for t in period_tenders) / total
            high_score = sum(1 for t in period_tenders if t.ai_score >= 0.7)
            
            metrics[period_name] = {
                "total_tenders": total,
                "recommended_count": recommended,
                "recommendation_rate": round(recommended / total, 3),
                "average_score": round(avg_score, 3),
                "high_score_count": high_score,
                "high_score_rate": round(high_score / total, 3)
            }
        else:
            metrics[period_name] = {
                "total_tenders": 0,
                "recommended_count": 0,
                "recommendation_rate": 0,
                "average_score": 0,
                "high_score_count": 0,
                "high_score_rate": 0
            }
    
    return {"performance_metrics": metrics}

@router.get("/regional-distribution")
def get_regional_distribution(db: Session = Depends(get_db)):
    """Get tender distribution by region"""
    
    regions = ["UK", "EU", "APAC", "MEA"]
    distribution = {}
    
    for region in regions:
        region_tenders = db.query(Tender).filter(Tender.region == region).all()
        
        if region_tenders:
            total = len(region_tenders)
            recommended = sum(1 for t in region_tenders if t.recommended)
            avg_score = sum(t.ai_score for t in region_tenders) / total
            total_value = sum(t.value for t in region_tenders if t.value)
            
            distribution[region] = {
                "total_tenders": total,
                "recommended_count": recommended,
                "recommendation_rate": round(recommended / total, 3),
                "average_score": round(avg_score, 3),
                "total_value": total_value,
                "avg_value": round(total_value / total, 2) if total > 0 else 0
            }
        else:
            distribution[region] = {
                "total_tenders": 0,
                "recommended_count": 0,
                "recommendation_rate": 0,
                "average_score": 0,
                "total_value": 0,
                "avg_value": 0
            }
    
    return {"regional_distribution": distribution}

@router.get("/alerts")
def get_dashboard_alerts(db: Session = Depends(get_db)):
    """Get important alerts and notifications"""
    
    alerts = []
    
    # Critical: Tenders closing within 3 days
    three_days = datetime.now() + timedelta(days=3)
    critical_tenders = db.query(Tender).filter(
        Tender.closing_date <= three_days,
        Tender.closing_date >= datetime.now(),
        Tender.recommended == True,
        Tender.status == "new"
    ).count()
    
    if critical_tenders > 0:
        alerts.append({
            "type": "critical",
            "title": "Urgent Action Required",
            "message": f"{critical_tenders} recommended tender(s) closing within 3 days",
            "count": critical_tenders,
            "action": "Review and apply immediately"
        })
    
    # High value opportunities
    high_value_new = db.query(Tender).filter(
        Tender.value >= 500000,
        Tender.recommended == True,
        Tender.status == "new"
    ).count()
    
    if high_value_new > 0:
        alerts.append({
            "type": "opportunity",
            "title": "High Value Opportunities",
            "message": f"{high_value_new} high-value recommended tender(s) available",
            "count": high_value_new,
            "action": "Review high-value opportunities"
        })
    
    # New highly scored tenders
    week_ago = datetime.now() - timedelta(days=7)
    new_high_score = db.query(Tender).filter(
        Tender.ai_score >= 0.8,
        Tender.created_at >= week_ago,
        Tender.status == "new"
    ).count()
    
    if new_high_score > 0:
        alerts.append({
            "type": "info",
            "title": "New High-Score Tenders",
            "message": f"{new_high_score} new tender(s) with high AI scores this week",
            "count": new_high_score,
            "action": "Review new opportunities"
        })
    
    return {"alerts": alerts}