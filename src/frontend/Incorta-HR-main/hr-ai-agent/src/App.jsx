import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/login";
import ProtectedRoute from "./components/ProtectedRoute";
import './App.css';
import HrDashboard from "./pages/hrHomePage";
import JobPipeline from "./pages/jobPipeline";
import RequisitionDetail from "./pages/requisitionDetail";
import CandidatesPage from "./pages/candidatesPage";
import UsersPage from "./pages/usersPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public route - Login */}
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Login />} />

        {/* Protected routes - HR Manager and Hiring Manager */}
        <Route
          path="/hr"
          element={
            <ProtectedRoute>
              <HrDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/candidates"
          element={
            <ProtectedRoute requiredRole="hr_manager">
              <CandidatesPage />
            </ProtectedRoute>
          }
        />

        {/* Protected routes - HR Manager: User Management */}
        <Route
          path="/users"
          element={
            <ProtectedRoute requiredRole="hr_manager">
              <UsersPage />
            </ProtectedRoute>
          }
        />

        {/* Protected routes - Any authenticated user */}
        <Route
          path="/jobs"
          element={
            <ProtectedRoute>
              <JobPipeline />
            </ProtectedRoute>
          }
        />

        {/* Requisition Detail Page */}
        <Route
          path="/requisition/:id"
          element={
            <ProtectedRoute>
              <RequisitionDetail />
            </ProtectedRoute>
          }
        />


      </Routes>
    </BrowserRouter>
  );
}
