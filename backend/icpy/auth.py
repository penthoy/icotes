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
        self.jwt_algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
        self.jwt_audience = os.getenv('JWT_AUDIENCE', 'authenticated')
        self.cookie_name = os.getenv('COOKIE_NAME', 'auth_token')
        
        # SaaS session handoff configuration
        self.session_jwt_secret = os.getenv('SAAS_SESSION_JWT_SECRET') or self.jwt_secret
        self.session_jwt_audience = os.getenv('SESSION_JWT_AUDIENCE', 'webapp-saas')
        self.session_jwt_issuer = os.getenv('SESSION_JWT_ISSUER', 'orchestrator')
        
        # Validate SaaS mode configuration
        if self.auth_mode == 'saas' and not self.jwt_secret and not self.session_jwt_secret:
            raise ValueError("A JWT secret is required when AUTH_MODE=saas (SUPABASE_JWT_SECRET or SAAS_SESSION_JWT_SECRET)")
            
        logger.info(f"Authentication initialized in {self.auth_mode} mode")
    
    def is_saas_mode(self) -> bool:
        """Check if running in SaaS mode."""
        return self.auth_mode == 'saas'
    
    def is_standalone_mode(self) -> bool:
        """Check if running in standalone mode."""
        return self.auth_mode == 'standalone'
    
    def _decode_with_secret(self, token: str, secret: str, *, verify_aud: bool = False, expected_aud: Optional[str] = None, expected_iss: Optional[str] = None) -> Dict[str, Any]:
        """Decode a JWT with the provided secret and optional audience/issuer checks."""
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_aud": verify_aud},
                audience=expected_aud if verify_aud else None,
                issuer=expected_iss if expected_iss else None,
            )
            # Expiry check (defensive; jose already verifies exp/nbf if present)
            exp = payload.get('exp')
            if exp:
                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                if datetime.now(timezone.utc) > exp_datetime:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
            return payload
        except JWTError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid authentication token: {e}")
    
    def validate_handoff_token(self, token: str) -> Dict[str, Any]:
        """Validate a short-lived orchestrator handoff token.
        Enforces issuer/audience and standard time checks. Uses SAAS_SESSION_JWT_SECRET when provided,
        otherwise falls back to SUPABASE_JWT_SECRET by agreement.
        """
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Handoff token required")
        secret = self.session_jwt_secret
        if not secret:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Handoff secret not configured")
        return self._decode_with_secret(
            token,
            secret,
            verify_aud=True,
            expected_aud=self.session_jwt_audience,
            expected_iss=self.session_jwt_issuer,
        )
    
    def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token from cookie and return user information.
        Tries SUPABASE_JWT_SECRET first; if that fails and a session secret is configured, tries that as well.
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is required"
            )
        
        last_error: Optional[Exception] = None
        
        # Try Supabase token validation
        if self.jwt_secret:
            try:
                payload = self._decode_with_secret(token, self.jwt_secret, verify_aud=False)
                return {
                    'user_id': payload.get('sub'),
                    'email': payload.get('email'),
                    'role': payload.get('role', 'user'),
                    'exp': payload.get('exp'),
                    'iat': payload.get('iat'),
                    'raw_payload': payload
                }
            except HTTPException as e:
                last_error = e
        
        # Fallback to session secret (cookie minted by webapp during handoff)
        if self.session_jwt_secret:
            try:
                payload = self._decode_with_secret(token, self.session_jwt_secret, verify_aud=False)
                return {
                    'user_id': payload.get('sub'),
                    'email': payload.get('email'),
                    'role': payload.get('role', 'user'),
                    'exp': payload.get('exp'),
                    'iat': payload.get('iat'),
                    'raw_payload': payload
                }
            except HTTPException as e:
                last_error = e
        
        # If all validations failed
        logger.warning(f"JWT validation failed: {last_error}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
    
    def get_user_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract and validate user from request.
        Returns None in standalone mode. Raises if SaaS mode and missing/invalid.
        """
        if self.is_standalone_mode():
            # In standalone mode, no authentication required
            return None
        
        # SaaS mode - extract JWT from configured cookie
        auth_token = request.cookies.get(self.cookie_name)
        
        if not auth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please log in."
            )
        
        return self.validate_jwt_token(auth_token)
    
    def require_authentication(self, request: Request) -> Optional[Dict[str, Any]]:
        """Dependency function to require authentication for endpoints."""
        return self.get_user_from_request(request)

# Global authentication manager instance
auth_manager = AuthenticationManager()

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """FastAPI dependency to get current user. Returns None in standalone mode, user info in SaaS mode."""
    return auth_manager.require_authentication(request)

def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """FastAPI dependency to optionally get current user. Never raises exceptions, returns None if not authenticated."""
    try:
        return auth_manager.get_user_from_request(request)
    except HTTPException:
        return None
