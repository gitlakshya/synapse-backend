#!/usr/bin/env python3
"""
Test the full API pipeline to identify where the 500 error occurs.
"""

import os
import sys
import traceback
import asyncio
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_api_pipeline():
    """Test the full API pipeline step by step"""
    try:
        load_dotenv()
        print("✅ Environment loaded")
        
        # 1. Test imports
        from app.routers.trip import PlanTripRequest, validate_auth_or_session
        from app.services.firestore_service import FirestoreService
        from app.services.itinerary_service import get_itinerary_service
        from app.dependencies import get_firestore_client
        print("✅ All imports successful")
        
        # 2. Test request model
        test_request_data = {
            "destination": "Tokyo",
            "days": 1,
            "budget": 10000,
            "startDate": "2024-04-15",
            "endDate": "2024-04-15",
            "preferences": {
                "heritage": 50,
                "culture": 50,
                "food": 50
            }
        }
        
        request = PlanTripRequest(**test_request_data)
        print("✅ Request model validation successful")
        
        # 3. Test dependencies
        fs = FirestoreService(get_firestore_client())
        print("✅ Firestore service created")
        
        itinerary_service = get_itinerary_service()
        print("✅ Itinerary service dependency resolved")
        
        # 4. Test auth validation (no token = anonymous)
        decoded_token = None  # Simulating no auth token
        user_id, session_id = await validate_auth_or_session(decoded_token, request.sessionId)
        print(f"✅ Auth validation successful - user_id: {user_id}, session_id: {session_id}")
        
        # 5. Test itinerary generation
        print("🧪 Testing itinerary generation...")
        
        itinerary_data = await itinerary_service.generate_itinerary(
            destination=request.destination,
            days=request.days,
            budget=request.budget,
            start_date=request.startDate,
            end_date=request.endDate,
            preferences=request.preferences,
            special_requirements=request.specialRequirements,
            session_id=session_id
        )
        print("✅ Itinerary generation successful")
        
        # 6. Test saving to Firestore
        print("🧪 Testing Firestore save...")
        
        try:
            itinerary_id = await itinerary_service.save_itinerary(
                itinerary_data=itinerary_data,
                user_id=user_id,
                session_id=session_id
            )
            print(f"✅ Firestore save successful, ID: {itinerary_id}")
        except Exception as save_error:
            print(f"❌ Firestore save error: {save_error}")
            # Use a mock ID for testing
            itinerary_id = f"mock_{session_id}_{int(asyncio.get_event_loop().time())}"
            print(f"Using mock ID: {itinerary_id}")
        
        # 7. Test response model with all required fields
        from app.routers.trip import PlanTripResponse
        from datetime import datetime, timezone
        
        processing_time = 2.5  # Mock processing time
        
        response_data = {
            "status": "success",
            "itineraryId": itinerary_id,
            "itinerary": itinerary_data,
            "processingTime": processing_time,
            "metadata": {
                "userId": user_id,
                "sessionId": session_id,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "llmUsed": True,
                "searchUsed": itinerary_data.get("meta", {}).get("searchUsed", False)
            }
        }
        
        response = PlanTripResponse(**response_data)
        print("✅ Response model validation successful")
        
        print(f"\n📋 Final Response:")
        print(f"Status: {response.status}")
        print(f"Itinerary ID: {response.itineraryId}")
        print(f"Session ID: {response.metadata.get('sessionId', 'Unknown')}")
        print(f"Itinerary title: {response.itinerary.get('title', 'Unknown')}")
        print(f"Processing time: {response.processingTime:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in API pipeline: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🧪 Full API Pipeline Test\n")
    success = asyncio.run(test_api_pipeline())
    
    if success:
        print("\n🎉 API pipeline test completed successfully!")
    else:
        print("\n💥 API pipeline test failed!")