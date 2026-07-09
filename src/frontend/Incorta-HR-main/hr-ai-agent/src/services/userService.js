// src/services/userService.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

import { getAccessToken, clearTokens, refreshAccessToken } from "./authService";

/**
 * Generic API request helper with auth header (mirrors authService.apiCall)
 */
const apiCall = async (endpoint, options = {}) => {
  const accessToken = getAccessToken();

  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const config = {
    ...options,
    headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

  // Handle 401 - try to refresh token
  if (response.status === 401) {
    try {
      await refreshAccessToken();
      return apiCall(endpoint, options);
    } catch {
      clearTokens();
      throw new Error("Session expired. Please login again.");
    }
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const errorMessage = data?.detail || data?.message || response.statusText;
    throw new Error(errorMessage);
  }

  return data;
};

// ============================================================================
// User Management Endpoints (HR Manager Only)
// ============================================================================

/**
 * List all users
 * GET /users
 *
 * @param {number} skip - Records to skip (default 0)
 * @param {number} limit - Max records (default 100)
 * @returns {Promise<Array>} - Array of user objects
 */
export const fetchUsers = async (skip = 0, limit = 100) => {
  return apiCall(`/users?skip=${skip}&limit=${limit}`, {
    method: "GET",
  });
};

/**
 * Get a single user by ID
 * GET /users/:id
 *
 * @param {number} userId
 * @returns {Promise<Object>} - User object
 */
export const fetchUserById = async (userId) => {
  return apiCall(`/users/${userId}`, {
    method: "GET",
  });
};

/**
 * Update a user
 * PUT /users/:id
 *
 * @param {number} userId
 * @param {Object} updates - { email?, full_name?, role?, is_active? }
 * @returns {Promise<Object>} - Updated user object
 */
export const updateUser = async (userId, updates) => {
  return apiCall(`/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
};

/**
 * Deactivate a user
 * PATCH /users/:id/deactivate
 *
 * @param {number} userId
 * @returns {Promise<Object>} - Updated user object
 */
export const deactivateUser = async (userId) => {
  return apiCall(`/users/${userId}/deactivate`, {
    method: "PATCH",
  });
};

/**
 * Activate a user
 * PATCH /users/:id/activate
 *
 * @param {number} userId
 * @returns {Promise<Object>} - Updated user object
 */
export const activateUser = async (userId) => {
  return apiCall(`/users/${userId}/activate`, {
    method: "PATCH",
  });
};

/**
 * Get requisitions assigned to a user (as hiring manager)
 * GET /?hiring_manager_id=:id
 *
 * @param {number} userId
 * @returns {Promise<Array>} - Array of requisition objects
 */
export const fetchUserRequisitions = async (userId) => {
  return apiCall(`/?hiring_manager_id=${userId}`, {
    method: "GET",
  });
};

export default {
  fetchUsers,
  fetchUserById,
  updateUser,
  deactivateUser,
  activateUser,
  fetchUserRequisitions,
};
