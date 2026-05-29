import { useNavigate } from "react-router-dom";
import * as authService from "../services/authService";
import { FiLogOut } from "react-icons/fi";

export default function Navbar() {
  const navigate = useNavigate();
  const user = authService.getUser();

  const handleLogout = async () => {
    try {
      await authService.logoutUser();
      navigate("/login");
    } catch (error) {
      console.error("Logout failed:", error);
      // Force logout even if API call fails
      navigate("/login");
    }
  };

  return (
    <nav className="w-full flex items-center justify-between py-4 px-10 bg-white shadow-sm">
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 bg-blue-600 rounded-md"></div>
        <h1 className="text-2xl font-semibold">Incorta</h1>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex flex-col items-end">
          <p className="text-sm font-medium text-gray-700">{user?.full_name}</p>
          <p className="text-xs text-gray-500">{user?.role === "hr_manager" ? "HR Manager" : "Hiring Manager"}</p>
        </div>
        <button
          onClick={handleLogout}
          className="ml-4 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition flex items-center gap-2"
          title="Logout"
        >
          <FiLogOut size={20} />
          <span className="text-sm font-medium">Logout</span>
        </button>
      </div>
    </nav>
  );
}
