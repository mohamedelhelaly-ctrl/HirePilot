import DashboardLayout from "../layouts/hrHomePageLayout";
import JobRow from "../components/jobCard";
import Button from "../components/button";
import { jobs } from "../data/jobs";
import { FiPlus } from "react-icons/fi";

export default function HrDashboard() {
  const departments = ["All", "Engineering", "Sales", "Marketing", "Finance"];

  return (
    <DashboardLayout>
      <div className="w-full mx-auto">
        <div className="w-full flex items-center justify-between gap-6 mt-10">
          <div>
            <h1 className="text-3xl md:text-6xl font-bold">Incorta AI HR Agent</h1>
            <p className="text-gray-600 mt-3 text-xl">
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

        {/* FILTERS */}
        <div className="flex gap-4 mt-25">
          {departments.map((dept, i) => (
            <button
              key={i}
              className={`px-4 py-2 rounded-lg border ${
                dept === "All" ? "bg-blue-600 text-white" : "bg-white text-gray-600"
              }`}
            >
              {dept}
            </button>
          ))}
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
              {jobs.map((job, index) => (
                <JobRow key={index} {...job} />
              ))}
            </tbody>
          </table>
        </div>

        <footer className="text-center text-gray-500 py-6 mt-10">
          <div className="flex justify-center gap-8 mb-2">
            <a>Privacy Policy</a>
            <a>Terms of Service</a>
            <a>Contact</a>
          </div>
          © 2025 Incorta. All rights reserved.
        </footer>
      </div>
    </DashboardLayout>
  );
}
