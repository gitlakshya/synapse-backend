"""
Test script to verify the smartAdjust fix works correctly
Tests that await properly returns a dict, not a coroutine
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_adjust_itinerary():
    """Test the adjust_itinerary method returns a proper dict"""
    print("🧪 Testing SmartAdjust fix...")
    
    # Mock itinerary
    test_itinerary = {
        "title": "Test Trip",
        "destination": {"name": "Paris"},
        "days": [
            {
                "dayNumber": 1,
                "date": "2025-11-10",
                "activities": []
            }
        ]
    }
    
    try:
        from app.services.smartAdjust import SmartAdjustAgent
        
        agent = SmartAdjustAgent()
        
        print("📞 Calling adjust_itinerary with await...")
        result = await agent.adjust_itinerary(
            current_itinerary=test_itinerary,
            user_request="Add a visit to the Eiffel Tower"
        )
        
        # Verify the result is a dict, not a coroutine
        print(f"✅ Result type: {type(result)}")
        
        if isinstance(result, dict):
            print("✅ Result is a dictionary (not a coroutine)")
            print(f"✅ Has .copy() method: {hasattr(result, 'copy')}")
            
            # Test the copy method that was failing
            try:
                copied = result.copy()
                print("✅ Successfully called .copy() on result")
                print(f"✅ Copy type: {type(copied)}")
                return True
            except Exception as e:
                print(f"❌ Failed to copy result: {e}")
                return False
        else:
            print(f"❌ Result is {type(result)}, not a dict!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing SmartAdjust Fix")
    print("=" * 60)
    
    success = asyncio.run(test_adjust_itinerary())
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Fix is working correctly.")
    else:
        print("❌ Tests failed! Check the errors above.")
    print("=" * 60)
