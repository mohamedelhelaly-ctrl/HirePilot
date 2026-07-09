import { useState, useEffect } from "react";
import { FiX, FiLoader, FiCalendar, FiClock, FiVideo, FiAlertCircle } from "react-icons/fi";

const INTERVIEW_TYPES = [
  { value: "hr_screen", label: "HR Screening" },
  { value: "technical", label: "Technical Interview" },
  { value: "behavioral", label: "Behavioral Interview" },
  { value: "final", label: "Final Round" },
];

const InterviewSchedulingModal = ({
  isOpen,
  onClose,
  mode = "create", // "create" | "manage"
  candidateName,
  candidateEmail,
  interviewSession,
  availableSlots = [],
  isLoadingSlots = false,
  onFetchSlots,
  onSubmitSchedule,
  onReschedule,
  onCancel,
}) => {
  const [viewState, setViewState] = useState(mode === "create" ? "create" : "view");
  const [interviewType, setInterviewType] = useState("hr_screen");
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setViewState(mode === "create" ? "create" : "view");
      setSelectedSlot(null);
      if (mode === "create") {
        setInterviewType("hr_screen");
      }
    }
  }, [isOpen, mode]);

  if (!isOpen) return null;
  // If in manage mode, we require the session to be loaded
  if (mode === "manage" && !interviewSession) return null;

  // Handlers
  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedSlot) return;
    try {
      setIsSubmitting(true);
      await onSubmitSchedule({
        interviewType,
        startTime: selectedSlot.start,
        endTime: selectedSlot.end,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRescheduleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedSlot) return;
    try {
      setIsSubmitting(true);
      await onReschedule(interviewSession.id, {
        newStartTime: selectedSlot.start,
        newEndTime: selectedSlot.end,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelSubmit = async () => {
    try {
      setIsSubmitting(true);
      await onCancel(interviewSession.id);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Format helpers
  const formatDateDisplay = (dateStr) => {
    if (!dateStr) return "Not set";
    const date = new Date(dateStr + "T00:00:00");
    const options = { weekday: "short", month: "short", day: "numeric", year: "numeric" };
    return date.toLocaleDateString("en-US", options);
  };

  const formatDateTimeDisplay = (isoStr) => {
    if (!isoStr) return "Not set";
    const date = new Date(isoStr);
    return date.toLocaleString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const formatTimeDisplay = (isoStr) => {
    if (!isoStr) return "Not set";
    const date = new Date(isoStr);
    return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  };

  // Group available slots by date
  const slotsByDate = availableSlots.reduce((acc, slot) => {
    const date = slot.start.split("T")[0];
    if (!acc[date]) acc[date] = [];
    acc[date].push(slot);
    return acc;
  }, {});

  // ── Common Subcomponents ──────────────────────────────────────────────

  const renderSlotPicker = () => (
    <div>
      <label className="block text-sm font-semibold text-gray-900 mb-2">
        Select Time Slot
      </label>

      {isLoadingSlots ? (
        <div className="flex items-center justify-center py-8 border border-gray-200 rounded-lg bg-gray-50">
          <FiLoader className="animate-spin text-blue-600 mr-2" />
          <span className="text-sm text-gray-600">Loading available slots...</span>
        </div>
      ) : availableSlots.length === 0 ? (
        <div className="text-center py-6 px-4 bg-gray-50 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-600">No available slots found</p>
        </div>
      ) : (
        <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg bg-gray-50">
          {Object.entries(slotsByDate).map(([date, slots]) => (
            <div key={date}>
              <div className="px-4 py-2 bg-gray-100 border-b border-gray-200 sticky top-0">
                <div className="flex items-center gap-2">
                  <FiCalendar size={14} className="text-gray-600" />
                  <span className="text-xs font-semibold text-gray-700 uppercase">
                    {formatDateDisplay(date)}
                  </span>
                </div>
              </div>
              <div className="p-2 space-y-1">
                {slots.map((slot, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSelectedSlot(slot)}
                    className={`w-full text-left px-3 py-2 rounded text-sm font-medium transition flex items-center gap-2 ${
                      selectedSlot === slot
                        ? "bg-blue-600 text-white border border-blue-700"
                        : "bg-white border border-gray-200 text-gray-700 hover:border-blue-300 hover:bg-blue-50"
                    }`}
                  >
                    <FiClock size={14} />
                    {formatTimeDisplay(slot.start)} - {formatTimeDisplay(slot.end)}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  // ── CREATE VIEW ────────────────────────────────────────────────────────

  const renderCreateContent = () => (
    <form onSubmit={handleScheduleSubmit} className="p-6 space-y-4">
      {/* Candidate Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <p className="text-xs font-semibold text-blue-700 uppercase tracking-wider">Candidate</p>
        <p className="text-sm font-semibold text-gray-900 mt-1">{candidateName}</p>
        <p className="text-xs text-gray-600">{candidateEmail}</p>
      </div>

      {/* Interview Type Selector */}
      <div>
        <label className="block text-sm font-semibold text-gray-900 mb-2">
          Interview Type
        </label>
        <select
          value={interviewType}
          onChange={(e) => {
            const newType = e.target.value;
            setInterviewType(newType);
            setSelectedSlot(null);
            if (onFetchSlots) onFetchSlots(newType);
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {INTERVIEW_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      {renderSlotPicker()}

      {/* Selected Slot Summary */}
      {selectedSlot && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <p className="text-xs font-semibold text-green-700 uppercase tracking-wider">Selected</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">
            {formatDateDisplay(selectedSlot.start.split("T")[0])}
          </p>
          <p className="text-sm text-gray-700 mt-1">
            {formatTimeDisplay(selectedSlot.start)} - {formatTimeDisplay(selectedSlot.end)}
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-border">
        <button
          type="button"
          onClick={onClose}
          className="flex-1 px-4 py-2 text-sm font-semibold text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting || !selectedSlot}
          className={`flex-1 px-4 py-2 text-sm font-semibold rounded-lg transition flex items-center justify-center gap-2 ${
            isSubmitting || !selectedSlot
              ? "bg-gray-300 text-gray-600 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {isSubmitting && <FiLoader className="animate-spin" size={16} />}
          {isSubmitting ? "Scheduling..." : "Schedule Interview"}
        </button>
      </div>
    </form>
  );

  // ── MANAGE: VIEW CONTENT ────────────────────────────────────────────────

  const renderViewContent = () => (
    <div className="p-6 space-y-6">
      <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5 text-center">
        <div className="mx-auto w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mb-3">
          <FiCalendar size={24} />
        </div>
        <h3 className="text-lg font-bold text-gray-900 mb-1">{candidateName}</h3>
        <p className="text-sm font-semibold text-indigo-700 capitalize">
          {interviewSession.interview_type.replace("_", " ")} Interview
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <div className="mt-1 text-gray-400">
            <FiClock size={18} />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Scheduled Time</p>
            <p className="text-sm text-gray-600 mt-0.5">
              {formatDateTimeDisplay(interviewSession.scheduled_start_time)}
              {" - "}
              {formatTimeDisplay(interviewSession.scheduled_end_time)}
            </p>
          </div>
        </div>

        {interviewSession.google_meet_link && (
          <div className="flex items-start gap-3">
            <div className="mt-1 text-blue-500">
              <FiVideo size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Google Meet</p>
              <a
                href={interviewSession.google_meet_link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline mt-0.5 inline-block"
              >
                Join Meeting
              </a>
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-3 pt-4 border-t border-border">
        <button
          type="button"
          onClick={() => setViewState("cancel")}
          className="flex-1 px-4 py-2 text-sm font-semibold text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition"
        >
          Cancel Interview
        </button>
        <button
          type="button"
          onClick={() => {
            setViewState("reschedule");
            if (onFetchSlots) onFetchSlots();
          }}
          className="flex-1 px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition"
        >
          Reschedule
        </button>
      </div>
    </div>
  );

  // ── MANAGE: RESCHEDULE CONTENT ──────────────────────────────────────────

  const renderRescheduleContent = () => (
    <form onSubmit={handleRescheduleSubmit} className="p-6 space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <p className="text-xs font-semibold text-blue-700 uppercase tracking-wider">
          Current Time
        </p>
        <p className="text-sm font-semibold text-gray-900 mt-1">
          {formatDateTimeDisplay(interviewSession.scheduled_start_time)}
        </p>
      </div>

      {renderSlotPicker()}

      <div className="flex gap-3 pt-4 border-t border-border">
        <button
          type="button"
          onClick={() => setViewState("view")}
          className="flex-1 px-4 py-2 text-sm font-semibold text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
        >
          Back
        </button>
        <button
          type="submit"
          disabled={isSubmitting || !selectedSlot}
          className={`flex-1 px-4 py-2 text-sm font-semibold rounded-lg transition flex items-center justify-center gap-2 ${
            isSubmitting || !selectedSlot
              ? "bg-gray-300 text-gray-600 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {isSubmitting && <FiLoader className="animate-spin" size={16} />}
          {isSubmitting ? "Updating..." : "Confirm Reschedule"}
        </button>
      </div>
    </form>
  );

  // ── MANAGE: CANCEL CONTENT ──────────────────────────────────────────────

  const renderCancelContent = () => (
    <div className="p-6 space-y-5">
      <div className="bg-red-50 text-red-700 p-4 rounded-xl flex items-start gap-3">
        <FiAlertCircle size={20} className="mt-0.5 shrink-0" />
        <div>
          <h4 className="font-bold text-red-800">Cancel Interview?</h4>
          <p className="text-sm mt-1 text-red-700/90">
            This will delete the event from Google Calendar and send a cancellation email to{" "}
            <strong>{candidateName}</strong>. This action cannot be undone.
          </p>
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={() => setViewState("view")}
          disabled={isSubmitting}
          className="flex-1 px-4 py-2 text-sm font-semibold text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
        >
          Keep Interview
        </button>
        <button
          type="button"
          onClick={handleCancelSubmit}
          disabled={isSubmitting}
          className={`flex-1 px-4 py-2 text-sm font-semibold rounded-lg transition flex items-center justify-center gap-2 ${
            isSubmitting
              ? "bg-red-400 text-white cursor-not-allowed"
              : "bg-red-600 text-white hover:bg-red-700"
          }`}
        >
          {isSubmitting && <FiLoader className="animate-spin" size={16} />}
          {isSubmitting ? "Cancelling..." : "Yes, Cancel It"}
        </button>
      </div>
    </div>
  );

  return (
    <>
      <div className="fixed inset-0 bg-black/45 z-50 transition-opacity" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-surface rounded-xl shadow-[0_24px_80px_rgb(0_0_0_/_0.2)] w-full max-w-md overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-gray-50/50">
            <h2 className="text-lg font-bold text-gray-900">
              {viewState === "create" && "Schedule Interview"}
              {viewState === "view" && "Manage Interview"}
              {viewState === "reschedule" && "Reschedule Interview"}
              {viewState === "cancel" && "Cancel Interview"}
            </h2>
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="p-1.5 hover:bg-gray-200 rounded-lg transition text-gray-500"
            >
              <FiX size={20} />
            </button>
          </div>

          {/* Content Router */}
          {viewState === "create" && renderCreateContent()}
          {viewState === "view" && renderViewContent()}
          {viewState === "reschedule" && renderRescheduleContent()}
          {viewState === "cancel" && renderCancelContent()}
        </div>
      </div>
    </>
  );
};

export default InterviewSchedulingModal;
