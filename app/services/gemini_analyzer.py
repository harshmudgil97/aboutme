import google.generativeai as genai
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re

from app.config import settings

logger = logging.getLogger(__name__)

class GeminiTenderAnalyzer:
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        self.wayground_profile = settings.company_description
        self.keywords = settings.tender_keywords
        self.scoring_weights = settings.scoring_weights

    async def analyze_tender(self, tender_data: Dict) -> Dict:
        """
        Analyze a tender using Gemini AI and return comprehensive scoring and recommendations
        """
        try:
            # Prepare the analysis prompt
            prompt = self._create_analysis_prompt(tender_data)
            
            # Get AI analysis
            response = self.model.generate_content(prompt)
            ai_analysis = self._parse_ai_response(response.text)
            
            # Calculate scores
            scores = self._calculate_scores(tender_data, ai_analysis)
            
            # Determine recommendation
            recommendation = self._make_recommendation(scores, ai_analysis)
            
            return {
                "ai_analysis": ai_analysis,
                "scores": scores,
                "recommendation": recommendation,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing tender {tender_data.get('tender_id', 'unknown')}: {str(e)}")
            return self._fallback_analysis(tender_data)

    def _create_analysis_prompt(self, tender_data: Dict) -> str:
        """Create a comprehensive prompt for Gemini AI analysis"""
        
        prompt = f"""
        You are an expert procurement analyst specializing in education technology tenders. 
        Analyze the following tender opportunity for Wayground, an education technology company.

        WAYGROUND COMPANY PROFILE:
        {self.wayground_profile}

        TENDER DETAILS:
        Title: {tender_data.get('title', 'N/A')}
        Description: {tender_data.get('description', 'N/A')}
        Organization: {tender_data.get('organization', 'N/A')}
        Location: {tender_data.get('location', 'N/A')}
        Country: {tender_data.get('country', 'N/A')}
        Value: {tender_data.get('value', 'N/A')} {tender_data.get('currency', '')}
        Closing Date: {tender_data.get('closing_date', 'N/A')}
        CPV Codes: {tender_data.get('cpv_codes', [])}

        TARGET KEYWORDS TO LOOK FOR:
        {', '.join(self.keywords)}

        Please provide a comprehensive analysis in JSON format with the following structure:
        {{
            "relevance_assessment": {{
                "overall_relevance": "High/Medium/Low",
                "explanation": "Detailed explanation of relevance to Wayground's services",
                "matching_services": ["List of Wayground services that match this tender"],
                "key_requirements": ["List of key technical requirements from the tender"]
            }},
            "keyword_analysis": {{
                "matched_keywords": ["List of matching keywords found in tender"],
                "keyword_match_percentage": "percentage as number between 0-100",
                "missing_keywords": ["Important keywords not found but relevant"],
                "additional_relevant_terms": ["Other relevant terms found in tender"]
            }},
            "competitive_assessment": {{
                "competition_level": "High/Medium/Low",
                "wayground_advantages": ["List of Wayground's competitive advantages for this tender"],
                "potential_challenges": ["List of potential challenges or gaps"],
                "required_partnerships": ["Potential partners needed if any"]
            }},
            "financial_analysis": {{
                "value_assessment": "High/Medium/Low value opportunity",
                "budget_alignment": "Does the budget align with Wayground's typical projects?",
                "roi_potential": "High/Medium/Low potential return on investment",
                "cost_considerations": ["Key cost factors to consider"]
            }},
            "timeline_analysis": {{
                "urgency_level": "High/Medium/Low urgency based on closing date",
                "preparation_time": "Amount of time available for proposal preparation",
                "implementation_timeline": "Expected project timeline if available",
                "timeline_feasibility": "Can Wayground meet the timeline requirements?"
            }},
            "geographic_factors": {{
                "location_advantage": "High/Medium/Low advantage based on location",
                "local_presence_required": "Is local presence required?",
                "cultural_considerations": ["Any cultural or regional factors to consider"],
                "regulatory_compliance": ["Regulatory requirements to be aware of"]
            }},
            "recommendation": {{
                "should_pursue": "Yes/No/Maybe",
                "confidence_level": "High/Medium/Low confidence in recommendation",
                "success_probability": "Estimated probability of winning (0-100)",
                "priority_level": "High/Medium/Low priority for Wayground",
                "reasoning": "Detailed reasoning for the recommendation"
            }},
            "action_items": {{
                "immediate_actions": ["Actions to take immediately"],
                "research_needed": ["Additional research or information needed"],
                "stakeholders_to_engage": ["Key stakeholders to involve"],
                "proposal_strategy": ["Key elements for proposal strategy"]
            }}
        }}

        Ensure your analysis is objective, detailed, and specifically tailored to Wayground's capabilities and strategic interests in the education technology sector.
        """
        
        return prompt

    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse and validate the AI response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Fallback: try to parse the entire response as JSON
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            # Return a structured fallback based on text analysis
            return self._create_fallback_response(response_text)

    def _create_fallback_response(self, response_text: str) -> Dict:
        """Create a fallback response structure when JSON parsing fails"""
        return {
            "relevance_assessment": {
                "overall_relevance": "Medium",
                "explanation": "AI analysis completed but structured parsing failed",
                "matching_services": [],
                "key_requirements": []
            },
            "keyword_analysis": {
                "matched_keywords": [],
                "keyword_match_percentage": 50,
                "missing_keywords": [],
                "additional_relevant_terms": []
            },
            "recommendation": {
                "should_pursue": "Maybe",
                "confidence_level": "Low",
                "success_probability": 50,
                "priority_level": "Medium",
                "reasoning": "Analysis completed but requires manual review"
            },
            "raw_response": response_text
        }

    def _calculate_scores(self, tender_data: Dict, ai_analysis: Dict) -> Dict:
        """Calculate numerical scores based on AI analysis and tender data"""
        scores = {}
        
        # Keyword match score (0-100)
        keyword_percentage = ai_analysis.get("keyword_analysis", {}).get("keyword_match_percentage", 0)
        scores["keyword_match_score"] = keyword_percentage / 100.0
        
        # Value score (0-1)
        scores["value_score"] = self._calculate_value_score(tender_data.get("value", 0))
        
        # Urgency score (0-1) - higher for more time to prepare
        scores["urgency_score"] = self._calculate_urgency_score(tender_data.get("closing_date"))
        
        # Geographic score (0-1)
        scores["geo_score"] = self._calculate_geographic_score(
            tender_data.get("country"), 
            tender_data.get("region")
        )
        
        # Success probability (0-1)
        success_prob = ai_analysis.get("recommendation", {}).get("success_probability", 50)
        scores["success_probability"] = success_prob / 100.0
        
        # Overall relevance score (0-1)
        relevance = ai_analysis.get("relevance_assessment", {}).get("overall_relevance", "Medium")
        relevance_map = {"High": 0.9, "Medium": 0.6, "Low": 0.3}
        scores["relevance_score"] = relevance_map.get(relevance, 0.6)
        
        # Calculate weighted AI score
        weights = self.scoring_weights
        scores["ai_score"] = (
            scores["keyword_match_score"] * weights["keyword_match"] +
            scores["value_score"] * weights["value_range"] +
            scores["urgency_score"] * weights["deadline_urgency"] +
            scores["geo_score"] * weights["geographical_preference"] +
            scores["success_probability"] * weights["past_success_probability"]
        )
        
        return scores

    def _calculate_value_score(self, value: Optional[float]) -> float:
        """Calculate score based on tender value"""
        if not value or value <= 0:
            return 0.5  # Unknown value gets neutral score
        
        # Score based on value ranges (adjust these based on Wayground's preferences)
        if value >= 1000000:  # £1M+
            return 1.0
        elif value >= 500000:  # £500K+
            return 0.8
        elif value >= 100000:  # £100K+
            return 0.6
        elif value >= 50000:   # £50K+
            return 0.4
        else:
            return 0.2

    def _calculate_urgency_score(self, closing_date: Optional[str]) -> float:
        """Calculate score based on time until closing"""
        if not closing_date:
            return 0.5
        
        try:
            if isinstance(closing_date, str):
                # Try multiple date formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"]:
                    try:
                        close_date = datetime.strptime(closing_date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return 0.5  # Can't parse date
            else:
                close_date = closing_date
            
            days_until_close = (close_date - datetime.now()).days
            
            if days_until_close < 0:
                return 0.0  # Already closed
            elif days_until_close < 7:
                return 0.2  # Very urgent, little time to prepare
            elif days_until_close < 14:
                return 0.5  # Urgent
            elif days_until_close < 30:
                return 0.8  # Good time to prepare
            else:
                return 1.0  # Plenty of time
                
        except Exception as e:
            logger.warning(f"Error calculating urgency score: {e}")
            return 0.5

    def _calculate_geographic_score(self, country: Optional[str], region: Optional[str]) -> float:
        """Calculate score based on geographic preferences"""
        if not country:
            return 0.5
        
        # Preference order (adjust based on Wayground's strategic preferences)
        country_scores = {
            "United Kingdom": 1.0,
            "Ireland": 0.9,
            "Australia": 0.8,
            "New Zealand": 0.8,
            "Singapore": 0.7,
            "Canada": 0.7,
            "United States": 0.6,
            "Germany": 0.6,
            "Netherlands": 0.6,
            "France": 0.5,
            "UAE": 0.5,
            "South Africa": 0.4
        }
        
        return country_scores.get(country, 0.3)

    def _make_recommendation(self, scores: Dict, ai_analysis: Dict) -> Dict:
        """Make final recommendation based on scores and AI analysis"""
        ai_score = scores.get("ai_score", 0)
        ai_recommendation = ai_analysis.get("recommendation", {})
        
        # Determine if should pursue based on AI score and AI recommendation
        should_pursue = ai_recommendation.get("should_pursue", "Maybe")
        
        if ai_score >= 0.7 and should_pursue == "Yes":
            recommendation = "Highly Recommended"
            priority = "High"
        elif ai_score >= 0.5 and should_pursue in ["Yes", "Maybe"]:
            recommendation = "Recommended"
            priority = "Medium"
        elif ai_score >= 0.3:
            recommendation = "Consider"
            priority = "Low"
        else:
            recommendation = "Not Recommended"
            priority = "Low"
        
        return {
            "recommendation": recommendation,
            "priority": priority,
            "should_pursue": should_pursue,
            "confidence": ai_recommendation.get("confidence_level", "Medium"),
            "reasoning": ai_recommendation.get("reasoning", "Analysis based on AI scoring and assessment"),
            "ai_score": ai_score,
            "success_probability": scores.get("success_probability", 0.5)
        }

    def _fallback_analysis(self, tender_data: Dict) -> Dict:
        """Provide fallback analysis when AI analysis fails"""
        return {
            "ai_analysis": {
                "relevance_assessment": {
                    "overall_relevance": "Medium",
                    "explanation": "AI analysis unavailable - manual review required"
                },
                "recommendation": {
                    "should_pursue": "Maybe",
                    "confidence_level": "Low",
                    "success_probability": 50,
                    "reasoning": "AI analysis failed - requires manual evaluation"
                }
            },
            "scores": {
                "keyword_match_score": 0.5,
                "value_score": 0.5,
                "urgency_score": 0.5,
                "geo_score": 0.5,
                "success_probability": 0.5,
                "relevance_score": 0.5,
                "ai_score": 0.5
            },
            "recommendation": {
                "recommendation": "Manual Review Required",
                "priority": "Medium",
                "should_pursue": "Maybe",
                "confidence": "Low",
                "reasoning": "AI analysis failed - manual evaluation needed",
                "ai_score": 0.5,
                "success_probability": 0.5
            },
            "analysis_timestamp": datetime.now().isoformat(),
            "error": "AI analysis failed"
        }

    async def batch_analyze_tenders(self, tenders: List[Dict]) -> List[Dict]:
        """Analyze multiple tenders in batch"""
        results = []
        for tender in tenders:
            try:
                analysis = await self.analyze_tender(tender)
                results.append({
                    "tender_id": tender.get("tender_id"),
                    "analysis": analysis
                })
            except Exception as e:
                logger.error(f"Error in batch analysis for tender {tender.get('tender_id')}: {e}")
                results.append({
                    "tender_id": tender.get("tender_id"),
                    "analysis": self._fallback_analysis(tender),
                    "error": str(e)
                })
        return results