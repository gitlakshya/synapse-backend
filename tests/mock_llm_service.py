#!/usr/bin/env python3
"""
Mock LLM service for testing purposes when API keys are not available.
"""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MockLLMResponse:
    """Mock response from LLM service"""
    success: bool
    content: str
    error: Optional[str] = None
    search_used: bool = False

class MockLLMService:
    """Mock LLM service that returns sample responses for testing"""
    
    def __init__(self):
        self.sample_itinerary = {
            "title": "Tokyo 1-Day Cultural Experience",
            "input": {
                "sessionId": "mock-session-123",
                "destination": "Tokyo",
                "startDate": "2024-04-15",
                "endDate": "2024-04-15",
                "numDays": 1,
                "budget": 10000,
                "preferences": {
                    "heritage": 50,
                    "culture": 50,
                    "food": 50
                }
            },
            "days": [
                {
                    "day": 1,
                    "date": "2024-04-15",
                    "activities": [
                        {
                            "time": "09:00",
                            "duration": 120,
                            "title": "Senso-ji Temple Visit",
                            "description": "Explore Tokyo's oldest temple in Asakusa district",
                            "category": "heritage",
                            "location": {
                                "name": "Senso-ji Temple",
                                "address": "2 Chome-3-1 Asakusa, Taito City, Tokyo",
                                "coordinates": {"lat": 35.7148, "lng": 139.7967}
                            },
                            "cost": {"amount": 0, "currency": "JPY", "description": "Free admission"},
                            "tips": ["Visit early to avoid crowds", "Wear comfortable walking shoes"]
                        },
                        {
                            "time": "12:30",
                            "duration": 90,
                            "title": "Traditional Lunch",
                            "description": "Authentic Japanese meal at local restaurant",
                            "category": "food",
                            "location": {
                                "name": "Daikokuya Tempura Restaurant",
                                "address": "1 Chome-38-10 Asakusa, Taito City, Tokyo",
                                "coordinates": {"lat": 35.7136, "lng": 139.7944}
                            },
                            "cost": {"amount": 2500, "currency": "JPY", "description": "Tempura set meal"},
                            "tips": ["Famous for traditional tempura", "Cash only"]
                        },
                        {
                            "time": "15:00",
                            "duration": 150,
                            "title": "Tokyo National Museum",
                            "description": "Discover Japanese art and cultural artifacts",
                            "category": "culture",
                            "location": {
                                "name": "Tokyo National Museum",
                                "address": "13-9 Uenokoen, Taito City, Tokyo",
                                "coordinates": {"lat": 35.7188, "lng": 139.7760}
                            },
                            "cost": {"amount": 1000, "currency": "JPY", "description": "General admission"},
                            "tips": ["Allow 2-3 hours for visit", "Audio guide available"]
                        }
                    ]
                }
            ],
            "estimatedCost": {
                "total": 8500,
                "currency": "JPY",
                "breakdown": {
                    "activities": 1000,
                    "food": 2500,
                    "transport": 1000,
                    "accommodation": 4000
                }
            },
            "meta": {
                "generatedAt": "2024-04-15T10:00:00Z",
                "searchUsed": False,
                "version": "1.0",
                "preferences": {
                    "heritage": 50,
                    "culture": 50,
                    "food": 50
                }
            }
        }
    
    def generate_content(self, user_message: str, system_instruction: str, config: Dict[str, Any]) -> MockLLMResponse:
        """Generate mock content for testing"""
        try:
            logger.info(f"Mock LLM generating content for: {user_message[:100]}...")
            
            # Return the sample itinerary as JSON
            content = json.dumps(self.sample_itinerary, indent=2)
            
            return MockLLMResponse(
                success=True,
                content=content,
                search_used=False
            )
        except Exception as e:
            logger.error(f"Mock LLM error: {e}")
            return MockLLMResponse(
                success=False,
                content="",
                error=str(e)
            )
    
    def validate_itinerary_structure(self, itinerary_json: str) -> Dict[str, Any]:
        """Mock validation - always returns valid"""
        return {
            "valid": True,
            "errors": [],
            "warnings": []
        }