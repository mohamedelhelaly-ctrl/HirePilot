const API_BASE_URL = '/api';

/**
 * Fetch all jobs with statistics
 */
export const fetchJobStats = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/job_stats`);
    if (!response.ok) throw new Error('Failed to fetch job stats');
    const data = await response.json();
    return data.job_stats;
  } catch (error) {
    console.error('Error fetching job stats:', error);
    throw error;
  }
};

/**
 * Fetch all jobs from jobs.json
 */
export const fetchJobs = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/jobs`);
    if (!response.ok) throw new Error('Failed to fetch jobs');
    const data = await response.json();
    return data.jobs;
  } catch (error) {
    console.error('Error fetching jobs:', error);
    throw error;
  }
};

/**
 * Fetch screening table for a specific job/thread
 */
export const fetchCandidates = async (threadId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/screening_table/${threadId}`);
    if (!response.ok) throw new Error('Failed to fetch candidates');
    const data = await response.json();
    return data.candidates;
  } catch (error) {
    console.error('Error fetching candidates:', error);
    throw error;
  }
};

/**
 * Fetch candidate details by ID
 */
export const fetchCandidateDetails = async (candidateId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/candidate/${candidateId}`);
    if (!response.ok) throw new Error('Failed to fetch candidate details');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching candidate details:', error);
    throw error;
  }
};

/**
 * Send a chat message
 */
export const sendChatMessage = async (message, threadId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_message: message,
        thread_id: threadId
      })
    });
    if (!response.ok) throw new Error('Failed to send message');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

/**
 * Fetch conversation history for a thread
 */
export const fetchConversationHistory = async (threadId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversation/${threadId}`);
    if (!response.ok) throw new Error('Failed to fetch conversation');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching conversation:', error);
    throw error;
  }
};

/**
 * Create a new job
 */
export const createJob = async (jobData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/jobs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(jobData)
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to create job');
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error creating job:', error);
    throw error;
  }
};
