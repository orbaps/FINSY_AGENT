"""
Authentication and authorization module.
Provides JWT-based authentication and role-based access control.
"""
from functools import wraps
from typing import Optional, List
from datetime import datetime, timedelta
from flask import request, jsonify, g
from jose import JWTError, jwt
from app.config import Config


class AuthError(Exception):
    """Custom authentication error"""
    pass


def generate_token(user_id: str, roles: List[str] = None) -> str:
    """Generate JWT token for user"""
    if roles is None:
        roles = ["viewer"]
    
    payload = {
        "sub": user_id,
        "roles": roles,
        "exp": datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    
    if not Config.JWT_SECRET_KEY:
        raise AuthError("JWT_SECRET_KEY not configured")
    
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    if not Config.JWT_SECRET_KEY:
        raise AuthError("JWT_SECRET_KEY not configured")
    
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise AuthError(f"Invalid token: {str(e)}")


def get_current_user() -> Optional[dict]:
    """Get current user from request"""
    if not Config.ENABLE_AUTH:
        return {"user_id": "anonymous", "roles": ["viewer"]}
    
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    try:
        token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        payload = verify_token(token)
        return {
            "user_id": payload.get("sub"),
            "roles": payload.get("roles", [])
        }
    except (AuthError, IndexError):
        return None


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not Config.ENABLE_AUTH:
            g.user = {"user_id": "anonymous", "roles": ["viewer"]}
            return f(*args, **kwargs)
        
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required", "message": "Missing or invalid token"}), 401
        
        g.user = user
        return f(*args, **kwargs)
    return decorated_function


def require_role(*allowed_roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_roles = g.user.get("roles", [])
            if not any(role in user_roles for role in allowed_roles):
                return jsonify({
                    "error": "Insufficient permissions",
                    "message": f"Required roles: {allowed_roles}"
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_approver(f):
    """Decorator to require approver role"""
    return require_role("approver", "admin")(f)


def require_admin(f):
    """Decorator to require admin role"""
    return require_role("admin")(f)


