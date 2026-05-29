import { FiMapPin, FiUsers, FiBell, FiMoreVertical, FiEdit, FiTrash2 } from "react-icons/fi";
import Badge from "./badge";

export default function RequisitionCard({ requisition, onEdit, onDelete }) {
  const {
    id,
    title,
    description,
    department,
    location,
    candidates = 0,
    new_applicants = 0,
  } = requisition;

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow duration-300 overflow-hidden h-full flex flex-col">
      {/* Header Section */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-start justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-800 flex-1 leading-tight">
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
        <div className="px-6 py-4 flex-1">
          <p className="text-gray-600 text-sm line-clamp-2 leading-relaxed">
            {description}
          </p>
        </div>
      )}

      {/* Location Section */}
      {location && (
        <div className="px-6 py-3 flex items-center gap-2 text-gray-600 border-t border-gray-100">
          <FiMapPin size={16} className="text-gray-400" />
          <span className="text-sm">{location}</span>
        </div>
      )}

      {/* Stats Section */}
      <div className="px-6 py-4 bg-gray-50 flex gap-4 border-t border-gray-100">
        <div className="flex items-center gap-2">
          <FiUsers size={16} className="text-blue-600" />
          <div>
            <div className="text-sm text-gray-600">Candidates</div>
            <div className="font-semibold text-gray-800">{candidates}</div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <FiBell size={16} className="text-orange-600" />
          <div>
            <div className="text-sm text-gray-600">New Apps</div>
            <div className="font-semibold text-gray-800">{new_applicants}</div>
          </div>
        </div>
      </div>

      {/* Action Section */}
      <div className="px-6 py-4 border-t border-gray-100">
        <button className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition font-medium text-sm">
          View Details
        </button>
      </div>
    </div>
  );
}
