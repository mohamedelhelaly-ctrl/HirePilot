// src/services/calendarService.js

import * as authService from "./authService";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

/**
 * Calendar Service - Handles all calendar and interview scheduling API calls
 */

/**
 * Generic API request helper with auth header
 */
const apiCall = async (endpoint, options = {}) => {
  const accessToken = authService.getAccessToken();

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
    const refreshed = await authService.refreshAccessToken();
    if (refreshed) {
      return apiCall(endpoint, options);
    } else {
      authService.clearTokens();
      throw new Error("Session expired. Please login again.");
    }
  }

  let data;
  try {
    data = await response.json();
  } catch (e) {
    data = null;
  }

  if (!response.ok) {
    const errorMessage = data?.detail || data?.message || response.statusText;
    throw new Error(errorMessage);
  }

  return data;
};

// ============================================================================
// Calendar Endpoints
// ============================================================================

/**
 * Get available interview time slots
 * GET /calendar/availability
 *
 * @param {string} dateFrom - Start date (YYYY-MM-DD format)
 * @param {string} dateTo - End date (YYYY-MM-DD format)
 * @param {string} interviewType - Type of interview (hr_screen, technical, behavioral, final)
 * @returns {Promise} - { available_slots, interview_type, total_slots }
 */
export const getAvailableSlots = async (dateFrom, dateTo, interviewType) => {
  try {
    const params = new URLSearchParams({
      date_from: dateFrom,
      date_to: dateTo,
      interview_type: interviewType,
    });

    const response = await apiCall(`/calendar/availability?${params.toString()}`, {
      method: "GET",
    });

    return response;
  } catch (error) {
    throw new Error(`Failed to fetch available slots: ${error.message}`);
  }
};

/**
 * Schedule an interview
 * POST /calendar/schedule-interview
 *
 * @param {object} scheduleData - Interview scheduling data
 * @returns {Promise} - { message, interview_session }
 */
export const scheduleInterview = async (scheduleData) => {
  try {
    const response = await apiCall("/calendar/schedule-interview", {
      method: "POST",
      body: JSON.stringify({
        candidate_email: scheduleData.candidateEmail,
        candidate_name: scheduleData.candidateName,
        application_id: scheduleData.applicationId,
        requisition_id: scheduleData.requisitionId,
        interview_type: scheduleData.interviewType,
        start_time: scheduleData.startTime,
        end_time: scheduleData.endTime,
      }),
    });

    return response;
  } catch (error) {
    throw new Error(`Failed to schedule interview: ${error.message}`);
  }
};

/**
 * Reschedule an interview
 * PUT /calendar/interviews/{interviewId}/reschedule
 *
 * @param {number} interviewId - Interview session ID
 * @param {object} rescheduleData - New interview times
 * @returns {Promise} - { message, interview_session }
 */
export const rescheduleInterview = async (interviewId, rescheduleData) => {
  try {
    const response = await apiCall(`/calendar/interviews/${interviewId}/reschedule`, {
      method: "PUT",
      body: JSON.stringify({
        new_start_time: rescheduleData.newStartTime,
        new_end_time: rescheduleData.newEndTime,
      }),
    });

    return response;
  } catch (error) {
    throw new Error(`Failed to reschedule interview: ${error.message}`);
  }
};

/**
 * Cancel an interview
 * DELETE /calendar/interviews/{interviewId}
 *
 * @param {number} interviewId - Interview session ID
 * @returns {Promise} - { message, event_id }
 */
export const cancelInterview = async (interviewId) => {
  try {
    const response = await apiCall(`/calendar/interviews/${interviewId}`, {
      method: "DELETE",
    });

    return response;
  } catch (error) {
    throw new Error(`Failed to cancel interview: ${error.message}`);
  }
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format date for API calls (YYYY-MM-DD)
 */
export const formatDateForAPI = (date) => {
  const d = new Date(date);
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${day}`;
};

/**
 * Format ISO datetime for display
 */
export const formatDateTimeForDisplay = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleString();
};

/**
 * Get date range for availability query (default: next 7 days)
 */
export const getDefaultDateRange = () => {
  const today = new Date();
  const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);

  return {
    dateFrom: formatDateForAPI(today),
    dateTo: formatDateForAPI(nextWeek),
  };
};

export default {
  getAvailableSlots,
  scheduleInterview,
  rescheduleInterview,
  cancelInterview,
  formatDateForAPI,
  formatDateTimeForDisplay,
  getDefaultDateRange,
};
