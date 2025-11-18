import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/login";
import './App.css';
import HrDashboard from "./pages/hrHomePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/hr" element={<HrDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}
