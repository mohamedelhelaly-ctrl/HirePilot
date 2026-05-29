import { FiMapPin, FiUsers, FiBell, FiMoreVertical, FiEdit, FiTrash2, FiCalendar } from "react-icons/fi";
import Badge from "./badge";
import { useState } from "react";

export default function RequisitionCard({ requisition, onEdit, onDelete }) {
  const [isHovering, setIsHovering] = useState(false);
  const {
    id,
    title,
    description,
    department,
    location,
    created_at,
  } = requisition;

  // Format the date
  const formatDate = (dateString) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", { 
      year: "numeric", 
      month: "short", 
      day: "numeric" 
    });
  };

  return (
    <div
      className="relative bg-white rounded-lg shadow hover:shadow-xl transition-all duration-300 overflow-hidden h-full flex flex-col"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* Header Section */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-start justify-between mb-3">
          <h3 
            className="text-lg font-semibold text-gray-800 flex-1 leading-tight"
            title={title}
          >
            {title}
          </h3>
          <div className="flex gap-2 ml-4">
            <button
              onClick={() => onEdit && onEdit(requisition)}
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
              title="Edit"
            >
              <FiEdit size={18} />
            </button>
            <button
              onClick={() => onDelete && onDelete(id)}
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
              title="Delete"
            >
              <FiTrash2 size={18} />
            </button>
          </div>
        </div>

        {department && (
          <div className="flex gap-2">
            <Badge text={department} />
          </div>
        )}
      </div>

      {/* Description Section */}
      {description && (
        <div className="px-6 py-4 flex-1 relative">
          <p 
            className={`text-gray-600 text-sm leading-relaxed transition-all duration-200 ${
              isHovering ? "line-clamp-none" : "line-clamp-2"
            }`}
            title={description}
          >
            {description}
          </p>
          
          {/* Full Description Tooltip on Hover */}
        </div>
      )}

      {/* Location Section */}
      {location && (
        <div className="px-6 py-3 flex items-center gap-2 text-gray-600 border-t border-gray-100">
          <FiMapPin size={16} className="text-gray-400 flex-shrink-0" />
          <span className="text-sm" title={location}>{location}</span>
        </div>
      )}

      {/* Date Section */}
      {created_at && (
        <div className="px-6 py-3 flex items-center gap-2 text-gray-600 border-t border-gray-100">
          <FiCalendar size={16} className="text-gray-400 flex-shrink-0" />
          <span className="text-sm">Posted on {formatDate(created_at)}</span>
        </div>
      )}

      {/* Action Section */}
      <div className="px-6 py-4 border-t border-gray-100">
        <button className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition font-medium text-sm">
          View Details
        </button>
      </div>
    </div>
  );
}
