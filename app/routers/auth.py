"""
Authentication router for Google Sign-In and user management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.services.auth_service import get_auth_service, AuthService
from app.dependencies import verify_id_token_dependency

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

# Request/Response Models
class GoogleSignInRequest(BaseModel):
    """Request model for Google Sign-In"""
    id_token: str
    session_id: Optional[str] = None  # For migrating guest session data

class GoogleSignInResponse(BaseModel):
    """Response model for Google Sign-In"""
    success: bool
    user: Optional[Dict[str, Any]] = None
    migration_result: Optional[Dict[str, Any]] = None
    message: str

class UserProfileResponse(BaseModel):
    """Response model for user profile"""
    success: bool
    user: Optional[Dict[str, Any]] = None
    message: str

@router.post("/auth/google", response_model=GoogleSignInResponse)
async def google_sign_in(
    request: GoogleSignInRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user with Google ID token
    
    This endpoint:
    1. Verifies the Google ID token
    2. Creates/updates user profile in Firestore
    3. Optionally migrates guest session data
    """
    try:
        logger.info("Processing Google Sign-In request")
        
        # Verify Google ID token
        user_info = await auth_service.verify_google_token(request.id_token)
        if not user_info:
            raise HTTPException(
                status_code=401, 
                detail="Invalid Google ID token"
            )
        
        # Create or update user profile
        uid = await auth_service.create_or_update_user(user_info)
        
        # Get updated user profile
        user_profile = await auth_service.get_user_profile(uid)
        
        # Migrate session data if provided
        migration_result = None
        if request.session_id:
            logger.info(f"Migrating session data: {request.session_id} -> {uid}")
            migration_result = await auth_service.migrate_session_data(
                request.session_id, 
                uid
            )
        
        return GoogleSignInResponse(
            success=True,
            user=user_profile,
            migration_result=migration_result,
            message="Successfully authenticated with Google"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google Sign-In: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error during authentication"
        )

@router.get("/auth/profile", response_model=UserProfileResponse)
async def get_user_profile(
    decoded_token: Dict[str, Any] = Depends(verify_id_token_dependency),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get authenticated user profile
    
    Requires valid Firebase ID token in Authorization header
    """
    try:
        if not decoded_token:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing authentication token"
            )
        
        uid = decoded_token.get('uid')
        if not uid:
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID in token"
            )
        
        user_profile = await auth_service.get_user_profile(uid)
        if not user_profile:
            raise HTTPException(
                status_code=404,
                detail="User profile not found"
            )
        
        return UserProfileResponse(
            success=True,
            user=user_profile,
            message="User profile retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving profile"
        )

@router.post("/auth/refresh")
async def refresh_user_session(
    decoded_token: Dict[str, Any] = Depends(verify_id_token_dependency),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh user session and update last active timestamp
    
    Requires valid Firebase ID token in Authorization header
    """
    try:
        if not decoded_token:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing authentication token"
            )
        
        uid = decoded_token.get('uid')
        if not uid:
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID in token"
            )
        
        # Update last active timestamp
        user_info = {
            'uid': uid,
            'email': decoded_token.get('email'),
            'name': decoded_token.get('name'),
            'picture': decoded_token.get('picture'),
            'email_verified': decoded_token.get('email_verified', False),
            'provider': 'google.com'
        }
        
        await auth_service.create_or_update_user(user_info)
        
        return {"success": True, "message": "Session refreshed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error refreshing session"
        )