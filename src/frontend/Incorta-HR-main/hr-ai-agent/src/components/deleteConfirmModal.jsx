import { FiAlertTriangle, FiX } from "react-icons/fi";
import Button from "./button";

export default function DeleteConfirmModal({ isOpen, requisitionTitle, onClose, onConfirm, loading = false }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
      <div className="bg-surface rounded-xl shadow-[0_24px_80px_rgb(0_0_0_/_0.2)] max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-red-100 rounded-full">
              <FiAlertTriangle className="text-red-600" size={22} />
            </div>
            <h2 className="text-xl font-bold text-gray-900">Delete Requisition</h2>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-gray-400 hover:text-gray-600 transition p-1 rounded-lg hover:bg-gray-100"
          >
            <FiX size={22} />
          </button>
        </div>

        <div className="p-6">
          <p className="text-gray-700 mb-2">Are you sure you want to delete this requisition?</p>
          <p className="text-muted text-sm">
            <span className="font-semibold text-gray-900">{requisitionTitle}</span> will be marked
            as inactive and cannot be recovered.
          </p>
        </div>

        <div className="flex gap-3 justify-end p-6 border-t border-border">
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} disabled={loading}>
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Deleting...
              </>
            ) : (
              "Delete"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
