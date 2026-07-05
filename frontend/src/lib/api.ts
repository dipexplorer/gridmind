import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor for attaching auth tokens (will be implemented fully in auth phase)
apiClient.interceptors.request.use((config) => {
  // const token = localStorage.getItem('token');
  // if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Transformers API Functions
export const getTransformers = async () => {
  const response = await apiClient.get('/transformers/');
  return response.data;
};

export const getTransformerRiskScore = async (id: string) => {
  const response = await apiClient.get(`/transformers/${id}/risk-score`);
  return response.data;
};

// Summary Stats API
export const getLatestAiRun = async () => {
  const response = await apiClient.get('/ai-runs/latest');
  return response.data;
};
