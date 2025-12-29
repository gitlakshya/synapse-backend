import json
import re
import sys
import os

# Add the project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_json_recovery(malformed_json):
    """Test the enhanced JSON recovery strategies"""
    print(f"🔍 Testing JSON recovery for: {malformed_json[:100]}...")
    
    try:
        # Strategy 1: Remove markdown and find JSON boundaries
        content = malformed_json.strip()
        
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        
        if content.endswith('```'):
            content = content[:-3]
        
        content = content.strip()
        
        # Strategy 2: Look for complete JSON object with balanced braces
        brace_count = 0
        start_idx = -1
        end_idx = -1
        
        for i, char in enumerate(content):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    end_idx = i
                    break
        
        if start_idx != -1 and end_idx != -1:
            json_candidate = content[start_idx:end_idx + 1]
            try:
                result = json.loads(json_candidate)
                print("✅ Successfully recovered JSON using brace balancing")
                return result
            except:
                pass
        
        # Strategy 3: Try to find any valid JSON object pattern
        json_pattern = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL)
        matches = json_pattern.findall(content)
        
        for match in matches:
            try:
                candidate = json.loads(match)
                if isinstance(candidate, dict):
                    print("✅ Successfully recovered JSON using pattern matching")
                    return candidate
            except:
                continue
        
        # Strategy 4: Try to fix common JSON issues
        # Remove trailing commas
        content_fixed = re.sub(r',(\s*[}\]])', r'\1', content)
        # Fix unclosed quotes (basic attempt)
        if content_fixed.count('"') % 2 == 1:
            content_fixed += '"'
        
        try:
            result = json.loads(content_fixed)
            print("✅ Successfully recovered JSON using syntax fixes")
            return result
        except:
            pass
            
        print("❌ All JSON recovery attempts failed")
        return None
        
    except Exception as e:
        print(f"❌ JSON recovery failed: {e}")
        return None

# Test with the exact error case from the logs
malformed_response = '''```json
{
"title": "9-Day Nature and Adventure Ladakh Itinerary",
"input": {
"sessionId": "12345",
"destination": {'''

print("🧪 Testing JSON Recovery Strategies")
print("=" * 50)

result = test_json_recovery(malformed_response)
if result:
    print(f"📊 Recovered result: {json.dumps(result, indent=2)}")
else:
    print("🔄 Would return original itinerary as fallback")

print("\n✅ JSON recovery strategies implemented and ready for testing!")