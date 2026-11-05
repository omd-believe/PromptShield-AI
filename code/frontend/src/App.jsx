import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { PwaProvider } from './contexts/PwaContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './components/AppLayout';
import Landing from './pages/Landing';
import Register from './pages/Register';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Optimizer from './pages/Optimizer';
import History from './pages/History';

export default function App() {
  return (
    <ThemeProvider>
      <PwaProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public routes — with top Navbar */}
              <Route path="/" element={<><Navbar /><Landing /></>} />
              <Route path="/register" element={<><Navbar /><Register /></>} />
              <Route path="/login" element={<><Navbar /><Login /></>} />

              {/* Protected routes — unified AppLayout */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <AppLayout activeRoute="dashboard">
                      <Dashboard />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/optimize"
                element={
                  <ProtectedRoute>
                    <AppLayout activeRoute="optimize">
                      <Optimizer />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/history"
                element={
                  <ProtectedRoute>
                    <AppLayout activeRoute="history">
                      <History />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </PwaProvider>
    </ThemeProvider>
  );
}
