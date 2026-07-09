import { FiCheckCircle, FiAlertCircle, FiX, FiInfo } from "react-icons/fi";
import { useEffect, useState } from "react";

export default function Toast({ notification, onClose }) {
  const [isClosing, setIsClosing] = useState(false);

  useEffect(() => {
    if (!notification) return;

    // Reset closing state when new notification arrives
    setIsClosing(false);

    const timer = setTimeout(() => {
      setIsClosing(true);
      setTimeout(onClose, 300);
    }, 4000);

    return () => clearTimeout(timer);
  }, [notification, onClose]);

  if (!notification) return null;

  const bgColor = {
    success: "bg-green-50 border-green-200",
    error: "bg-red-50 border-red-200",
    info: "bg-blue-50 border-blue-200",
  }[notification.type];

  const iconColor = {
    success: "text-green-600",
    error: "text-red-600",
    info: "text-blue-600",
  }[notification.type];

  const icon = {
    success: <FiCheckCircle size={20} />,
    error: <FiAlertCircle size={20} />,
    info: <FiInfo size={20} />,
  }[notification.type];

  return (
    <div
      className={`fixed top-6 right-6 z-50 transition-all duration-300 ${
        isClosing ? "opacity-0 translate-x-full" : "opacity-100 translate-x-0"
      }`}
    >
      <div
        className={`flex items-start gap-3 p-4 rounded-lg border shadow-lg ${bgColor}`}
      >
        <div className={`flex-shrink-0 ${iconColor}`}>{icon}</div>
        <div className="flex-1">
          <h3 className={`font-semibold ${iconColor}`}>{notification.title}</h3>
          {notification.message && (
            <p className="text-sm text-gray-600 mt-1">{notification.message}</p>
          )}
        </div>
        <button
          onClick={() => {
            setIsClosing(true);
            setTimeout(onClose, 300);
          }}
          className={`flex-shrink-0 ${iconColor} hover:opacity-70 transition`}
        >
          <FiX size={18} />
        </button>
      </div>
    </div>
  );
}
