"""
Tools for the RAG query agent.

Tools are async functions decorated with @tool, defined in a factory
to close over the scoping context (user_id, requisition_id).
"""

import json
from typing import List, Dict, Any
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import AsyncSessionLocal
from db.crud.candidate_crud import get_candidate_by_id
from db.crud.requisition_crud import get_requisition_by_id
from db.crud.application_crud import get_applications_by_requisition, get_application_by_id
from db.crud.application_detail_crud import get_application_details
from db.crud.screening_result_crud import get_screening_result_by_application


async def get_candidate_full_profile(db: AsyncSession, candidate_id: int, requisition_id: int) -> Dict[str, Any]:
    """
    Combine multiple CRUD operations to get full candidate profile.
    
    Fetches candidate, their application for this requisition, application details, and screening result.
    """
    # Get candidate
    candidate = await get_candidate_by_id(db, candidate_id)
    if not candidate:
        return {"error": "Candidate not found"}
    
    # Get application for this requisition
    applications = await get_applications_by_requisition(
        db, requisition_id, include_relations=True
    )
    application = next((app for app in applications if app.candidate_id == candidate_id), None)
    if not application:
        return {"error": "No application found for this candidate in the requisition"}
    
    # Get application details
    details = await get_application_details(db, application.id)
    details_dict = {detail.key: detail.value for detail in details}
    
    # Get screening result
    screening = await get_screening_result_by_application(db, application.id)
    screening_dict = None
    if screening:
        screening_dict = {
            "score": screening.score,
            "justification": screening.justification,
        }
    
    # Build full profile - only include details that are actually saved/used in screening
    profile = {
        "candidate": {
            "id": candidate.id,
            "lever_id": candidate.lever_id,
            "email": candidate.email,
            "full_name": candidate.full_name,
            "phone": candidate.phone,
            "linkedin_url": candidate.linkedin_url,
        },
        "application": {
            "id": application.id,
            "status": application.status.value if application.status else None,
            "combined_score": application.combined_score,
            "applied_at": application.applied_at.isoformat() if application.applied_at else None,
        },
        "details": details_dict,
        "screening_result": screening_dict,
    }
    
    return profile


def build_rag_tools(user_id: int, requisition_id: int):
    """
    Factory function that returns a list of tools for the RAG query agent.
    
    The tools close over user_id and requisition_id for scoped access.
    """

    @tool
    async def get_requisition_candidates() -> str:
        """
        Get all candidates for the current requisition.
        
        Returns a list of candidates with their basic application information,
        sorted by combined score descending.
        
        Returns:
            JSON string with list of candidates and their application data
        """
        try:
            async with AsyncSessionLocal() as db:
                applications = await get_applications_by_requisition(
                    db, requisition_id, include_relations=True
                )
                
                results = []
                for app in applications:
                    candidate = app.candidate
                    results.append({
                        "candidate_id": candidate.id,
                        "name": candidate.full_name,
                        "email": candidate.email,
                        "status": app.status.value if app.status else None,
                        "combined_score": app.combined_score,
                        "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                    })
                
                return json.dumps(results)
                
        except Exception as e:
            return json.dumps({"error": f"Failed to get requisition candidates: {str(e)}"})

    @tool
    async def get_candidate_details(candidate_id: str) -> str:
        """
        Get full profile details for a specific candidate.
        
        Includes candidate info, application data, extracted details, and screening results.
        
        Args:
            candidate_id: The ID of the candidate to retrieve
        
        Returns:
            JSON string with complete candidate profile
        """
        try:
            async with AsyncSessionLocal() as db:
                profile = await get_candidate_full_profile(db, int(candidate_id), requisition_id)
                return json.dumps(profile)
                
        except Exception as e:
            return json.dumps({"error": f"Failed to get candidate details: {str(e)}"})

    @tool
    async def get_requisition_details() -> str:
        """
        Get details of the current requisition.
        
        Returns job description, requirements, and other requisition information.
        
        Returns:
            JSON string with requisition details
        """
        try:
            async with AsyncSessionLocal() as db:
                requisition = await get_requisition_by_id(db, requisition_id)
                if not requisition:
                    return json.dumps({"error": "Requisition not found"})
                
                details = {
                    "id": requisition.id,
                    "title": requisition.title,
                    "description": requisition.description,
                    "requirements": requisition.requirements,
                    "lever_id": requisition.lever_id,
                    "hiring_manager_id": requisition.hiring_manager_id,
                    "is_active": requisition.is_active,
                    "created_at": requisition.created_at.isoformat() if requisition.created_at else None,
                }
                
                return json.dumps(details)
                
        except Exception as e:
            return json.dumps({"error": f"Failed to get requisition details: {str(e)}"})

    return [
        get_requisition_candidates,
        get_candidate_details,
        get_requisition_details,
    ]