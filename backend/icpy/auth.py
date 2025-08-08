"""
Authentication module for icotes backend.
Supports both standalone and SaaS authentication modes.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, Request, status
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """Manages authentication for both standalone and SaaS modes."""
    
    def __init__(self):
        self.auth_mode = os.getenv('AUTH_MODE', 'standalone').lower()
        self.jwt_secret = os.getenv('SUPABASE_JWT_SECRET')
        self.jwt_algorithm = 'HS256'
        
        # Validate SaaS mode configuration
        if self.auth_mode == 'saas' and not self.jwt_secret:
            raise ValueError("SUPABASE_JWT_SECRET is required when AUTH_MODE=saas")
            
        logger.info(f"Authentication initialized in {self.auth_mode} mode")
    
    def is_saas_mode(self) -> bool:
        """Check if running in SaaS mode."""
        return self.auth_mode == 'saas'
    
    def is_standalone_mode(self) -> bool:
        """Check if running in standalone mode."""
        return self.auth_mode == 'standalone'
    
    def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and return user information.
        
        Args:
            token: JWT token string
            
        Returns:
            Dict containing user information
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is required"
            )
        
        try:
            # Decode and validate JWT token
            # Disable audience validation for flexibility
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_aud": False}
            )
            
            # Check token expiration
            exp = payload.get('exp')
            if exp:
                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                if datetime.now(timezone.utc) > exp_datetime:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has expired"
                    )
            
            # Extract user information
            user_info = {
                'user_id': payload.get('sub'),
                'email': payload.get('email'),
                'role': payload.get('role', 'user'),
                'exp': payload.get('exp'),
                'iat': payload.get('iat'),
                'raw_payload': payload
            }
            
            logger.debug(f"Token validated for user: {user_info['user_id']}")
            return user_info
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
    
    def get_user_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract and validate user from request.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            User information dict if authenticated, None if standalone mode
            
        Raises:
            HTTPException: If SaaS mode and authentication fails
        """
        if self.is_standalone_mode():
            # In standalone mode, no authentication required
            return None
        
        # SaaS mode - extract JWT from auth_token cookie
        auth_token = request.cookies.get('auth_token')
        
        if not auth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please log in."
            )
        
        return self.validate_jwt_token(auth_token)
    
    def require_authentication(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Dependency function to require authentication for endpoints.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            User information if authenticated, None if standalone mode
            
        Raises:
            HTTPException: If authentication fails
        """
        return self.get_user_from_request(request)

# Global authentication manager instance
auth_manager = AuthenticationManager()

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to get current user.
    Returns None in standalone mode, user info in SaaS mode.
    """
    return auth_manager.require_authentication(request)

def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to optionally get current user.
    Never raises exceptions, returns None if not authenticated.
    """
    try:
        return auth_manager.get_user_from_request(request)
    except HTTPException:
        return None
