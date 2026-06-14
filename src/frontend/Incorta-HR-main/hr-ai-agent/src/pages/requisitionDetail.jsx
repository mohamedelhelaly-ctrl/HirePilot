import DashboardLayout from "../layouts/hrHomePageLayout";
import Toast from "../components/toast";
import InterviewModal from "../components/interviewModal";
import CandidateDetailsModal from "../components/candidateDetailsModal";
import RequisitionModal from "../components/requisitionModal";
import ChatDrawer from "../components/chatDrawer";
import Card from "../components/Card";
import Button from "../components/button";
import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import {
  FiArrowLeft,
  FiUpload,
  FiCheck,
  FiX,
  FiChevronDown,
  FiEdit3,
  FiMessageSquare,
  FiLoader,
  FiAlertTriangle,
} from "react-icons/fi";
import { MdMic } from "react-icons/md";
import { fetchRequisitionById, updateRequisition } from "../services/requisitionService";
import {
  fetchApplicationsByRequisition,
  fetchCandidateById,
  updateApplicationStatus,
  generateTechQuestions,
  uploadCVs,
} from "../services/candidateService";
import { executeGraph } from "../services/graphService";

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

  // Chatbot drawer state
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Tech questions modal state
  const [isQuestionsModalOpen, setIsQuestionsModalOpen] = useState(false);
  const [selectedQuestions, setSelectedQuestions] = useState(null);
  const [selectedQuestionsCandidate, setSelectedQuestionsCandidate] = useState(null);

  // Tech questions generation loading state
  const [generatingQuestionId, setGeneratingQuestionId] = useState(null);

  // CV screening state
  const [isScreeningCVs, setIsScreeningCVs] = useState(false);

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
  const interviewScheduled = applications.filter(
    (a) => a.status === "interview_scheduled"
  ).length;
  const offerExtended = applications.filter(
    (a) => a.status === "offer_extended"
  ).length;
  const hired = applications.filter(
    (a) => a.status === "hired"
  ).length;
  const rejected = applications.filter(
    (a) => a.status === "screening_rejected" || a.status === "rejected"
  ).length;

  // ── Unscreened CVs detection ──────────────────────────────────────────────
  // new_candidate_counter is incremented each time a CV is uploaded.
  // It is the sole signal for "unscreened" CVs — status "new" actually means
  // the candidate has ALREADY been screened and is awaiting HR action.
  const newCandidateCounter = requisition?.new_candidate_counter ?? 0;
  const hasUnscreenedCVs = newCandidateCounter > 0;
  const allScreened = applications.length > 0 && newCandidateCounter === 0;

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
      justification: application.justification || null,
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

  const handleGenerateTechQuestions = async (applicationId, candidateName) => {
    try {
      setGeneratingQuestionId(applicationId);
      const questions = await generateTechQuestions(applicationId);
      
      // Update the application in state with the generated questions
      setApplications((prev) =>
        prev.map((a) => 
          a.id === applicationId ? { ...a, tech_questions: questions } : a
        )
      );
      
      showNotification(
        "success",
        "Tech Questions Generated",
        `Generated ${questions.length} technical questions for ${candidateName}.`
      );
    } catch (err) {
      showNotification("error", "Generation Failed", err.message);
    } finally {
      setGeneratingQuestionId(null);
    }
  };

  const handleViewTechQuestions = (questions, candidateName) => {
    setSelectedQuestions(questions);
    setSelectedQuestionsCandidate(candidateName);
    setIsQuestionsModalOpen(true);
  };

  const handleScreenCVs = async () => {
    try {
      setIsScreeningCVs(true);
      showNotification(
        "info",
        "Screening in Progress",
        "Analyzing CVs and scoring candidates..."
      );

      const response = await executeGraph({
        intent: "batch_screening",
        requisition_id: parseInt(id),
      });

      if (response.error) {
        showNotification("error", "Screening Failed", response.error);
      } else {
        showNotification(
          "success",
          "Screening Complete",
          `Scored ${response.result?.candidates_scored || 0} candidates successfully.`
        );
        // Reload data to show updated scores and statuses
        await loadData();
      }
    } catch (err) {
      showNotification("error", "Screening Error", err.message);
    } finally {
      setIsScreeningCVs(false);
    }
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
    <DashboardLayout fullHeight>
      <div className="flex flex-col flex-1 min-h-0 w-full">
        {/* ── Workspace header (talent ws-header pattern) ─────────────────── */}
        <header className="shrink-0 w-full flex flex-wrap items-center gap-x-5 gap-y-2.5 px-6 py-3 bg-surface border-b border-border">
          <div className="flex-1 min-w-[200px]">
            <button
              onClick={() => navigate("/hr")}
              className="block text-[13px] font-semibold text-muted hover:text-brand-600 transition mb-0.5"
            >
              ← Requisitions
            </button>
            <div className="flex items-baseline flex-wrap gap-x-2.5 gap-y-1 mt-0.5 min-w-0">
              <h1 className="m-0 text-[1.2rem] font-bold leading-[1.2] text-gray-900 truncate max-w-full">
                {requisition?.title}
              </h1>
              {(requisition?.department || requisition?.location) && (
                <>
                  <span className="text-[0.85rem] text-muted select-none leading-none">·</span>
                  <span className="text-[0.9rem] text-muted whitespace-nowrap">
                    {[requisition?.department, requisition?.location].filter(Boolean).join(" · ")}
                  </span>
                </>
              )}
              <span className="text-[0.85rem] text-muted select-none leading-none">·</span>
              <button
                type="button"
                onClick={handleViewJD}
                className="p-0 m-0 bg-transparent border-none cursor-pointer text-[0.9rem] text-[#2563eb] underline underline-offset-2 whitespace-nowrap hover:text-brand-700"
              >
                View JD
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <div className="flex flex-wrap items-center gap-2">
              {[
                { label: "CVs", value: totalCVs },
                { label: "Interview Scheduled", value: interviewScheduled },
                { label: "Offer Extended", value: offerExtended },
                { label: "Hired", value: hired },
                { label: "Rejected", value: rejected },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="flex flex-col items-center px-3 py-1.5 min-w-[48px] rounded-lg border border-border bg-canvas"
                >
                  <span className="text-base font-bold leading-none text-gray-900">{value}</span>
                  <span className="text-[9px] font-semibold uppercase tracking-[0.06em] text-muted mt-0.5 whitespace-nowrap">
                    {label}
                  </span>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleScreenCVs}
                disabled={isScreeningCVs || (!hasUnscreenedCVs && (applications.length === 0 || allScreened))}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[10px] text-sm font-semibold transition-all ${
                  isScreeningCVs
                    ? "bg-brand-600 text-white cursor-wait opacity-80"
                    : hasUnscreenedCVs
                    ? "bg-brand-600 text-white hover:bg-brand-700 animate-pulse"
                    : allScreened
                    ? "bg-canvas text-muted border border-border cursor-not-allowed"
                    : applications.length === 0
                    ? "bg-canvas text-muted border border-border cursor-not-allowed"
                    : "bg-brand-600 text-white hover:bg-brand-700"
                }`}
                title={
                  allScreened
                    ? "All CVs have been screened"
                    : applications.length === 0
                    ? "Upload CVs first to screen"
                    : hasUnscreenedCVs
                    ? `${newCandidateCounter} new CV(s) awaiting screening`
                    : "Run batch screening on uploaded CVs"
                }
              >
                {isScreeningCVs ? (
                  <>
                    <FiLoader size={14} className="animate-spin" />
                    Screening...
                  </>
                ) : allScreened ? (
                  <>
                    <FiCheck size={14} />
                    All Screened
                  </>
                ) : (
                  <>
                    <FiCheck size={14} />
                    Screen CVs
                    {hasUnscreenedCVs && (
                      <span className="ml-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-white/25 text-[10px] font-bold">
                        {newCandidateCounter}
                      </span>
                    )}
                  </>
                )}
              </button>

              <Button variant="secondary" size="sm" onClick={handleEdit}>
                <FiEdit3 size={14} />
                Edit
              </Button>
            </div>
          </div>
        </header>

        {/* ── Unscreened CVs Banner ──────────────────────────────────────── */}
        {hasUnscreenedCVs && !isScreeningCVs && (
          <div className="shrink-0 mx-6 mt-3 flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg">
            <FiAlertTriangle size={15} className="text-amber-600 shrink-0" />
            <p className="text-xs font-semibold text-amber-800">
              {newCandidateCounter} new CV{newCandidateCounter !== 1 ? "s" : ""} awaiting screening
            </p>
          </div>
        )}

        {/* ── Candidates card (scrollable) ──────────────────────────────── */}
        <Card
          className={`mx-6 mt-4 mb-4 flex-1 min-h-0 flex flex-col shadow-[0_4px_24px_rgb(0_0_0_/_0.06)] ${
            openDropdownId !== null ? "overflow-visible" : "overflow-hidden"
          }`}
        >
          <div className="shrink-0 flex items-center justify-between px-5 py-3.5 border-b border-[#f0f0f2]">
            <div className="flex items-center gap-2.5">
              <h2 className="m-0 text-base font-bold text-gray-900">Candidates</h2>
              <span className="inline-flex items-center justify-center min-w-[22px] h-[22px] px-1.5 rounded-full bg-brand-600/10 text-xs font-bold text-brand-700">
                {totalCVs}
              </span>
            </div>

            <button
              onClick={handleUploadClick}
              disabled={uploading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold text-gray-700 border border-border rounded-[10px] hover:bg-gray-50 transition disabled:opacity-50"
            >
              <FiUpload size={14} />
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

          {applications.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <p className="text-base font-medium mb-1">No candidates yet</p>
                <p className="text-sm">Upload CVs to get started</p>
              </div>
            </div>
          ) : (
            <div
              className={`flex-1 min-h-0 ${
                openDropdownId !== null ? "overflow-visible" : "overflow-auto"
              }`}
            >
              <table className="w-full table-auto border-collapse text-sm">
                <colgroup>
                  <col className="w-10" />
                  <col />
                  <col className="w-[7.5rem]" />
                  <col className="w-[8.5rem]" />
                  <col className="w-[6.5rem]" />
                  <col className="w-[9.5rem]" />
                  <col className="w-[6.5rem]" />
                </colgroup>
                <thead className="sticky top-0 z-10 bg-surface">
                  <tr className="border-b border-border text-[10px] text-muted uppercase tracking-wider">
                    <th className="px-3 py-2.5 font-semibold text-center">#</th>
                    <th className="px-4 py-2.5 font-semibold text-left w-px whitespace-nowrap">Candidate</th>
                    <th className="px-4 py-2.5 font-semibold text-left whitespace-nowrap">Score</th>
                    <th className="px-4 py-2.5 font-semibold text-left whitespace-nowrap">Status</th>
                    <th className="px-3 py-2.5 font-semibold text-center whitespace-nowrap">Actions</th>
                    <th className="px-3 py-2.5 font-semibold text-center whitespace-nowrap">Questions</th>
                    <th className="px-3 py-2.5 font-semibold text-center whitespace-nowrap">Interview</th>
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
                        <td className="px-3 py-3 text-center text-gray-400 font-medium tabular-nums align-middle">
                          {index + 1}
                        </td>

                        {/* Candidate Name */}
                        <td className="px-4 py-3 w-px max-w-[min(100%,18rem)] text-left align-middle">
                          <button
                            onClick={() => handleCandidateClick(app)}
                            title={candidate?.full_name || "Unknown Candidate"}
                            className="text-sm font-semibold text-gray-900 hover:text-blue-600 hover:underline transition text-left truncate block max-w-[18rem]"
                          >
                            {candidate?.full_name || "Unknown Candidate"}
                          </button>
                        </td>

                        {/* Score */}
                        <td className="px-4 py-3 whitespace-nowrap text-left align-middle">
                          <div className="inline-flex items-center gap-2.5">
                            <div className="w-16 overflow-hidden rounded-full bg-gray-200 h-1.5 shrink-0">
                              <div
                                className={`h-full rounded-full ${getScoreColor(score)} transition-all duration-500`}
                                style={{ width: `${score}%` }}
                              />
                            </div>
                            <span className="text-sm font-semibold text-gray-700 tabular-nums">
                              {score}
                            </span>
                          </div>
                        </td>

                        {/* Status */}
                        <td className="px-4 py-3 whitespace-nowrap text-left align-middle">
                          <span
                            className={`inline-flex items-center rounded-md ${statusStyle.bg} px-2.5 py-1 text-xs font-semibold ${statusStyle.text}`}
                          >
                            {statusStyle.label}
                          </span>
                        </td>

                        {/* Actions — Approve / Reject dropdown */}
                        <td className="px-3 py-3 whitespace-nowrap text-center align-middle">
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
                                <div className="absolute right-0 top-10 z-30 w-52 bg-surface border border-border rounded-xl shadow-[0_8px_32px_rgb(0_0_0_/_0.12)] py-1.5">
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
                        <td className="px-3 py-3 whitespace-nowrap text-center align-middle">
                          <div className="flex items-center justify-center gap-2">
                            {app.tech_questions && app.tech_questions.length > 0 ? (
                              <button
                                onClick={() =>
                                  handleViewTechQuestions(
                                    app.tech_questions,
                                    candidate?.full_name || "Candidate"
                                  )
                                }
                                className="px-3 py-1.5 text-xs font-semibold text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition"
                              >
                                View Tech Q ({app.tech_questions.length})
                              </button>
                            ) : (
                              <button
                                onClick={() =>
                                  handleGenerateTechQuestions(
                                    app.id,
                                    candidate?.full_name || "Candidate"
                                  )
                                }
                                disabled={generatingQuestionId === app.id}
                                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                                  generatingQuestionId === app.id
                                    ? "bg-blue-50 text-blue-600 border border-blue-200 cursor-wait"
                                    : "text-gray-600 border border-gray-200 hover:bg-gray-50"
                                }`}
                              >
                                {generatingQuestionId === app.id ? "Generating..." : "Tech Q"}
                              </button>
                            )}
                            <button
                              onClick={() => handleComingSoon("CBI Questions")}
                              className="px-3 py-1.5 text-xs font-semibold text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                            >
                              CBI Q
                            </button>
                          </div>
                        </td>

                        {/* Interview */}
                        <td className="px-3 py-3 whitespace-nowrap text-center align-middle">
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
        </Card>

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
            <div className="fixed inset-0 bg-black/45 z-50" onClick={() => setIsJdModalOpen(false)} />
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <div
                className="bg-surface rounded-xl shadow-[0_24px_80px_rgb(0_0_0_/_0.2)] w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-5 border-b border-border">
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
                  <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
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

        {/* ── Chat Copilot Drawer ────────────────────────────────────────── */}
        <ChatDrawer
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          requisitionId={parseInt(id)}
          requisitionTitle={requisition?.title}
        />

        {/* ── Tech Questions Modal ────────────────────────────────────────── */}
        {isQuestionsModalOpen && (
          <>
            <div
              className="fixed inset-0 bg-black/45 z-50"
              onClick={() => setIsQuestionsModalOpen(false)}
            />
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <div
                className="bg-surface rounded-xl shadow-[0_24px_80px_rgb(0_0_0_/_0.2)] w-full max-w-3xl max-h-[80vh] flex flex-col overflow-hidden"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-5 border-b border-border">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">Technical Questions</h2>
                    <p className="text-sm text-gray-500 mt-0.5">{selectedQuestionsCandidate}</p>
                  </div>
                  <button
                    onClick={() => setIsQuestionsModalOpen(false)}
                    className="text-gray-400 hover:text-gray-600 transition p-1.5 hover:bg-gray-100 rounded-lg"
                  >
                    <FiX size={22} />
                  </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-6 py-6">
                  {selectedQuestions && selectedQuestions.length > 0 ? (
                    <div className="space-y-6">
                      {selectedQuestions.map((item, index) => (
                        <div
                          key={index}
                          className="border border-gray-200 rounded-lg p-5 hover:bg-gray-50 transition"
                        >
                          <div className="flex items-start gap-3 mb-3">
                            <span className="flex items-center justify-center w-7 h-7 rounded-full bg-blue-100 text-blue-700 text-sm font-semibold flex-shrink-0">
                              {index + 1}
                            </span>
                            <h3 className="text-base font-semibold text-gray-900 leading-relaxed">
                              {item.question}
                            </h3>
                          </div>
                          <div className="ml-10">
                            <p className="text-sm text-gray-600 leading-relaxed italic">
                              {item.answer}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center text-gray-400 py-8">
                      <p className="text-lg font-medium mb-1">No questions available</p>
                      <p className="text-sm">Questions will appear here once generated.</p>
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-2">
                  <button
                    onClick={() => setIsQuestionsModalOpen(false)}
                    className="px-5 py-2.5 bg-gray-100 text-gray-700 rounded-lg font-medium text-sm hover:bg-gray-200 transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── Toast ────────────────────────────────────────────────────── */}
        <Toast
          notification={notification}
          onClose={() => setNotification(null)}
        />

        {/* ── Floating AI Copilot Button ────────────────────────────────── */}
        <button
          onClick={() => setIsChatOpen(true)}
          className="fixed bottom-8 right-8 flex items-center justify-center w-16 h-16 bg-gradient-to-br from-brand-600 to-brand-800 hover:from-brand-700 hover:to-brand-800 text-white rounded-full shadow-[0_6px_22px_rgb(0_0_0_/_0.16)] hover:shadow-[0_8px_28px_rgb(0_0_0_/_0.2)] transition-all duration-300 hover:scale-105 active:scale-95 z-40 border-4 border-white"
          title="AI Recruiting Copilot"
        >
          <FiMessageSquare size={24} />
        </button>
      </div>
    </DashboardLayout>
  );
}
