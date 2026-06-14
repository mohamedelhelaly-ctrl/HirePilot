const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const CANDIDATES_URL = `${API_BASE_URL}/candidates`;

const getAuthHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

const handleResponse = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }
  return response.json();
};

/**
 * GET /api/candidates/directory
 * Immutable candidate identity grouped with application history.
 */
export const fetchCandidateDirectory = async () => {
  const response = await fetch(`${CANDIDATES_URL}/directory`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
};

export default { fetchCandidateDirectory };
