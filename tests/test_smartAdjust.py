import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.smartAdjust import SmartAdjustAgent

itinerary = {
  "title": "Goa Long Weekend",
  "input": {
    "sessionId": "sess_06181101b6",
    "startDate": "",
    "endDate": "",
    "destination": "Goa",
    "days": 4,
    "budget": 20000,
    "specialRequirements":"",
    "preferences":{
        "nature": 90,
        "nightlife": 24,
        "adventure": 59,
        "leisure": 60,
        "heritage": 30
    }  
},
  "days": [
    {
      "dayIndex": 2,
      "activities": [
        {
          "title": "Beach Club Evening",
          "durationMins": 180,
          "category": "nightlife",
          "dayIndex": 2,
          "poiSnapshot": {
            "name": "Popular Beach Club",
            "lat": 15.491,
            "lng": 73.821
          },
          "safetyNote": "Please consume alcohol responsibly and arrange safe transportation."
        }
      ]
    }
  ],
  "estimatedCost": 20000,
  "meta": {
    "adjustedBy": "SmartAdjustAgent",
    "llmTraceId": "trace_abc123"
  }
}

userRequest = "We're a group of 3, a couple and a kid. We want to enjoy the nightlife and don't want it to be boring for our kid."
def vertex_ai():
    pass
    
def test_smartAdjust_result():
    print("DEBUG: Starting test")
    
    try:
        agent = SmartAdjustAgent()
        print("DEBUG: SmartAdjustAgent created successfully")
        
        response = agent.adjust_itinerary(itinerary, userRequest)
        print("DEBUG: adjust_itinerary completed")
        print(f"DEBUG: Response type: {type(response)}")
        print(f"DEBUG: Response: {response}")
        
    except Exception as e:
        print(f"DEBUG: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_smartAdjust_result()
    

