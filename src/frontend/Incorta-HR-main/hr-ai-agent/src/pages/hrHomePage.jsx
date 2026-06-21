import DashboardLayout from "../layouts/hrHomePageLayout";
import RequisitionCard from "../components/requisitionCard";
import RequisitionModal from "../components/requisitionModal";
import DeleteConfirmModal from "../components/deleteConfirmModal";
import Toast from "../components/toast";
import Button from "../components/button";
import ListPagination from "../components/ListPagination";
import { FiPlus, FiAlertCircle } from "react-icons/fi";
import { useState, useEffect } from "react";
import {
  fetchRequisitions,
  createRequisition,
  updateRequisition,
  deleteRequisition,
} from "../services/requisitionService";
import { getUser } from "../services/authService";

const PAGE_SIZE = 8;

export default function HrDashboard() {
  const currentUser = getUser();
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
  const [page, setPage] = useState(1);

  useEffect(() => {
    const loadRequisitions = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const params = { is_active: true };
        if (currentUser?.role === "hiring_manager") {
          params.hiring_manager_id = currentUser.id;
        }
        
        const data = await fetchRequisitions(params);
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

  useEffect(() => {
    setPage(1);
  }, [searchTerm, selectedDept]);

  const totalPages = Math.max(1, Math.ceil(filteredRequisitions.length / PAGE_SIZE));
  const pageItems = filteredRequisitions.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

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
        setRequisitions([newRequisition, ...requisitions]);
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

  return (
    <DashboardLayout>
      <div className="page page--list">
        <div className="page-header">
          <div>
            <h1 className="page-title">Requisitions</h1>
            <p className="page-desc">
              {loading
                ? "Loading…"
                : `${filteredRequisitions.length} of ${requisitions.length} requisition${requisitions.length !== 1 ? "s" : ""}`}
            </p>
          </div>
        </div>

        <div className="toolbar toolbar--with-action">
          <input
            type="text"
            className="field-input toolbar__search"
            placeholder="Search by title, location, or keyword…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <select
            className="field-input toolbar__select"
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            aria-label="Filter by department"
          >
            {departments.map((dept, i) => (
              <option key={i} value={dept}>
                {dept === "All" ? "All departments" : dept}
              </option>
            ))}
          </select>
          <Button onClick={handlePostJob}>
            <FiPlus size={14} />
            New Requisition
          </Button>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2.5">
            <FiAlertCircle className="text-red-600 shrink-0 mt-0.5" size={16} />
            <div>
              <h3 className="text-sm font-semibold text-red-900">Error Loading Requisitions</h3>
              <p className="text-red-700 text-xs mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="card-grid">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-gray-200 rounded-xl h-52 animate-pulse" />
            ))}
          </div>
        ) : filteredRequisitions.length === 0 ? (
          <p className="text-muted text-center mt-8">
            No requisitions match your filters.
          </p>
        ) : (
          <>
            <div className="card-grid">
              {pageItems.map((req) => (
                <RequisitionCard
                  key={req.id}
                  requisition={req}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                />
              ))}
            </div>
            <ListPagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        )}
      </div>

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
