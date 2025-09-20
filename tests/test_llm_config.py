#!/usr/bin/env python3
"""
Test LLM service configuration and basic functionality.
"""

import os
import sys
import traceback
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_llm_service():
    """Test basic LLM service functionality"""
    try:
        # Load environment variables
        load_dotenv()
        print("✅ Environment variables loaded")
        
        # Check for required environment variables
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if google_api_key:
            print(f"✅ GOOGLE_API_KEY found (length: {len(google_api_key)})")
        else:
            print("❌ GOOGLE_API_KEY not found")
            return False
        
        # Try to import the LLM service
        from app.services.llm_service import LLMService
        print("✅ LLMService imported successfully")
        
        # Try to create an instance
        llm_service = LLMService()
        print("✅ LLMService instance created")
        
        # Try a simple generation
        print("🧪 Testing simple content generation...")
        response = llm_service.generate_content(
            user_message="Generate a simple JSON object with just a title field containing 'test'",
            system_instruction="You are a helpful assistant. Return only valid JSON.",
            config={'max_output_tokens': 100}
        )
        
        if response.success:
            print(f"✅ Content generation successful!")
            print(f"Response: {response.content[:100]}...")
            return True
        else:
            print(f"❌ Content generation failed: {response.error}")
            return False
            
    except Exception as e:
        print(f"❌ Error during LLM service test: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🧪 Testing LLM Service Configuration\n")
    success = test_llm_service()
    
    if success:
        print("\n🎉 LLM service test completed successfully!")
    else:
        print("\n💥 LLM service test failed!")