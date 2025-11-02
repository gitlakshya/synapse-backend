from fastapi import APIRouter, Request, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Union, List
import uuid
import logging
from datetime import datetime, timezone

from app.services.firestore_service import FirestoreService
from app.services.itinerary_service import get_itinerary_service
from app.services.smartAdjust import SmartAdjustAgent
from app.dependencies import get_firestore_client, verify_id_token_dependency, optional_verify_id_token_dependency
from app.routers.session import create_session

logger = logging.getLogger(__name__)
router = APIRouter(tags=["trip"])

# Request Models
class PlanTripRequest(BaseModel):
    """Request model for trip planning with validation"""
    sessionId: Optional[str] = None
    destination: str = Field(..., min_length=2, max_length=100, description="Travel destination")
    days: int = Field(1, ge=1, le=30, description="Number of days (1-30)")
    startDate: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$', description="Start date (YYYY-MM-DD)")
    endDate: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$', description="End date (YYYY-MM-DD)")
    budget: float = Field(..., ge=0, description="Total budget in local currency")
    preferences: Optional[Dict[str, Union[int, float]]] = Field(default_factory=dict, description="Preference sliders (0-100)")
    specialRequirements: Optional[str] = Field(None, max_length=500, description="Special requirements or accessibility needs")
    people:  int = Field(1, ge=1, le=10, description="Number of people (1-10)")
    budgetBreakdown: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Budget breakdown")
    themes: Optional[List[str]] = None
    
    @field_validator('preferences')
    @classmethod
    def validate_preferences(cls, v):
        if v:
            valid_prefs = {'nature', 'nightlife', 'adventure', 'leisure', 'heritage', 'culture', 'food', 'shopping', 'unexplored'}
            for key, value in v.items():
                if key not in valid_prefs:
                    raise ValueError(f"Invalid preference: {key}. Must be one of {valid_prefs}")
                if not (0 <= value <= 100):
                    raise ValueError(f"Preference values must be between 0-100, got {value} for {key}")
        return v

class SmartAdjustRequest(BaseModel):
    """Request model for itinerary adjustment"""
    sessionId: Optional[str] = None
    itinerary: Dict[str, Any] = Field(..., description="Current itinerary to adjust")
    userRequest: str = Field(..., min_length=5, max_length=500, description="Adjustment request")

# Response Models
class PlanTripResponse(BaseModel):
    """Response model for trip planning"""
    status: str
    itineraryId: str
    itinerary: Dict[str, Any]
    processingTime: float
    metadata: Dict[str, Any]

class SmartAdjustResponse(BaseModel):
    """Response model for itinerary adjustment"""
    status: str
    adjustedItinerary: Dict[str, Any]
    processingTime: float
    metadata: Dict[str, Any]

class ErrorResponse(BaseModel):
    """Error response model"""
    status: str = "error"
    message: str
    details: Optional[Dict[str, Any]] = None

# Helper Functions
def get_firestore_service():
    """Dependency to get FirestoreService instance"""
    return FirestoreService(get_firestore_client())

async def validate_auth_or_session(
    decoded_token: Optional[str], 
    session_id: Optional[str]
) -> tuple[Optional[str], str]:
    """Validate that either auth token or session ID is present"""
    user_id = decoded_token.get("uid") if decoded_token else None
    
    if not user_id and not session_id:
        session_id = create_session()
        logger.info(f"Created session {session_id} for unauthenticated user")

    return user_id, session_id

# API Endpoints
@router.post("/plantrip", response_model=PlanTripResponse, responses={
    400: {"model": ErrorResponse, "description": "Bad Request"},
    401: {"model": ErrorResponse, "description": "Unauthorized"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"}
})
async def plan_trip(
    request: PlanTripRequest,
    response: Response,
    fs: FirestoreService = Depends(get_firestore_service),
    decoded_token: Optional[str] = Depends(optional_verify_id_token_dependency)
):
    start_time = datetime.now()
    
    try:
        logger.info(f"Planning trip to {request.destination} for {request.days} days, budget: {request.budget}")
        
        user_id, session_id = await validate_auth_or_session(decoded_token, request.sessionId)
        
        itinerary_service = get_itinerary_service()
        
        # Generate itinerary using AI
        logger.info("Generating itinerary with AI service")
        itinerary_data = await itinerary_service.generate_itinerary(
            destination=request.destination,
            days=request.days,
            budget=request.budget,
            preferences=request.preferences,
            start_date=request.startDate,
            end_date=request.endDate,
            special_requirements=request.specialRequirements
        )
        
        logger.info("Saving itinerary to Firestore")
        itinerary_id = await itinerary_service.save_itinerary(
            itinerary_data=itinerary_data,
            user_id=user_id,
            session_id=session_id
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Prepare response
        response_data = PlanTripResponse(
            status="success",
            itineraryId=itinerary_id,
            itinerary=itinerary_data,
            processingTime=processing_time,
            metadata={
                "userId": user_id,
                "sessionId": session_id,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "llmUsed": True,
                "searchUsed": itinerary_data.get("meta", {}).get("searchUsed", False)
            }
        )
        
        logger.info(f"Trip planning completed successfully in {processing_time:.2f}s")
        
        # Add timeout headers for frontend
        response.headers["X-Request-Timeout"] = "120"
        response.headers["X-Processing-Time"] = str(processing_time)
        
        return response_data
        
    except ValueError as e:
        logger.error(f"Validation error in trip planning: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": f"Invalid request: {str(e)}"}
        )
    except RuntimeError as e:
        logger.error(f"Runtime error in trip planning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "AI service temporarily unavailable"}
        )
    except Exception as e:
        logger.error(f"Unexpected error in trip planning: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Internal server error"}
        )

@router.post("/smartadjust", response_model=SmartAdjustResponse, responses={
    400: {"model": ErrorResponse, "description": "Bad Request"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"}
})
async def adjust_itinerary(
    request: SmartAdjustRequest,
    response: Response,
    fs: FirestoreService = Depends(get_firestore_service),
    decoded_token: Optional[str] = Depends(optional_verify_id_token_dependency)
):
    """
    Adjust an existing itinerary using AI with Google Search integration.
    
    This endpoint intelligently modifies travel itineraries based on user requests
    while maintaining the original structure and constraints.
    
    **Features:**
    - AI-powered itinerary adjustment with schema compliance
    - Google Search integration for real-time venue information
    - Preservation of trip-level constraints (dates, budget, destination)
    - Activity reordering, addition, and removal
    - Cost recalculation and validation
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Adjusting itinerary with request: {request.userRequest[:100]}...")
        
        # Validate authentication or session
        user_id, session_id = await validate_auth_or_session(decoded_token, request.sessionId)
        
        # Get SmartAdjust agent
        agent = SmartAdjustAgent()
        
        # Adjust itinerary using AI
        logger.info("Adjusting itinerary with SmartAdjust agent")
        adjusted_itinerary = await agent.adjust_itinerary(
            current_itinerary=request.itinerary,
            user_request=request.userRequest
        )
        
        # Save adjusted itinerary
        if user_id:
            itinerary_id = fs.save_itinerary_for_user(user_id, adjusted_itinerary)
        else:
            itinerary_id = fs.save_itinerary_for_session(session_id, adjusted_itinerary)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Prepare response
        response_data = SmartAdjustResponse(
            status="success",
            adjustedItinerary=adjusted_itinerary,
            processingTime=processing_time,
            metadata={
                "userId": user_id,
                "sessionId": session_id,
                "adjustedAt": datetime.now(timezone.utc).isoformat(),
                "itineraryId": itinerary_id,
                "userRequest": request.userRequest
            }
        )
        
        logger.info(f"Itinerary adjustment completed successfully in {processing_time:.2f}s")
        
        response.headers["X-Request-Timeout"] = "120"
        response.headers["X-Processing-Time"] = str(processing_time)
        
        return response_data
        
    except ValueError as e:
        logger.error(f"Validation error in itinerary adjustment: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": f"Invalid request: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Unexpected error in itinerary adjustment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Internal server error"}
        )

@router.get("/health")
async def health_check():
    """Health check endpoint for the trip service"""
    try:
        # Test basic service dependencies
        itinerary_service = get_itinerary_service()
        fs = get_firestore_service()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "itinerary_service": "available",
                "firestore_service": "available",
                "llm_service": "available"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": str(e)}
        )
