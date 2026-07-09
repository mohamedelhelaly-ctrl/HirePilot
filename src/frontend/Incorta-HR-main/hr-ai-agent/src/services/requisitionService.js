// src/services/requisitionService.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

/**
 * Requisition Service - Handles all requisition API calls
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
 * Fetch all requisitions with optional filters
 */
export const fetchRequisitions = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    if (filters.hiring_manager_id) {
      params.append("hiring_manager_id", filters.hiring_manager_id);
    }
    if (filters.is_active !== undefined) {
      params.append("is_active", filters.is_active);
    }
    if (filters.skip) {
      params.append("skip", filters.skip);
    }
    if (filters.limit) {
      params.append("limit", filters.limit);
    }

    const queryString = params.toString();
    const url = queryString ? `${API_BASE_URL}/?${queryString}` : `${API_BASE_URL}/`;

    const response = await fetch(url, {
      method: "GET",
      headers: getAuthHeaders(),
    });

    return await handleResponse(response);
  } catch (error) {
    console.error("Error fetching requisitions:", error);
    throw error;
  }
};

/**
 * Fetch a single requisition by ID
 */
export const fetchRequisitionById = async (requisitionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/${requisitionId}`, {
      method: "GET",
      headers: getAuthHeaders(),
    });

    return await handleResponse(response);
  } catch (error) {
    console.error(`Error fetching requisition ${requisitionId}:`, error);
    throw error;
  }
};

/**
 * Create a new requisition
 */
export const createRequisition = async (requisitionData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(requisitionData),
    });

    return await handleResponse(response);
  } catch (error) {
    console.error("Error creating requisition:", error);
    throw error;
  }
};

/**
 * Update a requisition
 */
export const updateRequisition = async (requisitionId, updates) => {
  try {
    const response = await fetch(`${API_BASE_URL}/${requisitionId}`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify(updates),
    });

    return await handleResponse(response);
  } catch (error) {
    console.error(`Error updating requisition ${requisitionId}:`, error);
    throw error;
  }
};

/**
 * Delete a requisition (soft delete - marks as inactive)
 */
export const deleteRequisition = async (requisitionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/${requisitionId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to delete requisition: ${response.status}`);
    }

    return { success: true };
  } catch (error) {
    console.error(`Error deleting requisition ${requisitionId}:`, error);
    throw error;
  }
};

export default {
  fetchRequisitions,
  fetchRequisitionById,
  createRequisition,
  updateRequisition,
  deleteRequisition,
};
