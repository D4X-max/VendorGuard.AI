import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/useAuthStore';
import Login from './features/auth/components/Login';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/layout/ProtectedRoute';

function App() {
  const { isAuthenticated } = useAuthStore();

  return (
    <Routes>
      {/* Public */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Login />}
      />

      {/* Protected — wrapped in layout */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route
            path="/"
            element={
              <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                📊 Dashboard — Coming Next
              </div>
            }
          />
          <Route
            path="/vendors"
            element={
              <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                🏢 Vendor Directory — Coming Next
              </div>
            }
          />
          <Route
            path="/vendors/:vendorId"
            element={
              <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                🏢 Vendor Detail — Coming Next
              </div>
            }
          />
          <Route
            path="/risk"
            element={
              <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                🛡️ Risk Register — Coming Next
              </div>
            }
          />
          <Route
            path="/evidence"
            element={
              <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                📄 Evidence Portal — Coming Next
              </div>
            }
          />
        </Route>
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;