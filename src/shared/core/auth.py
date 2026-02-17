"""
Shared Authentication
JWT token validation and user management
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional, Dict

from shared.core.config import settings

security = HTTPBearer()


class User:
    """User model"""
    
    def __init__(
        self,
        user_id: str,
        email: str,
        organization_id: str,
        is_superuser: bool = False,
        permissions: Optional[List[str]] = None
    ):
        self.user_id = user_id
        self.email = email
        self.organization_id = organization_id
        self.is_superuser = is_superuser
        self.permissions = permissions or []


def decode_token(token: str) -> Dict:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException if token is invalid
    """
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current authenticated user from JWT token
    
    FastAPI dependency for protected endpoints
    """
    
    token = credentials.credentials
    payload = decode_token(token)
    
    # Extract user information from token
    user_id = payload.get("sub")
    email = payload.get("email")
    organization_id = payload.get("organization_id")
    is_superuser = payload.get("is_superuser", False)
    permissions = payload.get("permissions", [])
    
    if not user_id or not organization_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return User(
        user_id=user_id,
        email=email,
        organization_id=organization_id,
        is_superuser=is_superuser,
        permissions=permissions
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """Get user if authenticated, None otherwise"""
    
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_permission(permission: str):
    """Decorator to require specific permission"""
    
    async def permission_checker(user: User = Depends(get_current_user)):
        if user.is_superuser:
            return user  # Superusers have all permissions
        
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        
        return user
    
    return permission_checker
```

