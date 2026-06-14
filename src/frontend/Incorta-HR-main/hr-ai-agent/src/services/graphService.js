// src/services/graphService.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

/**
 * Universal Graph Execution Service — calls the /api/execute endpoint
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

/**
 * Execute the main orchestration graph with a specific intent
 * POST /api/execute
 */
export const executeGraph = async (payload) => {
  try {
    const response = await fetch(`${API_BASE_URL}/execute`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    return await handleResponse(response);
  } catch (error) {
    console.error(`Error executing graph for intent ${payload.intent}:`, error);
    throw error;
  }
};

/**
 * Ask the RAG chatbot about candidates for a specific requisition.
 * Pass chatThreadId to continue an in-memory conversation on the backend.
 */
export const queryRagChatbot = async (requisitionId, queryText, chatThreadId = null) => {
  return executeGraph({
    intent: "rag_query",
    requisition_id: requisitionId,
    query: queryText,
    ...(chatThreadId && { chat_thread_id: chatThreadId }),
  });
};

export default {
  executeGraph,
  queryRagChatbot,
};
