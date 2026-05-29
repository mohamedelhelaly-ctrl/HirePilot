import { FiX, FiMail, FiPhone, FiLinkedin, FiExternalLink } from "react-icons/fi";
import { MdCheck, MdSchedule } from "react-icons/md";
import { useState, useEffect } from "react";
import { fetchApplicationDetails } from "../services/candidateService";

export default function CandidateDetailsModal({ candidate, application, isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState("overview");
  const [cvDetails, setCvDetails] = useState([]);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Load CV details when the CV tab is selected
  useEffect(() => {
    if (isOpen && application?.id && activeTab === "cv") {
      loadCvDetails();
    }
  }, [isOpen, application?.id, activeTab]);

  // Reset tab on open
  useEffect(() => {
    if (isOpen) setActiveTab("overview");
  }, [isOpen]);

  const loadCvDetails = async () => {
    try {
      setLoadingDetails(true);
      const details = await fetchApplicationDetails(application.id);
      setCvDetails(details || []);
    } catch (err) {
      console.error("Error loading CV details:", err);
      setCvDetails([]);
    } finally {
      setLoadingDetails(false);
    }
  };

  if (!isOpen || !candidate) return null;

  const score = candidate.score || 0;
  const initials = candidate.name
    ? candidate.name
        .split(" ")
        .map((w) => w[0])
        .join("")
        .substring(0, 2)
        .toUpperCase()
    : "?";

  // Format CV detail values nicely
  const formatValue = (key, value) => {
    if (value === null || value === undefined) return "—";
    if (Array.isArray(value)) {
      if (value.length === 0) return "—";
      // Array of objects (e.g., education, previous_roles)
      if (typeof value[0] === "object") {
        return value;
      }
      // Array of strings (e.g., skills, certifications)
      return value.join(", ");
    }
    if (typeof value === "object") {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  const formatKey = (key) => {
    return key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose}></div>

      {/* Slide-Over Panel */}
      <div className="fixed top-0 right-0 h-full w-full max-w-2xl bg-white shadow-2xl z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">Candidate Details</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-900 transition"
          >
            <FiX size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Profile Header */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
              <div className="flex gap-4">
                <div className="h-20 w-20 min-w-[80px] rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-blue-500/20">
                  {initials}
                </div>
                <div className="flex flex-col justify-center">
                  <p className="text-2xl font-bold text-gray-900">{candidate.name}</p>
                  {/* Contact Info */}
                  <div className="flex flex-wrap gap-3 mt-2">
                    {candidate.email && (
                      <a
                        href={`mailto:${candidate.email}`}
                        className="flex items-center gap-1.5 text-l text-gray-500 hover:text-blue-600 transition"
                      >
                        <FiMail size={14} />
                        {candidate.email}
                      </a>
                    )}
                    {candidate.phone && (
                      <span className="flex items-center gap-1.5 text-l text-gray-500">
                        <FiPhone size={14} />
                        {candidate.phone}
                      </span>
                    )}
                    {candidate.linkedin_url && (
                      <a
                        href={candidate.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-l text-blue-600 hover:text-blue-700 transition"
                      >
                        <FiLinkedin size={14} />
                        LinkedIn
                        <FiExternalLink size={12} />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Status */}
          <div className="flex gap-3 p-6 border-b border-gray-200 items-center">
            <p className="text-sm font-medium text-gray-600">Status:</p>
            <span className="h-8 px-3 rounded-lg bg-gray-100 text-gray-800 text-sm font-medium flex items-center">
              {candidate.status?.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()) || "—"}
            </span>
          </div>

          {/* Tabs */}
          <div className="px-6 border-b border-gray-200">
            <div className="flex gap-8">
              {["overview", "cv"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`pb-4 pt-4 text-sm font-bold border-b-2 transition ${
                    activeTab === tab
                      ? "border-b-blue-500 text-blue-500"
                      : "border-b-transparent text-gray-600 hover:text-gray-900"
                  }`}
                >
                  {tab === "overview" && "Overview"}
                  {tab === "cv" && "CV Details"}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          <div className="p-6 space-y-8">
            {activeTab === "overview" && (
              <>
                {/* Score */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 pb-4">Score Overview</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-5 rounded-xl border border-gray-200 bg-gradient-to-br from-blue-50 to-white">
                      <p className="text-gray-500 text-sm font-medium mb-2">
                        Overall Score
                      </p>
                      <p className="text-3xl font-bold text-blue-600">
                        {score}
                        <span className="text-lg text-gray-400 font-normal">/100</span>
                      </p>
                    </div>
                    <div className="p-5 rounded-xl border border-gray-200 bg-white">
                      <p className="text-gray-500 text-sm font-medium mb-2">
                        Application Date
                      </p>
                      <p className="text-lg font-semibold text-gray-800">
                        {application?.applied_at
                          ? new Date(application.applied_at).toLocaleDateString("en-US", {
                              year: "numeric",
                              month: "short",
                              day: "numeric",
                            })
                          : "—"}
                      </p>
                    </div>
                  </div>
                </div>
              </>
            )}

            {activeTab === "cv" && (
              <div>
                <h3 className="text-lg font-bold text-gray-900 pb-4">CV Details</h3>
                {loadingDetails ? (
                  <div className="space-y-3">
                    {[...Array(5)].map((_, i) => (
                      <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : cvDetails.length === 0 ? (
                  <div className="p-8 text-center rounded-xl border border-gray-200 bg-gray-50 text-gray-400">
                    <p className="text-base font-medium mb-1">No CV details available</p>
                    <p className="text-sm">
                      CV data will appear here after screening is complete
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {cvDetails.map((detail) => {
                      const formattedValue = formatValue(detail.key, detail.value);
                      const isArray = Array.isArray(formattedValue);
                      const isObjectArray =
                        isArray && formattedValue.length > 0 && typeof formattedValue[0] === "object";

                      return (
                        <div
                          key={detail.id}
                          className="p-4 rounded-xl border border-gray-200 bg-white"
                        >
                          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                            {formatKey(detail.key)}
                          </p>

                          {isObjectArray ? (
                            <div className="space-y-2">
                              {formattedValue.map((item, idx) => (
                                <div
                                  key={idx}
                                  className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg"
                                >
                                  {Object.entries(item).map(([k, v]) => (
                                    <p key={k}>
                                      <span className="font-medium text-gray-600">
                                        {formatKey(k)}:
                                      </span>{" "}
                                      {String(v)}
                                    </p>
                                  ))}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-gray-700 leading-relaxed">
                              {typeof formattedValue === "string" ? formattedValue : String(formattedValue)}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

          </div>
        </div>
      </div>
    </>
  );
}
