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

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
client = None
class SmartAdjustAgent:
    def __init__(self):
        self.fs = FirestoreService(get_firestore_client())
        self.llm_service = get_llm_service()

    def adjust_itinerary(self, current_itinerary: Dict[str, Any], user_request: str) -> Dict[str, Any]:
        """
        Adjust itinerary using centralized LLM service with Google Search integration.
        """
        logger.info("SmartAdjustAgent: adjust_itinerary method called")
        
        # Prepare user message with itinerary and request
        user_msg = (
            f"Here is the current itinerary JSON:\n{json.dumps(current_itinerary, indent=2)}\n\n"
            f"User adjustment request: {user_request}\n\n"
            "Return the adjusted itinerary as a full JSON object."
        )
        
        # Use LLM config with Google Search enabled
        config = LLMConfig(
            model="gemini-2.5-flash-lite",
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=8192,
            use_google_search=True,
            safety_settings_off=True
        )
        
        try:
            logger.info("Making LLM call with Google Search for itinerary adjustment")
            
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
                # Parse the adjusted itinerary with cleanup for markdown formatting
                if isinstance(response.content, str):
                    # Remove markdown formatting if present
                    content = response.content.strip()
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.startswith('```'):
                        content = content[3:]
                    if content.endswith('```'):
                        content = content[:-3]
                    
                    adjusted_itinerary = json.loads(content)
                else:
                    adjusted_itinerary = response.content
                return adjusted_itinerary
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response content: {response.content[:500]}...")
                raise RuntimeError("Failed to parse LLM response as JSON")
            
        except Exception as e:
            logger.error(f"Exception in adjust_itinerary: {e}")
            raise


