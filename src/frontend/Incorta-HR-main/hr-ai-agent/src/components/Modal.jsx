import { FiX } from "react-icons/fi";

export default function Modal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  wide = false,
  loading = false,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
      <div
        className={`bg-surface rounded-xl shadow-[0_24px_80px_rgb(0_0_0_/_0.2)] w-full mx-4 max-h-[90vh] overflow-y-auto ${
          wide ? "max-w-4xl" : "max-w-lg"
        }`}
      >
        {title && (
          <div className="sticky top-0 flex items-center justify-between p-6 border-b border-border bg-surface z-10">
            <h2 className="text-xl font-bold text-gray-900">{title}</h2>
            <button
              onClick={onClose}
              disabled={loading}
              className="text-gray-400 hover:text-gray-600 transition p-1 rounded-lg hover:bg-gray-100"
            >
              <FiX size={22} />
            </button>
          </div>
        )}
        <div className={title ? "" : "relative"}>
          {!title && (
            <button
              onClick={onClose}
              disabled={loading}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition p-1 rounded-lg hover:bg-gray-100 z-10"
            >
              <FiX size={22} />
            </button>
          )}
          {children}
        </div>
        {footer && (
          <div className="flex gap-3 justify-end p-6 border-t border-border">{footer}</div>
        )}
      </div>
    </div>
  );
}
