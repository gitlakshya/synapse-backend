"""
Authentication service for Google Sign-In and Firebase token verification.
"""

import os
import logging
from typing import Optional, Dict, Any
import requests
from firebase_admin import auth
from app.services.firestore_service import FirestoreService
from app.dependencies import get_firestore_client

logger = logging.getLogger(__name__)

class AuthService:
    """Service for handling Google OAuth and Firebase authentication"""
    
    def __init__(self):
        self.fs = FirestoreService(get_firestore_client())
        self.google_client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        self.google_client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
        
        if not self.google_client_id:
            logger.warning("GOOGLE_OAUTH_CLIENT_ID not configured")
    
    async def verify_google_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google ID token and return user information
        
        Args:
            id_token: Google ID token from frontend
            
        Returns:
            User information dict or None if invalid
        """
        try:
            # Verify token with Firebase Auth (which handles Google tokens)
            decoded_token = auth.verify_id_token(id_token)
            
            # Extract user information
            user_info = {
                'uid': decoded_token.get('uid'),
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture'),
                'email_verified': decoded_token.get('email_verified', False),
                'provider': 'google.com',
                'firebase_token': decoded_token
            }
            
            logger.info(f"Successfully verified Google token for user: {user_info['email']}")
            return user_info
            
        except auth.InvalidIdTokenError as e:
            logger.error(f"Invalid Google ID token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying Google token: {e}")
            return None
    
    async def create_or_update_user(self, user_info: Dict[str, Any]) -> str:
        """
        Create or update user profile in Firestore
        
        Args:
            user_info: User information from Google token
            
        Returns:
            User ID
        """
        try:
            uid = user_info['uid']
            
            # Prepare user profile data
            profile_data = {
                'uid': uid,
                'email': user_info['email'],
                'name': user_info['name'],
                'picture': user_info.get('picture'),
                'email_verified': user_info.get('email_verified', False),
                'provider': user_info.get('provider', 'google.com'),
                'created_at': self.fs._get_server_timestamp(),
                'updated_at': self.fs._get_server_timestamp(),
                'last_login': self.fs._get_server_timestamp()
            }
            
            # Check if user exists
            existing_user = self.fs.get_user_profile(uid)
            
            if existing_user:
                # Update existing user
                profile_data['created_at'] = existing_user.get('created_at')
                self.fs.update_user_profile(uid, profile_data)
                logger.info(f"Updated existing user profile: {uid}")
            else:
                # Create new user
                self.fs.create_user_profile(uid, profile_data)
                logger.info(f"Created new user profile: {uid}")
            
            return uid
            
        except Exception as e:
            logger.error(f"Error creating/updating user profile: {e}")
            raise
    
    async def get_user_profile(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get user profile from Firestore"""
        try:
            return self.fs.get_user_profile(uid)
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def migrate_session_data(self, session_id: str, uid: str) -> Dict[str, Any]:
        """
        Migrate session data to authenticated user
        
        Args:
            session_id: Guest session ID
            uid: Authenticated user ID
            
        Returns:
            Migration result
        """
        try:
            return self.fs.migrate_session_to_user(session_id, uid)
        except Exception as e:
            logger.error(f"Error migrating session data: {e}")
            return {"migrated": False, "error": str(e)}

# Global service instance
_auth_service = None

def get_auth_service() -> AuthService:
    """Get or create authentication service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service