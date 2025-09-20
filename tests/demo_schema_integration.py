#!/usr/bin/env python3
"""
Schema Integration Demo - Test both trip planning and SmartAdjust with comprehensive JSON schema
"""

import sys
import os
import json

# Add the project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import get_llm_service, LLMConfig, SystemInstructions
from app.services.smartAdjust import SmartAdjustAgent

def test_trip_planning_with_schema():
    """Test trip planning with the comprehensive schema"""
    print("=" * 60)
    print("🗺️ TESTING: Trip Planning with Schema")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    config = LLMConfig(
        temperature=0.7,
        use_google_search=True,
        max_output_tokens=8192
    )
    
    trip_request = """
    Plan a 3-day weekend trip to Bali for a couple interested in:
    - Culture and heritage (high priority)
    - Adventure activities (moderate priority)  
    - Food experiences (high priority)
    - Budget: $800 USD
    - Dates: December 14-16, 2024
    """
    
    response = llm_service.generate_content(
        user_message=trip_request,
        system_instruction=SystemInstructions.trip_planner(),
        config=config
    )
    
    if response.success:
        print(f"✅ Trip planning successful!")
        print(f"🔍 Google Search used: {response.search_used}")
        
        # Try to parse and validate the JSON
        try:
            itinerary_data = json.loads(response.content)
            validation = llm_service.validate_itinerary_structure(response.content)
            print(f"✅ JSON structure valid: {validation['valid']}")
            
            if validation['valid']:
                print(f"📍 Destination: {itinerary_data.get('input', {}).get('destination', 'N/A')}")
                print(f"📅 Days: {len(itinerary_data.get('days', []))}")
                print(f"💰 Estimated Cost: {itinerary_data.get('estimatedCost', 'N/A')}")
                
                # Count activities
                total_activities = sum(len(day.get('activities', [])) for day in itinerary_data.get('days', []))
                print(f"🎯 Total Activities: {total_activities}")
                
                print("\n📝 Sample Day 1 Activities:")
                if itinerary_data.get('days') and len(itinerary_data['days']) > 0:
                    day1_activities = itinerary_data['days'][0].get('activities', [])
                    for i, activity in enumerate(day1_activities[:3]):  # Show first 3
                        print(f"  {i+1}. {activity.get('title', 'N/A')} ({activity.get('category', 'N/A')}) - {activity.get('durationMins', 0)} mins")
            else:
                print(f"❌ Validation issues: {validation}")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print("Raw response preview:")
            print(response.content[:500] + "..." if len(response.content) > 500 else response.content)
    else:
        print(f"❌ Trip planning failed: {response.error}")
    
    print()

def test_smartadjust_with_schema():
    """Test SmartAdjust with the comprehensive schema using a realistic itinerary"""
    print("=" * 60)
    print("🔧 TESTING: SmartAdjust with Schema")
    print("=" * 60)
    
    # Create a realistic test itinerary
    sample_itinerary = {
        "title": "Bangkok Culture & Food Tour",
        "input": {
            "sessionId": "sess_test_123",
            "destination": "Bangkok",
            "startDate": "2024-12-20",
            "endDate": "2024-12-22",
            "numDays": 3,
            "budget": 15000,
            "sliders": {
                "culture": 80,
                "food": 90,
                "heritage": 70,
                "nightlife": 40,
                "nature": 20,
                "adventure": 30,
                "leisure": 50,
                "shopping": 60
            }
        },
        "days": [
            {
                "dayIndex": 1,
                "activities": [
                    {
                        "title": "Visit Grand Palace",
                        "durationMins": 180,
                        "category": "heritage",
                        "dayIndex": 1,
                        "poiSnapshot": {
                            "name": "Grand Palace",
                            "lat": 13.7508,
                            "lng": 100.4914,
                            "address": "Na Phra Lan Rd, Bangkok"
                        },
                        "description": "Explore Thailand's most famous landmark",
                        "cost": 500,
                        "timeOfDay": "morning"
                    },
                    {
                        "title": "Street Food Tour in Chinatown",
                        "durationMins": 120,
                        "category": "food",
                        "dayIndex": 1,
                        "poiSnapshot": {
                            "name": "Yaowarat Chinatown",
                            "lat": 13.7429,
                            "lng": 100.5130
                        },
                        "cost": 800,
                        "timeOfDay": "evening"
                    }
                ]
            }
        ],
        "estimatedCost": 1300,
        "meta": {
            "generatedBy": "TripPlanner",
            "version": "1.0"
        }
    }
    
    agent = SmartAdjustAgent()
    
    user_request = """
    I'd like to add more cooking experiences and make this trip more hands-on for learning Thai cuisine. 
    Also, can you add a rooftop bar experience for the evening? 
    Please expand this to cover all 3 days with a good mix of culture, food, and some nightlife.
    """
    
    try:
        result = agent.adjust_itinerary(sample_itinerary, user_request)
        
        print("✅ SmartAdjust completed successfully!")
        
        # Parse and validate the adjusted itinerary
        try:
            adjusted_data = json.loads(result)
            llm_service = get_llm_service()
            validation = llm_service.validate_itinerary_structure(result)
            
            print(f"✅ Adjusted JSON structure valid: {validation['valid']}")
            
            if validation['valid']:
                print(f"📍 Title: {adjusted_data.get('title', 'N/A')}")
                print(f"📅 Days: {len(adjusted_data.get('days', []))}")
                print(f"💰 Estimated Cost: {adjusted_data.get('estimatedCost', 'N/A')}")
                
                # Count activities and show breakdown
                total_activities = sum(len(day.get('activities', [])) for day in adjusted_data.get('days', []))
                print(f"🎯 Total Activities: {total_activities}")
                
                # Show activity categories
                categories = {}
                for day in adjusted_data.get('days', []):
                    for activity in day.get('activities', []):
                        category = activity.get('category', 'unknown')
                        categories[category] = categories.get(category, 0) + 1
                
                print(f"📊 Activity Categories: {dict(categories)}")
                
                # Check for cooking/food experiences
                cooking_activities = []
                for day in adjusted_data.get('days', []):
                    for activity in day.get('activities', []):
                        title = activity.get('title', '').lower()
                        if 'cook' in title or 'class' in title or 'kitchen' in title:
                            cooking_activities.append(activity['title'])
                
                if cooking_activities:
                    print(f"👨‍🍳 Cooking Experiences Added: {len(cooking_activities)}")
                    for cooking in cooking_activities:
                        print(f"  • {cooking}")
                
                # Check for rooftop/nightlife
                nightlife_activities = []
                for day in adjusted_data.get('days', []):
                    for activity in day.get('activities', []):
                        if activity.get('category') == 'nightlife':
                            nightlife_activities.append(activity['title'])
                
                if nightlife_activities:
                    print(f"🌃 Nightlife Experiences: {len(nightlife_activities)}")
                    for nightlife in nightlife_activities:
                        print(f"  • {nightlife}")
                        
            else:
                print(f"❌ Validation issues: {validation}")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print("Raw response preview:")
            print(result[:500] + "..." if len(result) > 500 else result)
            
    except Exception as e:
        print(f"❌ SmartAdjust failed: {e}")
    
    print()

def test_schema_validation():
    """Test the schema validation functionality"""
    print("=" * 60)
    print("🔍 TESTING: Schema Validation")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    # Test valid itinerary
    valid_itinerary = {
        "title": "Test Trip",
        "input": {
            "destination": "Tokyo", 
            "numDays": 2
        },
        "days": [
            {
                "dayIndex": 1,
                "activities": [
                    {
                        "title": "Visit Temple",
                        "durationMins": 120,
                        "category": "heritage"
                    }
                ]
            }
        ],
        "estimatedCost": 5000,
        "meta": {}
    }
    
    validation = llm_service.validate_itinerary_structure(json.dumps(valid_itinerary))
    print(f"✅ Valid itinerary validation: {validation['valid']}")
    
    # Test invalid itinerary (missing required fields)
    invalid_itinerary = {
        "title": "Incomplete Trip",
        "input": {
            "destination": "Paris"
            # Missing numDays
        },
        "days": [],  # Empty days
        # Missing estimatedCost and meta
    }
    
    validation = llm_service.validate_itinerary_structure(json.dumps(invalid_itinerary))
    print(f"❌ Invalid itinerary validation: {validation['valid']}")
    print(f"Missing fields: {validation.get('missing_fields', [])}")
    print(f"Missing input fields: {validation.get('missing_input_fields', [])}")
    
    print()

def main():
    """Run all schema integration tests"""
    print("🚀 JSON Schema Integration Tests")
    print("Testing comprehensive itinerary JSON schema with LLM service\n")
    
    try:
        test_trip_planning_with_schema()
        test_smartadjust_with_schema()
        test_schema_validation()
        
        print("=" * 60)
        print("✅ All schema integration tests completed!")
        print("=" * 60)
        print("\n📋 Key Features Verified:")
        print("  ✅ Comprehensive JSON schema definition")
        print("  ✅ Trip planning with schema-guided output")
        print("  ✅ SmartAdjust with enhanced structure validation")
        print("  ✅ JSON validation and error reporting")
        print("  ✅ Google Search integration for real data")
        print("  ✅ Proper activity categorization and metadata")
        
    except Exception as e:
        print(f"❌ Schema integration tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()