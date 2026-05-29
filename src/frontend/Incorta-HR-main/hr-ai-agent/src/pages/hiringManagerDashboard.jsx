import { useState } from "react";
import { useNavigate } from "react-router-dom";
import HiringManagerLayout from "../layouts/HiringManagerLayout";
import JobCard from "../components/jobListCard";
import CandidateTable from "../components/candidateTable";
import { hiringManagerJobs } from "../data/hiringManagerJobs";
import { FiLogOut } from "react-icons/fi";
import * as authService from "../services/authService";

export default function HiringManagerDashboard() {
  const [selectedJobId, setSelectedJobId] = useState(1);
  const navigate = useNavigate();

  const selectedJob = hiringManagerJobs.find((job) => job.id === selectedJobId);

  const handleLogout = async () => {
    try {
      await authService.logoutUser();
      navigate("/login");
    } catch (error) {
      console.error("Logout failed:", error);
      navigate("/login");
    }
  };

  return (
    <HiringManagerLayout>
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 pb-6 mb-6">
        <div className="flex min-w-72 flex-col">
          <p className="text-4xl font-black leading-tight text-gray-900">
            My Open Jobs
          </p>
          <p className="text-base font-normal leading-normal text-gray-500">
            Select a job to view and manage candidates
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition flex items-center gap-2"
          title="Logout"
        >
          <FiLogOut size={20} />
          <span className="font-medium">Logout</span>
        </button>
      </header>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
        {/* Left Panel: Job List */}
        <div className="lg:col-span-1 flex flex-col gap-4">
          <div className="flex flex-col divide-y divide-gray-200 rounded-xl border border-gray-200 bg-white overflow-hidden">
            {hiringManagerJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJobId === job.id}
                onSelect={() => setSelectedJobId(job.id)}
              />
            ))}
          </div>
        </div>

        {/* Right Panel: Candidate Table */}
        <div className="lg:col-span-2">
          <CandidateTable
            candidates={selectedJob?.candidates_list || []}
            selectedJob={selectedJob}
          />
        </div>
      </div>
    </HiringManagerLayout>
  );
}
