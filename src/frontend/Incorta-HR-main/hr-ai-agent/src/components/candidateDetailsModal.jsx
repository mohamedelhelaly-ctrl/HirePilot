import { FiX, FiExternalLink } from "react-icons/fi";
import { useState, useEffect, useMemo } from "react";
import { fetchApplicationDetails } from "../services/candidateService";
import Badge from "./badge";

function scoreBarColor(score) {
  if (score >= 70) return "bg-green-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-brand-600";
}

function formatKey(key) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    if (typeof value[0] === "object") return value;
    return value.join(", ");
  }
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function isChipList(value) {
  if (Array.isArray(value) && value.length > 0 && typeof value[0] !== "object") return true;
  if (typeof value === "string" && value.includes(",")) return true;
  return false;
}

function toChipItems(value) {
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (typeof value === "string" && value.includes(",")) {
    return value.split(",").map((s) => s.trim()).filter(Boolean);
  }
  return [];
}

function categorizeKey(key) {
  const k = key.toLowerCase();
  if (/skill|certif|language|tech/.test(k)) return "skills";
  if (/compan|industr|employer|role/.test(k)) return "companies";
  if (/univers|education|graduat|experience|national|city|field|level|country|degree/.test(k)) {
    return "background";
  }
  return "background";
}

function DetailRow({ label, children }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-3 py-2 border-b border-[#f0f0f2] last:border-b-0 text-sm items-start">
      <div className="text-xs font-semibold text-muted">{label}</div>
      <div className="text-gray-900 leading-relaxed break-words">{children}</div>
    </div>
  );
}

function ChipList({ items }) {
  if (!items.length) return <span className="text-sm text-muted">—</span>;
  return (
    <ul className="flex flex-wrap gap-1.5 list-none m-0 p-0">
      {items.map((item, i) => (
        <li
          key={i}
          className="inline-flex px-2.5 py-1 rounded-full bg-[#f0f0f2] text-xs font-semibold text-gray-700"
        >
          {item}
        </li>
      ))}
    </ul>
  );
}

function SectionCard({ title, children }) {
  return (
    <section className="rounded-xl border border-border bg-surface overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[#f0f0f2] bg-[#fafafa]">
        <h3 className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted m-0">{title}</h3>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function ScoreHero({ score }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-4xl font-bold tracking-tight text-gray-900">{score}</span>
      <div className="flex-1 h-2.5 bg-gray-200 rounded-full overflow-hidden min-w-[100px]">
        <div
          className={`h-full rounded-full transition-all ${scoreBarColor(score)}`}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
    </div>
  );
}

function ContactItem({ label, href, value, primary = false }) {
  const Tag = href ? "a" : "div";
  return (
    <Tag
      href={href}
      target={href?.startsWith("http") ? "_blank" : undefined}
      rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}
      className={`flex flex-col gap-0.5 px-3.5 py-2.5 rounded-xl border transition ${
        primary
          ? "bg-blue-50 border-blue-200 hover:border-blue-300"
          : "bg-[#fafafa] border-border hover:border-blue-200 hover:shadow-[0_2px_12px_rgb(0_0_0_/_0.06)]"
      } ${href ? "no-underline text-inherit" : ""}`}
    >
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted">{label}</span>
      <span
        className={`text-sm font-semibold flex items-center gap-1 truncate ${
          primary || href ? "text-brand-600" : "text-gray-900"
        }`}
      >
        {value}
        {href?.startsWith("http") && <FiExternalLink size={11} className="shrink-0" />}
      </span>
    </Tag>
  );
}

function UniCard({ item }) {
  const name =
    item.university || item.institution || item.school || item.name || Object.values(item)[0];
  const level = item.education_level || item.degree || item.level;
  return (
    <li className="p-3 rounded-xl bg-[#fafafa] border border-border">
      <div className="text-sm font-semibold text-gray-900">{String(name ?? "—")}</div>
      {level && <div className="text-xs text-muted mt-0.5">{String(level)}</div>}
    </li>
  );
}

function statusBadgeColor(status) {
  const s = (status || "").toLowerCase();
  if (s.includes("reject")) return "bg-red-100 text-red-700";
  if (s.includes("hired") || s.includes("pass") || s.includes("shortlist")) return "bg-green-100 text-green-700";
  if (s.includes("interview") || s.includes("offer")) return "bg-indigo-100 text-indigo-700";
  return "bg-gray-100 text-gray-700";
}

export default function CandidateDetailsModal({ candidate, application, isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState("overview");
  const [cvDetails, setCvDetails] = useState([]);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    if (isOpen && application?.id) {
      loadCvDetails();
    }
  }, [isOpen, application?.id]);

  useEffect(() => {
    if (isOpen) {
      setActiveTab("overview");
      setCvDetails([]);
    }
  }, [isOpen, application?.id]);

  const loadCvDetails = async () => {
    try {
      setLoadingDetails(true);
      const details = await fetchApplicationDetails(application.id);
      setCvDetails((details || []).filter((d) => d.key !== "contact_info"));
    } catch (err) {
      console.error("Error loading CV details:", err);
      setCvDetails([]);
    } finally {
      setLoadingDetails(false);
    }
  };

  const groupedDetails = useMemo(() => {
    const groups = { background: [], skills: [], companies: [] };
    for (const detail of cvDetails) {
      if (isChipList(detail.value)) {
        const cat = categorizeKey(detail.key);
        groups[cat].push({ ...detail, type: "chips" });
      } else {
        const formatted = formatValue(detail.value);
        const isObjectArray = Array.isArray(formatted) && formatted[0] && typeof formatted[0] === "object";
        const cat = categorizeKey(detail.key);
        groups[cat].push({ ...detail, type: isObjectArray ? "objects" : "row", formatted });
      }
    }
    return groups;
  }, [cvDetails]);

  if (!isOpen || !candidate) return null;

  const score = candidate.score || 0;
  const statusLabel =
    candidate.status?.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()) || "—";
  const justification = candidate.justification || application?.justification;

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "cv", label: "Profile & skills" },
  ];

  const renderDetailBlock = (detail) => {
    if (detail.type === "chips") {
      return (
        <div key={detail.id} className="mb-4 last:mb-0">
          <p className="text-sm font-bold text-gray-900 mb-2">{formatKey(detail.key)}</p>
          <ChipList items={toChipItems(detail.value)} />
        </div>
      );
    }
    if (detail.type === "objects") {
      return (
        <div key={detail.id} className="mb-4 last:mb-0">
          <p className="text-sm font-bold text-gray-900 mb-2">{formatKey(detail.key)}</p>
          <ul className="space-y-2 list-none m-0 p-0">
            {detail.formatted.map((item, idx) => (
              <UniCard key={idx} item={item} />
            ))}
          </ul>
        </div>
      );
    }
    return (
      <DetailRow key={detail.id} label={formatKey(detail.key)}>
        {detail.formatted}
      </DetailRow>
    );
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/35 z-40" onClick={onClose} />

      <aside className="fixed top-0 right-0 h-full w-full max-w-[680px] bg-surface shadow-[12px_0_40px_rgb(0_0_0_/_0.12)] z-50 flex flex-col overflow-hidden border-l border-border">
        <header className="shrink-0 px-5 pt-4 pb-3 border-b border-[#eee] flex justify-between items-start gap-3">
          <div className="flex-1 min-w-0 pr-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-brand-600 mb-1">
              Candidate
            </p>
            <h2 className="text-[1.65rem] font-bold text-gray-900 tracking-tight leading-snug">
              {candidate.name}
            </h2>
            <div className="mt-2">
              <Badge text={statusLabel} color={statusBadgeColor(candidate.status)} />
            </div>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 w-9 h-9 flex items-center justify-center rounded-[10px] border border-border text-gray-500 hover:bg-gray-50 hover:text-gray-900 transition"
            aria-label="Close"
          >
            <FiX size={18} />
          </button>
        </header>

        <div className="shrink-0 flex gap-1 px-4 pt-2 border-b border-[#eee] bg-[#fafafa]" role="tablist">
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              role="tab"
              aria-selected={activeTab === id}
              onClick={() => setActiveTab(id)}
              className={`flex-1 text-xs font-semibold py-2 px-2 rounded-t-[10px] border-none cursor-pointer transition ${
                activeTab === id
                  ? "bg-surface text-gray-900"
                  : "bg-transparent text-muted hover:text-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto p-4 bg-canvas">
          {activeTab === "overview" && (
            <div className="flex flex-col gap-4">
              <SectionCard title="Score">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-2">
                  Overall score
                </p>
                <ScoreHero score={score} />
                {application?.applied_at && (
                  <p className="text-xs text-muted mt-3">
                    Applied{" "}
                    {new Date(application.applied_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </p>
                )}
              </SectionCard>

              {justification && (
                <div className="p-4 rounded-xl bg-canvas border-l-[3px] border-brand-600">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1.5">
                    Fit rationale
                  </p>
                  <p className="text-sm leading-relaxed text-gray-900">{justification}</p>
                </div>
              )}

              <SectionCard title="Contact & documents">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {candidate.email && (
                    <ContactItem
                      label="Email"
                      href={`mailto:${candidate.email}`}
                      value={candidate.email}
                    />
                  )}
                  {candidate.phone && (
                    <ContactItem label="Phone" href={`tel:${candidate.phone}`} value={candidate.phone} />
                  )}
                  {candidate.linkedin_url && (
                    <ContactItem
                      label="LinkedIn"
                      href={candidate.linkedin_url}
                      value="View profile"
                      primary
                    />
                  )}
                  {!candidate.email && !candidate.phone && !candidate.linkedin_url && (
                    <p className="text-sm text-muted col-span-full">No contact information available.</p>
                  )}
                </div>
              </SectionCard>
            </div>
          )}

          {activeTab === "cv" && (
            <div className="flex flex-col gap-4">
              {loadingDetails ? (
                <div className="space-y-3">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />
                  ))}
                </div>
              ) : cvDetails.length === 0 ? (
                <div className="py-12 text-center rounded-xl border border-border bg-surface">
                  <p className="text-sm font-medium text-muted mb-1">No profile data yet</p>
                  <p className="text-xs text-gray-400">CV details appear after screening completes.</p>
                </div>
              ) : (
                <>
                  {groupedDetails.background.length > 0 && (
                    <SectionCard title="Background">
                      {groupedDetails.background.map(renderDetailBlock)}
                    </SectionCard>
                  )}
                  {groupedDetails.companies.length > 0 && (
                    <SectionCard title="Companies & industry">
                      {groupedDetails.companies.map(renderDetailBlock)}
                    </SectionCard>
                  )}
                  {groupedDetails.skills.length > 0 && (
                    <SectionCard title="Skills & certifications">
                      {groupedDetails.skills.map(renderDetailBlock)}
                    </SectionCard>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
