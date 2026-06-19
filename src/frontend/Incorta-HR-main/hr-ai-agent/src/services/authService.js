// src/services/authService.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

/**
 * Auth Service - Handles all authentication API calls
 * Manages tokens and user session
 */

// ============================================================================
// Token Management Utilities
// ============================================================================

/**
 * Store tokens in localStorage
 */
export const storeTokens = (accessToken, refreshToken) => {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
};

/**
 * Retrieve access token
 */
export const getAccessToken = () => {
  return localStorage.getItem("access_token");
};

/**
 * Retrieve refresh token
 */
export const getRefreshToken = () => {
  return localStorage.getItem("refresh_token");
};

/**
 * Clear all tokens (logout)
 */
export const clearTokens = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
};

/**
 * Store user info in localStorage
 */
export const storeUser = (user) => {
  localStorage.setItem("user", JSON.stringify(user));
};

/**
 * Retrieve stored user info
 */
export const getUser = () => {
  const user = localStorage.getItem("user");
  return user ? JSON.parse(user) : null;
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = () => {
  return !!getAccessToken();
};

// ============================================================================
// API Helper Functions
// ============================================================================

/**
 * Generic API request helper with auth header
 */
const apiCall = async (endpoint, options = {}) => {
  const accessToken = getAccessToken();
  
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  // Add Authorization header if token exists
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
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry the original request with new token
      return apiCall(endpoint, options);
    } else {
      // Refresh failed, logout user
      clearTokens();
      throw new Error("Session expired. Please login again.");
    }
  }

  // Parse response
  let data;
  try {
    data = await response.json();
  } catch (e) {
    data = null;
  }

  // Handle errors
  if (!response.ok) {
    const errorMessage = data?.detail || data?.message || response.statusText;
    throw new Error(errorMessage);
  }

  return data;
};

// ============================================================================
// Authentication Endpoints
// ============================================================================

/**
 * Google OAuth Login - Authorization Code Flow
 * POST /auth/google/callback
 * 
 * Exchanges authorization code for application tokens.
 * This implements OAuth 2.0 Authorization Code Flow for secure offline access.
 * 
 * @param {string} authCode - Authorization code from Google OAuth consent screen
 * @returns {Promise} - { access_token, refresh_token, token_type }
 */
export const googleLogin = async (authCode) => {
  try {
    const response = await apiCall("/auth/google/callback", {
      method: "POST",
      body: JSON.stringify({ authorization_code: authCode }),
    });

    // Store tokens and user info
    storeTokens(response.access_token, response.refresh_token);
    
    // Fetch and store user info
    const user = await getCurrentUser();
    storeUser(user);

    return response;
  } catch (error) {
    throw new Error(`Google login failed: ${error.message}`);
  }
};

/**
 * Refresh Access Token
 * POST /auth/refresh
 * 
 * @param {string} refreshToken - Optional refresh token (uses stored if not provided)
 * @returns {Promise} - { access_token, refresh_token, token_type }
 */
export const refreshAccessToken = async (refreshToken = null) => {
  try {
    const token = refreshToken || getRefreshToken();
    
    if (!token) {
      throw new Error("No refresh token available");
    }

    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: token }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error?.detail || "Token refresh failed");
    }

    const data = await response.json();
    
    // Store new tokens
    storeTokens(data.access_token, data.refresh_token);

    return data;
  } catch (error) {
    clearTokens();
    throw new Error(`Token refresh failed: ${error.message}`);
  }
};

/**
 * Get Current User Profile
 * GET /auth/me
 * 
 * @returns {Promise} - User object with id, email, full_name, role, is_active, created_at, updated_at
 */
export const getCurrentUser = async () => {
  try {
    const response = await apiCall("/auth/me", {
      method: "GET",
    });

    return response;
  } catch (error) {
    throw new Error(`Failed to fetch current user: ${error.message}`);
  }
};

/**
 * Logout User
 * POST /auth/logout
 * 
 * @param {string} refreshToken - Optional specific refresh token to revoke
 *                                If not provided, all tokens are revoked
 * @returns {Promise} - { message }
 */
export const logoutUser = async (refreshToken = null) => {
  try {
    const body = {};
    if (refreshToken) {
      body.refresh_token = refreshToken;
    }

    await apiCall("/auth/logout", {
      method: "POST",
      body: JSON.stringify(body),
    });

    // Clear tokens from storage
    clearTokens();

    return { message: "Logout successful" };
  } catch (error) {
    // Clear tokens even if API call fails
    clearTokens();
    throw new Error(`Logout failed: ${error.message}`);
  }
};

// ============================================================================
// Admin Endpoints (HR Manager Only)
// ============================================================================

/**
 * Create New User (Admin Only)
 * POST /auth/admin/users
 * Requires HR Manager role
 * 
 * @param {string} email - Employee email address
 * @param {string} fullName - Employee full name
 * @param {string} role - Employee role (hr_manager or hiring_manager)
 * @returns {Promise} - Created user object
 */
export const createUser = async (email, fullName, role) => {
  try {
    const response = await apiCall("/auth/admin/users", {
      method: "POST",
      body: JSON.stringify({
        email,
        full_name: fullName,
        role,
      }),
    });

    return response;
  } catch (error) {
    throw new Error(`Failed to create user: ${error.message}`);
  }
};

// ============================================================================
// System Setup Endpoint (One-time)
// ============================================================================

/**
 * Initial System Setup - Create First Admin User
 * POST /auth/setup
 * Unauthenticated endpoint - only works once during system initialization
 * 
 * @param {string} email - Admin email address
 * @param {string} fullName - Admin full name
 * @param {string} role - Must be "hr_manager"
 * @returns {Promise} - Created admin user object
 */
export const setupSystem = async (email, fullName, role = "hr_manager") => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/setup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        full_name: fullName,
        role,
      }),
    });

    let data;
    try {
      data = await response.json();
    } catch (e) {
      data = null;
    }

    if (!response.ok) {
      const errorMessage = data?.detail || response.statusText;
      throw new Error(errorMessage);
    }

    return data;
  } catch (error) {
    throw new Error(`System setup failed: ${error.message}`);
  }
};

// ============================================================================
// Protected API Helper
// ============================================================================

/**
 * Get authorization header with current access token
 * Useful for other API calls that need authentication
 */
export const getAuthHeader = () => {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// ============================================================================
// Export all functions for use in components
// ============================================================================

export default {
  // Token management
  storeTokens,
  getAccessToken,
  getRefreshToken,
  clearTokens,
  storeUser,
  getUser,
  isAuthenticated,
  getAuthHeader,

  // Auth endpoints
  googleLogin,
  refreshAccessToken,
  getCurrentUser,
  logoutUser,

  // Admin endpoints
  createUser,

  // Setup endpoint
  setupSystem,
};
