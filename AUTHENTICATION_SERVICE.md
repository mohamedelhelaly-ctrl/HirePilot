# Authentication Service Setup Guide

## Overview

This document describes the authentication service implementation for the Incorta-HR backend. The service supports email/password login and Google OAuth authentication with JWT token management.

## Architecture

```
app/
├── security.py                    # JWT and password utilities
├── services/
│   └── auth_service.py           # Authentication business logic
├── dependencies/
│   ├── __init__.py
│   └── auth_dependencies.py      # FastAPI dependency injection
├── api/routers/
│   └── auth_router.py            # Authentication endpoints
└── main.py                        # (Updated) - Includes auth router
```

## Files Created

### 1. `app/security.py`

Core security utilities for password hashing and JWT token management.

**Functions:**

- `hash_password(password: str) -> str` - Hash password with bcrypt
- `verify_password(plain: str, hashed: str) -> bool` - Verify password
- `create_access_token(data: Dict, expires_delta: Optional[timedelta]) -> str` - Create JWT access token
- `create_refresh_token(user_id: int, expires_delta: Optional[timedelta]) -> str` - Create JWT refresh token
- `decode_token(token: str) -> Optional[Dict]` - Decode and validate JWT
- `decode_access_token(token: str) -> Optional[Dict]` - Validate access token
- `decode_refresh_token(token: str) -> Optional[Dict]` - Validate refresh token
- `hash_token(token: str) -> str` - Hash token for database storage

**Configuration:**

```python
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
```

### 2. `app/services/auth_service.py`

Business logic for authentication operations.

**Functions:**

#### `email_login(db, login_request) -> Token`

Email and password authentication.

```
Steps:
1. Fetch user by email
2. Verify password
3. Generate access token (30 min exp)
4. Generate refresh token (7 day exp)
5. Store hashed refresh token in database
```

#### `google_login(db, id_token_str) -> Token`

Google OAuth authentication.

```
Steps:
1. Verify Google ID token signature
2. Extract email, name, and Google user ID
3. Find user by email
4. Return 403 if user not found (pre-registration required)
5. Generate access token and refresh token
6. Store hashed refresh token in database
```

#### `refresh_access_token(db, refresh_token) -> Token`

Generate new access token from refresh token.

```
Steps:
1. Decode refresh token
2. Verify token exists in database
3. Load user and verify active status
4. Generate new access token
5. Return token response
```

#### `get_current_user(db, user_id) -> User`

Load current user from database.

### 3. `app/dependencies/auth_dependencies.py`

FastAPI dependency injection for authentication and authorization.

**OAuth2 Scheme:**

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
```

**Dependencies:**

#### `get_current_user(token, db) -> User`

Validates JWT and returns authenticated user.

- Decodes access token
- Loads user from database
- Verifies user is active

#### `require_role(allowed_roles: List[UserRole]) -> Callable`

Role-based authorization middleware.

- Checks if user's role is in allowed list
- Raises 403 if not authorized
- Returns dependency function

#### Convenience Role Checkers

- `require_hr_manager()` - HR managers only
- `require_hiring_manager()` - Hiring managers only
- `require_any_manager()` - Any manager role

**Usage Example:**

```python
@router.get("/admin")
async def admin_endpoint(
    current_user: User = Depends(require_hr_manager())
):
    return current_user
```

### 4. `app/api/routers/auth_router.py`

FastAPI endpoints for authentication.

**Endpoints:**

#### `POST /api/auth/login`

Email and password login.

```
Request:
{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}

Errors:
- 401: Invalid email or password
```

#### `POST /api/auth/google`

Google OAuth ID token login.

```
Request:
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEx..."
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}

Errors:
- 400: Invalid ID token
- 403: User not found in database
```

#### `POST /api/auth/refresh`

Refresh access token.

```
Request:
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}

Errors:
- 401: Invalid or expired refresh token
- 403: User is inactive
```

#### `GET /api/auth/me`

Get current user profile.

```
Headers:
Authorization: Bearer <access_token>

Response:
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "hr_manager",
  "is_active": true,
  "created_at": "2026-03-13T10:00:00",
  "updated_at": "2026-03-13T10:00:00"
}

Errors:
- 401: Missing or invalid access token
- 403: User is inactive
```

## Environment Variables

Add to `.env`:

```env
# JWT Configuration
SECRET_KEY=your-super-secret-key-change-in-production

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id-here.apps.googleusercontent.com
```

## Dependencies

Add to `requirements.txt`:

```
# For Google OAuth (NEEDS TO BE ADDED)
google-auth>=2.25.0
google-auth-oauthlib>=1.0.0

# Already in requirements
fastapi>=0.129.0
pydantic>=2.12.5
pydantic[email]
sqlalchemy>=2.0.46
bcrypt>=5.0.0
python-jose[cryptography]
```

## JWT Token Claims

### Access Token

```json
{
  "user_id": 1,
  "email": "user@example.com",
  "role": "hr_manager",
  "exp": 1710423000,
  "type": "access"
}
```

**Expiration:** 30 minutes

### Refresh Token

```json
{
  "user_id": 1,
  "exp": 1711287000,
  "type": "refresh"
}
```

**Expiration:** 7 days

## Database Schema

Uses existing models:

- **User** - User account with hashed password
- **RefreshToken** - Stores hashed refresh tokens

## Authentication Flow

### Email/Password Login

```
Client Request
    ↓
POST /api/auth/login {email, password}
    ↓
Verify email exists and password matches
    ↓
Generate access token (30 min)
Generate refresh token (7 days)
Hash and store refresh token in DB
    ↓
Return Token {access_token, refresh_token, token_type}
    ↓
Client stores tokens
```

### Google OAuth Login

```
Client obtains Google ID Token
    ↓
POST /api/auth/google {id_token}
    ↓
Verify Google ID token signature
Extract email from token
    ↓
Find or create user
    ↓
Generate access token (30 min)
Generate refresh token (7 days)
Hash and store refresh token in DB
    ↓
Return Token {access_token, refresh_token, token_type}
    ↓
Client stores tokens
```

### Protected Request

```
Client includes access token
    ↓
GET /api/auth/me
Headers: Authorization: Bearer {access_token}
    ↓
Decode and validate JWT
Load user from database
    ↓
Check user is active
    ↓
Return User object
```

### Token Refresh

```
Client includes refresh token
    ↓
POST /api/auth/refresh {refresh_token}
    ↓
Decode and validate refresh token
Verify token stored in database
Load user and verify active
    ↓
Generate new access token
    ↓
Return Token {access_token, refresh_token, token_type}
    ↓
Client updates stored access token
```

## Security Considerations

1. **Password Hashing:** All passwords are hashed with bcrypt before storage
2. **Token Hashing:** Refresh tokens are hashed with bcrypt before storing in database
3. **JWT Secrets:** Use strong SECRET_KEY in production
4. **HTTPS:** Always use HTTPS in production
5. **CORS:** Configure CORS if frontend is on different domain
6. **Token Expiration:** Access tokens expire in 30 minutes, refresh tokens in 7 days
7. **Token Revocation:** Refresh tokens are stored in database and can be revoked
8. **User Validation:** Users must be active (is_active=True) to authenticate
9. **Google OAuth:** Requires pre-registered users, no auto-signup

## Testing

### Test Email Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

### Test Protected Endpoint

```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Test Token Refresh

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

## Troubleshooting

### "Invalid or expired access token" (401)

- Token has expired (30 minute expiration)
- Token signature is invalid
- Token type is wrong (refresh instead of access)

### "Invalid or expired refresh token" (401)

- Refresh token has expired (7 day expiration)
- Refresh token is not stored in database
- Refresh token signature is invalid

### "User not found" (403)

- User was deleted from database
- User email doesn't exist
- User is inactive (is_active=False)

### Google OAuth failures

- GOOGLE_CLIENT_ID not set
- ID token is invalid or expired
- User not pre-registered in database

## Next Steps

1. Add google-auth package to requirements.txt
2. Set SECRET_KEY environment variable
3. Set GOOGLE_CLIENT_ID environment variable (if using Google OAuth)
4. Test authentication endpoints
5. Update API documentation if needed
6. Add more detailed error handling if required
7. Consider adding logout endpoint with token revocation
8. Add rate limiting to login endpoints
