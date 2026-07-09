import { useState } from "react";
import { FiSearch, FiChevronDown, FiPlus } from "react-icons/fi";
import DashboardLayout from "../layouts/hrHomePageLayout";
import CandidateRow from "../components/candidateRow";
import AIChatSidebar from "../components/aiChatSidebar";
import CandidateDetailsModal from "../components/candidateDetailsModal";
import Button from "../components/button";
import { candidates } from "../data/candidates";

export default function JobPipeline() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleCandidateClick = (candidate) => {
    setSelectedCandidate(candidate);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedCandidate(null);
  };

  return (
    <DashboardLayout>
      <div className="flex flex-1 gap-6 h-[calc(100vh-100px)]">
        {/* Main Content */}
        <div className="flex flex-col flex-[2] min-w-0 bg-white rounded-xl border border-gray-200 shadow-sm">
          {/* Header */}
          <div className="p-6">
            <div className="flex items-center justify-between gap-4">
              <h1 className="text-3xl font-bold tracking-tight text-gray-900">Job Pipeline: Senior Developer</h1>
              <div>
              <Button
                title={
                  <span className="flex items-center justify-center gap-1 text-md">
                    <FiPlus size={16} />
                    <span>Add Candidate</span>
                  </span>
                }
                className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-sm"
              /></div>
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
                  {candidates.map((candidate) => (
                    <CandidateRow 
                      key={candidate.id} 
                      {...candidate}
                      onCandidateClick={handleCandidateClick}
                      candidateData={candidate}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* AI Chat Sidebar */}
        <AIChatSidebar />
      </div>

      {/* Candidate Details Modal */}
      <CandidateDetailsModal 
        candidate={selectedCandidate}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </DashboardLayout>
  );
}
