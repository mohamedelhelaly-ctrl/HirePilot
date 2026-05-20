"""
Tools for the RAG query agent.

Tools are async functions decorated with @tool, defined in a factory
to close over the scoping context (user_id, requisition_id).
"""

import json
from langchain_core.tools import tool


from models.database import AsyncSessionLocal
from controllers import CandidateController,RequisitionController,ApplicationController
candidate_controller = CandidateController()
req_controller = RequisitionController()
application_controller = ApplicationController()


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
                applications = await application_controller.get_applications_by_requisition(
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
                profile = await candidate_controller.get_candidate_full_profile(db, int(candidate_id), requisition_id)
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
                requisition = await req_controller.get_requisition(requisition_id, db)
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