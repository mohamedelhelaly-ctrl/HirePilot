import { useNavigate } from "react-router-dom";
import * as authService from "../services/authService";
import { FiLogOut } from "react-icons/fi";
import Button from "./button";

function getInitials(name) {
  if (!name) return "?";
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .substring(0, 2)
    .toUpperCase();
}

export default function Navbar({ compact = false }) {
  const navigate = useNavigate();
  const user = authService.getUser();

  const handleLogout = async () => {
    try {
      await authService.logoutUser();
      navigate("/login");
    } catch (error) {
      console.error("Logout failed:", error);
      navigate("/login");
    }
  };

  return (
    <nav
      className={`sticky top-0 z-30 w-full flex items-center justify-between px-10 bg-surface border-b border-border shadow-[0_1px_0_rgb(0_0_0_/_0.04)] ${
        compact ? "h-[52px]" : "h-[68px]"
      }`}
    >
      <div className="flex items-center gap-2.5">
        <img src="/favicon.svg" alt="" className={compact ? "h-7 w-7 rounded-md" : "h-9 w-9 rounded-lg"} />
        <div>
          <h1 className={`font-bold text-gray-900 leading-tight ${compact ? "text-base" : "text-lg"}`}>
            Incorta HR
          </h1>
          {!compact && (
            <p className="text-[11px] text-muted font-medium">AI Recruitment Assistant</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className={`rounded-full bg-gradient-to-br from-brand-600 to-brand-800 flex items-center justify-center text-white font-bold ${compact ? "h-8 w-8 text-[10px]" : "h-9 w-9 text-xs"}`}>
            {getInitials(user?.full_name)}
          </div>
          <div className="hidden sm:flex flex-col items-end">
            <p className="text-sm font-semibold text-gray-900">{user?.full_name}</p>
            <p className="text-xs text-muted">
              {user?.role === "hr_manager" ? "HR Manager" : "Hiring Manager"}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          title={
            <span className="flex items-center gap-2">
              <FiLogOut size={16} />
              <span>Logout</span>
            </span>
          }
        />
      </div>
    </nav>
  );
}
