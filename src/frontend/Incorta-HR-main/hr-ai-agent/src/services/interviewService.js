// src/services/interviewService.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

/**
 * Interview & Graph Service — calls /api/interview/* and /api/execute endpoints
 */

/**
 * Get authorization headers
 */
const getAuthHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
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
// Interview Session Endpoints
// ============================================================================

/**
 * List interview sessions for an application
 * GET /api/interview/sessions/{application_id}
 */
export const fetchInterviewSessions = async (applicationId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/interview/sessions/${applicationId}`, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error fetching interview sessions for application ${applicationId}:`, error);
    throw error;
  }
};

/**
 * Create a new interview session
 * POST /api/interview/sessions
 *
 * @param {number} applicationId
 * @param {number} requisitionId
 * @param {string} interviewType - "hr_screen" | "technical" | "behavioral" | "final"
 */
export const createInterviewSession = async (applicationId, requisitionId, interviewType = "hr_screen") => {
  try {
    const response = await fetch(`${API_BASE_URL}/interview/sessions`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        application_id: applicationId,
        requisition_id: requisitionId,
        interview_type: interviewType,
      }),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error("Error creating interview session:", error);
    throw error;
  }
};

// ============================================================================
// Graph Executor Endpoint
// ============================================================================

/**
 * Execute the main orchestration graph
 * POST /api/execute
 *
 * @param {string} intent - "batch_screening" | "live_interview" | "rag_query"
 * @param {object} params - Additional parameters (requisition_id, application_id, etc.)
 */
export const executeGraph = async (intent, params = {}) => {
  try {
    const response = await fetch(`${API_BASE_URL}/execute`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        intent,
        ...params,
      }),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Error executing graph with intent '${intent}':`, error);
    throw error;
  }
};

// ============================================================================
// WebSocket Helper (for live interview)
// ============================================================================

/**
 * Create a WebSocket connection for live interview streaming
 *
 * @param {Function} onMessage - Callback for incoming messages
 * @param {Function} onClose - Callback when connection closes
 * @param {Function} onError - Callback for errors
 * @returns {WebSocket} WebSocket instance
 */
export const createInterviewWebSocket = (onMessage, onClose, onError) => {
  const wsUrl = (API_BASE_URL.replace("http", "ws")) + "/interview/stream";
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  ws.onclose = onClose;
  ws.onerror = onError;

  return ws;
};

// ============================================================================
// Default Export
// ============================================================================

export default {
  fetchInterviewSessions,
  createInterviewSession,
  executeGraph,
  createInterviewWebSocket,
};
