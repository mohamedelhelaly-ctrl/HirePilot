"""
Security module for JWT token generation, validation, and password hashing.
Handles encryption/decryption of authentication tokens.
"""

from jose import jwt, JWTError
import bcrypt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError
import os


# ============================================================================
# Configuration
# ============================================================================

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")



# # ============================================================================
# # Password Hashing
# # ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    Args:
        password: The plaintext password to hash
        
    Returns:
        The bcrypt hashed password (str)
    """
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its bcrypt hash.
    
    Args:
        plain_password: The plaintext password to verify
        hashed_password: The hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# ============================================================================
# JWT Token Generation
# ============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with user claims.
    
    Args:
        data: Dictionary containing token claims (user_id, email, role)
        expires_delta: Optional custom expiration time; uses default if not provided
        
    Returns:
        Encoded JWT access token (str)
    """
    to_encode = data.copy()
    
    # Set expiration time (default: 30 minutes)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    # Encode the token using the secret key and HS256 algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token for obtaining new access tokens.
    
    Args:
        user_id: The ID of the user
        expires_delta: Optional custom expiration time; uses default if not provided
        
    Returns:
        Encoded JWT refresh token (str)
    """
    to_encode = {"user_id": user_id, "type": "refresh"}
    
    # Set expiration time (default: 7 days)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    
    # Encode the token using the secret key and HS256 algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ============================================================================
# JWT Token Validation
# ============================================================================

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Dictionary of token claims if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate an access token, ensuring it's the correct type.
    
    Args:
        token: The JWT access token to decode
        
    Returns:
        Dictionary of token claims if valid, None otherwise
    """
    payload = decode_token(token)
    
    # Verify this is an access token (not a refresh token)
    if payload and payload.get("type") == "access":
        return payload
    
    return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a refresh token, ensuring it's the correct type.
    
    Args:
        token: The JWT refresh token to decode
        
    Returns:
        Dictionary of token claims if valid, None otherwise
    """
    payload = decode_token(token)
    
    # Verify this is a refresh token (not an access token)
    if payload and payload.get("type") == "refresh":
        return payload
    
    return None


# ============================================================================
# Refresh Token Hashing
# ============================================================================

def hash_token(token: str) -> str:
    """
    Hash a token before storing in database.
    Uses SHA256 to create a fixed-size hash of the refresh token.
    
    JWT tokens are typically 200+ characters, which exceeds bcrypt's 72-byte limit.
    SHA256 is used instead to produce a fixed-size hash suitable for database storage.
    
    Args:
        token: The JWT token to hash
        
    Returns:
        The SHA256 hashed token as hex string (64 characters)
        
    Example:
        original_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        token_hash = hash_token(original_token)
        # token_hash = "a1b2c3d4e5f6..."
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
