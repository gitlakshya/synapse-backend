#!/usr/bin/env python3
"""
Direct test of the itinerary service to debug the 500 error.
"""

import os
import sys
import traceback
import asyncio
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_itinerary_service():
    """Test the itinerary service directly"""
    try:
        load_dotenv()
        print("✅ Environment loaded")
        
        # Import required modules
        from app.services.itinerary_service import ItineraryService
        print("✅ ItineraryService imported")
        
        # Create service instance
        service = ItineraryService()
        print(f"✅ ItineraryService created (using_mock: {getattr(service, 'using_mock', 'unknown')})")
        
        # Test parameters
        test_params = {
            "destination": "Tokyo",
            "days": 1,
            "budget": 10000,
            "start_date": "2024-04-15",
            "end_date": "2024-04-15",
            "preferences": {
                "heritage": 50,
                "culture": 50,
                "food": 50
            },
            "special_requirements": None,
            "session_id": "test-session-123"
        }
        
        print("🧪 Testing itinerary generation...")
        
        # Call the service
        result = await service.generate_itinerary(**test_params)
        
        print("✅ Itinerary generated successfully!")
        print(f"Title: {result.get('title', 'No title')}")
        print(f"Days: {len(result.get('days', []))}")
        print(f"Estimated cost: {result.get('estimatedCost', {}).get('total', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🧪 Direct Itinerary Service Test\n")
    success = asyncio.run(test_itinerary_service())
    
    if success:
        print("\n🎉 Direct test completed successfully!")
    else:
        print("\n💥 Direct test failed!")