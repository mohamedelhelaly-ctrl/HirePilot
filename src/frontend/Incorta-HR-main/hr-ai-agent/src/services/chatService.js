const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const CHAT_URL = `${API_BASE_URL}/chat`;

const getAuthHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

const handleResponse = async (response) => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }
  if (response.status === 204) return null;
  return response.json();
};

export const fetchThreads = async (requisitionId) => {
  const response = await fetch(
    `${CHAT_URL}/threads?requisition_id=${requisitionId}`,
    { method: "GET", headers: getAuthHeaders() }
  );
  return handleResponse(response);
};

export const createThread = async (requisitionId, title) => {
  const response = await fetch(`${CHAT_URL}/threads`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      requisition_id: requisitionId,
      ...(title ? { title } : {}),
    }),
  });
  return handleResponse(response);
};

export const fetchMessages = async (threadExternalId) => {
  const response = await fetch(`${CHAT_URL}/threads/${threadExternalId}/messages`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
};

export const renameThread = async (threadExternalId, title) => {
  const response = await fetch(`${CHAT_URL}/threads/${threadExternalId}`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: JSON.stringify({ title }),
  });
  return handleResponse(response);
};

export const deleteThread = async (threadExternalId) => {
  const response = await fetch(`${CHAT_URL}/threads/${threadExternalId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
};

export default {
  fetchThreads,
  createThread,
  fetchMessages,
  renameThread,
  deleteThread,
};
