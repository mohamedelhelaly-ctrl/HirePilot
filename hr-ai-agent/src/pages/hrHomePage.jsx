import DashboardLayout from "../layouts/hrHomePageLayout";
import JobRow from "../components/jobCard";
import Button from "../components/button";
import { FiPlus, FiX } from "react-icons/fi";
import Footer from "../components/footer";
import { useState, useEffect } from "react";
import { fetchJobStats, fetchJobs, createJob } from "../services/api";

export default function HrDashboard() {
  const departments = ["All", "Engineering", "Sales", "Marketing", "Finance"];
  const [selectedDept, setSelectedDept] = useState("All");
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    details: "",
    location: "",
    level: "",
    requirements: ""
  });

  useEffect(() => {
    loadJobData();
  }, []);

  const loadJobData = async () => {
    try {
      setLoading(true);
      const [jobsData, statsData] = await Promise.all([
        fetchJobs(),
        fetchJobStats()
      ]);
      
      // Merge job details with stats
      const enrichedJobs = jobsData.map(job => {
        const stats = statsData.find(s => s.job_id === job.id);
        return {
          jobId: job.id,
          title: job.title,
          department: "Engineering", // You can add this to jobs.json if needed
          location: job.location || "Remote",
          candidates: stats ? stats.applied : 0,
          screened: stats ? stats.screened : 0,
          newApplicants: stats ? (stats.applied - stats.screened) : 0
        };
      });
      
      setJobs(enrichedJobs);
    } catch (error) {
      console.error('Error loading job data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    
    try {
      // Convert requirements string to array
      const requirementsArray = formData.requirements
        .split('\n')
        .map(req => req.trim())
        .filter(req => req.length > 0);
      
      const jobData = {
        ...formData,
        requirements: requirementsArray
      };
      
      await createJob(jobData);
      
      // Close modal and reset form
      setShowModal(false);
      setFormData({
        title: "",
        description: "",
        details: "",
        location: "",
        level: "",
        requirements: ""
      });
      
      // Reload job data
      loadJobData();
      
      alert('Job created successfully!');
    } catch (error) {
      alert(`Error creating job: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="w-full mx-auto">
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
              onClick={() => setShowModal(true)}
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
          {loading ? (
            <div className="p-8 text-center text-gray-500">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2">Loading jobs...</p>
            </div>
          ) : (
            <table className="w-full text-left">
              <thead className="border-b border-gray-200/100 text-gray-600 text-sm uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Job Title</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Location</th>
                  <th className="py-3 px-4">Total Candidates</th>
                  <th className="py-3 px-4">Screened</th>
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
          )}
        </div>

        <Footer />
      </div>

      {/* Job Creation Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-2xl">
              <h2 className="text-2xl font-bold text-gray-800">Post New Job</h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-gray-600 transition"
              >
                <FiX size={24} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Job Title *
                </label>
                <input
                  type="text"
                  name="title"
                  value={formData.title}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                  placeholder="e.g., Senior Software Engineer"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Short Description *
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  required
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition resize-none"
                  placeholder="Brief overview of the role..."
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Full Job Details *
                </label>
                <textarea
                  name="details"
                  value={formData.details}
                  onChange={handleInputChange}
                  required
                  rows={8}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition resize-none"
                  placeholder="Detailed job description, responsibilities, qualifications..."
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Location *
                  </label>
                  <input
                    type="text"
                    name="location"
                    value={formData.location}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                    placeholder="e.g., Cairo, Egypt"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Employment Level *
                  </label>
                  <input
                    type="text"
                    name="level"
                    value={formData.level}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                    placeholder="e.g., Full-time, Part-time"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Requirements *
                </label>
                <textarea
                  name="requirements"
                  value={formData.requirements}
                  onChange={handleInputChange}
                  required
                  rows={6}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition resize-none"
                  placeholder="Enter each requirement on a new line...
e.g.,
5+ years in AI/ML development
Python, TensorFlow, PyTorch
Strong communication skills"
                />
                <p className="text-xs text-gray-500 mt-1">Enter each requirement on a new line</p>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  disabled={submitting}
                  className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-semibold disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:opacity-90 transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Creating...' : 'Create Job'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
