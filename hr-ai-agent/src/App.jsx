import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/login";
import './App.css';
import HrDashboard from "./pages/hrHomePage";
import JobPipeline from "./pages/jobPipeline";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/hr" element={<HrDashboard />} />
        <Route path="/jobs" element={<JobPipeline />} />
      </Routes>
    </BrowserRouter>
  );
}
