from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthorizationCodeRequest(BaseModel):
    """
    Request body for Google OAuth authorization code exchange.
    Frontend sends the authorization code received from Google consent screen.
    """
    authorization_code: str


class GoogleOAuthCredentialResponse(BaseModel):
    """
    Response containing user and Google account info after successful OAuth.
    """
    user_id: int
    email: EmailStr
    google_account_email: EmailStr
    full_name: str
    
    class Config:
        from_attributes = True