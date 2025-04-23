import { configureStore } from '@reduxjs/toolkit';
// These slices will be created later
// import authReducer from './slices/authSlice';
// import leadReducer from './slices/leadSlice';
// import planReducer from './slices/planSlice';

export const store = configureStore({
  reducer: {
    // Uncomment as slices are created
    // auth: authReducer,
    // leads: leadReducer,
    // plans: planReducer,
  },
});