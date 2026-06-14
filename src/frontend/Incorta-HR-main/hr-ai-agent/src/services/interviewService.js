// src/services/interviewService.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const INTERVIEW_BASE_URL = `${API_BASE_URL}/interview`;

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
// Interview types
// ============================================================================

export const INTERVIEW_TYPES = {
  HR_SCREEN: "hr_screen",
  TECHNICAL: "technical",
};

export const INTERVIEW_TYPE_OPTIONS = [
  {
    value: INTERVIEW_TYPES.HR_SCREEN,
    label: "HR Interview",
    description: "Behavioral and culture-fit questions with HR-style follow-ups",
  },
  {
    value: INTERVIEW_TYPES.TECHNICAL,
    label: "Technical Interview",
    description: "Technical depth, implementation details, and scored evaluation",
  },
];

export const getInterviewTypeLabel = (interviewType) =>
  INTERVIEW_TYPE_OPTIONS.find((o) => o.value === interviewType)?.label ?? interviewType;

// ============================================================================
// Interview Session Endpoints
// ============================================================================

/**
 * List interview sessions for an application
 * GET /api/interview/sessions/{application_id}
 */
export const fetchInterviewSessions = async (applicationId) => {
  try {
    const response = await fetch(`${INTERVIEW_BASE_URL}/sessions/${applicationId}`, {
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
export const createInterviewSession = async (
  applicationId,
  requisitionId,
  interviewType = "hr_screen"
) => {
  try {
    const response = await fetch(`${INTERVIEW_BASE_URL}/sessions`, {
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

/**
 * Find an existing scheduled/in-progress session or create a new one.
 *
 * @param {number} applicationId
 * @param {number} requisitionId
 * @param {string} interviewType
 */
export const getOrCreateInterviewSession = async (
  applicationId,
  requisitionId,
  interviewType = "hr_screen"
) => {
  const sessions = await fetchInterviewSessions(applicationId);
  const existing = sessions.find(
    (s) =>
      ["scheduled", "in_progress"].includes(s.status) &&
      s.interview_type === interviewType
  );
  if (existing) return existing;
  return createInterviewSession(applicationId, requisitionId, interviewType);
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
// WebSocket helpers (live interview)
// ============================================================================

/**
 * Build the WebSocket URL for the live interview stream.
 * ws://host/api/interview/stream
 */
export const getInterviewWebSocketUrl = () => {
  return `${API_BASE_URL.replace(/^http/, "ws")}/interview/stream`;
};

/**
 * Create a WebSocket connection for live interview streaming.
 *
 * @param {Function} onMessage - Callback for incoming messages
 * @param {Function} onClose - Callback when connection closes
 * @param {Function} onError - Callback for errors
 * @param {Function} [onOpen] - Callback when connection opens
 * @returns {WebSocket} WebSocket instance
 */
export const createInterviewWebSocket = (onMessage, onClose, onError, onOpen) => {
  const ws = new WebSocket(getInterviewWebSocketUrl());

  ws.onopen = () => {
    if (onOpen) onOpen(ws);
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  ws.onclose = onClose;
  ws.onerror = onError;

  return ws;
};

/**
 * Send the init handshake after the WebSocket connects.
 */
export const sendInterviewInit = (
  ws,
  { sessionId, applicationId, requisitionId, interviewType = "hr_screen" }
) => {
  ws.send(
    JSON.stringify({
      type: "init",
      session_id: sessionId,
      application_id: applicationId,
      requisition_id: requisitionId,
      interview_type: interviewType,
    })
  );
};

/**
 * Send a base64-encoded audio chunk to the server.
 */
export const sendAudioChunk = (
  ws,
  audioBase64,
  audioFormat = "webm",
  audioSource = "microphone"
) => {
  ws.send(
    JSON.stringify({
      type: "audio_chunk",
      audio_data: audioBase64,
      audio_format: audioFormat,
      audio_source: audioSource,
    })
  );
};

/** Request interview summary generation and session teardown. */
export const sendEndInterview = (ws) => {
  ws.send(JSON.stringify({ type: "end_interview" }));
};

/** Keep-alive ping. */
export const sendInterviewPing = (ws) => {
  ws.send(JSON.stringify({ type: "ping" }));
};

/**
 * Convert a Blob to a base64 string (no data-URL prefix).
 */
export const blobToBase64 = (blob) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });

// ============================================================================
// Default Export
// ============================================================================

export default {
  INTERVIEW_TYPES,
  INTERVIEW_TYPE_OPTIONS,
  getInterviewTypeLabel,
  fetchInterviewSessions,
  createInterviewSession,
  getOrCreateInterviewSession,
  executeGraph,
  getInterviewWebSocketUrl,
  createInterviewWebSocket,
  sendInterviewInit,
  sendAudioChunk,
  sendEndInterview,
  sendInterviewPing,
  blobToBase64,
};
