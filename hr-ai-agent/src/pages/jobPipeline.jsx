import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { FiSearch, FiChevronDown, FiPlus, FiX, FiUpload } from "react-icons/fi";
import DashboardLayout from "../layouts/hrHomePageLayout";
import CandidateRow from "../components/candidateRow";
import AIChatSidebar from "../components/aiChatSidebar";
import CandidateDetailsModal from "../components/candidateDetailsModal";
import Button from "../components/button";
import { fetchCandidates, fetchJobs } from "../services/api";

export default function JobPipeline() {
  const { jobId } = useParams();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [jobTitle, setJobTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadFiles, setUploadFiles] = useState([]);

  useEffect(() => {
    loadData();
  }, [jobId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [candidatesData, jobsData] = await Promise.all([
        fetchCandidates(jobId),
        fetchJobs()
      ]);
      
      const job = jobsData.find(j => j.id === jobId);
      setJobTitle(job ? job.title : "Job Pipeline");
      
      // Transform candidates data to match UI expectations
      const transformedCandidates = candidatesData.map(candidate => ({
        id: candidate.candidate_id,
        name: candidate.english_name,
        score: parseFloat(candidate.score) || 0,
        scoreColor: getScoreColor(parseFloat(candidate.score)),
        status: candidate.status || "New Applicant",
        statusBg: getStatusBg(candidate.status),
        statusText: getStatusText(candidate.status),
        actionButton: getActionButton(candidate.status),
        actionBg: getActionBg(candidate.status),
        candidateData: candidate
      }));
      
      setCandidates(transformedCandidates);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return "bg-green-500";
    if (score >= 80) return "bg-purple-500";
    if (score >= 70) return "bg-yellow-500";
    return "bg-blue-500";
  };

  const getStatusBg = (status) => {
    const map = {
      "Offer": "bg-green-100",
      "Recruiter Screen": "bg-purple-100",
      "Technical Assessment": "bg-yellow-100",
      "New Applicant": "bg-blue-100",
      "New Lead": "bg-blue-100"
    };
    return map[status] || "bg-blue-100";
  };

  const getStatusText = (status) => {
    const map = {
      "Offer": "text-green-800",
      "Recruiter Screen": "text-purple-800",
      "Technical Assessment": "text-yellow-800",
      "New Applicant": "text-blue-800",
      "New Lead": "text-blue-800"
    };
    return map[status] || "text-blue-800";
  };

  const getActionButton = (status) => {
    const map = {
      "Offer": "Add to Shortlist",
      "Recruiter Screen": "Schedule Screen",
      "Technical Assessment": "Send Assessment",
      "New Applicant": "Send Outreach Email",
      "New Lead": "Send Outreach Email"
    };
    return map[status] || "Review";
  };

  const getActionBg = (status) => {
    const map = {
      "Offer": "bg-green-500 hover:bg-green-600",
      "Recruiter Screen": "bg-purple-500 hover:bg-purple-600",
      "Technical Assessment": "bg-yellow-500 hover:bg-yellow-600",
      "New Applicant": "bg-blue-500 hover:bg-blue-600",
      "New Lead": "bg-blue-500 hover:bg-blue-600"
    };
    return map[status] || "bg-blue-500 hover:bg-blue-600";
  };

  const handleCandidateClick = (candidate) => {
    setSelectedCandidate(candidate);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedCandidate(null);
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    setUploadFiles(files);
  };

  const handleUploadCVs = async () => {
    if (uploadFiles.length === 0) {
      alert("Please select at least one PDF file");
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('thread_id', jobId);
      
      uploadFiles.forEach(file => {
        formData.append('files', file);
      });

      const response = await fetch('/api/upload_cvs', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.success.length > 0) {
        alert(`✅ Successfully uploaded ${result.success.length} CV(s)!\n\nYou can now ask the AI to screen them.`);
        setIsUploadModalOpen(false);
        setUploadFiles([]);
        // Refresh the candidate list
        loadData();
      } else {
        alert(`⚠️ Upload completed but no files were processed successfully.`);
      }
    } catch (error) {
      console.error('Error uploading CVs:', error);
      alert('❌ Error uploading CVs. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const filteredCandidates = candidates.filter(candidate =>
    candidate.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <DashboardLayout>
      <div className="flex flex-1 gap-6 h-[calc(100vh-100px)]">
        {/* Main Content */}
        <div className="flex flex-col flex-[2] min-w-0 bg-white rounded-xl border border-gray-200 shadow-sm">
          {/* Header */}
          <div className="p-6">
            <div className="flex items-center justify-between gap-4">
              <h1 className="text-3xl font-bold tracking-tight text-gray-900">
                Job Pipeline: {jobTitle}
              </h1>
              <div>
                <Button
                  title={
                    <span className="flex items-center justify-center gap-1 text-md">
                      <FiPlus size={16} />
                      <span>Add Candidate</span>
                    </span>
                  }
                  className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-sm"
                  onClick={() => setIsUploadModalOpen(true)}
                />
              </div>
            </div>
          </div>

          {/* Filters & Search */}
          <div className="flex flex-wrap items-center gap-4 px-6 pb-4 border-b border-gray-200">
            {/* Search */}
            <div className="flex-1 min-w-[250px]">
              <div className="flex items-center rounded-lg bg-gray-50 border border-gray-200 h-12">
                <div className="text-gray-500 flex items-center justify-center pl-4">
                  <FiSearch size={18} />
                </div>
                <input
                  type="text"
                  placeholder="Search candidates by name or keyword..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex w-full flex-1 bg-transparent text-gray-900 focus:outline-none pl-2 text-sm placeholder:text-gray-500"
                />
              </div>
            </div>

            {/* Dropdowns */}
            <div className="flex gap-3 overflow-x-auto">
              <button className="flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg bg-gray-50 border border-gray-200 pl-4 pr-3 text-sm font-medium text-gray-700 hover:bg-gray-100">
                <p>Status</p>
                <FiChevronDown size={16} />
              </button>
              <button className="flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg bg-gray-50 border border-gray-200 pl-4 pr-3 text-sm font-medium text-gray-700 hover:bg-gray-100">
                <p>Score</p>
                <FiChevronDown size={16} />
              </button>
              <button className="flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg bg-gray-50 border border-gray-200 pl-4 pr-3 text-sm font-medium text-gray-700 hover:bg-gray-100">
                <p>Sort By</p>
                <FiChevronDown size={16} />
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-y-auto p-2">
            <div className="p-4">
              {loading ? (
                <div className="flex justify-center items-center h-64">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <p className="ml-3 text-gray-500">Loading candidates...</p>
                </div>
              ) : filteredCandidates.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <p>No candidates found.</p>
                </div>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 w-2/5">
                        Name
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 w-1/5">
                        Score
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 w-1/5">
                        Status
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 w-1/5">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {filteredCandidates.map((candidate) => (
                      <CandidateRow 
                        key={candidate.id} 
                        {...candidate}
                        onCandidateClick={handleCandidateClick}
                        candidateData={candidate}
                      />
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* AI Chat Sidebar */}
        <AIChatSidebar 
          threadId={jobId} 
          onMessageSent={loadData}
        />
      </div>

      {/* Candidate Details Modal */}
      <CandidateDetailsModal 
        candidate={selectedCandidate}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />

      {/* Upload CVs Modal */}
      {isUploadModalOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/50 z-40" 
            onClick={() => !uploading && setIsUploadModalOpen(false)}
          />

          {/* Modal */}
          <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-2xl z-50 w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">Upload Candidate CVs</h2>
              <button
                onClick={() => !uploading && setIsUploadModalOpen(false)}
                disabled={uploading}
                className="text-gray-500 hover:text-gray-900 disabled:opacity-50"
              >
                <FiX size={24} />
              </button>
            </div>

            <div className="p-6">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition">
                <FiUpload className="mx-auto text-gray-400 mb-4" size={48} />
                <p className="text-gray-700 mb-2">
                  {uploadFiles.length > 0 
                    ? `${uploadFiles.length} file(s) selected`
                    : "Select PDF files to upload"
                  }
                </p>
                <input
                  type="file"
                  accept=".pdf"
                  multiple
                  onChange={handleFileChange}
                  disabled={uploading}
                  className="hidden"
                  id="cv-upload"
                />
                <label
                  htmlFor="cv-upload"
                  className="inline-block mt-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg cursor-pointer hover:bg-gray-200 disabled:opacity-50"
                >
                  Choose Files
                </label>
                <p className="text-xs text-gray-500 mt-2">
                  You can select multiple PDF files
                </p>
              </div>

              {uploadFiles.length > 0 && (
                <div className="mt-4 max-h-32 overflow-y-auto">
                  <p className="text-sm font-semibold text-gray-700 mb-2">Selected files:</p>
                  <ul className="space-y-1">
                    {uploadFiles.map((file, index) => (
                      <li key={index} className="text-sm text-gray-600 flex items-center gap-2">
                        <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                        {file.name}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setIsUploadModalOpen(false)}
                  disabled={uploading}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUploadCVs}
                  disabled={uploading || uploadFiles.length === 0}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Uploading...
                    </>
                  ) : (
                    <>
                      <FiUpload size={18} />
                      Upload
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
