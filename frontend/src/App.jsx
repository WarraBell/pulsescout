import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
// These components will be created in the future
// import Dashboard from './pages/Dashboard';
// import Login from './pages/Login';
// import Register from './pages/Register';
// import LeadSearch from './pages/LeadSearch';
// import SavedLeads from './pages/SavedLeads';
// import Profile from './pages/Profile';
// import Plans from './pages/Plans';
// import NotFound from './pages/NotFound';
// import PrivateRoute from './components/PrivateRoute';

function App() {
  useEffect(() => {
    // Any app initialization code would go here
    console.log('PulseScout app initialized');
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        {/* These routes will be uncommented as you build them */}
        {/* <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/leads/search" element={<PrivateRoute><LeadSearch /></PrivateRoute>} />
        <Route path="/leads/saved" element={<PrivateRoute><SavedLeads /></PrivateRoute>} />
        <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
        <Route path="/plans" element={<PrivateRoute><Plans /></PrivateRoute>} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFound />} /> */}
        
        {/* Temporary route until components are built */}
        <Route path="/" element={
          <div className="flex min-h-screen items-center justify-center">
            <div className="text-center p-8 max-w-md">
              <h1 className="text-3xl font-bold text-gray-800 mb-4">Welcome to PulseScout</h1>
              <p className="text-gray-600 mb-6">Your AI-enhanced lead discovery platform is under construction.</p>
              <div className="bg-blue-100 p-4 rounded-lg text-blue-800">
                Start building your components to see them here!
              </div>
            </div>
          </div>
        } />
      </Routes>
    </div>
  );
}

export default App;