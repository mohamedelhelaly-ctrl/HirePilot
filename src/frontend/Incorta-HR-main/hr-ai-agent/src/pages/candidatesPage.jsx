import DashboardLayout from "../layouts/hrHomePageLayout";
import Button from "../components/button";
import ListPagination from "../components/ListPagination";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FiMail,
  FiPhone,
  FiLinkedin,
  FiChevronRight,
  FiX,
  FiAlertCircle,
} from "react-icons/fi";
import { fetchCandidateDirectory } from "../services/candidateDirectoryService";
import { fetchRequisitions } from "../services/requisitionService";

const PAGE_SIZE = 8;

const STATUS_COLORS = {
  new: { bg: "bg-gray-100", text: "text-gray-700", label: "New" },
  screening_pending: { bg: "bg-yellow-50", text: "text-yellow-700", label: "Screening" },
  screening_passed: { bg: "bg-green-50", text: "text-green-700", label: "Shortlisted" },
  screening_rejected: { bg: "bg-red-50", text: "text-red-600", label: "Rejected" },
  interview_scheduled: { bg: "bg-indigo-50", text: "text-indigo-700", label: "Interview Scheduled" },
  interview_completed: { bg: "bg-purple-50", text: "text-purple-700", label: "Interview Done" },
  offer_extended: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Offer Extended" },
  hired: { bg: "bg-green-50", text: "text-green-700", label: "Hired" },
  rejected: { bg: "bg-red-50", text: "text-red-600", label: "Rejected" },
};

function getStatusStyle(status) {
  return STATUS_COLORS[status] || { bg: "bg-gray-100", text: "text-gray-600", label: status?.replace(/_/g, " ") || "Unknown" };
}

function hasKnownValue(value) {
  if (!value) return false;
  const normalized = String(value).trim().toLowerCase();
  return normalized && !["unknown", "n/a", "na", "-"].includes(normalized);
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function scoreTone(score) {
  if (score == null) return "text-muted";
  if (score >= 70) return "text-green-700 bg-green-50";
  if (score >= 40) return "text-amber-700 bg-amber-50";
  return "text-red-700 bg-red-50";
}

function appMatchesQuery(app, query) {
  return [
    app.requisition_title,
    app.department,
    app.location,
    String(app.requisition_id),
  ].some((v) => v?.toLowerCase().includes(query));
}

function CandidateCard({ candidate, onOpen }) {
  const showEmail = hasKnownValue(candidate.email);
  const showPhone = hasKnownValue(candidate.phone_number);
  const showLinkedIn = hasKnownValue(candidate.linkedin_url);

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={() => onOpen(candidate)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(candidate);
        }
      }}
      className="flex flex-col gap-3 rounded-[18px] border border-[#ececef] bg-surface p-4 min-h-[196px] cursor-pointer shadow-[0_8px_24px_rgb(15_23_42_/_0.08)] transition hover:-translate-y-px hover:border-brand-200 hover:bg-[#fcfdff] hover:shadow-[0_16px_34px_rgb(15_23_42_/_0.12)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600"
    >
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-brand-600 mb-1">Candidate</p>
        <div className="flex items-baseline flex-wrap gap-2">
          <h2 className="m-0 text-base font-bold text-gray-900 leading-snug line-clamp-2">{candidate.name}</h2>
          <span className="text-xs text-muted">#{candidate.candidate_id}</span>
        </div>
      </div>

      <div className="flex flex-col gap-1.5 text-sm min-h-[72px]">
        {showEmail ? (
          <a
            href={`mailto:${candidate.email}`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-2 text-gray-700 hover:text-brand-600 truncate"
          >
            <FiMail size={13} className="shrink-0 text-muted" />
            <span className="truncate">{candidate.email}</span>
          </a>
        ) : (
          <span className="text-xs text-gray-300 select-none">Email not available</span>
        )}
        {showLinkedIn ? (
          <a
            href={candidate.linkedin_url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-2 text-gray-700 hover:text-brand-600"
          >
            <FiLinkedin size={13} className="shrink-0 text-muted" />
            LinkedIn
          </a>
        ) : (
          <span className="text-xs text-gray-300 select-none">LinkedIn not available</span>
        )}
        {showPhone ? (
          <span className="inline-flex items-center gap-2 text-gray-700">
            <FiPhone size={13} className="shrink-0 text-muted" />
            {candidate.phone_number}
          </span>
        ) : (
          <span className="text-xs text-gray-300 select-none">Phone not available</span>
        )}
      </div>

      <div className="mt-auto flex items-center justify-between text-xs text-muted pt-1 border-t border-[#f0f0f2]">
        <span>
          {candidate.applications.length} requisition{candidate.applications.length === 1 ? "" : "s"}
        </span>
        <span className="text-brand-600 font-semibold">View details</span>
      </div>
    </article>
  );
}

function ApplicationRow({ application, accessibleIds, onNavigate }) {
  const statusStyle = getStatusStyle(application.status);
  const score = application.screen_score;
  const accessible = accessibleIds.has(application.requisition_id);
  const meta = [application.department, application.location].filter(Boolean).join(" · ");

  const content = (
    <>
      <div className="flex-1 min-w-0">
        <p className="m-0 text-sm font-semibold text-gray-900 truncate">
          {application.requisition_title || `Requisition #${application.requisition_id}`}
        </p>
        <p className="m-0 mt-0.5 text-xs text-muted truncate">
          {meta || `Req #${application.requisition_id}`}
        </p>
        <p className="m-0 mt-1 text-[11px] text-muted">
          Updated {formatDate(application.updated_at || application.applied_at)}
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2 shrink-0">
        <span className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold ${statusStyle.bg} ${statusStyle.text}`}>
          {statusStyle.label}
        </span>
        {score != null && (
          <span className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-bold tabular-nums ${scoreTone(score)}`}>
            {score}%
          </span>
        )}
        {application.interview_score != null && (
          <span className="inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold bg-purple-50 text-purple-700">
            Interview {application.interview_score}
          </span>
        )}
        {accessible ? (
          <FiChevronRight size={16} className="text-muted" />
        ) : (
          <span className="text-[10px] text-muted">Restricted</span>
        )}
      </div>
    </>
  );

  if (!accessible) {
    return (
      <div className="flex items-start gap-3 p-3 rounded-xl border border-border bg-gray-50/80 opacity-80">
        {content}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onNavigate(application.requisition_id)}
      className="w-full flex items-start gap-3 p-3 rounded-xl border border-border bg-surface text-left hover:bg-brand-50/40 hover:border-brand-200 transition"
    >
      {content}
    </button>
  );
}

function CandidateDetailsModal({ candidate, accessibleIds, onClose, onNavigate }) {
  if (!candidate) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />
      <aside className="fixed top-0 right-0 h-full w-full max-w-[560px] bg-surface shadow-[12px_0_40px_rgb(0_0_0_/_0.12)] z-50 flex flex-col border-l border-border">
        <header className="shrink-0 px-5 pt-4 pb-3 border-b border-[#eee] flex justify-between items-start gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-brand-600 mb-1">Candidate</p>
            <h2 className="m-0 text-xl font-bold text-gray-900">{candidate.name}</h2>
            <p className="m-0 mt-1 text-xs text-muted">ID #{candidate.candidate_id}</p>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 w-9 h-9 flex items-center justify-center rounded-[10px] border border-border text-gray-500 hover:bg-gray-50"
            aria-label="Close"
          >
            <FiX size={18} />
          </button>
        </header>

        <div className="shrink-0 px-5 py-3 border-b border-[#eee] flex flex-wrap gap-3 text-sm">
          {hasKnownValue(candidate.email) && (
            <a href={`mailto:${candidate.email}`} className="inline-flex items-center gap-1.5 text-gray-700 hover:text-brand-600">
              <FiMail size={14} /> {candidate.email}
            </a>
          )}
          {hasKnownValue(candidate.linkedin_url) && (
            <a href={candidate.linkedin_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-gray-700 hover:text-brand-600">
              <FiLinkedin size={14} /> LinkedIn
            </a>
          )}
          {hasKnownValue(candidate.phone_number) && (
            <span className="inline-flex items-center gap-1.5 text-gray-700">
              <FiPhone size={14} /> {candidate.phone_number}
            </span>
          )}
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto p-5 bg-canvas">
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted mb-3">
            Applications ({candidate.applications.length})
          </p>
          <div className="flex flex-col gap-2">
            {candidate.applications.map((app) => (
              <ApplicationRow
                key={app.application_id}
                application={app}
                accessibleIds={accessibleIds}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        </div>
      </aside>
    </>
  );
}

export default function CandidatesPage() {
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState([]);
  const [accessibleIds, setAccessibleIds] = useState(new Set());
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const [directory, requisitions] = await Promise.all([
          fetchCandidateDirectory(),
          fetchRequisitions({ is_active: true }),
        ]);
        setCandidates(directory.candidates || []);
        setAccessibleIds(new Set((requisitions || []).map((r) => r.id)));
      } catch (err) {
        setError(err.message || "Failed to load candidates");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const statusOptions = useMemo(() => {
    const set = new Set();
    candidates.forEach((c) =>
      c.applications.forEach((a) => {
        if (a.status) set.add(a.status);
      })
    );
    return Array.from(set).sort();
  }, [candidates]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return candidates.filter((candidate) => {
      const matchesSearch =
        !q ||
        candidate.name.toLowerCase().includes(q) ||
        String(candidate.candidate_id).includes(q) ||
        candidate.email?.toLowerCase().includes(q) ||
        candidate.applications.some((app) => appMatchesQuery(app, q));

      const matchesStatus =
        !statusFilter ||
        candidate.applications.some((app) => app.status === statusFilter);

      return matchesSearch && matchesStatus;
    });
  }, [candidates, search, statusFilter]);

  useEffect(() => setPage(1), [search, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleNavigate = (requisitionId) => {
    navigate(`/requisition/${requisitionId}`);
  };

  return (
    <DashboardLayout>
      <div className="page page--list">
        <div className="page-header">
          <div>
            <h1 className="page-title">Candidates</h1>
            <p className="page-desc">
              {loading
                ? "Loading…"
                : `${filtered.length} of ${candidates.length} candidate${candidates.length === 1 ? "" : "s"}`}
            </p>
          </div>
        </div>

        <div className="toolbar">
          <input
            type="text"
            className="field-input toolbar__search"
            placeholder="Search by candidate, email, requisition, or location…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="field-input toolbar__select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by application status"
          >
            <option value="">All statuses</option>
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {getStatusStyle(status).label}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2.5">
            <FiAlertCircle className="text-red-600 shrink-0 mt-0.5" size={16} />
            <p className="text-sm text-red-700 m-0">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="candidate-directory-grid">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-52 rounded-xl bg-gray-200 animate-pulse" />
            ))}
          </div>
        ) : pageItems.length === 0 ? (
          <p className="text-muted text-center mt-8 m-0">
            No candidates match your filters.
            {(search || statusFilter) && (
              <>
                {" "}
                <button
                  type="button"
                  className="text-brand-600 font-semibold hover:underline"
                  onClick={() => {
                    setSearch("");
                    setStatusFilter("");
                  }}
                >
                  Clear filters
                </button>
              </>
            )}
          </p>
        ) : (
          <>
            <div className="candidate-directory-grid">
              {pageItems.map((candidate) => (
                <CandidateCard key={candidate.candidate_id} candidate={candidate} onOpen={setSelected} />
              ))}
            </div>
            <ListPagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        )}
      </div>

      <CandidateDetailsModal
        candidate={selected}
        accessibleIds={accessibleIds}
        onClose={() => setSelected(null)}
        onNavigate={handleNavigate}
      />
    </DashboardLayout>
  );
}
