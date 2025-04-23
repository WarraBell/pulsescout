// src/contexts/AuthContext.jsx
import React, { createContext, useContext, useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import authService from '../api/authService';

// Create the context
const AuthContext = createContext(null);

// Custom hook for consuming the context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check for logged in user on mount
  useEffect(() => {
    const fetchCurrentUser = async () => {
      try {
        // Check if token exists
        const token = localStorage.getItem('token');
        if (!token) {
          setLoading(false);
          return;
        }

        // Get current user data
        const userData = await authService.getCurrentUser();
        setCurrentUser(userData);
      } catch (err) {
        console.error('Error fetching user:', err);
        // Token might be invalid or expired, clear it
        authService.logout();
      } finally {
        setLoading(false);
      }
    };

    fetchCurrentUser();
  }, []);

  // Login function
  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const data = await authService.login(email, password);
      // Set the user in state
      if (data.user) {
        setCurrentUser(data.user);
      } else {
        // If the backend doesn't return user info with login, fetch it
        const userData = await authService.getCurrentUser();
        setCurrentUser(userData);
      }
      return data;
    } catch (err) {
      setError(err.detail || 'Login failed. Please check your credentials.');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = () => {
    authService.logout();
    setCurrentUser(null);
  };

  // Register function
  const register = async (userData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.register(userData);
      return result;
    } catch (err) {
      setError(err.detail || 'Registration failed. Please try again.');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Verify email
  const verifyEmail = async (token) => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.verifyEmail(token);
      return result;
    } catch (err) {
      setError(err.detail || 'Email verification failed.');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Request password reset
  const requestPasswordReset = async (email) => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.requestPasswordReset(email);
      return result;
    } catch (err) {
      setError(err.detail || 'Password reset request failed.');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Reset password
  const resetPassword = async (token, newPassword) => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.resetPassword(token, newPassword);
      return result;
    } catch (err) {
      setError(err.detail || 'Password reset failed.');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Update user profile
  const updateProfile = async (userData) => {
    setLoading(true);
    setError(null);
    try {
      // This is a placeholder - you'll need to implement this function in authService
      const result = await authService.updateProfile(userData);
      setCurrentUser({...currentUser, ...result});
      return result;
    } catch (err) {
      setError(err.detail || 'Profile update failed.');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const value = {
    currentUser,
    loading,
    error,
    login,
    logout,
    register,
    verifyEmail,
    requestPasswordReset,
    resetPassword,
    updateProfile,
    isAuthenticated: !!currentUser
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};