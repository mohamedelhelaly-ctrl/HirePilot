import DashboardLayout from "../layouts/hrHomePageLayout";
import Toast from "../components/toast";
import InterviewModal from "../components/interviewModal";
import CandidateDetailsModal from "../components/candidateDetailsModal";
import RequisitionModal from "../components/requisitionModal";
import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import {
  FiArrowLeft,
  FiUpload,
  FiCheck,
  FiX,
  FiChevronDown,
  FiFileText,
  FiEdit3,
} from "react-icons/fi";
import { MdMic } from "react-icons/md";
import { fetchRequisitionById, updateRequisition } from "../services/requisitionService";
import {
  fetchApplicationsByRequisition,
  fetchCandidateById,
  updateApplicationStatus,
  uploadCVs,
} from "../services/candidateService";

// ── Status helpers ────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  { value: "interview_scheduled", label: "Interview Scheduled" },
  { value: "interview_completed", label: "Interview Completed" },
  { value: "offer_extended", label: "Offer Extended" },
  { value: "hired", label: "Hired" },
  { value: "rejected", label: "Rejected" },
];

const STATUS_COLORS = {
  new: { bg: "bg-gray-100", text: "text-gray-700", label: "New" },
  screening_pending: { bg: "bg-yellow-50", text: "text-yellow-700", label: "Screening" },
  screening_passed: { bg: "bg-green-50", text: "text-green-700", label: "Shortlisted" },
  screening_rejected: { bg: "bg-red-50", text: "text-red-600", label: "Rejected" },
  assessment_sent: { bg: "bg-blue-50", text: "text-blue-700", label: "Assessment Sent" },
  assessment_completed: { bg: "bg-blue-50", text: "text-blue-700", label: "Assessment Done" },
  interview_scheduled: { bg: "bg-indigo-50", text: "text-indigo-700", label: "Interview Scheduled" },
  interview_completed: { bg: "bg-purple-50", text: "text-purple-700", label: "Interview Done" },
  offer_extended: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Offer Extended" },
  hired: { bg: "bg-green-50", text: "text-green-700", label: "Hired" },
  rejected: { bg: "bg-red-50", text: "text-red-600", label: "Rejected" },
  withdrawn: { bg: "bg-gray-100", text: "text-gray-500", label: "Withdrawn" },
};

const getStatusStyle = (status) =>
  STATUS_COLORS[status] || { bg: "bg-gray-100", text: "text-gray-600", label: status };

// ── Score bar color ───────────────────────────────────────────────────────────

const getScoreColor = (score) => {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  if (score >= 40) return "bg-orange-500";
  return "bg-red-500";
};

// ============================================================================
// Component
// ============================================================================

export default function RequisitionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // Data states
  const [requisition, setRequisition] = useState(null);
  const [applications, setApplications] = useState([]);
  const [candidateMap, setCandidateMap] = useState({}); // candidateId → candidate data
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // UI states
  const [notification, setNotification] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [openDropdownId, setOpenDropdownId] = useState(null);
  const [updatingStatusId, setUpdatingStatusId] = useState(null);

  // Modal states
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [selectedApplication, setSelectedApplication] = useState(null);
  const [isCandidateModalOpen, setIsCandidateModalOpen] = useState(false);

  // Interview modal states
  const [isInterviewModalOpen, setIsInterviewModalOpen] = useState(false);
  const [interviewTarget, setInterviewTarget] = useState(null);

  // JD viewer modal state
  const [isJdModalOpen, setIsJdModalOpen] = useState(false);

  // Edit modal states
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ── Load data on mount ────────────────────────────────────────────────────

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Fetch requisition details
      const reqData = await fetchRequisitionById(id);
      setRequisition(reqData);

      // 2. Fetch applications for this requisition
      const apps = await fetchApplicationsByRequisition(id);
      setApplications(apps);

      // 3. Fetch candidate info for each unique candidate_id
      const uniqueCandidateIds = [...new Set(apps.map((a) => a.candidate_id))];
      const candidatePromises = uniqueCandidateIds.map(async (cid) => {
        try {
          const cand = await fetchCandidateById(cid);
          return [cid, cand];
        } catch {
          return [cid, { full_name: "Unknown", email: "", phone: "", linkedin_url: "" }];
        }
      });

      const candidateEntries = await Promise.all(candidatePromises);
      const map = Object.fromEntries(candidateEntries);
      setCandidateMap(map);
    } catch (err) {
      setError(err.message || "Failed to load requisition details");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // ── Statistics ─────────────────────────────────────────────────────────────

  const totalCVs = applications.length;
  const screened = applications.filter(
    (a) => a.status !== "new" && a.status !== "screening_pending"
  ).length;
  const shortlisted = applications.filter(
    (a) => a.status === "screening_passed"
  ).length;
  const rejected = applications.filter(
    (a) => a.status === "screening_rejected" || a.status === "rejected"
  ).length;
  const avgScore =
    applications.length > 0
      ? (
          applications.reduce((sum, a) => sum + (a.combined_score || 0), 0) /
          applications.length
        ).toFixed(1)
      : "—";

  // ── Handlers ───────────────────────────────────────────────────────────────

  const showNotification = (type, title, message = "") => {
    setNotification({ type, title, message });
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    try {
      setUploading(true);
      await uploadCVs(id, files);
      showNotification(
        "success",
        "CVs Uploaded",
        `${files.length} file(s) uploaded and vectorized successfully.`
      );
      // Reload to reflect new applications
      await loadData();
    } catch (err) {
      showNotification("error", "Upload Failed", err.message);
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleStatusChange = async (applicationId, newStatus) => {
    try {
      setUpdatingStatusId(applicationId);
      await updateApplicationStatus(applicationId, newStatus);
      setApplications((prev) =>
        prev.map((a) => (a.id === applicationId ? { ...a, status: newStatus } : a))
      );
      const label = STATUS_OPTIONS.find((s) => s.value === newStatus)?.label || newStatus;
      showNotification("success", "Status Updated", `Application status changed to "${label}".`);
    } catch (err) {
      showNotification("error", "Update Failed", err.message);
    } finally {
      setUpdatingStatusId(null);
      setOpenDropdownId(null);
    }
  };

  const handleCandidateClick = (application) => {
    const candidate = candidateMap[application.candidate_id];
    setSelectedCandidate({
      ...candidate,
      name: candidate?.full_name || "Unknown",
      score: application.combined_score
        ? Math.round(application.combined_score * 100)
        : 0,
      status: application.status,
    });
    setSelectedApplication(application);
    setIsCandidateModalOpen(true);
  };

  const handleInterviewClick = (application) => {
    const candidate = candidateMap[application.candidate_id];
    setInterviewTarget({
      candidateName: candidate?.full_name || "Candidate",
      applicationId: application.id,
      requisitionId: parseInt(id),
    });
    setIsInterviewModalOpen(true);
  };

  const handleComingSoon = (featureName) => {
    showNotification("info", "Coming Soon", `${featureName} feature is coming soon!`);
  };

  const handleViewJD = () => {
    setIsJdModalOpen(true);
  };

  const handleEdit = () => {
    setIsEditModalOpen(true);
  };

  const handleEditSubmit = async (formData) => {
    try {
      setIsSubmitting(true);
      const updated = await updateRequisition(id, formData);
      setRequisition(updated);
      setIsEditModalOpen(false);
      showNotification("success", "Requisition Updated", `"${formData.title}" has been updated.`);
    } catch (err) {
      showNotification("error", "Update Failed", err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Close dropdown when clicking outside ───────────────────────────────────

  useEffect(() => {
    const handleClickOutside = () => setOpenDropdownId(null);
    if (openDropdownId !== null) {
      document.addEventListener("click", handleClickOutside);
    }
    return () => document.removeEventListener("click", handleClickOutside);
  }, [openDropdownId]);

  // ── Render ─────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <DashboardLayout>
        <div className="w-full mx-auto animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mb-6" />
          <div className="h-40 bg-gray-200 rounded-xl mb-6" />
          <div className="h-96 bg-gray-200 rounded-xl" />
        </div>
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="w-full mx-auto">
          <button
            onClick={() => navigate("/hr")}
            className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition mb-6"
          >
            <FiArrowLeft size={18} /> Back to Requisitions
          </button>
          <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
            {error}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="w-full mx-auto">
        {/* ── Back Link ─────────────────────────────────────────────────── */}
        <button
          onClick={() => navigate("/hr")}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition mb-4 group"
        >
          <FiArrowLeft size={16} className="group-hover:-translate-x-0.5 transition-transform" />
          <span>Requisitions</span>
        </button>

        {/* ── Header Section ────────────────────────────────────────────── */}
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6 mb-8">
          {/* Left — Title & Meta */}
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900 mb-1">
              {requisition?.title}
            </h1>
            <p className="text-gray-500 text-base mb-3">
              {requisition?.department}
              {requisition?.location ? ` · ${requisition.location}` : ""}
            </p>
            <div className="flex flex-wrap gap-4 text-sm text-gray-500">
              {requisition?.hiring_manager_id && (
                <span>
                  <span className="font-medium text-gray-600 mr-1">CREATED BY</span>
                  Hiring Manager #{requisition.hiring_manager_id}
                </span>
              )}
            </div>
          </div>

          {/* Right — Stats + Actions */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Stat Boxes */}
            {[
              { label: "CVs", value: totalCVs },
              { label: "Screened", value: screened },
              { label: "Shortlisted", value: shortlisted },
              { label: "Rejected", value: rejected },
              { label: "AVG Score", value: avgScore },
            ].map(({ label, value }) => (
              <div
                key={label}
                className="flex flex-col items-center px-4 py-2.5 bg-white border border-gray-200 rounded-lg min-w-[70px] shadow-sm"
              >
                <span className="text-xl font-bold text-gray-800">{value}</span>
                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">
                  {label}
                </span>
              </div>
            ))}

            {/* View JD */}
            <button
              onClick={handleViewJD}
              className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition bg-white shadow-sm"
            >
              <FiFileText size={16} />
              View JD
            </button>

            {/* Edit */}
            <button
              onClick={handleEdit}
              className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition bg-white shadow-sm"
            >
              <FiEdit3 size={16} />
              Edit
            </button>
          </div>
        </div>

        {/* ── Candidates Section ────────────────────────────────────────── */}
        <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${openDropdownId !== null ? 'overflow-visible' : 'overflow-hidden'}`}>
          {/* Section Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-gray-900">Candidates</h2>
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-gray-100 text-sm font-bold text-gray-600">
                {totalCVs}
              </span>
            </div>

            {/* Upload CVs Button */}
            <button
              onClick={handleUploadClick}
              disabled={uploading}
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
            >
              <FiUpload size={16} />
              {uploading ? "Uploading..." : "Upload CVs"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx"
              onChange={handleFileChange}
              className="hidden"
            />
          </div>

          {/* Table */}
          {applications.length === 0 ? (
            <div className="px-6 py-16 text-center text-gray-400">
              <p className="text-lg font-medium mb-1">No candidates yet</p>
              <p className="text-sm">Upload CVs to get started</p>
            </div>
          ) : (
            <div className={openDropdownId !== null ? 'overflow-visible' : 'overflow-x-auto'}>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="px-6 py-3 font-semibold w-10">#</th>
                    <th className="px-6 py-3 font-semibold">Candidate</th>
                    <th className="px-6 py-3 font-semibold w-48">Score</th>
                    <th className="px-6 py-3 font-semibold w-40">Status</th>
                    <th className="px-6 py-3 font-semibold w-28 text-center">Actions</th>
                    <th className="px-6 py-3 font-semibold w-44 text-center">
                      Question Generation
                    </th>
                    <th className="px-6 py-3 font-semibold w-32 text-center">Interview</th>
                  </tr>
                </thead>
                <tbody>
                  {applications.map((app, index) => {
                    const candidate = candidateMap[app.candidate_id];
                    const score = app.combined_score
                      ? Math.round(app.combined_score * 100)
                      : 0;
                    const statusStyle = getStatusStyle(app.status);
                    const isDropdownOpen = openDropdownId === app.id;

                    return (
                      <tr
                        key={app.id}
                        className="border-b border-gray-50 hover:bg-gray-50/60 transition group"
                      >
                        {/* # */}
                        <td className="px-6 py-4 text-gray-400 font-medium">
                          {index + 1}
                        </td>

                        {/* Candidate Name */}
                        <td className="px-6 py-4">
                          <button
                            onClick={() => handleCandidateClick(app)}
                            className="text-sm font-semibold text-gray-900 hover:text-blue-600 hover:underline transition text-left"
                          >
                            {candidate?.full_name || "Unknown Candidate"}
                          </button>
                        </td>

                        {/* Score */}
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-24 overflow-hidden rounded-full bg-gray-200 h-1.5">
                              <div
                                className={`h-full rounded-full ${getScoreColor(score)} transition-all duration-500`}
                                style={{ width: `${score}%` }}
                              />
                            </div>
                            <span className="text-sm font-semibold text-gray-700 min-w-[30px]">
                              {score}
                            </span>
                          </div>
                        </td>

                        {/* Status */}
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center rounded-md ${statusStyle.bg} px-2.5 py-1 text-xs font-semibold ${statusStyle.text}`}
                          >
                            {statusStyle.label}
                          </span>
                        </td>

                        {/* Actions — Approve / Reject dropdown */}
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-center gap-1.5 relative">
                            {/* Quick actions: Check / X */}
                            <button
                              onClick={() =>
                                handleStatusChange(app.id, "interview_scheduled")
                              }
                              disabled={updatingStatusId === app.id}
                              className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-200 text-green-600 hover:bg-green-50 hover:border-green-200 transition disabled:opacity-50"
                              title="Schedule Interview"
                            >
                              <FiCheck size={16} />
                            </button>
                            <button
                              onClick={() =>
                                handleStatusChange(app.id, "rejected")
                              }
                              disabled={updatingStatusId === app.id}
                              className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-200 text-red-500 hover:bg-red-50 hover:border-red-200 transition disabled:opacity-50"
                              title="Reject"
                            >
                              <FiX size={16} />
                            </button>

                            {/* Dropdown for more statuses */}
                            <div className="relative">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setOpenDropdownId(isDropdownOpen ? null : app.id);
                                }}
                                className="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-200 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition"
                              >
                                <FiChevronDown size={14} />
                              </button>

                              {isDropdownOpen && (
                                <div className="absolute right-0 top-10 z-30 w-52 bg-white border border-gray-200 rounded-xl shadow-xl py-1.5 animate-in fade-in slide-in-from-top-2">
                                  {STATUS_OPTIONS.map((opt) => (
                                    <button
                                      key={opt.value}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleStatusChange(app.id, opt.value);
                                      }}
                                      className={`w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 transition flex items-center gap-2 ${
                                        app.status === opt.value
                                          ? "text-blue-600 font-semibold bg-blue-50/50"
                                          : "text-gray-700"
                                      }`}
                                    >
                                      {app.status === opt.value && (
                                        <FiCheck size={14} className="text-blue-600" />
                                      )}
                                      <span
                                        className={
                                          app.status === opt.value ? "" : "ml-5"
                                        }
                                      >
                                        {opt.label}
                                      </span>
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Question Generation — Coming Soon */}
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-center gap-2">
                            <button
                              onClick={() => handleComingSoon("Technical Questions")}
                              className="px-3 py-1.5 text-xs font-semibold text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                            >
                              Tech Q
                            </button>
                            <button
                              onClick={() => handleComingSoon("CBI Questions")}
                              className="px-3 py-1.5 text-xs font-semibold text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                            >
                              CBI Q
                            </button>
                          </div>
                        </td>

                        {/* Interview */}
                        <td className="px-6 py-4">
                          <div className="flex justify-center">
                            <button
                              onClick={() => handleInterviewClick(app)}
                              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition"
                            >
                              <MdMic size={14} />
                              Interview
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── Candidate Detail Slide-Over ───────────────────────────────── */}
        <CandidateDetailsModal
          candidate={selectedCandidate}
          application={selectedApplication}
          isOpen={isCandidateModalOpen}
          onClose={() => {
            setIsCandidateModalOpen(false);
            setSelectedCandidate(null);
            setSelectedApplication(null);
          }}
        />

        {/* ── Interview Modal ──────────────────────────────────────────── */}
        <InterviewModal
          isOpen={isInterviewModalOpen}
          onClose={() => {
            setIsInterviewModalOpen(false);
            setInterviewTarget(null);
          }}
          candidateName={interviewTarget?.candidateName}
          applicationId={interviewTarget?.applicationId}
          requisitionId={interviewTarget?.requisitionId}
        />

        {/* ── View JD Modal ──────────────────────────────────────────── */}
        {isJdModalOpen && (
          <>
            <div className="fixed inset-0 bg-black/50 z-50" onClick={() => setIsJdModalOpen(false)} />
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <div
                className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">Job Description</h2>
                    <p className="text-sm text-gray-500 mt-0.5">{requisition?.title}</p>
                  </div>
                  <button
                    onClick={() => setIsJdModalOpen(false)}
                    className="text-gray-400 hover:text-gray-600 transition p-1.5 hover:bg-gray-100 rounded-lg"
                  >
                    <FiX size={22} />
                  </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-6 py-6">
                  {/* Meta Info */}
                  <div className="flex flex-wrap gap-4 mb-6">
                    {requisition?.department && (
                      <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium">
                        {requisition.department}
                      </div>
                    )}
                    {requisition?.location && (
                      <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium">
                        {requisition.location}
                      </div>
                    )}
                    {requisition?.created_at && (
                      <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 text-gray-500 rounded-lg text-sm">
                        Posted {new Date(requisition.created_at).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        })}
                      </div>
                    )}
                  </div>

                  {/* Description */}
                  <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {requisition?.description || "No description provided."}
                  </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-100 flex justify-end">
                  <button
                    onClick={() => setIsJdModalOpen(false)}
                    className="px-5 py-2.5 bg-gray-100 text-gray-700 rounded-lg font-medium text-sm hover:bg-gray-200 transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── Edit Requisition Modal ────────────────────────────────────── */}
        <RequisitionModal
          isOpen={isEditModalOpen}
          mode="edit"
          requisition={requisition}
          onClose={() => setIsEditModalOpen(false)}
          onSubmit={handleEditSubmit}
          loading={isSubmitting}
        />

        {/* ── Toast ────────────────────────────────────────────────────── */}
        <Toast
          notification={notification}
          onClose={() => setNotification(null)}
        />
      </div>
    </DashboardLayout>
  );
}
