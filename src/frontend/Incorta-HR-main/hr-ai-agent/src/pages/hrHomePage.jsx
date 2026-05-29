import DashboardLayout from "../layouts/hrHomePageLayout";
import RequisitionCard from "../components/requisitionCard";
import Button from "../components/button";
import { FiPlus, FiSearch, FiAlertCircle } from "react-icons/fi";
import { useState, useEffect } from "react";
import { fetchRequisitions } from "../services/requisitionService";

export default function HrDashboard() {
  const [requisitions, setRequisitions] = useState([]);
  const [filteredRequisitions, setFilteredRequisitions] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDept, setSelectedDept] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Get unique departments from requisitions
  const [departments, setDepartments] = useState(["All"]);

  // Fetch requisitions on mount
  useEffect(() => {
    const loadRequisitions = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchRequisitions({ is_active: true });
        setRequisitions(data);

        // Extract unique departments
        const uniqueDepts = ["All", ...new Set(data.map(r => r.department).filter(Boolean))];
        setDepartments(uniqueDepts);
      } catch (err) {
        setError(err.message || "Failed to load requisitions");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadRequisitions();
  }, []);

  // Filter requisitions based on search and department
  useEffect(() => {
    let filtered = requisitions;

    // Filter by department
    if (selectedDept !== "All") {
      filtered = filtered.filter(req => req.department === selectedDept);
    }

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(req =>
        req.title.toLowerCase().includes(term) ||
        req.description?.toLowerCase().includes(term) ||
        req.location?.toLowerCase().includes(term) ||
        req.department?.toLowerCase().includes(term)
      );
    }

    setFilteredRequisitions(filtered);
  }, [requisitions, selectedDept, searchTerm]);

  const handleEdit = (requisition) => {
    console.log("Edit requisition:", requisition);
    // TODO: Implement edit functionality
  };

  const handleDelete = (requisitionId) => {
    console.log("Delete requisition:", requisitionId);
    // TODO: Implement delete functionality
  };

  const handlePostJob = () => {
    console.log("Post new job");
    // TODO: Implement post job functionality
  };

  return (
    <DashboardLayout>
      <div className="w-full mx-auto">
        {/* Header Section */}
        <div className="w-full flex items-center justify-between gap-6 mt-10 mb-8">
          <div className="flex-1">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900">
              Incorta AI HR Agent
            </h1>
            <p className="text-gray-600 mt-3 text-lg">
              Streamline Your Hiring Process with AI-Powered Insights
            </p>
          </div>

          <div>
            <Button
              onClick={handlePostJob}
              title={
                <span className="flex items-center gap-3">
                  <FiPlus size={20} />
                  <span>Post New Job</span>
                </span>
              }
              className="w-auto px-6 py-3 shadow hover:shadow-lg transition"
            />
          </div>
        </div>

        {/* Search and Filter Section */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
            {/* Search Bar */}
            <div className="flex-1 relative">
              <FiSearch className="absolute left-4 top-3.5 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Search by job title, location, or keyword..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-11 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition"
              />
            </div>

            {/* Department Filter */}
            <div className="flex gap-2 flex-wrap">
              {departments.map((dept, i) => {
                const active = selectedDept === dept;
                return (
                  <button
                    key={i}
                    onClick={() => setSelectedDept(dept)}
                    aria-pressed={active}
                    className={`focus:outline-none transition px-4 py-2.5 rounded-lg text-sm font-medium ${
                      active
                        ? "bg-blue-700 text-white shadow-md"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {dept}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <FiAlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-red-900">Error Loading Requisitions</h3>
              <p className="text-red-700 text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="bg-gray-200 rounded-lg h-80 animate-pulse"
              />
            ))}
          </div>
        ) : filteredRequisitions.length > 0 ? (
          <>
            {/* Stats Bar */}
            <div className="mb-6 p-4 bg-blue-50 rounded-lg flex gap-6 items-center">
              <div>
                <p className="text-gray-600 text-sm">Total Open Positions</p>
                <p className="text-2xl font-bold text-blue-700">{filteredRequisitions.length}</p>
              </div>
              <div>
                <p className="text-gray-600 text-sm">Total Candidates</p>
                <p className="text-2xl font-bold text-blue-700">
                  {filteredRequisitions.reduce((sum, req) => sum + (req.candidates || 0), 0)}
                </p>
              </div>
              <div>
                <p className="text-gray-600 text-sm">New Applications</p>
                <p className="text-2xl font-bold text-orange-600">
                  {filteredRequisitions.reduce((sum, req) => sum + (req.new_applicants || 0), 0)}
                </p>
              </div>
            </div>

            {/* Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredRequisitions.map((req) => (
                <RequisitionCard
                  key={req.id}
                  requisition={req}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          </>
        ) : (
          <div className="text-center py-16 bg-gray-50 rounded-lg">
            <p className="text-gray-600 text-lg">
              No requisitions found for {selectedDept === "All" ? "your filters" : `the ${selectedDept} department`}
            </p>
            {searchTerm && (
              <p className="text-gray-500 text-sm mt-2">
                Try adjusting your search term or filters
              </p>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
