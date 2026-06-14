import { FiMapPin, FiEdit, FiTrash2, FiCalendar } from "react-icons/fi";
import Badge from "./badge";
import Button from "./button";
import Card from "./Card";
import { useNavigate } from "react-router-dom";

const JD_SNIPPET_LEN = 220;

export default function RequisitionCard({ requisition, onEdit, onDelete }) {
  const navigate = useNavigate();
  const { id, title, description, department, location, created_at } = requisition;

  const formatDate = (dateString) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const jdSnippet =
    description && description.length > JD_SNIPPET_LEN
      ? description.slice(0, JD_SNIPPET_LEN).trimEnd() + "…"
      : description;

  return (
    <Card accentColor="#1d4ed8" interactive className="flex flex-col h-full group shadow-[0_4px_24px_rgb(0_0_0_/_0.06)]">
      <div className="px-5 py-4 flex flex-col gap-2.5 flex-1">
        {/* Top row: badge + actions */}
        <div className="flex items-start justify-between gap-3">
          {department ? <Badge text={department} /> : <span />}
          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit?.(requisition);
              }}
              className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-brand-600 hover:bg-blue-50 rounded-lg border border-transparent hover:border-gray-200 transition"
              title="Edit"
            >
              <FiEdit size={14} />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete?.(id);
              }}
              className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg border border-transparent hover:border-gray-200 transition"
              title="Delete"
            >
              <FiTrash2 size={14} />
            </button>
          </div>
        </div>

        {/* Title */}
        <h3 className="m-0 text-[1.2rem] font-bold leading-[1.2] text-gray-900" title={title}>
          {title}
        </h3>

        {/* Meta + JD */}
        <div className="grid grid-cols-1 sm:grid-cols-[120px_1fr] gap-3 flex-1">
          <div className="flex flex-col gap-1.5 text-[0.9rem] text-muted">
            {location && (
              <div className="flex items-center gap-1.5">
                <FiMapPin size={12} className="shrink-0 text-gray-400" />
                <span className="truncate" title={location}>
                  {location}
                </span>
              </div>
            )}
            {created_at && (
              <div className="flex items-center gap-1.5">
                <FiCalendar size={12} className="shrink-0 text-gray-400" />
                <span>{formatDate(created_at)}</span>
              </div>
            )}
          </div>

          {jdSnippet && (
            <p className="text-[13px] text-muted leading-relaxed line-clamp-3 m-0">{jdSnippet}</p>
          )}
        </div>

        {/* CTA */}
        <Button
          variant="primary"
          size="sm"
          className="w-full mt-1"
          onClick={() => navigate(`/requisition/${id}`)}
        >
          View Details →
        </Button>
      </div>
    </Card>
  );
}
