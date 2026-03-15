from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    
    # Transcript content
    text = Column(Text, nullable=False)
    speaker = Column(String(50))  # "interviewer" or "candidate"
    sequence_number = Column(Integer, nullable=False)  # Order of chunks
    
    # Timing
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    offset_seconds = Column(Float)  # Time from interview start
    
    # Relationships
    session = relationship("InterviewSession", back_populates="transcript_chunks")
