"""
Node 3 — Response Generation

Responsibilities:
- Construct structured LLM prompt with user query and candidate context
- Call LLM (llama-3.3-70b via llm_rag) to generate natural language answer
- Extract citations (candidate mentions) from LLM response
- Format final response with answer and structured citations
- Populate state.llm_response

Environment variables:
    GROQ_API_KEY, OPENROUTER_API_KEY, or GEMINI_API_KEY (via llm_config.py)
"""

import logging
import json
import re
from typing import List

from ..state import RAGQueryState, LLMResponse, CitedCandidate
# TODO: Import LLM client once implemented
# from utils.llm_config import llm_rag

logger = logging.getLogger(__name__)


async def response_generation_node(state: RAGQueryState) -> RAGQueryState:
    """
    Node 3: Generate LLM answer with citations.
    
    Reads:
        state.processed_query.original_query — user's question
        state.retrieval_result.matched_candidates — candidates to include in context
    
    Writes:
        state.llm_response — answer with citations
    
    Sets state.error on:
        - Missing retrieval_result
        - No candidates found
        - LLM call failure
    """
    # ── Fail-fast: propagate upstream errors ──────────────────────────────────
    if state.error:
        return state
    
    if not state.retrieval_result:
        state.error = "[Node 3: response_generation] Missing retrieval_result from Node 2"
        logger.error(state.error)
        return state
    
    if not state.retrieval_result.matched_candidates:
        state.error = "[Node 3: response_generation] No candidates found for query"
        logger.error(state.error)
        return state
    
    logger.info(
        f"[Node 3: response_generation] Generating answer for "
        f"{len(state.retrieval_result.matched_candidates)} candidates"
    )
    
    try:
        # ── Step 1: Build LLM prompt ───────────────────────────────────────────
        prompt = _build_llm_prompt(
            state.processed_query.original_query,
            state.retrieval_result.matched_candidates
        )
        
        logger.info(
            f"[Node 3] Prompt constructed: {len(prompt)} chars, "
            f"~{len(prompt) // 4} tokens"
        )
        
        # ── Step 2: Call LLM ───────────────────────────────────────────────────
        # TODO: Implement LLM call
        # response = await llm_rag.ainvoke(prompt)
        # answer = response.content
        
        answer = (
            "Placeholder: LLM integration not yet implemented. "
            f"Query: {state.processed_query.original_query}. "
            f"Found {len(state.retrieval_result.matched_candidates)} candidates."
        )
        
        logger.info(f"[Node 3] LLM response: {len(answer)} chars")
        
        # ── Step 3: Extract citations ──────────────────────────────────────────
        cited_candidates = _extract_citations(
            answer,
            state.retrieval_result.matched_candidates
        )
        
        logger.info(f"[Node 3] Extracted {len(cited_candidates)} citations")
        
        # ── Step 4: Populate state ─────────────────────────────────────────────
        state.llm_response = LLMResponse(
            answer=answer,
            cited_candidates=cited_candidates,
            total_candidates_considered=len(state.retrieval_result.matched_candidates),
            confidence="high" if len(cited_candidates) > 0 else "medium",
        )
        
        logger.info("[Node 3] Response generation complete")
        return state
        
    except Exception as exc:
        state.error = f"[Node 3: response_generation] Failed: {exc}"
        logger.error(state.error, exc_info=True)
        return state


# ── Helper Functions ──────────────────────────────────────────────────────────

def _build_llm_prompt(query: str, candidates: List) -> str:
    """
    Construct structured prompt for LLM.
    
    Format:
    - System instruction (RAG assistant role)
    - User query
    - Candidate context (structured JSON)
    """
    # Build candidate context
    candidate_summaries = []
    for candidate in candidates:
        summary = {
            "name": candidate.full_name,
            "candidate_id": candidate.candidate_id,
            "skills": candidate.skills,
            "experience_years": candidate.total_years_experience,
            "combined_score": candidate.combined_score,
            "technical_score": candidate.technical_score,
            "key_strengths": candidate.key_strengths,
            "key_concerns": candidate.key_concerns,
        }
        
        # Include CV summary if available and similarity is high
        if candidate.cv_summary and candidate.similarity_to_query and candidate.similarity_to_query > 0.8:
            summary["cv_summary"] = candidate.cv_summary
        
        # Include interview summary if available
        if candidate.interview_summary:
            summary["interview_summary"] = candidate.interview_summary
        
        candidate_summaries.append(summary)
    
    context_json = json.dumps(candidate_summaries, indent=2)
    
    # Construct full prompt
    prompt = f"""You are an expert AI recruiting assistant for Incorta's HR team. Your role is to answer questions about candidates based on their profiles, screening results, and interview data.

USER QUERY:
{query}

CANDIDATE CONTEXT:
{context_json}

INSTRUCTIONS:
1. Answer the user's query in natural language using ONLY the information provided in the candidate context above.
2. When mentioning a candidate, always include their full name.
3. Be concise but informative. Highlight key strengths and relevant experience.
4. If asked for comparisons, provide balanced assessments based on scores and qualifications.
5. If the query cannot be answered with the given context, state that clearly.
6. Do not hallucinate information not present in the context.

ANSWER:"""
    
    return prompt


def _extract_citations(answer: str, candidates: List) -> List[CitedCandidate]:
    """
    Extract candidate mentions from LLM response and create citations.
    
    Process:
    1. Use NER/regex to find candidate name mentions in answer
    2. Cross-check against retrieved candidates only (prevent hallucination)
    3. Create structured citation with relevance snippet
    """
    cited = []
    
    for candidate in candidates:
        # Check if candidate name appears in answer
        if candidate.full_name.lower() in answer.lower():
            # Extract sentence containing the mention for context
            sentences = re.split(r'[.!?]\s+', answer)
            relevance_snippet = ""
            
            for sentence in sentences:
                if candidate.full_name.lower() in sentence.lower():
                    relevance_snippet = sentence.strip()
                    break
            
            # Limit snippet length
            if len(relevance_snippet) > 150:
                relevance_snippet = relevance_snippet[:147] + "..."
            
            cited.append(CitedCandidate(
                candidate_id=candidate.candidate_id,
                application_id=candidate.application_id,
                full_name=candidate.full_name,
                relevance_snippet=relevance_snippet or "Mentioned in response",
            ))
    
    return cited
