from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
import logging
from datetime import datetime, timedelta

from app.database import get_db
from app.models.tender import Tender, TenderAnalysis, TenderAnalysisResponse
from app.services.gemini_analyzer import GeminiTenderAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/insights")
def get_analysis_insights(db: Session = Depends(get_db)):
    """Get AI analysis insights and trends"""
    
    # Calculate average scores by region
    regions = ["UK", "EU", "APAC", "MEA"]
    region_insights = {}
    
    for region in regions:
        tenders = db.query(Tender).filter(Tender.region == region).all()
        if tenders:
            avg_score = sum(t.ai_score for t in tenders) / len(tenders)
            recommended_count = sum(1 for t in tenders if t.recommended)
            region_insights[region] = {
                "total_tenders": len(tenders),
                "average_score": round(avg_score, 2),
                "recommended_count": recommended_count,
                "recommendation_rate": round(recommended_count / len(tenders), 2) if tenders else 0
            }
        else:
            region_insights[region] = {
                "total_tenders": 0,
                "average_score": 0,
                "recommended_count": 0,
                "recommendation_rate": 0
            }
    
    # Score distribution
    score_ranges = {
        "0.0-0.3": 0,
        "0.3-0.5": 0,
        "0.5-0.7": 0,
        "0.7-1.0": 0
    }
    
    all_tenders = db.query(Tender).all()
    for tender in all_tenders:
        score = tender.ai_score
        if score < 0.3:
            score_ranges["0.0-0.3"] += 1
        elif score < 0.5:
            score_ranges["0.3-0.5"] += 1
        elif score < 0.7:
            score_ranges["0.5-0.7"] += 1
        else:
            score_ranges["0.7-1.0"] += 1
    
    # Top keywords in recommended tenders
    recommended_tenders = db.query(Tender).filter(Tender.recommended == True).all()
    keyword_frequency = {}
    
    for tender in recommended_tenders:
        if tender.keywords:
            for keyword in tender.keywords:
                keyword_frequency[keyword] = keyword_frequency.get(keyword, 0) + 1
    
    top_keywords = sorted(keyword_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Recent trends (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_tenders = db.query(Tender).filter(Tender.created_at >= thirty_days_ago).all()
    
    return {
        "region_insights": region_insights,
        "score_distribution": score_ranges,
        "top_keywords": dict(top_keywords),
        "total_analyzed": len(all_tenders),
        "recent_activity": {
            "total_recent": len(recent_tenders),
            "recommended_recent": sum(1 for t in recent_tenders if t.recommended),
            "avg_score_recent": round(sum(t.ai_score for t in recent_tenders) / len(recent_tenders), 2) if recent_tenders else 0
        }
    }

@router.get("/keyword-analysis")
def get_keyword_analysis(db: Session = Depends(get_db)):
    """Analyze keyword performance across tenders"""
    
    tenders = db.query(Tender).all()
    keyword_stats = {}
    
    for tender in tenders:
        if tender.keywords:
            for keyword in tender.keywords:
                if keyword not in keyword_stats:
                    keyword_stats[keyword] = {
                        "total_occurrences": 0,
                        "recommended_occurrences": 0,
                        "total_score": 0,
                        "avg_score": 0
                    }
                
                stats = keyword_stats[keyword]
                stats["total_occurrences"] += 1
                stats["total_score"] += tender.ai_score
                
                if tender.recommended:
                    stats["recommended_occurrences"] += 1
    
    # Calculate averages and sort by performance
    for keyword, stats in keyword_stats.items():
        if stats["total_occurrences"] > 0:
            stats["avg_score"] = round(stats["total_score"] / stats["total_occurrences"], 3)
            stats["recommendation_rate"] = round(stats["recommended_occurrences"] / stats["total_occurrences"], 3)
    
    # Sort by average score
    sorted_keywords = sorted(
        keyword_stats.items(), 
        key=lambda x: x[1]["avg_score"], 
        reverse=True
    )
    
    return {
        "keyword_performance": dict(sorted_keywords[:20]),  # Top 20 keywords
        "total_unique_keywords": len(keyword_stats)
    }

@router.get("/competition-analysis")
def get_competition_analysis(db: Session = Depends(get_db)):
    """Analyze competition levels across different tender types"""
    
    tenders = db.query(Tender).all()
    
    # Analyze by value ranges
    value_ranges = {
        "0-50K": [],
        "50K-100K": [],
        "100K-500K": [],
        "500K-1M": [],
        "1M+": []
    }
    
    for tender in tenders:
        if tender.value:
            value = tender.value
            if value < 50000:
                value_ranges["0-50K"].append(tender)
            elif value < 100000:
                value_ranges["50K-100K"].append(tender)
            elif value < 500000:
                value_ranges["100K-500K"].append(tender)
            elif value < 1000000:
                value_ranges["500K-1M"].append(tender)
            else:
                value_ranges["1M+"].append(tender)
    
    analysis = {}
    for range_name, range_tenders in value_ranges.items():
        if range_tenders:
            avg_score = sum(t.ai_score for t in range_tenders) / len(range_tenders)
            recommended_count = sum(1 for t in range_tenders if t.recommended)
            analysis[range_name] = {
                "count": len(range_tenders),
                "avg_score": round(avg_score, 3),
                "recommended_count": recommended_count,
                "recommendation_rate": round(recommended_count / len(range_tenders), 3)
            }
        else:
            analysis[range_name] = {
                "count": 0,
                "avg_score": 0,
                "recommended_count": 0,
                "recommendation_rate": 0
            }
    
    return {
        "value_range_analysis": analysis,
        "summary": {
            "most_competitive_range": max(analysis.keys(), key=lambda x: analysis[x]["recommendation_rate"]),
            "largest_opportunity_range": max(analysis.keys(), key=lambda x: analysis[x]["count"]),
        }
    }

@router.post("/batch-analyze")
async def batch_analyze_tenders(tender_ids: List[str], db: Session = Depends(get_db)):
    """Analyze multiple tenders in batch"""
    
    tenders = db.query(Tender).filter(Tender.tender_id.in_(tender_ids)).all()
    
    if not tenders:
        raise HTTPException(status_code=404, detail="No tenders found with provided IDs")
    
    analyzer = GeminiTenderAnalyzer()
    results = []
    
    # Convert tenders to dict format for analysis
    tender_data_list = []
    for tender in tenders:
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
        tender_data_list.append(tender_data)
    
    try:
        # Batch analyze with Gemini
        batch_results = await analyzer.batch_analyze_tenders(tender_data_list)
        
        # Update database with results
        for result in batch_results:
            tender_id = result["tender_id"]
            analysis = result["analysis"]
            
            tender = next((t for t in tenders if t.tender_id == tender_id), None)
            if tender:
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
                
                results.append({
                    "tender_id": tender_id,
                    "ai_score": tender.ai_score,
                    "recommended": tender.recommended
                })
        
        db.commit()
        
        return {
            "message": f"Analyzed {len(results)} tenders successfully",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Error performing batch analysis")

@router.get("/recommendations/summary")
def get_recommendations_summary(db: Session = Depends(get_db)):
    """Get summary of AI recommendations"""
    
    # Get all recommended tenders
    recommended_tenders = db.query(Tender).filter(Tender.recommended == True).all()
    
    # Group by recommendation priority/score
    high_priority = [t for t in recommended_tenders if t.ai_score >= 0.8]
    medium_priority = [t for t in recommended_tenders if 0.6 <= t.ai_score < 0.8]
    low_priority = [t for t in recommended_tenders if t.ai_score < 0.6]
    
    # Closing soon (within 14 days)
    fourteen_days = datetime.now() + timedelta(days=14)
    closing_soon = [
        t for t in recommended_tenders 
        if t.closing_date and t.closing_date <= fourteen_days
    ]
    
    # High value opportunities (over £100K)
    high_value = [t for t in recommended_tenders if t.value and t.value >= 100000]
    
    return {
        "total_recommended": len(recommended_tenders),
        "by_priority": {
            "high": len(high_priority),
            "medium": len(medium_priority),
            "low": len(low_priority)
        },
        "urgent_attention": {
            "closing_soon": len(closing_soon),
            "high_value": len(high_value)
        },
        "top_opportunities": [
            {
                "tender_id": t.tender_id,
                "title": t.title,
                "ai_score": round(t.ai_score, 3),
                "value": t.value,
                "closing_date": t.closing_date.isoformat() if t.closing_date else None,
                "country": t.country
            }
            for t in sorted(recommended_tenders, key=lambda x: x.ai_score, reverse=True)[:5]
        ]
    }