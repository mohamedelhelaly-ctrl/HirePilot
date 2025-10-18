from pydantic import BaseModel, Field
from typing import List, Optional

class JDDetails(BaseModel):
    """Schema for Job Description entity extraction"""
    
    job_title: str = Field(description="Job title")
    years_of_experience: str = Field(description="Required years of experience (e.g., '3-5', '5+', '0-2')")
    required_skills: List[str] = Field(default_factory=list, description="Required technical skills")
    required_education: Optional[str] = Field(default=None, description="Required education level/field")
    location: Optional[str] = Field(default=None, description="Job location")
    languages: List[str] = Field(default_factory=list, description="Required languages")
    soft_skills: List[str] = Field(default_factory=list, description="Required soft skills")
    certifications: List[str] = Field(default_factory=list, description="Preferred certifications")