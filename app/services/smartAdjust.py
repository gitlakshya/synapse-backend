import os
import json
import sys
import logging
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

# Add project root to path for direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.firestore_service import FirestoreService
from app.services.llm_service import get_llm_service, LLMConfig, SystemInstructions
from app.dependencies import get_firestore_client
from app.services.itinerary_service import ItineraryService

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
client = None
class SmartAdjustAgent:
    def __init__(self):
        self.fs = FirestoreService(get_firestore_client())
        self.llm_service = get_llm_service()

    async def adjust_itinerary(self, current_itinerary: Dict[str, Any], user_request: str) -> Dict[str, Any]:
        """
        Adjust itinerary using centralized LLM service with Google Search integration.
        """
        logger.info("SmartAdjustAgent: adjust_itinerary method called")
        
        # Prepare user message with clear JSON formatting instructions
        user_msg = (
            f"CURRENT ITINERARY:\n{json.dumps(current_itinerary, indent=2)}\n\n"
            f"ADJUSTMENT REQUEST: {user_request}\n\n"
            "RESPONSE FORMAT REQUIREMENTS:\n"
            "1. Return ONLY a valid JSON object\n"
            "2. Start with '{' and end with '}'\n"
            "3. No markdown formatting, explanations, or extra text\n"
            "4. Ensure all JSON syntax is correct (proper quotes, commas, brackets)\n"
            "5. Include all required fields: destination, days, duration, etc.\n\n"
            "RESPOND WITH VALID JSON ONLY:"
        )
        
        # Use LLM config optimized for speed and reliability
        config = LLMConfig(
            model="gemini-2.0-flash-lite",
            temperature=0.5,  
            top_p=0.9,
            max_output_tokens=8192,  # Reduced from 12184 to stay within limits
            use_google_search=True,
            safety_settings_off=True
        )
        
        try:
            logger.info("Making optimized LLM call for itinerary adjustment (Google Search disabled for speed)")
            
            # Make the LLM call using centralized service
            response = self.llm_service.generate_content(
                user_message=user_msg,
                system_instruction=SystemInstructions.smart_adjust_agent(),
                config=config
            )
            
            if not response.success:
                logger.error(f"LLM call failed: {response.error}")
                raise RuntimeError(f"Failed to adjust itinerary: {response.error}")
            
            logger.info(f"LLM call successful, response length: {len(response.content)}")
            logger.info(f"Google Search was used: {response.search_used}")
            
            try:
                # Parse the adjusted itinerary using the shared method
                itineraryData = ItineraryService.parse_llm_response(response.content)
                logger.info("Successfully parsed adjusted itinerary")
                return itineraryData
            except Exception as e:
                logger.error(f"Failed to parse LLM response: {e}")
                logger.warning("Returning original itinerary due to parsing error")
                return current_itinerary
                
        except Exception as e:
            logger.error(f"Exception in adjust_itinerary: {e}")
            logger.warning("Returning original itinerary due to error")
            return current_itinerary


