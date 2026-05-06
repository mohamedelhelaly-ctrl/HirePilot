from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .sqlachemy_base import SQLAlchemyBase as Base

class ApplicationDetail(Base):
    __tablename__ = "application_details"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)

    # Flexible key/value detail entry (e.g. key="technical_skills", value=[...])
    key = Column(String(255), nullable=False, index=True)
    value = Column(JSON, nullable=False)
    extracted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="details")
