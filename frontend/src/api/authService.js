// src/api/authService.js
import axios from 'axios';

const API_URL = process.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const axiosInstance = axios.create({
  baseURL: `${API_URL}`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add authorization header
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

const authService = {
  register: async (userData) => {
    try {
      const response = await axiosInstance.post('/auth/register', userData);
      return response.data;
    } catch (error) {
      throw error.response?.data || { detail: 'Network error occurred' };
    }
  },

  login: async (email, password) => {
    // Convert to form data as the backend expects OAuth2PasswordRequestForm
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    
    try {
      const response = await axios.post(`${API_URL}/auth/login`, formData);
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
      }
      return response.data;
    } catch (error) {
      throw error.response?.data || { detail: 'Network error occurred' };
    }
  },

  logout: () => {
    localStorage.removeItem('token');
  },

  verifyEmail: async (token) => {
    try {
      const response = await axiosInstance.post('/auth/verify-email', { token });
      return response.data;
    } catch (error) {
      throw error.response?.data || { detail: 'Network error occurred' };
    }
  },

  requestPasswordReset: async (email) => {
    try {
      const response = await axiosInstance.post('/auth/forgot-password', { email });
      return response.data;
    } catch (error) {
      throw error.response?.data || { detail: 'Network error occurred' };
    }
  },

  resetPassword: async (token, newPassword) => {
    try {
      const response = await axiosInstance.post('/auth/reset-password', {
        token,
        new_password: newPassword
      });
      return response.data;
    } catch (error) {
      throw error.response?.data || { detail: 'Network error occurred' };
    }
  },

  getCurrentUser: async () => {
    try {
      const response = await axiosInstance.get('/auth/me');
      return response.data;
    } catch (error) {
      throw error.response?.data || { detail: 'Network error occurred' };
    }
  }
};

export default authService;

