import os
import json
import sys
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add project root to path for direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.firestore_service import FirestoreService
from app.services.llm_service import get_llm_service, LLMConfig, SystemInstructions
from app.dependencies import get_firestore_client
from app.models.itinerary import Itinerary, ItineraryInput

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ItineraryService:
    """Service for generating and managing travel itineraries using centralized LLM service"""
    
    def __init__(self):
        self.fs = FirestoreService(get_firestore_client())
        
        # Try to use real LLM service, fall back to mock if project ID not available
        if os.getenv('GOOGLE_CLOUD_PROJECT'):
            self.llm_service = get_llm_service()
            self.using_mock = False
            logger.info("Using real LLM service")
        else:
            from tests.mock_llm_service import MockLLMService
            self.llm_service = MockLLMService()
            self.using_mock = True
            logger.warning("Using mock LLM service - GOOGLE_CLOUD_PROJECT not found")
    
    async def generate_itinerary(
        self, 
        destination: str,
        days: int,
        budget: float,
        preferences: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        special_requirements: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a new itinerary using the centralized LLM service
        
        Args:
            destination: Travel destination
            days: Number of days for the trip
            budget: Total budget in local currency
            preferences: User preference sliders (0-100 scale)
            start_date: Trip start date (YYYY-MM-DD)
            end_date: Trip end date (YYYY-MM-DD)
            special_requirements: Any special needs or requirements
            session_id: Session ID for tracking
            
        Returns:
            Generated itinerary as a dictionary
        """
        try:
            logger.info(f"Generating itinerary for {destination}, {days} days, budget: {budget}")
            
            # Prepare user message with trip details
            user_message = self._create_trip_planning_prompt(
                destination=destination,
                days=days,
                budget=budget,
                preferences=preferences or {},
                start_date=start_date,
                end_date=end_date,
                special_requirements=special_requirements
            )
            
            # Configure LLM with Google Search for real-time information
            config = LLMConfig(
                model="gemini-2.0-flash-lite",
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=8000,
                use_google_search=True,
                safety_settings_off=True
            )
            
            # Generate itinerary using LLM service
            logger.info("Making LLM call for itinerary generation")
            
            if self.using_mock:
                # Mock service doesn't need system instructions or config
                response = self.llm_service.generate_content(
                    user_message=user_message,
                    system_instruction="",
                    config={}
                )
            else:
                # Real LLM service with full configuration
                response = self.llm_service.generate_content(
                    user_message=user_message,
                    system_instruction=SystemInstructions.trip_planner(),
                    config=config
                )
            
            if not response.success:
                logger.error(f"LLM call failed: {response.error}")
                raise RuntimeError(f"Failed to generate itinerary: {response.error}")
            
            logger.info(f"LLM call successful, response length: {len(response.content)}")
            logger.info(f"Google Search was used: {response.search_used}")
            
            # Parse and validate the response
            itinerary_data = self._parse_llm_response(response.content)
            
            # Add fallback POI IDs to activities
            itinerary_data = self._add_fallback_poi_ids(itinerary_data)
            
            # Enhance with metadata
            itinerary_data = self._add_metadata(
                itinerary_data, 
                session_id=session_id,
                search_used=response.search_used,
                destination=destination,
                days=days,
                budget=budget,
                preferences=preferences,
                start_date=start_date,
                end_date=end_date
            )
            
            # Validate the structure
            validation = self.llm_service.validate_itinerary_structure(
                json.dumps(itinerary_data)
            )
            
            if not validation['valid']:
                logger.warning(f"Generated itinerary has validation issues: {validation}")
                # Try to fix common issues or regenerate if needed
                itinerary_data = self._fix_validation_issues(itinerary_data, validation)
            
            logger.info("Itinerary generation completed successfully")
            return itinerary_data
            
        except Exception as e:
            logger.error(f"Error generating itinerary: {e}")
            raise
    
    def _create_trip_planning_prompt(
        self,
        destination: str,
        days: int,
        budget: float,
        preferences: Dict[str, Any],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        special_requirements: Optional[str] = None
    ) -> str:
        """Create a detailed prompt for trip planning"""
        
        prompt_parts = [
            f"Plan a {days}-day trip to {destination} with a budget of {budget}."
        ]
        
        if start_date and end_date:
            prompt_parts.append(f"Travel dates: {start_date} to {end_date}")
        elif start_date:
            prompt_parts.append(f"Starting date: {start_date}")
        
        # Add preferences with clear explanations
        if preferences:
            pref_descriptions = []
            for pref, value in preferences.items():
                if value and value > 0:
                    intensity = "low" if value < 40 else "moderate" if value < 70 else "high"
                    pref_descriptions.append(f"{pref}: {intensity} interest ({value}/100)")
            
            if pref_descriptions:
                prompt_parts.append(f"Preferences: {', '.join(pref_descriptions)}")
        
        if special_requirements:
            prompt_parts.append(f"Special requirements: {special_requirements}")
        
        # Add specific instructions
        prompt_parts.extend([
            "\nPlease include:",
            "- Realistic timing and duration for each activity",
            "- Specific location coordinates when possible",
            "- Cost estimates for activities and meals",
            "- Safety considerations where relevant",
            "- Local cultural insights and recommendations",
            "- Mix of popular attractions and hidden gems",
            f"- Activities distributed across all {days} days",
            "\nUse Google Search to get current information about opening hours, prices, and availability."
        ])
        
        return " ".join(prompt_parts)
    
    def _parse_llm_response(self, response_content: str) -> Dict[str, Any]:
        """Parse LLM response and extract JSON itinerary"""
        try:
            # Log the raw response for debugging
            logger.info(f"Raw LLM response (first 200 chars): {response_content[:200]}")
            
            # Try to find JSON in the response
            response_content = response_content.strip()
            
            # Remove markdown code blocks if present
            if response_content.startswith('```json'):
                response_content = response_content[7:]
            if response_content.startswith('```'):
                response_content = response_content[3:]
            if response_content.endswith('```'):
                response_content = response_content[:-3]
            
            response_content = response_content.strip()
            logger.info(f"Cleaned response (first 200 chars): {response_content[:200]}")
            
            # Parse JSON
            itinerary_data = json.loads(response_content)
            logger.info(f"Successfully parsed JSON with keys: {list(itinerary_data.keys()) if isinstance(itinerary_data, dict) else 'Not a dict'}")
            return itinerary_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Error at position {e.pos if hasattr(e, 'pos') else 'unknown'}")
            logger.error(f"Full response content (first 1000 chars): {response_content[:1000]}")
            raise ValueError("LLM did not return valid JSON")
    
    def _add_metadata(
        self, 
        itinerary_data: Dict[str, Any], 
        session_id: Optional[str] = None,
        search_used: bool = False,
        destination: Optional[str] = None,
        days: Optional[int] = None,
        budget: Optional[float] = None,
        preferences: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add metadata and input section to the generated itinerary"""
        
        # Add input section
        if "input" not in itinerary_data:
            itinerary_data["input"] = {}
        
        if destination:
            itinerary_data["input"]["destination"] = {"name": destination}
        if days:
            itinerary_data["input"]["numDays"] = days
        if budget:
            itinerary_data["input"]["budget"] = budget
        if start_date:
            itinerary_data["input"]["startDate"] = start_date
        if end_date:
            itinerary_data["input"]["endDate"] = end_date
        if preferences:
            itinerary_data["input"]["sliders"] = preferences
        
        if "meta" not in itinerary_data:
            itinerary_data["meta"] = {}
        
        itinerary_data["meta"].update({
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "generatedBy": "ItineraryService",
            "llmTraceId": f"trace_{uuid.uuid4().hex[:12]}",
            "version": "1.0",
            "searchUsed": search_used
        })
        
        if session_id:
            itinerary_data["meta"]["sessionId"] = session_id
        
        # Add generated ID
        if "itineraryId" not in itinerary_data:
            itinerary_data["itineraryId"] = f"itin_{uuid.uuid4().hex[:12]}"
        
        return itinerary_data
    
    def _fix_validation_issues(
        self, 
        itinerary_data: Dict[str, Any], 
        validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt to fix common validation issues"""
        
        # Add missing required fields with defaults
        if "missing_fields" in validation:
            for field in validation["missing_fields"]:
                if field == "title" and "title" not in itinerary_data:
                    dest = itinerary_data.get("input", {}).get("destination", "Unknown")
                    itinerary_data["title"] = f"Trip to {dest}"
                elif field == "estimatedCost" and "estimatedCost" not in itinerary_data:
                    # Sum up activity costs or use budget
                    total_cost = 0
                    for day in itinerary_data.get("days", []):
                        for activity in day.get("activities", []):
                            total_cost += activity.get("cost", 0)
                    itinerary_data["estimatedCost"] = total_cost or itinerary_data.get("input", {}).get("budget", 0)
                elif field == "meta" and "meta" not in itinerary_data:
                    itinerary_data["meta"] = {}
        
        # Fix input field issues
        if "missing_input_fields" in validation:
            if "input" not in itinerary_data:
                itinerary_data["input"] = {}
            
            for field in validation["missing_input_fields"]:
                if field == "numDays" and "numDays" not in itinerary_data["input"]:
                    itinerary_data["input"]["numDays"] = len(itinerary_data.get("days", []))
                elif field == "destination" and "destination" not in itinerary_data["input"]:
                    # Try to extract from title or set as unknown
                    title = itinerary_data.get("title", "")
                    if "to " in title:
                        dest = title.split("to ")[-1].split()[0]
                        itinerary_data["input"]["destination"] = {"name": dest}
                    else:
                        itinerary_data["input"]["destination"] = {"name": "Unknown"}
        
        return itinerary_data
    
    async def save_itinerary(
        self, 
        itinerary_data: Dict[str, Any], 
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Save itinerary to Firestore"""
        try:
            if user_id:
                itinerary_id = self.fs.save_itinerary_for_user(user_id, itinerary_data)
                logger.info(f"Saved itinerary {itinerary_id} for user {user_id}")
            elif session_id:
                itinerary_id = self.fs.save_itinerary_for_session(session_id, itinerary_data)
                logger.info(f"Saved itinerary {itinerary_id} for session {session_id}")
            else:
                raise ValueError("Either user_id or session_id must be provided")
            
            return itinerary_id
            
        except Exception as e:
            logger.error(f"Error saving itinerary: {e}")
            
            # For testing/development when Firebase isn't configured,
            # return a mock ID instead of failing
            if self.using_mock or "No module named" in str(e) or "credentials" in str(e).lower():
                mock_id = f"mock_{session_id or user_id}_{int(datetime.now().timestamp())}"
                logger.warning(f"Using mock itinerary ID: {mock_id}")
                return mock_id
            
            raise

    def _add_fallback_poi_ids(self, itinerary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add fallback POI IDs to activities that don't have them"""
        try:
            if 'days' in itinerary_data:
                for day in itinerary_data['days']:
                    if 'activities' in day:
                        for activity in day['activities']:
                            if not activity.get('poiId'):
                                activity['poiId'] = f"fallback_{uuid.uuid4().hex[:8]}"
                                
                                # Add basic snapshot
                                activity_name = activity.get('title') or activity.get('name', 'Unknown Activity')
                                activity['poiSnapshot'] = {
                                    'name': activity_name
                                }
            
            return itinerary_data
            
        except Exception as e:
            logger.error(f"Error adding fallback POI IDs: {e}")
            return itinerary_data

def get_itinerary_service() -> ItineraryService:
    """Get instance of ItineraryService"""
    return ItineraryService()
