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
        
        # Prepare user message with clear JSON formatting instructions
        user_msg = (
            f"Here is the current itinerary JSON:\n{json.dumps(current_itinerary, indent=2)}\n\n"
            f"User adjustment request: {user_request}\n\n"
            "IMPORTANT: Return ONLY the adjusted itinerary as a valid JSON object. "
            "Do not include any explanations, markdown formatting, or additional text. "
            "The response must start with '{' and end with '}' and be valid JSON."
        )
        
        # Use LLM config optimized for speed and reliability
        config = LLMConfig(
            model="gemini-2.0-flash-lite",
            temperature=0.3,  # Reduced for more consistent JSON output
            top_p=0.8,  # Reduced for more focused generation
            max_output_tokens=4096,  # Reduced for faster generation
            use_google_search=False,  # Disabled for speed (adjustments rarely need real-time data)
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
                # Robust JSON parsing with improved cleanup
                if isinstance(response.content, str):
                    content = response.content.strip()
                    
                    # Remove common markdown formatting
                    if content.startswith('```json'):
                        content = content[7:]
                    elif content.startswith('```'):
                        content = content[3:]
                    
                    if content.endswith('```'):
                        content = content[:-3]
                    
                    # Remove any leading/trailing whitespace and newlines
                    content = content.strip()
                    
                    # Try to find JSON object boundaries if there's extra text
                    start_idx = content.find('{')
                    end_idx = content.rfind('}')
                    
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        content = content[start_idx:end_idx + 1]
                    
                    # Parse the cleaned content
                    adjusted_itinerary = json.loads(content)
                else:
                    adjusted_itinerary = response.content
                
                # Validate that we got a proper itinerary structure
                if not isinstance(adjusted_itinerary, dict):
                    raise ValueError("Response is not a valid JSON object")
                
                if 'days' not in adjusted_itinerary:
                    raise ValueError("Response missing required 'days' field")
                
                return adjusted_itinerary
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response content: {response.content[:1000]}...")
                
                # Try alternative parsing approach - extract JSON from text
                try:
                    import re
                    # Look for JSON object pattern in the response
                    json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        adjusted_itinerary = json.loads(json_str)
                        logger.info("Successfully recovered JSON using regex extraction")
                        return adjusted_itinerary
                except:
                    pass
                
                raise RuntimeError(f"Failed to parse LLM response as JSON: {e}")
            except ValueError as e:
                logger.error(f"Invalid itinerary structure: {e}")
                raise RuntimeError(f"Invalid itinerary structure: {e}")
            
        except Exception as e:
            logger.error(f"Exception in adjust_itinerary: {e}")
            raise


