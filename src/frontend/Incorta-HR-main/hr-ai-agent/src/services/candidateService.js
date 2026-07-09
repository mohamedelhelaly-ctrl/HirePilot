// src/services/candidateService.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const CANDIDATES_URL = `${API_BASE_URL}/candidates`;

/**
 * Candidate & Application Service — calls /api/candidates/* endpoints
 */

/**
 * Get authorization headers (JSON)
 */
const getAuthHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

/**
 * Get authorization headers (no Content-Type — for FormData uploads)
 */
const getAuthHeadersMultipart = () => {
  const token = localStorage.getItem("access_token");
  return {
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

/**
 * Handle API response errors
 */
const handleResponse = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }
  return response.json();
};

// ============================================================================
// Candidate Endpoints
// ============================================================================

/**
 * Get a single candidate by ID
 * GET /api/candidates/{candidate_id}
 */
export const fetchCandidateById = async (candidateId) => {
  try {
    const response = await fetch(`${CANDIDATES_URL}/${candidateId}`, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error fetching candidate ${candidateId}:`, error);
    throw error;
  }
};

/**
 * Get all candidates for a requisition
 * GET /api/candidates/by-requisition/{requisition_id}
 */
export const fetchCandidatesByRequisition = async (requisitionId) => {
  try {
    const response = await fetch(`${CANDIDATES_URL}/by-requisition/${requisitionId}`, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error fetching candidates for requisition ${requisitionId}:`, error);
    throw error;
  }
};

/**
 * Create a new candidate
 * POST /api/candidates/
 */
export const createCandidate = async (candidateData) => {
  try {
    const response = await fetch(`${CANDIDATES_URL}/`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(candidateData),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error("Error creating candidate:", error);
    throw error;
  }
};

/**
 * Update a candidate
 * PATCH /api/candidates/{candidate_id}
 */
export const updateCandidate = async (candidateId, updates) => {
  try {
    const response = await fetch(`${CANDIDATES_URL}/${candidateId}`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify(updates),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error updating candidate ${candidateId}:`, error);
    throw error;
  }
};

// ============================================================================
// Application Endpoints
// ============================================================================

/**
 * Get applications for a requisition with optional filters
 * GET /api/candidates/applications/by-requisition/{requisition_id}
 */
export const fetchApplicationsByRequisition = async (requisitionId, filters = {}) => {
  try {
    const params = new URLSearchParams();
    if (filters.status) params.append("status", filters.status);
    if (filters.min_score !== undefined) params.append("min_score", filters.min_score);
    if (filters.skip) params.append("skip", filters.skip);
    if (filters.limit) params.append("limit", filters.limit);
    if (filters.include_relations) params.append("include_relations", filters.include_relations);

    const queryString = params.toString();
    const url = queryString
      ? `${CANDIDATES_URL}/applications/by-requisition/${requisitionId}?${queryString}`
      : `${CANDIDATES_URL}/applications/by-requisition/${requisitionId}`;

    const response = await fetch(url, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error fetching applications for requisition ${requisitionId}:`, error);
    throw error;
  }
};

/**
 * Get a single application by ID
 * GET /api/candidates/applications/{application_id}
 */
export const fetchApplicationById = async (applicationId, includeRelations = false) => {
  try {
    const url = includeRelations
      ? `${CANDIDATES_URL}/applications/${applicationId}?include_relations=true`
      : `${CANDIDATES_URL}/applications/${applicationId}`;

    const response = await fetch(url, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error fetching application ${applicationId}:`, error);
    throw error;
  }
};

/**
 * Get application details (CV extraction key-value pairs)
 * GET /api/candidates/applicationDetail/{application_id}
 */
export const fetchApplicationDetails = async (applicationId) => {
  try {
    const response = await fetch(`${CANDIDATES_URL}/applicationDetail/${applicationId}`, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error fetching application details ${applicationId}:`, error);
    throw error;
  }
};

/**
 * Update an application
 * PATCH /api/candidates/applications/{application_id}
 */
export const updateApplication = async (applicationId, updates) => {
  try {
    const response = await fetch(`${CANDIDATES_URL}/applications/${applicationId}`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify(updates),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error updating application ${applicationId}:`, error);
    throw error;
  }
};

/**
 * Update application status
 * PATCH /api/candidates/applications/{application_id}/status
 */
export const updateApplicationStatus = async (applicationId, newStatus, userId = null, reason = null) => {
  try {
    const params = new URLSearchParams();
    params.append("new_status", newStatus);
    if (userId) params.append("user_id", userId);
    if (reason) params.append("reason", reason);

    const response = await fetch(
      `${CANDIDATES_URL}/applications/${applicationId}/status?${params.toString()}`,
      {
        method: "PATCH",
        headers: getAuthHeaders(),
      }
    );
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error updating application status ${applicationId}:`, error);
    throw error;
  }
};

/**
 * Generate technical questions for an application
 * POST /api/candidates/applications/{application_id}/tech-questions
 */
export const generateTechQuestions = async (applicationId, { force = false } = {}) => {
  try {
    const params = force ? "?force=true" : "";
    const response = await fetch(
      `${CANDIDATES_URL}/applications/${applicationId}/tech-questions${params}`,
      {
        method: "POST",
        headers: getAuthHeaders(),
      }
    );
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error generating tech questions for application ${applicationId}:`, error);
    throw error;
  }
};

/**
 * Load static STAR-method CBI questions for an application (8 standard questions)
 * POST /api/candidates/applications/{application_id}/cbi-questions
 */
export const generateCBIQuestions = async (applicationId, { force = false } = {}) => {
  try {
    const params = force ? "?force=true" : "";
    const response = await fetch(
      `${CANDIDATES_URL}/applications/${applicationId}/cbi-questions${params}`,
      {
        method: "POST",
        headers: getAuthHeaders(),
      }
    );
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error generating CBI questions for application ${applicationId}:`, error);
    throw error;
  }
};

// ============================================================================
// CV Upload
// ============================================================================

/**
 * Upload and vectorize CVs for a requisition
 * POST /api/candidates/upload
 *
 * @param {number} requisitionId - Requisition ID
 * @param {FileList|File[]} files - CV files (.pdf or .docx)
 */
export const uploadCVs = async (requisitionId, files) => {
  try {
    const formData = new FormData();
    formData.append("requisition_id", requisitionId);

    for (const file of files) {
      formData.append("files", file);
    }

    const response = await fetch(`${CANDIDATES_URL}/upload`, {
      method: "POST",
      headers: getAuthHeadersMultipart(),
      body: formData,
    });
    return await handleResponse(response);
  } catch (error) {
    console.error("Error uploading CVs:", error);
    throw error;
  }
};

// ============================================================================
// Default Export
// ============================================================================

export default {
  fetchCandidateById,
  fetchCandidatesByRequisition,
  createCandidate,
  updateCandidate,
  fetchApplicationsByRequisition,
  fetchApplicationById,
  fetchApplicationDetails,
  updateApplication,
  updateApplicationStatus,
  generateTechQuestions,
  generateCBIQuestions,
  uploadCVs,
};
