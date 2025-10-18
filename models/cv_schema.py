from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class CVDetails(BaseModel):
    """Schema for CV data extraction"""
    
    english_name: str = Field(description="Candidate's full name in English")
    email: Optional[str] = Field(default=None, description="Email address")
    phone_number: Optional[str] = Field(default=None, description="Phone number")
    nationality: Optional[str] = Field(default=None, description="Nationality")
    gender: Optional[str] = Field(default=None, description="Gender (Male/Female)")
    current_city: Optional[str] = Field(default=None, description="Current city of residence")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    graduation_year: Optional[int] = Field(default=None, description="Year of graduation")
    study_field: Optional[str] = Field(default=None, description="Field of study")
    universities: List[str] = Field(default_factory=list, description="Universities attended")
    years_of_experience: Optional[int] = Field(default=None, description="Total years of professional experience")
    technical_skills: List[str] = Field(default_factory=list, description="Technical skills")
    soft_skills: List[str] = Field(default_factory=list, description="Soft skills")
    Languages: List[str] = Field(default_factory=list, description="Languages spoken")
    Certifications: List[str] = Field(default_factory=list, description="Certifications obtained")
    score: float = Field(description="Match score out of 100")
    justification: str = Field(description="Brief justification for the score")