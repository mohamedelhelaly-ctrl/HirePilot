"""
Tools for the RAG query agent.

Tools are async functions decorated with @tool, defined in a factory
to close over the scoping context (user_id, requisition_id).
"""

import json
import logging
from langchain_core.tools import tool


from models.database import AsyncSessionLocal
from controllers import CandidateController,RequisitionController,ApplicationController
candidate_controller = CandidateController()
req_controller = RequisitionController()
application_controller = ApplicationController()

logger = logging.getLogger(__name__)


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
        Output is JSON and includes name, email, status, score, and applied_at.
        """
        logger.info(
            f"[rag_tools] get_requisition_candidates called requisition_id={requisition_id} "
            f"user_id={user_id}"
        )
        try:
            async with AsyncSessionLocal() as db:
                applications = await application_controller.get_applications_by_requisition(
                    requisition_id, db, include_relations=True
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

                logger.debug(
                    f"[rag_tools] get_requisition_candidates returning {len(results)} applications"
                )
                return json.dumps(results, ensure_ascii=False)

        except Exception as e:
            logger.exception("[rag_tools] get_requisition_candidates failed")
            return json.dumps({"error": f"Failed to get requisition candidates: {str(e)}"})
    get_requisition_candidates.name = "get_requisition_candidates"

    @tool
    async def get_candidate_details(candidate_id: str) -> str:
        """
        Get full profile details for a specific candidate.

        Includes candidate info, application data, extracted details, and screening results.
        Output is JSON and includes candidate profile, application metadata and screening results.
        """
        logger.info(
            f"[rag_tools] get_candidate_details called candidate_id={candidate_id} "
            f"requisition_id={requisition_id} user_id={user_id}"
        )
        try:
            async with AsyncSessionLocal() as db:
                profile = await candidate_controller.get_candidate_full_profile(db, int(candidate_id), requisition_id)
                logger.debug("[rag_tools] get_candidate_details returning profile data")
                return json.dumps(profile, ensure_ascii=False)

        except Exception as e:
            logger.exception("[rag_tools] get_candidate_details failed")
            return json.dumps({"error": f"Failed to get candidate details: {str(e)}"})
    get_candidate_details.name = "get_candidate_details"

    @tool
    async def get_requisition_details() -> str:
        """
        Get details of the current requisition.

        Returns job title, description, requirements, and other requisition metadata.
        Output is JSON.
        """
        logger.info(
            f"[rag_tools] get_requisition_details called requisition_id={requisition_id} "
            f"user_id={user_id}"
        )
        try:
            async with AsyncSessionLocal() as db:
                requisition = await req_controller.get_requisition(requisition_id, db)
                if not requisition:
                    logger.warning("[rag_tools] get_requisition_details requisition not found")
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

                logger.debug("[rag_tools] get_requisition_details returning requisition details")
                return json.dumps(details, ensure_ascii=False)

        except Exception as e:
            logger.exception("[rag_tools] get_requisition_details failed")
            return json.dumps({"error": f"Failed to get requisition details: {str(e)}"})
    get_requisition_details.name = "get_requisition_details"

    return [
        get_requisition_candidates,
        get_candidate_details,
        get_requisition_details,
    ]