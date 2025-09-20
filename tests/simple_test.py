#!/usr/bin/env python3
"""
Simple test to check server connectivity and basic endpoint response.
"""

import requests
import json
import time

def test_basic_connectivity():
    """Test basic server connectivity and endpoint response."""
    try:
        # Test health endpoint
        print("🩺 Testing health endpoint...")
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Server is running!")
        else:
            print(f"❌ Health check failed with status: {response.status_code}")
            return False
        
        # Test the plan trip endpoint with minimal payload
        print("\n🚀 Testing /plantrip endpoint...")
        test_payload = {
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
        
        print(f"Making request to /plantrip with payload: {json.dumps(test_payload, indent=2)}")
        
        response = requests.post(
            "http://localhost:8000/api/v1/plantrip",
            json=test_payload,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("\n✅ Got successful response!")
                print(f"Response type: {type(data)}")
                print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Print the raw response structure
                print(f"\n📝 Raw response:\n{json.dumps(data, indent=2)}")
                
                return True
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Raw response text: {response.text}")
                return False
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response text: {response.text}")
            return False
            
    except requests.ConnectionError:
        print("🔌 Connection error - is the server running on localhost:8000?")
        return False
    except requests.Timeout:
        print("⏰ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Simple connectivity test\n")
    success = test_basic_connectivity()
    
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")