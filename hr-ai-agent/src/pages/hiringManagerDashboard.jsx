import { useState } from "react";
import HiringManagerLayout from "../layouts/HiringManagerLayout";
import JobCard from "../components/jobListCard";
import CandidateTable from "../components/candidateTable";
import { hiringManagerJobs } from "../data/hiringManagerJobs";

export default function HiringManagerDashboard() {
  const [selectedJobId, setSelectedJobId] = useState(1);

  const selectedJob = hiringManagerJobs.find((job) => job.id === selectedJobId);

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
