// src/components/ProtectedRoute.jsx

import { Navigate } from "react-router-dom";
import * as authService from "../services/authService";

/**
 * ProtectedRoute Component
 * 
 * Wraps routes that require authentication and/or specific user roles.
 * Redirects to login if not authenticated, or to home if lacking required role.
 * 
 * @component
 * @param {React.ReactNode} children - The component to render if authorized
 * @param {string} [requiredRole] - Optional role requirement (e.g., "hr_manager", "hiring_manager")
 * @param {function} [fallback] - Optional fallback component if not authorized
 * 
 * @example
 * // Simple auth check
 * <Route
 *   path="/dashboard"
 *   element={<ProtectedRoute><Dashboard /></ProtectedRoute>}
 * />
 * 
 * @example
 * // Role-based protection
 * <Route
 *   path="/hr"
 *   element={<ProtectedRoute requiredRole="hr_manager"><HRHome /></ProtectedRoute>}
 * />
 */
export default function ProtectedRoute({ 
  children, 
  requiredRole = null,
  fallback = null 
}) {
  const user = authService.getUser();
  const isAuthenticated = authService.isAuthenticated();

  // Not authenticated - redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check role requirement
  if (requiredRole && user?.role !== requiredRole) {
    // Return fallback component or redirect to home
    if (fallback) {
      return fallback;
    }
    return <Navigate to="/" replace />;
  }

  // Authorized - render component
  return children;
}
