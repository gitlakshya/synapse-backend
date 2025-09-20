#!/usr/bin/env python3
"""
Demo script showing the capabilities of the centralized LLM service.

This script demonstrates:
1. Basic LLM calls without Google Search
2. LLM calls with Google Search integration
3. Different system instructions (predefined and custom)
4. Different model configurations
5. Error handling and response structure
"""

import sys
import os
import asyncio
import json

# Add the project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import (
    get_llm_service, 
    LLMConfig, 
    SystemInstructions
)

def demo_basic_chat():
    """Demo basic chat functionality without Google Search"""
    print("=" * 60)
    print("🤖 DEMO 1: Basic Chat (No Google Search)")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    config = LLMConfig(
        temperature=0.7,
        use_google_search=False
    )
    
    response = llm_service.generate_content(
        user_message="What are the best places to visit in Paris?",
        system_instruction=SystemInstructions.chat_assistant(),
        config=config
    )
    
    print(f"Success: {response.success}")
    print(f"Search Used: {response.search_used}")
    print(f"Response:\n{response.content}\n")


def demo_search_enhanced_chat():
    """Demo chat with Google Search integration"""
    print("=" * 60)
    print("🔍 DEMO 2: Chat with Google Search")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    config = LLMConfig(
        temperature=0.7,
        use_google_search=True
    )
    
    response = llm_service.generate_content(
        user_message="What are the current opening hours for the Louvre Museum in Paris?",
        system_instruction=SystemInstructions.chat_assistant(),
        config=config
    )
    
    print(f"Success: {response.success}")
    print(f"Search Used: {response.search_used}")
    print(f"Response:\n{response.content}\n")


def demo_trip_planning():
    """Demo trip planning system instruction"""
    print("=" * 60)
    print("✈️ DEMO 3: Trip Planning Assistant")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    config = LLMConfig(
        temperature=0.8,
        use_google_search=True
    )
    
    response = llm_service.generate_content(
        user_message="Plan a 3-day itinerary for Tokyo focusing on technology and anime culture with a budget of $500",
        system_instruction=SystemInstructions.trip_planner(),
        config=config
    )
    
    print(f"Success: {response.success}")
    print(f"Search Used: {response.search_used}")
    print(f"Response:\n{response.content}\n")


def demo_custom_system_instruction():
    """Demo custom system instruction"""
    print("=" * 60)
    print("🎨 DEMO 4: Custom System Instruction")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    custom_instruction = SystemInstructions.custom(
        "You are a helpful restaurant critic who provides detailed reviews. "
        "Always mention specific dishes, ambiance, and pricing when reviewing restaurants. "
        "Use Google Search to find current information about restaurants."
    )
    
    config = LLMConfig(
        temperature=0.6,
        use_google_search=True
    )
    
    response = llm_service.generate_content(
        user_message="Review the best sushi restaurants in New York City",
        system_instruction=custom_instruction,
        config=config
    )
    
    print(f"Success: {response.success}")
    print(f"Search Used: {response.search_used}")
    print(f"Response:\n{response.content}\n")


def demo_smartadjust_integration():
    """Demo SmartAdjust functionality using the centralized service with comprehensive schema"""
    print("=" * 60)
    print("🔧 DEMO 5: SmartAdjust Integration with JSON Schema")
    print("=" * 60)
    
    from app.services.smartAdjust import SmartAdjustAgent
    
    # Sample itinerary with proper schema structure
    sample_itinerary = {
        "title": "Bangkok Adventure",
        "input": {
            "sessionId": "sess_demo_123",
            "destination": "Bangkok",
            "startDate": "2024-03-15",
            "endDate": "2024-03-17",
            "numDays": 3,
            "budget": 15000,
            "sliders": {"culture": 80, "food": 90, "nightlife": 30, "heritage": 70}
        },
        "days": [
            {
                "dayIndex": 1,
                "activities": [
                    {
                        "title": "Visit Grand Palace",
                        "durationMins": 120,
                        "category": "heritage",
                        "dayIndex": 1,
                        "poiSnapshot": {
                            "name": "Grand Palace",
                            "lat": 13.7508,
                            "lng": 100.4914
                        },
                        "cost": 500,
                        "timeOfDay": "morning"
                    }
                ]
            }
        ],
        "estimatedCost": 500,
        "meta": {
            "generatedBy": "TripPlanner",
            "version": "1.0"
        }
    }
    
    agent = SmartAdjustAgent()
    result = agent.adjust_itinerary(
        current_itinerary=sample_itinerary,
        user_request="Add more street food experiences and expand this to cover all 3 days with Thai cooking classes"
    )
    
    print(f"Adjustment Result Preview:\n{result[:800]}...\n")


def demo_schema_validation():
    """Demo JSON schema validation capabilities"""
    print("=" * 60)
    print("🔍 DEMO 6: JSON Schema Validation")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    # Show schema documentation
    print("📋 Available Schema Features:")
    print("  • Comprehensive JSON schema for itinerary structure")
    print("  • Validation of required fields and data types")
    print("  • Activity categorization with predefined enums")
    print("  • Location data with lat/lng coordinates")
    print("  • Cost estimation and budget tracking")
    print("  • Metadata for tracing and versioning\n")
    
    # Test validation with incomplete data
    incomplete_json = '{"title": "Test", "input": {"destination": "Paris"}, "days": []}'
    validation = llm_service.validate_itinerary_structure(incomplete_json)
    
    print(f"❌ Validation Test - Incomplete Data:")
    print(f"Valid: {validation['valid']}")
    print(f"Missing fields: {validation.get('missing_fields', [])}")
    print(f"Missing input fields: {validation.get('missing_input_fields', [])}")
    print()
    
    # Show schema helper methods
    print("🛠️ Available Schema Helper Methods:")
    print("  • get_itinerary_schema_json() - Full JSON schema object")
    print("  • get_itinerary_schema_docs() - Human-readable documentation")
    print("  • validate_itinerary_structure() - JSON validation")
    print("  • create_schema_enhanced_instruction() - Schema-aware instructions")


def demo_error_handling():
    """Demo error handling"""
    print("=" * 60)
    print("⚠️ DEMO 7: Error Handling & Validation")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    # Try with an invalid configuration to show error handling
    config = LLMConfig(
        model="invalid-model-name",  # This should cause an error
        temperature=0.7
    )
    
    response = llm_service.generate_content(
        user_message="This should fail",
        system_instruction=SystemInstructions.chat_assistant(),
        config=config
    )
    
    print(f"Success: {response.success}")
    print(f"Error handled gracefully: {response.error is not None}")
    if response.error:
        print(f"Error message: {response.error[:100]}...")


def main():
    """Run all demos"""
    print("🚀 LLM Service Centralization Demo")
    print("This demo showcases the centralized LLM service with comprehensive JSON schema\n")
    
    try:
        demo_basic_chat()
        demo_search_enhanced_chat()
        demo_trip_planning()
        demo_custom_system_instruction()
        demo_smartadjust_integration()
        demo_schema_validation()
        demo_error_handling()
        
        print("=" * 60)
        print("✅ All demos completed successfully!")
        print("=" * 60)
        print("\n🎯 Key Features Demonstrated:")
        print("  ✅ Centralized LLM service with singleton pattern")
        print("  ✅ Google Search integration for real-time data")
        print("  ✅ Comprehensive JSON schema for itineraries")
        print("  ✅ Predefined system instructions for different use cases")
        print("  ✅ JSON validation and error handling")
        print("  ✅ SmartAdjust integration with schema compliance")
        print("  ✅ Configurable LLM parameters and safety settings")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()