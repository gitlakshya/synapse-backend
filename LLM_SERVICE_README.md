# LLM Service Documentation

## Overview

The centralized LLM service provides a unified interface for all AI/LLM interactions in the Synapse Backend. It standardizes Vertex AI integration, Google Search tool usage, and system instruction management.

## Architecture

```
app/services/llm_service.py
├── VertexAILLMService (Main service class)
├── LLMConfig (Configuration dataclass)
├── LLMResponse (Standardized response)
├── SystemInstructions (Predefined instructions)
└── get_llm_service() (Singleton factory)
```

## Quick Start

### Basic Usage

```python
from app.services.llm_service import get_llm_service, SystemInstructions

# Get service instance
llm_service = get_llm_service()

# Make a simple call
response = llm_service.generate_content(
    user_message="What are the best restaurants in Tokyo?",
    system_instruction=SystemInstructions.chat_assistant()
)

print(response.content)
```

### With Google Search

```python
from app.services.llm_service import get_llm_service, LLMConfig, SystemInstructions

llm_service = get_llm_service()

# Enable Google Search
config = LLMConfig(use_google_search=True)

response = llm_service.generate_content(
    user_message="What are the current opening hours for the Tokyo National Museum?",
    system_instruction=SystemInstructions.chat_assistant(),
    config=config
)

print(f"Search was used: {response.search_used}")
print(response.content)
```

### Custom System Instructions

```python
from app.services.llm_service import get_llm_service, SystemInstructions

llm_service = get_llm_service()

custom_instruction = SystemInstructions.custom(
    "You are a helpful restaurant critic. Always mention specific dishes and pricing."
)

response = llm_service.generate_content(
    user_message="Review the best pizza places in New York",
    system_instruction=custom_instruction
)
```

## Configuration Options

### LLMConfig Parameters

```python
@dataclass
class LLMConfig:
    model: str = "gemini-2.5-flash-lite"           # Vertex AI model name
    temperature: float = 0.7                       # Creativity (0.0-1.0)
    top_p: float = 0.95                           # Nucleus sampling
    max_output_tokens: int = 8192                 # Maximum response length
    use_google_search: bool = False               # Enable Google Search tool
    safety_settings_off: bool = True              # Disable safety filters
```

### Example Configurations

```python
# Conservative/Factual
factual_config = LLMConfig(
    temperature=0.1,
    use_google_search=True
)

# Creative/Conversational
creative_config = LLMConfig(
    temperature=0.9,
    max_output_tokens=4096
)

# Search-Enhanced
search_config = LLMConfig(
    use_google_search=True,
    temperature=0.6
)
```

## Predefined System Instructions

### Available Instructions

1. **`SystemInstructions.smart_adjust_agent()`**
   - For itinerary adjustment tasks
   - Includes safety guardrails and JSON formatting rules

2. **`SystemInstructions.trip_planner()`**
   - For creating travel itineraries
   - Emphasizes practical considerations and local insights

3. **`SystemInstructions.chat_assistant()`**
   - For general travel Q&A
   - Conversational and helpful tone

4. **`SystemInstructions.custom(instruction)`**
   - For custom use cases
   - Pass any custom instruction string

### Example Usage

```python
# Using predefined instructions
response = llm_service.generate_content(
    user_message="Plan a 3-day trip to Paris",
    system_instruction=SystemInstructions.trip_planner()
)

# Using custom instructions
custom_system = SystemInstructions.custom(
    "You are a budget travel expert. Always suggest affordable options."
)
response = llm_service.generate_content(
    user_message="Plan a budget trip to Europe",
    system_instruction=custom_system
)
```

## Response Structure

### LLMResponse Object

```python
@dataclass
class LLMResponse:
    success: bool                    # True if call succeeded
    content: str                     # Generated text content
    raw_response: Any               # Full Vertex AI response object
    error: Optional[str] = None     # Error message if failed
    search_used: bool = False       # Whether Google Search was used
```

### Error Handling

```python
response = llm_service.generate_content(
    user_message="Your message",
    system_instruction=SystemInstructions.chat_assistant()
)

if response.success:
    print(f"Response: {response.content}")
    if response.search_used:
        print("Response enhanced with Google Search data")
else:
    print(f"Error: {response.error}")
```

## Integration Examples

### SmartAdjust Service

```python
class SmartAdjustAgent:
    def __init__(self):
        self.llm_service = get_llm_service()

    def adjust_itinerary(self, itinerary, request):
        config = LLMConfig(
            use_google_search=True,
            temperature=0.7
        )
        
        response = self.llm_service.generate_content(
            user_message=f"Adjust this itinerary: {json.dumps(itinerary)}\nRequest: {request}",
            system_instruction=SystemInstructions.smart_adjust_agent(),
            config=config
        )
        
        return response.content
```

### Chat Router

```python
@router.post("/chat")
async def chat(request: ChatRequest):
    llm_service = get_llm_service()
    
    config = LLMConfig(
        use_google_search=request.use_search,
        temperature=0.7
    )
    
    response = llm_service.generate_content(
        user_message=request.query,
        system_instruction=SystemInstructions.chat_assistant(),
        config=config
    )
    
    return {
        "response": response.content,
        "search_used": response.search_used
    }
```

## Streaming Support

For real-time responses, use the streaming interface:

```python
def stream_response():
    llm_service = get_llm_service()
    
    for chunk in llm_service.generate_content_stream(
        user_message="Tell me about Tokyo",
        system_instruction=SystemInstructions.chat_assistant()
    ):
        print(chunk, end="", flush=True)
```

## Environment Setup

### Required Environment Variables

```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
VERTEX_AI_LOCATION=us-central1  # Optional, defaults to us-central1
```

### Service Account Permissions

Ensure your service account has these IAM roles:
- `roles/aiplatform.user` - For Vertex AI access
- `roles/cloudsearch.admin` - For Google Search tool (if used)

## Best Practices

### 1. Configuration Management

```python
# Define configs for different use cases
CONFIGS = {
    "factual": LLMConfig(temperature=0.1, use_google_search=True),
    "creative": LLMConfig(temperature=0.9),
    "balanced": LLMConfig(temperature=0.7, use_google_search=True),
}

response = llm_service.generate_content(
    user_message="Your message",
    system_instruction=SystemInstructions.chat_assistant(),
    config=CONFIGS["factual"]
)
```

### 2. Error Handling

```python
def safe_llm_call(user_message, system_instruction, config=None):
    try:
        llm_service = get_llm_service()
        response = llm_service.generate_content(
            user_message=user_message,
            system_instruction=system_instruction,
            config=config
        )
        
        if not response.success:
            logger.error(f"LLM call failed: {response.error}")
            return "Sorry, I couldn't process your request."
        
        return response.content
        
    except Exception as e:
        logger.error(f"LLM service error: {e}")
        return "Sorry, there was a technical issue."
```

### 3. Logging and Monitoring

```python
import logging

logger = logging.getLogger(__name__)

response = llm_service.generate_content(
    user_message=user_message,
    system_instruction=system_instruction,
    config=config
)

logger.info(f"LLM call: success={response.success}, search_used={response.search_used}")
```

## Migration Guide

### From SmartAdjust (Old)

**Before:**
```python
# Direct genai client usage
client = genai.Client(vertexai=True, project=PROJECT_ID)
response = client.models.generate_content(...)
```

**After:**
```python
# Centralized service
llm_service = get_llm_service()
response = llm_service.generate_content(
    user_message="...",
    system_instruction=SystemInstructions.smart_adjust_agent()
)
```

### Benefits of Migration

1. **Standardized Configuration**: Consistent LLM settings across all services
2. **Error Handling**: Unified error handling and response structure
3. **Google Search Integration**: Easy to enable/disable search enhancement
4. **System Instructions**: Reusable, tested instruction templates
5. **Monitoring**: Centralized logging and response tracking
6. **Maintainability**: Single point of configuration for all LLM calls

## Testing

Run the demo script to see all capabilities:

```bash
python demo_llm_service.py
```

Run the SmartAdjust test to verify integration:

```bash
python -m pytest tests/test_smartAdjust.py -v
```

## Troubleshooting

### Common Issues

1. **Authentication Error**
   - Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account JSON
   - Check service account has required IAM permissions

2. **Model Not Found**
   - Verify model name in `LLMConfig.model`
   - Check available models in your Vertex AI project

3. **Search Tool Errors**
   - Ensure Google Search API is enabled in your project
   - Verify service account has `cloudsearch.admin` role

4. **Rate Limiting**
   - Implement exponential backoff for production usage
   - Consider request batching for high-volume scenarios

### Debug Mode

Enable debug logging to see detailed API calls:

```python
import logging
logging.getLogger('app.services.llm_service').setLevel(logging.DEBUG)
```

## Future Enhancements

- [ ] Conversation memory/context management
- [ ] Response caching for identical requests
- [ ] A/B testing framework for different configurations
- [ ] Metrics and analytics dashboard
- [ ] Multi-model support (Claude, GPT-4, etc.)
- [ ] Custom tool integration beyond Google Search