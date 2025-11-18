import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/login";
import './App.css';
import HrDashboard from "./pages/hrHomePage";
import JobPipeline from "./pages/jobPipeline";
import HiringManagerDashboard from "./pages/hiringManagerDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/hr" element={<HrDashboard />} />
        <Route path="/jobs" element={<JobPipeline />} />
        <Route path="/hiring-manager" element={<HiringManagerDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}
