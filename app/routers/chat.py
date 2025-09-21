from fastapi import APIRouter, Request, HTTPException, Response
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.llm_service import get_llm_service, LLMConfig, SystemInstructions

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    query: str
    use_search: Optional[bool] = False
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    status: str
    query: str
    response: str
    search_used: bool
    session_id: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, response: Response):
    """
    Chat endpoint using centralized LLM service with optional Google Search.
    """
    try:
        llm_service = get_llm_service()
        
        # Configure LLM with optional Google Search
        config = LLMConfig(
            model="gemini-2.0-flash-lite",
            temperature=0.7,
            use_google_search=request.use_search,
            safety_settings_off=True
        )
        
        # Use the chat assistant system instruction
        llm_response = llm_service.generate_content(
            user_message=request.query,
            system_instruction=SystemInstructions.chat_assistant(),
            config=config
        )
        
        if not llm_response.success:
            raise HTTPException(status_code=500, detail=f"Chat failed: {llm_response.error}")
        
        # Add timeout headers for frontend
        response.headers["X-Request-Timeout"] = "120"
        
        return ChatResponse(
            status="success",
            query=request.query,
            response=llm_response.content,
            search_used=llm_response.search_used,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
