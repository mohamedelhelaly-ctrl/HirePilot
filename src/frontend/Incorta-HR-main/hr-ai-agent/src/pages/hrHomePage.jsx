import DashboardLayout from "../layouts/hrHomePageLayout";
import RequisitionCard from "../components/requisitionCard";
import RequisitionModal from "../components/requisitionModal";
import DeleteConfirmModal from "../components/deleteConfirmModal";
import Toast from "../components/toast";
import Button from "../components/button";
import Card from "../components/Card";
import PageHeader from "../components/PageHeader";
import { inputClasses } from "../components/inputField";
import { FiPlus, FiSearch, FiAlertCircle } from "react-icons/fi";
import { useState, useEffect } from "react";
import {
  fetchRequisitions,
  createRequisition,
  updateRequisition,
  deleteRequisition,
} from "../services/requisitionService";

export default function HrDashboard() {
  const [requisitions, setRequisitions] = useState([]);
  const [filteredRequisitions, setFilteredRequisitions] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDept, setSelectedDept] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [isRequisitionModalOpen, setIsRequisitionModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create");
  const [selectedRequisition, setSelectedRequisition] = useState(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [requisitionToDelete, setRequisitionToDelete] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState(null);
  const [departments, setDepartments] = useState(["All"]);

  useEffect(() => {
    const loadRequisitions = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchRequisitions({ is_active: true });
        setRequisitions(data);
        const uniqueDepts = ["All", ...new Set(data.map((r) => r.department).filter(Boolean))];
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

  const showNotification = (type, title, message = "") => {
    setNotification({ type, title, message });
  };

  useEffect(() => {
    let filtered = requisitions;
    if (selectedDept !== "All") {
      filtered = filtered.filter((req) => req.department === selectedDept);
    }
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (req) =>
          req.title.toLowerCase().includes(term) ||
          req.description?.toLowerCase().includes(term) ||
          req.location?.toLowerCase().includes(term) ||
          req.department?.toLowerCase().includes(term)
      );
    }
    setFilteredRequisitions(filtered);
  }, [requisitions, selectedDept, searchTerm]);

  const handlePostJob = () => {
    setModalMode("create");
    setSelectedRequisition(null);
    setIsRequisitionModalOpen(true);
  };

  const handleEdit = (requisition) => {
    setModalMode("edit");
    setSelectedRequisition(requisition);
    setIsRequisitionModalOpen(true);
  };

  const handleDelete = (requisitionId) => {
    const req = requisitions.find((r) => r.id === requisitionId);
    setRequisitionToDelete(req);
    setIsDeleteModalOpen(true);
  };

  const handleRequisitionSubmit = async (formData) => {
    try {
      setIsSubmitting(true);
      if (modalMode === "create") {
        const newRequisition = await createRequisition(formData);
        setRequisitions([...requisitions, newRequisition]);
        if (formData.department && !departments.includes(formData.department)) {
          setDepartments([...departments, formData.department]);
        }
        showNotification("success", "Job Posted Successfully", `${formData.title} has been added.`);
      } else {
        const updatedRequisition = await updateRequisition(selectedRequisition.id, formData);
        setRequisitions(
          requisitions.map((r) => (r.id === selectedRequisition.id ? updatedRequisition : r))
        );
        if (formData.department && !departments.includes(formData.department)) {
          setDepartments([...departments, formData.department]);
        }
        showNotification("success", "Job Updated Successfully", `${formData.title} has been updated.`);
      }
      setIsRequisitionModalOpen(false);
      setSelectedRequisition(null);
    } catch (err) {
      console.error("Error submitting requisition:", err);
      showNotification("error", "Error", err.message || "Failed to save the job.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    try {
      setIsSubmitting(true);
      await deleteRequisition(requisitionToDelete.id);
      const updatedRequisitions = requisitions.filter((r) => r.id !== requisitionToDelete.id);
      setRequisitions(updatedRequisitions);
      const deletedDept = requisitionToDelete.department;
      if (deletedDept && deletedDept !== "All") {
        const deptStillExists = updatedRequisitions.some((r) => r.department === deletedDept);
        if (!deptStillExists) {
          setDepartments(departments.filter((d) => d !== deletedDept));
          if (selectedDept === deletedDept) setSelectedDept("All");
        }
      }
      setIsDeleteModalOpen(false);
      setRequisitionToDelete(null);
      showNotification("success", "Job Deleted", `${requisitionToDelete.title} has been removed.`);
    } catch (err) {
      console.error("Error deleting requisition:", err);
      showNotification("error", "Error", err.message || "Failed to delete the job.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeDeptCount =
    selectedDept === "All"
      ? new Set(filteredRequisitions.map((r) => r.department).filter(Boolean)).size
      : 1;

  return (
    <DashboardLayout>
      <PageHeader
        title="Requisitions"
        description="Manage active job openings"
        actions={
          <Button size="sm" onClick={handlePostJob}>
            <FiPlus size={14} />
            Post New Job
          </Button>
        }
      />

      {/* Toolbar */}
      <Card className="mb-4 shadow-[0_4px_24px_rgb(0_0_0_/_0.06)]">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center px-5 py-3.5">
          <div className="flex-1 relative">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
            <input
              type="text"
              placeholder="Search by job title, location, or keyword..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={`${inputClasses} pl-9 text-sm py-2`}
            />
          </div>
          <select
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className={`${inputClasses} md:w-44 bg-white cursor-pointer text-sm font-medium py-2`}
          >
            {departments.map((dept, i) => (
              <option key={i} value={dept}>
                {dept}
              </option>
            ))}
          </select>
        </div>
      </Card>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2.5">
          <FiAlertCircle className="text-red-600 shrink-0 mt-0.5" size={16} />
          <div>
            <h3 className="text-sm font-semibold text-red-900">Error Loading Requisitions</h3>
            <p className="text-red-700 text-xs mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-gray-200 rounded-xl h-64 animate-pulse" />
          ))}
        </div>
      ) : filteredRequisitions.length > 0 ? (
        <>
          {/* Stats */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            {[
              { label: "Total", value: filteredRequisitions.length },
              { label: "Departments", value: activeDeptCount },
            ].map(({ label, value }) => (
              <div
                key={label}
                className="flex flex-col items-center px-3 py-1.5 min-w-[48px] rounded-lg border border-border bg-canvas"
              >
                <span className="text-base font-bold leading-none text-gray-900">{value}</span>
                <span className="text-[9px] font-semibold uppercase tracking-[0.06em] text-muted mt-0.5 whitespace-nowrap">
                  {label}
                </span>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
        <Card className="py-12 text-center shadow-[0_4px_24px_rgb(0_0_0_/_0.06)]">
          <p className="text-sm font-medium text-muted">
            No requisitions found for{" "}
            {selectedDept === "All" ? "your filters" : `the ${selectedDept} department`}
          </p>
          {searchTerm && (
            <p className="text-xs text-gray-400 mt-1.5">Try adjusting your search term or filters</p>
          )}
        </Card>
      )}

      <RequisitionModal
        isOpen={isRequisitionModalOpen}
        mode={modalMode}
        requisition={selectedRequisition}
        onClose={() => {
          setIsRequisitionModalOpen(false);
          setSelectedRequisition(null);
        }}
        onSubmit={handleRequisitionSubmit}
        loading={isSubmitting}
      />

      <DeleteConfirmModal
        isOpen={isDeleteModalOpen}
        requisitionTitle={requisitionToDelete?.title}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setRequisitionToDelete(null);
        }}
        onConfirm={handleConfirmDelete}
        loading={isSubmitting}
      />

      <Toast notification={notification} onClose={() => setNotification(null)} />
    </DashboardLayout>
  );
}
