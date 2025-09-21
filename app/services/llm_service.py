import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Comprehensive JSON Schema for Itinerary Structure
ITINERARY_JSON_SCHEMA = {
    "type": "object",
    "required": ["title", "input", "days", "estimatedCost", "meta"],
    "properties": {
        "title": {
            "type": "string",
            "description": "Descriptive title for the itinerary (e.g., 'Goa Long Weekend')"
        },
        "input": {
            "type": "object",
            "required": ["destination", "numDays"],
            "properties": {
                "sessionId": {
                    "type": "string",
                    "description": "Session identifier for the trip request"
                },
                "destination": {
                    "type": "string",
                    "description": "Primary destination for the trip"
                },
                "startDate": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                },
                "endDate": {
                    "type": "string", 
                    "description": "End date in YYYY-MM-DD format",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                },
                "numDays": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Number of days for the trip"
                },
                "budget": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Total budget in the local currency"
                },
                "sliders": {
                    "type": "object",
                    "description": "Preference weightings (0-100 scale)",
                    "properties": {
                        "nature": {"type": "number", "minimum": 0, "maximum": 100},
                        "nightlife": {"type": "number", "minimum": 0, "maximum": 100},
                        "adventure": {"type": "number", "minimum": 0, "maximum": 100},
                        "leisure": {"type": "number", "minimum": 0, "maximum": 100},
                        "heritage": {"type": "number", "minimum": 0, "maximum": 100},
                        "culture": {"type": "number", "minimum": 0, "maximum": 100},
                        "food": {"type": "number", "minimum": 0, "maximum": 100},
                        "shopping": {"type": "number", "minimum": 0, "maximum": 100}
                    }
                },
                "specialRequirements": {
                    "type": "string",
                    "description": "Any special requirements or accessibility needs"
                },
                "preferences": {
                    "type": "object",
                    "description": "Alternative preference structure (legacy support)"
                }
            }
        },
        "days": {
            "type": "array",
            "description": "Array of daily plans",
            "items": {
                "type": "object",
                "required": ["dayIndex", "activities"],
                "properties": {
                    "dayIndex": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Day number (1-indexed)"
                    },
                    "activities": {
                        "type": "array",
                        "description": "List of activities for this day",
                        "items": {
                            "type": "object",
                            "required": ["title", "durationMins", "category"],
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "Activity name or title"
                                },
                                "durationMins": {
                                    "type": "integer",
                                    "minimum": 15,
                                    "description": "Duration in minutes"
                                },
                                "category": {
                                    "type": "string",
                                    "enum": ["nature", "nightlife", "adventure", "leisure", "heritage", "culture", "food", "shopping", "transport", "accommodation"],
                                    "description": "Activity category"
                                },
                                "dayIndex": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "description": "Which day this activity belongs to"
                                },
                                "poiId": {
                                    "type": "string",
                                    "description": "Point of Interest ID if available"
                                },
                                "poiSnapshot": {
                                    "type": "object",
                                    "description": "Basic location information",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name of the place"
                                        },
                                        "lat": {
                                            "type": "number",
                                            "description": "Latitude coordinate"
                                        },
                                        "lng": {
                                            "type": "number", 
                                            "description": "Longitude coordinate"
                                        },
                                        "imageUrl": {
                                            "type": "string",
                                            "description": "Optional image URL"
                                        },
                                        "address": {
                                            "type": "string",
                                            "description": "Address or location description"
                                        }
                                    }
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Detailed description of the activity"
                                },
                                "cost": {
                                    "type": "number",
                                    "minimum": 0,
                                    "description": "Estimated cost for this activity"
                                },
                                "safetyNote": {
                                    "type": "string",
                                    "description": "Any safety considerations or notes"
                                },
                                "bookingRequired": {
                                    "type": "boolean",
                                    "description": "Whether advance booking is required"
                                },
                                "timeOfDay": {
                                    "type": "string",
                                    "enum": ["morning", "afternoon", "evening", "night"],
                                    "description": "Recommended time of day"
                                }
                            }
                        }
                    }
                }
            }
        },
        "estimatedCost": {
            "type": "number",
            "minimum": 0,
            "description": "Total estimated cost for the entire itinerary"
        },
        "meta": {
            "type": "object",
            "description": "Metadata about the itinerary",
            "properties": {
                "generatedAt": {
                    "type": "string",
                    "description": "ISO timestamp when generated"
                },
                "generatedBy": {
                    "type": "string",
                    "description": "Service that generated this itinerary"
                },
                "adjustedBy": {
                    "type": "string",
                    "description": "Service that last adjusted this itinerary"
                },
                "llmTraceId": {
                    "type": "string",
                    "description": "Trace ID for LLM call debugging"
                },
                "version": {
                    "type": "string",
                    "description": "Schema version for compatibility"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Categorization tags"
                }
            }
        }
    }
}

# Human-readable schema documentation
ITINERARY_SCHEMA_DOCS = """
ITINERARY JSON SCHEMA:

{
  "title": "string - Descriptive title (e.g., 'Tokyo Adventure')",
  "input": {
    "sessionId": "string - Session identifier",
    "destination": "string - Primary destination (REQUIRED)",
    "startDate": "string - YYYY-MM-DD format",
    "endDate": "string - YYYY-MM-DD format", 
    "numDays": "integer - Number of days (REQUIRED)",
    "budget": "number - Total budget in local currency",
    "sliders": {
      "nature": "number (0-100) - Nature/outdoor preference",
      "nightlife": "number (0-100) - Nightlife preference",
      "adventure": "number (0-100) - Adventure activities",
      "leisure": "number (0-100) - Relaxation activities",
      "heritage": "number (0-100) - Historical sites",
      "culture": "number (0-100) - Cultural experiences",
      "food": "number (0-100) - Food experiences", 
      "shopping": "number (0-100) - Shopping activities"
    },
    "specialRequirements": "string - Accessibility or special needs"
  },
  "days": [
    {
      "dayIndex": "integer - Day number (1-indexed, REQUIRED)",
      "activities": [
        {
          "title": "string - Activity name (REQUIRED)",
          "durationMins": "integer - Duration in minutes (REQUIRED)",
          "category": "string - One of: nature|nightlife|adventure|leisure|heritage|culture|food|shopping|transport|accommodation (REQUIRED)",
          "dayIndex": "integer - Which day (1-indexed)",
          "poiId": "string - POI identifier (if available)",
          "poiSnapshot": {
            "name": "string - Place name (REQUIRED if poiSnapshot present)",
            "lat": "number - Latitude",
            "lng": "number - Longitude",
            "imageUrl": "string - Image URL",
            "address": "string - Address or description"
          },
          "description": "string - Detailed activity description",
          "cost": "number - Estimated cost",
          "safetyNote": "string - Safety considerations",
          "bookingRequired": "boolean - Advance booking needed",
          "timeOfDay": "string - morning|afternoon|evening|night"
        }
      ]
    }
  ],
  "estimatedCost": "number - Total estimated cost (REQUIRED)",
  "meta": {
    "generatedAt": "string - ISO timestamp",
    "generatedBy": "string - Generating service",
    "adjustedBy": "string - Last adjustment service", 
    "llmTraceId": "string - Debug trace ID",
    "version": "string - Schema version",
    "tags": ["string"] - Category tags
  }
}

IMPORTANT NOTES:
- Include either poiId OR poiSnapshot for each activity
- dayIndex must match the day the activity belongs to
- Categories must be from the predefined enum list
- All required fields must be present
- Coordinates should be decimal degrees format
- Cost estimates should be in the same currency as the budget
"""


@dataclass
class LLMConfig:
    """Configuration for LLM calls"""
    model: str = "gemini-2.5-flash-lite"
    temperature: float = 0.7
    top_p: float = 0.95
    max_output_tokens: int = 8192
    use_google_search: bool = False
    safety_settings_off: bool = True


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    success: bool
    content: str
    raw_response: Any
    error: Optional[str] = None
    search_used: bool = False


class VertexAILLMService:
    """Centralized service for Vertex AI LLM calls with configurable tools and system instructions"""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        
        if not self.project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT environment variable is required")
        
        try:
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location
            )
            logger.info(f"Initialized Vertex AI client for project: {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI client: {e}")
            raise RuntimeError(f"Vertex AI client initialization failed: {e}")
    
    def _create_safety_settings(self, safety_off: bool = True) -> List[types.SafetySetting]:
        """Create safety settings configuration"""
        if not safety_off:
            return []  # Use default safety settings
        
        return [
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="OFF"
            )
        ]
    
    def _create_tools(self, use_google_search: bool = False) -> List[types.Tool]:
        """Create tools configuration"""
        tools = []
        
        if use_google_search:
            tools.append(types.Tool(google_search=types.GoogleSearch()))
        
        return tools
    
    def _create_contents(self, system_instruction: str, user_message: str) -> List[types.Content]:
        """Create content structure for the LLM"""
        combined_message = f"{system_instruction}\n\n{user_message}"
        
        return [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=combined_message)
                ]
            )
        ]
    
    def generate_content(
        self,
        user_message: str,
        system_instruction: str,
        config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """
        Generate content using Vertex AI with configurable system instruction and tools
        
        Args:
            user_message: The user's input message
            system_instruction: Custom system instruction for this call
            config: LLM configuration (optional, uses defaults if not provided)
        
        Returns:
            LLMResponse object with standardized response structure
        """
        if config is None:
            config = LLMConfig()
        
        try:
            logger.info(f"Making LLM call with model: {config.model}, search: {config.use_google_search}")
            
            # Create contents
            contents = self._create_contents(system_instruction, user_message)
            
            # Create tools
            tools = self._create_tools(config.use_google_search)
            
            # Create safety settings
            safety_settings = self._create_safety_settings(config.safety_settings_off)
            
            # Create generation config
            generate_content_config = types.GenerateContentConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                max_output_tokens=config.max_output_tokens,
                tools=tools,
                safety_settings=safety_settings
            )
            
            # Make the API call
            response = self.client.models.generate_content(
                model=config.model,
                contents=contents,
                config=generate_content_config
            )
            
            content = response.text
            logger.info(f"LLM call successful, response length: {len(content)}")
            
            return LLMResponse(
                success=True,
                content=content,
                raw_response=response,
                search_used=config.use_google_search
            )
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return LLMResponse(
                success=False,
                content="",
                raw_response=None,
                error=str(e),
                search_used=config.use_google_search
            )
    
    def generate_content_stream(
        self,
        user_message: str,
        system_instruction: str,
        config: Optional[LLMConfig] = None
    ):
        """
        Generate content using streaming with Vertex AI
        
        Args:
            user_message: The user's input message
            system_instruction: Custom system instruction for this call
            config: LLM configuration (optional, uses defaults if not provided)
        
        Yields:
            Content chunks from the streaming response
        """
        if config is None:
            config = LLMConfig()
        
        try:
            logger.info(f"Making streaming LLM call with model: {config.model}, search: {config.use_google_search}")
            
            # Create contents
            contents = self._create_contents(system_instruction, user_message)
            
            # Create tools
            tools = self._create_tools(config.use_google_search)
            
            # Create safety settings
            safety_settings = self._create_safety_settings(config.safety_settings_off)
            
            # Create generation config
            generate_content_config = types.GenerateContentConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                max_output_tokens=config.max_output_tokens,
                tools=tools,
                safety_settings=safety_settings
            )
            
            # Make the streaming API call
            for chunk in self.client.models.generate_content_stream(
                model=config.model,
                contents=contents,
                config=generate_content_config
            ):
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Streaming LLM call failed: {e}")
            raise
    
    def get_itinerary_schema_json(self) -> Dict[str, Any]:
        """Get the full JSON schema for itinerary structure"""
        return ITINERARY_JSON_SCHEMA.copy()
    
    def get_itinerary_schema_docs(self) -> str:
        """Get human-readable schema documentation"""
        return ITINERARY_SCHEMA_DOCS
    
    def create_schema_enhanced_instruction(self, base_instruction: str, include_examples: bool = True) -> str:
        """
        Enhance a system instruction with the itinerary schema
        
        Args:
            base_instruction: The base system instruction
            include_examples: Whether to include example JSON structure
        
        Returns:
            Enhanced instruction with schema information
        """
        schema_section = f"\n\n=== ITINERARY JSON SCHEMA ===\n{ITINERARY_SCHEMA_DOCS}"
        
        if include_examples:
            example_section = """

=== EXAMPLE ACTIVITY STRUCTURE ===
```json
{
  "title": "Visit Golden Temple",
  "durationMins": 120,
  "category": "heritage",
  "dayIndex": 1,
  "poiSnapshot": {
    "name": "Golden Temple",
    "lat": 31.6200,
    "lng": 74.8765,
    "address": "Golden Temple Road, Amritsar"
  },
  "description": "Explore the spiritual heart of Sikhism",
  "cost": 0,
  "safetyNote": "Dress modestly and cover your head",
  "bookingRequired": false,
  "timeOfDay": "morning"
}
```

=== EXAMPLE COMPLETE ITINERARY ===
```json
{
  "title": "Delhi Weekend Getaway",
  "input": {
    "destination": "Delhi",
    "numDays": 2,
    "budget": 10000,
    "sliders": {"heritage": 80, "food": 70, "culture": 60}
  },
  "days": [
    {
      "dayIndex": 1,
      "activities": [/* activities array */]
    }
  ],
  "estimatedCost": 8500,
  "meta": {
    "generatedBy": "TripPlannerService",
    "version": "1.0"
  }
}
```"""
            schema_section += example_section
        
        return base_instruction + schema_section
    
    def validate_itinerary_structure(self, itinerary_json: str) -> Dict[str, Any]:
        """
        Basic validation of itinerary JSON structure
        
        Args:
            itinerary_json: JSON string to validate
            
        Returns:
            Dict with validation results
        """
        try:
            data = json.loads(itinerary_json)
            
            # Check required top-level fields
            required_fields = ["title", "input", "days", "estimatedCost", "meta"]
            missing_fields = [field for field in required_fields if field not in data]
            
            # Check input requirements
            input_required = ["destination", "numDays"]
            if "input" in data:
                missing_input = [field for field in input_required if field not in data["input"]]
            else:
                missing_input = input_required
            
            # Check days structure
            days_valid = True
            days_errors = []
            if "days" in data and isinstance(data["days"], list):
                for i, day in enumerate(data["days"]):
                    if not isinstance(day, dict):
                        days_errors.append(f"Day {i+1} is not an object")
                        continue
                    if "dayIndex" not in day:
                        days_errors.append(f"Day {i+1} missing dayIndex")
                    if "activities" not in day or not isinstance(day["activities"], list):
                        days_errors.append(f"Day {i+1} missing or invalid activities array")
            else:
                days_valid = False
                days_errors.append("days must be an array")
            
            return {
                "valid": len(missing_fields) == 0 and len(missing_input) == 0 and days_valid,
                "missing_fields": missing_fields,
                "missing_input_fields": missing_input,
                "days_errors": days_errors,
                "parsed_data": data
            }
            
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "error": f"Invalid JSON: {str(e)}",
                "parsed_data": None
            }


# Singleton instance
_llm_service_instance = None

def get_llm_service() -> VertexAILLMService:
    """Get singleton instance of LLM service"""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = VertexAILLMService()
    return _llm_service_instance


# Predefined System Instructions
class SystemInstructions:
    """Collection of predefined system instructions"""
    
    @staticmethod
    def smart_adjust_agent() -> str:
        base_instruction = (
            "You are a safe, helpful, and efficient travel itinerary assistant specialized in adjusting existing itineraries. Your primary goal is to modify the provided JSON itinerary according to the user's request. Prioritize strict adherence to user preferences and be creative with your suggestions for new activities.\n"
            "Respond as quickly as possible.\n"
            "=== RULES FOR MODIFICATION ===\n"
            "1. STRICTLY FOLLOW PREFERENCES: The most important rule is to adhere to the user's explicit request and implicit preferences. Analyze the existing itinerary to understand its theme (e.g., nature, history, relaxation) and ensure your changes are consistent.\n"
            "2. BE CREATIVE: When adding or replacing activities, suggest interesting, well-regarded alternatives that fit the trip's theme. Think beyond the most obvious tourist spots to provide unique value.\n"
            "3. WHAT TO CHANGE: ONLY modify the days[].activities[] array. You may reorder, remove, or add activities within this array to satisfy the user's request.\n"
            "4. WHAT NOT TO CHANGE: DO NOT change any trip-level input fields: input.destination, input.startDate, input.endDate, input.numDays, input.sliders, input.budget.\n"
            "5. COST: DO NOT modify estimatedCost unless you are adding or removing a significant cost item like a major tour or entry ticket.\n"
            "6. NEW ACTIVITIES: For any new activity, you MUST include either a poiId OR a poiSnapshot with at minimum {name, lat?, lng?}.\n\n"
            "=== SAFETY & EFFICIENCY ===\n"
            "- No harmful, illegal, or inappropriate activities\n"
            "- Consider local laws and customs\n"
            "- Respect cultural sensitivities\n"
            "- Ensure accessibility needs are met when mentioned\n"
            "- Use Google Search EFFICIENTLY to find real, current information for new activities. Do not spend excessive time on this step.\n\n"
            "=== OUTPUT FORMAT ===\n"
            "Return ONLY a valid JSON itinerary object following the schema below. "
            "Do not include explanations, markdown formatting, or any text outside the JSON."
            "Ensure all required fields are present and properly typed, and use appropriate activity categories from the predefined enum list."
        )
        
        schema_section = f"\n\n=== REQUIRED JSON SCHEMA ===\n{ITINERARY_SCHEMA_DOCS}"
        
        examples_section = """

=== ADJUSTMENT EXAMPLES ===

Example 1 - Adding an activity:
If user says "add a cooking class", add this structure:
```json
{
  "title": "Balinese Cooking Class",
  "durationMins": 180,
  "category": "culture",
  "dayIndex": 2,
  "poiSnapshot": {
    "name": "Paon Bali Cooking Class",
    "lat": -8.5069,
    "lng": 115.2625
  },
  "description": "Learn traditional Balinese cooking techniques",
  "cost": 350000,
  "bookingRequired": true,
  "timeOfDay": "morning"
}
```

Example 2 - Modifying activity details:
Keep the same structure but update specific fields like title, duration, or location.

Example 3 - Category mapping:
- Restaurants, street food, cooking classes → "food"
- Museums, temples, monuments → "heritage"  
- Bars, clubs, night markets → "nightlife"
- Parks, beaches, hiking → "nature"
- Zip-lining, diving, sports → "adventure"
- Spas, resorts, lounging → "leisure"
- Art galleries, performances, festivals → "culture"
- Markets, malls, boutiques → "shopping"

CRITICAL: Always preserve the original input object completely unchanged!"""
        
        return base_instruction + schema_section + examples_section
    
    @staticmethod
    def trip_planner() -> str:
        base_instruction = (
            "You are an expert travel planning assistant that creates detailed, personalized itineraries. Your primary objective is to generate a complete, high-quality itinerary that strictly adheres to user preferences, is creative, and is delivered rapidly.\n\n"
            "=== CORE OBJECTIVES ===\n"
            "1. STRICT ADHERENCE TO PREFERENCES: Prioritize and meticulously incorporate all user-specified preferences, interests, budget, and preference settings. Every element of the itinerary must align with these inputs.\n"
            "2. CREATIVITY & VALUE: Suggest unique, well-regarded activities and experiences that go beyond the obvious. Add local cultural insights and practical tips to enhance the user's trip.\n"
            "3. EFFICIENCY & SPEED: Generate the itinerary as quickly as possible. Use Google Search efficiently for necessary information (like opening hours, current availability, travel times) and avoid unnecessary delays. Aim for rapid, yet thorough, processing.\n\n"
            "=== ITINERARY GENERATION GUIDELINES ===\n"
            "1. Activities: Select and sequence activities logically for each day, considering the trip's theme and user interests. Include realistic travel times between activities (30-240 mins typically).\n"
            "2. Logistics: Factor in opening hours, proximity, and general feasibility. Distribute activities evenly across days where possible.\n"
            "3. Information: Provide accurate timing, location data (lat/lng) for all POIs, and realistic cost estimates in the local currency.\n"
            "4. Safety & Culture: Integrate safety considerations and relevant local cultural insights naturally.\n"
            "5. Verification: Use Google Search efficiently to verify current information. This includes verifying POIs, opening hours, and suggesting realistic cost estimates.\n\n"
            "=== OUTPUT REQUIREMENTS ===\n"
            "1. FORMAT: Return ONLY a valid JSON itinerary object that strictly follows the provided schema.\n"
            "2. COMPLETENESS: Include all required fields with correct data types.\n"
            "3. CONTENT: Use appropriate activity categories from the predefined enum. Ensure location data (lat/lng) is present for all POIs where available.\n"
            "4. NO EXTRA TEXT: Do not include any explanations, conversational text, markdown formatting, or text outside the JSON object."
        )
        
        schema_section = f"\n\n=== REQUIRED JSON SCHEMA ===\n{ITINERARY_SCHEMA_DOCS}"
        
        planning_examples = """

=== TRIP PLANNING EXAMPLES ===

Example activity distribution for 3-day trip:
Day 1: 3-4 activities (arrival day, lighter schedule)
Day 2: 4-5 activities (full exploration day)  
Day 3: 2-3 activities (departure day)

Example budget distribution:
- Accommodation: 40-50% of budget
- Food: 25-30% of budget  
- Activities: 15-20% of budget
- Transport: 5-10% of budget

Example preference mapping:
- High nature (80+): Parks, beaches, hiking, wildlife
- High nightlife (70+): Bars, clubs, night markets, live music
- High adventure (60+): Water sports, zip-lining, extreme activities
- High heritage (70+): Museums, temples, historical sites, monuments
- High culture (60+): Art galleries, performances, local festivals
- High food (80+): Cooking classes, food tours, local restaurants
- High leisure (70+): Spas, resorts, relaxing activities

Example activity structure:
```json
{
  "title": "Sunset at Tanah Lot Temple",
  "durationMins": 120,
  "category": "heritage",
  "dayIndex": 2,
  "poiSnapshot": {
    "name": "Tanah Lot Temple",
    "lat": -8.6211,
    "lng": 115.0868,
    "address": "Tabanan Regency, Bali"
  },
  "description": "Ancient Hindu temple perched on a rock formation",
  "cost": 60000,
  "safetyNote": "Be careful on wet rocks during high tide",
  "bookingRequired": false,
  "timeOfDay": "evening"
}
```"""
        
        return base_instruction + schema_section + planning_examples
    
    @staticmethod
    def chat_assistant() -> str:
        return (
            "You are a highly efficient travel assistant focused on providing quick, accurate, and actionable answers to travel planning questions.\n\n"
            "=== GOAL ===\n"
            "Deliver concise, helpful information with minimal delay. Get to the core of the user's query directly.\n\n"
            "=== GUIDELINES ===\n"
            "1. DIRECT ANSWERS: Address the user's question clearly and directly. Avoid lengthy introductions or unnecessary preamble.\n"
            "2. ACTIONABLE ADVICE: Provide practical, concrete recommendations and information that the user can use immediately.\n"
            "3. EFFICIENT INFORMATION GATHERING: Use Google Search rapidly when needed for current, specific details (e.g., opening hours, prices, travel times). Prioritize speed and relevance in search.\n"
            "4. CONCISE DETAILS: Include specific details (like names, locations, estimated times) only when they are essential to answering the question accurately and efficiently.\n"
            "5. CLARIFICATION: If a query is ambiguous, ask a brief, targeted clarifying question to get the necessary information as quickly as possible.\n\n"
            "=== RESPONSE STYLE ===\n"
            "- Be friendly but efficient. Focus on helpfulness without being overly verbose.\n"
            "- Avoid lengthy conversational tangents.\n"
            "- Prioritize delivering the answer promptly."
        )
    
    @staticmethod
    def custom(instruction: str) -> str:
        """Create a custom system instruction"""
        return instruction


smartAdjustInstruction = SystemInstructions