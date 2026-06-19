from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .sqlachemy_base import SQLAlchemyBase as Base


class GoogleOAuthCredential(Base):
    """
    Stores encrypted Google OAuth credentials for HR managers.
    Enables offline access to Google Calendar for scheduling interviews.
    """
    __tablename__ = "google_oauth_credentials"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to users table
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Google account email associated with credentials
    google_account_email = Column(String(255), nullable=False, index=True)
    
    # Encrypted tokens (encrypted with Fernet before storage)
    access_token = Column(String(1000), nullable=False)  # Encrypted
    refresh_token = Column(String(1000), nullable=False)  # Encrypted
    
    # Token expiry timestamp
    token_expiry = Column(DateTime(timezone=True), nullable=False)
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="google_oauth_credential")
