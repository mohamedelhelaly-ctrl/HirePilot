import DashboardLayout from "../layouts/hrHomePageLayout";
import JobRow from "../components/jobCard";
import Button from "../components/button";
import { jobs } from "../data/jobs";
import { FiPlus } from "react-icons/fi";
import { useState } from "react";

export default function HrDashboard() {
  const departments = ["All", "Engineering", "Sales", "Marketing", "Finance"];
  const [selectedDept, setSelectedDept] = useState("All");

  // Filter jobs based on selected department
  const filteredJobs = selectedDept === "All" 
    ? jobs 
    : jobs.filter(job => job.department === selectedDept);

  return (
    <DashboardLayout>
      <div className="w-full mx-auto ">
        <div className="w-full flex items-center justify-between gap-6 mt-10">
          <div>
            <h1 className="text-3xl md:text-6xl font-bold">Incorta AI HR Agent</h1>
            <p className="text-gray-600 mt-5 text-xl">
              Streamline Your Hiring Process with AI-Powered Insights.
            </p>
          </div>

          <div>
            <Button
              title={
                <span className="flex items-center gap-3 text-2xl">
                  <FiPlus size={22} />
                  <span>Post New Job</span>
                </span>
              }
              className="w-auto px-5 py-2 shadow"
            />
          </div>
        </div>

        <div className="mt-20">
          <div className="inline-flex items-center gap-2 bg-gray-50 rounded-lg border border-gray-200 p-1">
            {departments.map((dept, i) => {
              const active = selectedDept === dept;
              return (
                <button
                  key={i}
                  onClick={() => setSelectedDept(dept)}
                  aria-pressed={active}
                  className={`focus:outline-none transition ${
                    active
                      ? "bg-blue-700 text-white shadow-sm"
                      : "text-gray-600 hover:bg-gray-50"
                  } px-4 py-2 rounded-xl text-md`}
                >
                  {dept}
                </button>
              );
            })}
          </div>
        </div>

        {/* JOB TABLE */}
        <div className="bg-white rounded-xl shadow mt-6 overflow-hidden">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200/100 text-gray-600 text-sm uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Job Title</th>
                <th className="py-3 px-4">Department</th>
                <th className="py-3 px-4">Location</th>
                <th className="py-3 px-4">Candidates</th>
                <th className="py-3 px-4">New Applicants</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>

            <tbody>
              {filteredJobs.length > 0 ? (
                filteredJobs.map((job, index) => (
                  <JobRow key={index} {...job} />
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-gray-500">
                    No jobs found for {selectedDept === "All" ? "this filter" : `${selectedDept} department`}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardLayout>
  );
}
