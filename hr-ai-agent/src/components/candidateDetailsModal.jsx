import { FiX } from "react-icons/fi";
import { MdCheck, MdSchedule } from "react-icons/md";
import { useState, useEffect } from "react";
import { fetchCandidateDetails } from "../services/api";

export default function CandidateDetailsModal({ candidate, isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState("overview");
  const [candidateDetails, setCandidateDetails] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && candidate) {
      loadCandidateDetails();
    }
  }, [isOpen, candidate]);

  const loadCandidateDetails = async () => {
    if (!candidate || !candidate.candidateData || !candidate.candidateData.candidate_id) return;
    
    try {
      setLoading(true);
      const details = await fetchCandidateDetails(candidate.candidateData.candidate_id);
      setCandidateDetails(details);
    } catch (error) {
      console.error('Error loading candidate details:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !candidate) return null;

  const details = candidateDetails || candidate.candidateData || {};

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
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="ml-3 text-gray-500">Loading details...</p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {/* Profile Header */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
                <div className="flex gap-4">
                  <div className="h-24 w-24 min-w-[96px] rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-2xl font-bold">
                    {candidate.name.charAt(0)}
                  </div>
                  <div className="flex flex-col justify-center">
                    <p className="text-2xl font-bold text-gray-900">{details.english_name || candidate.name}</p>
                    <p className="text-gray-600 text-base">{details.email || 'N/A'}</p>
                    <p className="text-gray-600 text-sm">{details.phone_number || 'N/A'}</p>
                  </div>
                </div>

                <div className="flex gap-3 w-full sm:w-auto">
                  <button className="flex-1 sm:flex-auto px-4 py-2 h-10 rounded-lg bg-gray-200 text-gray-900 text-sm font-bold hover:bg-gray-300 transition">
                    Schedule Interview
                  </button>
                  <button className="flex-1 sm:flex-auto px-4 py-2 h-10 rounded-lg bg-blue-500 text-white text-sm font-bold hover:bg-blue-600 transition">
                    Message
                  </button>
                </div>
              </div>
            </div>

            {/* Status */}
            <div className="flex gap-3 p-6 border-b border-gray-200 items-center">
              <p className="text-sm font-medium text-gray-600">Status:</p>
              <button className="h-8 px-3 rounded-lg bg-gray-200 text-gray-900 text-sm font-medium hover:bg-gray-300 transition flex items-center gap-2">
                {details.status || candidate.status}
              </button>
            </div>

            {/* Tabs */}
            <div className="px-6 border-b border-gray-200">
              <div className="flex gap-8">
                {["overview", "cv", "timeline"].map((tab) => (
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
                    {tab === "timeline" && "Timeline"}
                  </button>
                ))}
              </div>
            </div>

            {/* Tab Content */}
            <div className="p-6 space-y-8">
              {activeTab === "overview" && (
                <>
                  {/* Scores Breakdown */}
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 pb-4">Match Score</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="p-4 rounded-lg border border-gray-200 bg-white">
                        <p className="text-gray-600 text-sm font-medium mb-2">Overall Match</p>
                        <p className="text-2xl font-bold text-blue-500">{parseFloat(details.score || candidate.score || 0).toFixed(0)}%</p>
                      </div>
                      <div className="p-4 rounded-lg border border-gray-200 bg-white">
                        <p className="text-gray-600 text-sm font-medium mb-2">Years of Experience</p>
                        <p className="text-2xl font-bold text-gray-900">{details.years_of_experience || 0} years</p>
                      </div>
                    </div>
                  </div>

                  {/* Justification */}
                  {details.justification && (
                    <div>
                      <h3 className="text-lg font-bold text-gray-900 pb-4">AI Assessment</h3>
                      <div className="p-4 rounded-lg border border-gray-200 bg-white text-gray-600 text-sm">
                        <p className="whitespace-pre-wrap">{details.justification}</p>
                      </div>
                    </div>
                  )}

                  {/* Contact Info */}
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 pb-4">Contact Information</h3>
                    <div className="p-4 rounded-lg border border-gray-200 bg-white space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600 text-sm">Email:</span>
                        <span className="text-gray-900 text-sm font-medium">{details.email || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 text-sm">Phone:</span>
                        <span className="text-gray-900 text-sm font-medium">{details.phone_number || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 text-sm">Location:</span>
                        <span className="text-gray-900 text-sm font-medium">{details.current_city || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 text-sm">Nationality:</span>
                        <span className="text-gray-900 text-sm font-medium">{details.nationality || 'N/A'}</span>
                      </div>
                      {details.linkedin_url && (
                        <div className="flex justify-between">
                          <span className="text-gray-600 text-sm">LinkedIn:</span>
                          <a href={details.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 text-sm hover:underline">View Profile</a>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}

              {activeTab === "cv" && (
                <div className="space-y-6">
                  <h3 className="text-lg font-bold text-gray-900">CV Details</h3>
                  
                  {/* Education */}
                  <div>
                    <p className="font-semibold text-gray-900 mb-2">Education</p>
                    <div className="p-4 rounded-lg border border-gray-200 bg-white space-y-2">
                      <p className="text-gray-600 text-sm">Field: {details.study_field || 'N/A'}</p>
                      <p className="text-gray-600 text-sm">Graduation Year: {details.graduation_year || 'N/A'}</p>
                      {details.universities && details.universities.length > 0 && (
                        <div>
                          <p className="text-gray-900 text-sm font-medium mt-2">Universities:</p>
                          <ul className="list-disc list-inside text-gray-600 text-sm">
                            {details.universities.map((uni, idx) => (
                              <li key={idx}>{uni}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Technical Skills */}
                  {details.technical_skills && details.technical_skills.length > 0 && (
                    <div>
                      <p className="font-semibold text-gray-900 mb-2">Technical Skills</p>
                      <div className="p-4 rounded-lg border border-gray-200 bg-white">
                        <div className="flex flex-wrap gap-2">
                          {details.technical_skills.map((skill, idx) => (
                            <span key={idx} className="px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-sm">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Soft Skills */}
                  {details.soft_skills && details.soft_skills.length > 0 && (
                    <div>
                      <p className="font-semibold text-gray-900 mb-2">Soft Skills</p>
                      <div className="p-4 rounded-lg border border-gray-200 bg-white">
                        <div className="flex flex-wrap gap-2">
                          {details.soft_skills.map((skill, idx) => (
                            <span key={idx} className="px-3 py-1 rounded-full bg-green-100 text-green-700 text-sm">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Languages */}
                  {details.Languages && details.Languages.length > 0 && (
                    <div>
                      <p className="font-semibold text-gray-900 mb-2">Languages</p>
                      <div className="p-4 rounded-lg border border-gray-200 bg-white">
                        <p className="text-gray-600 text-sm">{details.Languages.join(', ')}</p>
                      </div>
                    </div>
                  )}

                  {/* Certifications */}
                  {details.Certifications && details.Certifications.length > 0 && (
                    <div>
                      <p className="font-semibold text-gray-900 mb-2">Certifications</p>
                      <div className="p-4 rounded-lg border border-gray-200 bg-white">
                        <ul className="list-disc list-inside text-gray-600 text-sm">
                          {details.Certifications.map((cert, idx) => (
                            <li key={idx}>{cert}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "timeline" && (
                <div>
                  <h3 className="text-lg font-bold text-gray-900 pb-4">Timeline</h3>
                  <div className="relative pl-6 space-y-8">
                    {/* Vertical Line */}
                    <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-gray-200"></div>

                    {/* Timeline Item 1 */}
                    <div className="flex gap-4">
                      <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-white flex-shrink-0">
                        <MdCheck size={18} />
                      </div>
                      <div>
                        <p className="font-semibold text-sm text-gray-900">CV Received</p>
                        <p className="text-xs text-gray-600">Application submitted</p>
                      </div>
                    </div>

                    {/* Timeline Item 2 */}
                    <div className="flex gap-4">
                      <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-white flex-shrink-0">
                        <MdCheck size={18} />
                      </div>
                      <div>
                        <p className="font-semibold text-sm text-gray-900">AI Screening Complete</p>
                        <p className="text-xs text-gray-600">Score: {parseFloat(details.score || 0).toFixed(0)}%</p>
                      </div>
                    </div>

                    {/* Timeline Item 3 */}
                    <div className="flex gap-4">
                      <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-blue-200 text-blue-500 flex-shrink-0">
                        <MdSchedule size={18} />
                      </div>
                      <div>
                        <p className="font-semibold text-sm text-gray-900">Next Steps</p>
                        <p className="text-xs text-gray-600">Pending review</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
