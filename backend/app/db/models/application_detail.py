from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class ApplicationDetail(Base):
    __tablename__ = "application_details"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    
    # Normalized CV fields for fast filtering
    skill_name = Column(String(255), index=True)
    years_of_experience = Column(Float)
    education_degree = Column(String(255))
    education_institution = Column(String(255))
    previous_company = Column(String(255))
    previous_role = Column(String(255))
    certification = Column(String(255))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="details")
