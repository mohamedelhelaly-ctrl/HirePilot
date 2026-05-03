from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .sqlachemy_base import SQLAlchemyBase as Base
from ..tables_enums import ApplicationStatus


class StatusHistory(Base):
    __tablename__ = "status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    
    # Status change
    from_status = Column(SQLEnum(ApplicationStatus))
    to_status = Column(SQLEnum(ApplicationStatus), nullable=False)
    
    # Context
    changed_by_user_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(String(500))
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="status_history")
