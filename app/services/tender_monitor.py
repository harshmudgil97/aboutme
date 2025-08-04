import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.tender import Tender, TenderCreate
from app.services.tender_scraper import TenderScraper
from app.services.gemini_analyzer import GeminiTenderAnalyzer
from app.config import settings

logger = logging.getLogger(__name__)

class TenderMonitorService:
    def __init__(self):
        self.scraper = None
        self.analyzer = GeminiTenderAnalyzer()
        self.is_running = False
        
    async def start_monitoring(self):
        """Start the automated tender monitoring service"""
        logger.info("Starting Wayground Tender Monitor Service...")
        self.is_running = True
        
        # Schedule periodic searches
        schedule.every(6).hours.do(self.run_scheduled_search)
        schedule.every().day.at("09:00").do(self.run_daily_analysis)
        schedule.every().monday.at("08:00").do(self.run_weekly_report)
        
        # Run initial search
        await self.run_full_search_and_analysis()
        
        # Main monitoring loop
        while self.is_running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute
    
    def stop_monitoring(self):
        """Stop the monitoring service"""
        logger.info("Stopping Wayground Tender Monitor Service...")
        self.is_running = False
    
    async def run_scheduled_search(self):
        """Run scheduled tender search"""
        try:
            logger.info("Running scheduled tender search...")
            await self.run_full_search_and_analysis()
        except Exception as e:
            logger.error(f"Error in scheduled search: {str(e)}")
    
    async def run_full_search_and_analysis(self):
        """Run full search across all portals and analyze results"""
        logger.info("Starting full tender search and analysis...")
        
        async with TenderScraper() as scraper:
            # Search all portals
            new_tenders = await scraper.search_all_portals()
            logger.info(f"Found {len(new_tenders)} tenders across all portals")
            
            # Process each tender
            processed_count = 0
            for tender_data in new_tenders:
                try:
                    saved = await self.save_and_analyze_tender(tender_data, self.analyzer)
                    if saved:
                        processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing tender {tender_data.get('tender_id')}: {str(e)}")
                    continue
            
            logger.info(f"Successfully processed {processed_count} new tenders")
            
            # Generate summary
            await self.generate_search_summary(len(new_tenders), processed_count)
    
    async def save_and_analyze_tender(self, tender_data: Dict, analyzer: GeminiTenderAnalyzer) -> bool:
        """Save tender to database and analyze with AI"""
        db = SessionLocal()
        try:
            # Check if tender already exists
            existing = db.query(Tender).filter(Tender.tender_id == tender_data.get('tender_id')).first()
            if existing:
                logger.debug(f"Tender {tender_data.get('tender_id')} already exists, skipping...")
                return False
            
            # Create new tender record
            tender = Tender(
                tender_id=tender_data.get('tender_id'),
                title=tender_data.get('title'),
                description=tender_data.get('description'),
                organization=tender_data.get('organization'),
                location=tender_data.get('location'),
                country=tender_data.get('country'),
                region=tender_data.get('region'),
                value=tender_data.get('value'),
                currency=tender_data.get('currency'),
                publication_date=tender_data.get('publication_date'),
                closing_date=tender_data.get('closing_date'),
                tender_url=tender_data.get('tender_url'),
                source_portal=tender_data.get('source_portal'),
                cpv_codes=tender_data.get('cpv_codes', []),
                keywords=tender_data.get('keywords', [])
            )
            
            # Save to database first
            db.add(tender)
            db.commit()
            
            # Analyze with Gemini AI
            try:
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
                
                db.commit()
                
                logger.info(f"Successfully analyzed tender {tender.tender_id} - Score: {tender.ai_score:.2f}, Recommended: {tender.recommended}")
                
            except Exception as e:
                logger.error(f"Error analyzing tender {tender.tender_id}: {str(e)}")
                # Keep the tender in database even if analysis fails
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving tender {tender_data.get('tender_id')}: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def run_daily_analysis(self):
        """Run daily analysis and reporting"""
        logger.info("Running daily analysis...")
        asyncio.create_task(self._daily_analysis())
    
    async def _daily_analysis(self):
        """Internal daily analysis method"""
        db = SessionLocal()
        try:
            # Get tenders from last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            recent_tenders = db.query(Tender).filter(Tender.created_at >= yesterday).all()
            
            # Generate daily summary
            total_new = len(recent_tenders)
            recommended_new = sum(1 for t in recent_tenders if t.recommended)
            high_score_new = sum(1 for t in recent_tenders if t.ai_score >= 0.7)
            
            logger.info(f"Daily Summary: {total_new} new tenders, {recommended_new} recommended, {high_score_new} high-score")
            
            # Check for urgent tenders (closing within 7 days)
            week_ahead = datetime.now() + timedelta(days=7)
            urgent_tenders = db.query(Tender).filter(
                Tender.closing_date <= week_ahead,
                Tender.closing_date >= datetime.now(),
                Tender.recommended == True,
                Tender.status == "new"
            ).all()
            
            if urgent_tenders:
                logger.warning(f"URGENT: {len(urgent_tenders)} recommended tenders closing within 7 days!")
                for tender in urgent_tenders:
                    days_left = (tender.closing_date - datetime.now()).days
                    logger.warning(f"  - {tender.title} (Score: {tender.ai_score:.2f}) - {days_left} days left")
            
        except Exception as e:
            logger.error(f"Error in daily analysis: {str(e)}")
        finally:
            db.close()
    
    def run_weekly_report(self):
        """Run weekly performance report"""
        logger.info("Running weekly performance report...")
        asyncio.create_task(self._weekly_report())
    
    async def _weekly_report(self):
        """Internal weekly report method"""
        db = SessionLocal()
        try:
            # Get tenders from last week
            week_ago = datetime.now() - timedelta(days=7)
            weekly_tenders = db.query(Tender).filter(Tender.created_at >= week_ago).all()
            
            # Calculate metrics
            total_weekly = len(weekly_tenders)
            recommended_weekly = sum(1 for t in weekly_tenders if t.recommended)
            avg_score = sum(t.ai_score for t in weekly_tenders) / total_weekly if total_weekly > 0 else 0
            
            # Top keywords this week
            keyword_freq = {}
            for tender in weekly_tenders:
                if tender.keywords:
                    for keyword in tender.keywords:
                        keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
            
            top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Regional distribution
            region_dist = {}
            for tender in weekly_tenders:
                region = tender.region
                region_dist[region] = region_dist.get(region, 0) + 1
            
            # Generate report
            report = f"""
            WAYGROUND TENDER MONITOR - WEEKLY REPORT
            ======================================
            
            Period: {week_ago.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}
            
            SUMMARY:
            - Total new tenders: {total_weekly}
            - Recommended tenders: {recommended_weekly}
            - Recommendation rate: {(recommended_weekly/total_weekly*100):.1f}% 
            - Average AI score: {avg_score:.2f}
            
            TOP KEYWORDS:
            {chr(10).join([f"- {keyword}: {count}" for keyword, count in top_keywords])}
            
            REGIONAL DISTRIBUTION:
            {chr(10).join([f"- {region}: {count}" for region, count in region_dist.items()])}
            """
            
            logger.info(report)
            
        except Exception as e:
            logger.error(f"Error in weekly report: {str(e)}")
        finally:
            db.close()
    
    async def generate_search_summary(self, total_found: int, processed: int):
        """Generate summary of search results"""
        db = SessionLocal()
        try:
            # Get recent stats
            today = datetime.now().date()
            today_tenders = db.query(Tender).filter(
                Tender.created_at >= datetime.combine(today, datetime.min.time())
            ).all()
            
            recommended_today = sum(1 for t in today_tenders if t.recommended)
            high_score_today = sum(1 for t in today_tenders if t.ai_score >= 0.7)
            
            summary = f"""
            SEARCH SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M')}
            =================================================
            
            - Tenders found: {total_found}
            - New tenders processed: {processed}
            - Recommended today: {recommended_today}
            - High-score tenders today: {high_score_today}
            """
            
            logger.info(summary)
            
        except Exception as e:
            logger.error(f"Error generating search summary: {str(e)}")
        finally:
            db.close()
    
    async def manual_search_region(self, region: str) -> Dict:
        """Manually search a specific region"""
        logger.info(f"Manual search requested for region: {region}")
        
        async with TenderScraper() as scraper:
            portals = scraper.portals.get(region, [])
            if not portals:
                raise ValueError(f"Unknown region: {region}")
            
            all_tenders = []
            for portal in portals:
                try:
                    tenders = await scraper.search_portal(portal, region)
                    all_tenders.extend(tenders)
                except Exception as e:
                    logger.error(f"Error searching portal {portal}: {str(e)}")
                    continue
            
            # Process tenders
            processed = 0
            for tender_data in all_tenders:
                try:
                    if await self.save_and_analyze_tender(tender_data, self.analyzer):
                        processed += 1
                except Exception as e:
                    logger.error(f"Error processing tender: {str(e)}")
            
            return {
                "region": region,
                "portals_searched": len(portals),
                "tenders_found": len(all_tenders),
                "tenders_processed": processed
            }
    
    async def reanalyze_tenders(self, tender_ids: Optional[List[str]] = None) -> int:
        """Re-analyze existing tenders"""
        db = SessionLocal()
        try:
            if tender_ids:
                tenders = db.query(Tender).filter(Tender.tender_id.in_(tender_ids)).all()
            else:
                # Re-analyze all tenders older than 24 hours without analysis
                yesterday = datetime.now() - timedelta(days=1)
                tenders = db.query(Tender).filter(
                    Tender.created_at <= yesterday,
                    Tender.ai_analysis.is_(None)
                ).all()
            
            reanalyzed = 0
            for tender in tenders:
                try:
                    # Convert to dict for analysis
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
                    
                    analysis = await self.analyzer.analyze_tender(tender_data)
                    
                    # Update tender
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
                    
                    reanalyzed += 1
                    
                except Exception as e:
                    logger.error(f"Error re-analyzing tender {tender.tender_id}: {str(e)}")
                    continue
            
            db.commit()
            logger.info(f"Re-analyzed {reanalyzed} tenders")
            return reanalyzed
            
        except Exception as e:
            logger.error(f"Error in re-analysis: {str(e)}")
            db.rollback()
            return 0
        finally:
            db.close()