import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

import { supabase } from './supabaseClient';

// Interceptor for attaching auth tokens
apiClient.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.set('Authorization', `Bearer ${session.access_token}`);
  }
  return config;
});

// Interceptor for handling 401 Unauthorized responses globally
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      console.warn("Unauthorized request, signing out...");
      await supabase.auth.signOut();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

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
