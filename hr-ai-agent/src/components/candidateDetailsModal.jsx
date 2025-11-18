import { FiX } from "react-icons/fi";
import { MdCheck, MdSchedule } from "react-icons/md";
import { useState } from "react";

export default function CandidateDetailsModal({ candidate, isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState("overview");

  if (!isOpen || !candidate) return null;

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
                <div className="h-24 w-24 min-w-[96px] rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-2xl font-bold">
                  {candidate.name.charAt(0)}
                </div>
                <div className="flex flex-col justify-center">
                  <p className="text-2xl font-bold text-gray-900">{candidate.name}</p>
                  <p className="text-gray-600 text-base">Senior {candidate.status}</p>
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
              {candidate.status}
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
                  <h3 className="text-lg font-bold text-gray-900 pb-4">Scores Breakdown</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-4 rounded-lg border border-gray-200 bg-white">
                      <p className="text-gray-600 text-sm font-medium mb-2">Overall Fit</p>
                      <p className="text-2xl font-bold text-blue-500">{candidate.score}%</p>
                    </div>
                    <div className="p-4 rounded-lg border border-gray-200 bg-white">
                      <p className="text-gray-600 text-sm font-medium mb-2">Technical Skills</p>
                      <p className="text-2xl font-bold text-gray-900">92%</p>
                    </div>
                    <div className="p-4 rounded-lg border border-gray-200 bg-white">
                      <p className="text-gray-600 text-sm font-medium mb-2">Behavioral</p>
                      <p className="text-2xl font-bold text-gray-900">85%</p>
                    </div>
                    <div className="p-4 rounded-lg border border-gray-200 bg-white">
                      <p className="text-gray-600 text-sm font-medium mb-2">Soft Skills</p>
                      <p className="text-2xl font-bold text-gray-900">89%</p>
                    </div>
                  </div>
                </div>

                {/* CV Summary */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 pb-4">AI-Generated CV Summary</h3>
                  <div className="p-4 rounded-lg border border-gray-200 bg-white text-gray-600 text-sm space-y-3">
                    <p>Highly skilled Senior {candidate.status} with over 8 years of experience in developing scalable applications. Proven ability to lead projects from conception to deployment.</p>
                    <ul className="list-disc list-inside space-y-1 text-gray-600">
                      <li>Expert in modern technology stacks and cloud-native solutions</li>
                      <li>Strong track record of mentoring junior developers</li>
                      <li>Contributed to major projects with excellent results</li>
                    </ul>
                  </div>
                </div>
              </>
            )}

            {activeTab === "cv" && (
              <div>
                <h3 className="text-lg font-bold text-gray-900 pb-4">CV Details</h3>
                <div className="p-4 rounded-lg border border-gray-200 bg-white text-gray-600 text-sm space-y-4">
                  <div>
                    <p className="font-semibold text-gray-900 mb-2">Experience</p>
                    <p>8+ years of professional experience in software development</p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 mb-2">Skills</p>
                    <p>React, Node.js, Python, AWS, Docker, Kubernetes</p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 mb-2">Education</p>
                    <p>Bachelor's degree in Computer Science</p>
                  </div>
                </div>
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
                      <p className="text-xs text-gray-600">June 10, 2024</p>
                    </div>
                  </div>

                  {/* Timeline Item 2 */}
                  <div className="flex gap-4">
                    <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-white flex-shrink-0">
                      <MdCheck size={18} />
                    </div>
                    <div>
                      <p className="font-semibold text-sm text-gray-900">AI Screening Complete</p>
                      <p className="text-xs text-gray-600">June 11, 2024</p>
                    </div>
                  </div>

                  {/* Timeline Item 3 */}
                  <div className="flex gap-4">
                    <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-blue-200 text-blue-500 flex-shrink-0">
                      <MdSchedule size={18} />
                    </div>
                    <div>
                      <p className="font-semibold text-sm text-gray-900">Interview Scheduled</p>
                      <p className="text-xs text-gray-600">Pending for June 18, 2024</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
