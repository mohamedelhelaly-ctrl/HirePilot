import { useState, useEffect, useCallback } from "react";
import HrShellLayout from "../layouts/hrShellLayout";
import Toast from "../components/toast";
import Button from "../components/button";
import EditUserModal from "../components/editUserModal";
import Modal from "../components/Modal";
import { fetchUsers, deactivateUser, activateUser } from "../services/userService";
import { getUser } from "../services/authService";
import {
  FiSearch,
  FiEdit2,
  FiUserX,
  FiUserCheck,
  FiAlertCircle,
  FiShield,
  FiUser,
  FiMail,
  FiCalendar,
} from "react-icons/fi";

function RoleBadge({ role }) {
  const isHr = role === "hr_manager";
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
        isHr
          ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
          : "bg-amber-50 text-amber-700 border border-amber-200"
      }`}
    >
      <FiShield size={12} />
      {isHr ? "HR Manager" : "Hiring Manager"}
    </span>
  );
}

function StatusBadge({ isActive }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
        isActive
          ? "bg-green-50 text-green-700 border border-green-200"
          : "bg-red-50 text-red-700 border border-red-200"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${isActive ? "bg-green-500" : "bg-red-500"}`} />
      {isActive ? "Active" : "Inactive"}
    </span>
  );
}

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notification, setNotification] = useState(null);

  // Edit modal
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Deactivate / activate confirm modal
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null); // { userId, action: 'deactivate' | 'activate', userName }
  const [confirmLoading, setConfirmLoading] = useState(false);

  const currentUser = getUser();

  // Load users
  const loadUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchUsers();
      setUsers(data);
    } catch (err) {
      setError(err.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // Filter users
  useEffect(() => {
    let filtered = users;

    if (roleFilter !== "all") {
      filtered = filtered.filter((u) => u.role === roleFilter);
    }

    if (statusFilter !== "all") {
      const isActive = statusFilter === "active";
      filtered = filtered.filter((u) => u.is_active === isActive);
    }

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (u) =>
          u.full_name?.toLowerCase().includes(term) ||
          u.email?.toLowerCase().includes(term)
      );
    }

    setFilteredUsers(filtered);
  }, [users, searchTerm, roleFilter, statusFilter]);

  // Handlers
  const handleEdit = (user) => {
    setSelectedUser(user);
    setEditModalOpen(true);
  };

  const handleEditSuccess = (updatedUser) => {
    setUsers((prev) =>
      prev.map((u) => (u.id === updatedUser.id ? updatedUser : u))
    );
    setNotification({
      type: "success",
      title: "User Updated",
      message: `${updatedUser.full_name}'s profile has been updated.`,
    });
  };

  const handleToggleActive = (user) => {
    setConfirmAction({
      userId: user.id,
      action: user.is_active ? "deactivate" : "activate",
      userName: user.full_name,
    });
    setConfirmModalOpen(true);
  };

  const handleConfirmToggle = async () => {
    if (!confirmAction) return;
    setConfirmLoading(true);
    try {
      const fn = confirmAction.action === "deactivate" ? deactivateUser : activateUser;
      const updatedUser = await fn(confirmAction.userId);
      setUsers((prev) =>
        prev.map((u) => (u.id === updatedUser.id ? updatedUser : u))
      );
      setNotification({
        type: "success",
        title: confirmAction.action === "deactivate" ? "User Deactivated" : "User Activated",
        message: `${confirmAction.userName}'s account has been ${confirmAction.action}d.`,
      });
      setConfirmModalOpen(false);
      setConfirmAction(null);
    } catch (err) {
      setNotification({
        type: "error",
        title: "Error",
        message: err.message || `Failed to ${confirmAction.action} user.`,
      });
    } finally {
      setConfirmLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const activeCount = users.filter((u) => u.is_active).length;
  const hrCount = users.filter((u) => u.role === "hr_manager").length;
  const hiringCount = users.filter((u) => u.role === "hiring_manager").length;

  return (
    <HrShellLayout>
      <div className="page page--list">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">User Management</h1>
            <p className="page-desc">
              {loading
                ? "Loading…"
                : `${filteredUsers.length} of ${users.length} user${users.length !== 1 ? "s" : ""}`}
            </p>
          </div>
        </div>

        {/* Stats row */}
        {!loading && !error && (
          <div className="flex flex-wrap gap-3 mb-6">
            <div className="flex items-center gap-2 px-4 py-2.5 bg-surface rounded-xl border border-border">
              <FiUser size={14} className="text-muted" />
              <span className="text-sm font-semibold text-gray-900">{users.length}</span>
              <span className="text-xs text-muted">Total</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2.5 bg-green-50 rounded-xl border border-green-200">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-sm font-semibold text-green-700">{activeCount}</span>
              <span className="text-xs text-green-600">Active</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2.5 bg-indigo-50 rounded-xl border border-indigo-200">
              <FiShield size={14} className="text-indigo-600" />
              <span className="text-sm font-semibold text-indigo-700">{hrCount}</span>
              <span className="text-xs text-indigo-600">HR Managers</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 rounded-xl border border-amber-200">
              <FiShield size={14} className="text-amber-600" />
              <span className="text-sm font-semibold text-amber-700">{hiringCount}</span>
              <span className="text-xs text-amber-600">Hiring Managers</span>
            </div>
          </div>
        )}

        {/* Toolbar */}
        <div className="toolbar toolbar--with-action">
          <div className="relative flex-1 min-w-[200px]">
            <FiSearch size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              className="field-input toolbar__search pl-10"
              placeholder="Search by name or email…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              id="users-search"
            />
          </div>
          <select
            className="field-input toolbar__select"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            aria-label="Filter by role"
            id="users-role-filter"
          >
            <option value="all">All roles</option>
            <option value="hr_manager">HR Manager</option>
            <option value="hiring_manager">Hiring Manager</option>
          </select>
          <select
            className="field-input toolbar__select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
            id="users-status-filter"
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2.5">
            <FiAlertCircle className="text-red-600 shrink-0 mt-0.5" size={16} />
            <div>
              <h3 className="text-sm font-semibold text-red-900">Error Loading Users</h3>
              <p className="text-red-700 text-xs mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Loading skeleton */}
        {loading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-gray-200 rounded-xl h-[72px] animate-pulse" />
            ))}
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="text-center py-16">
            <FiUser size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-muted text-sm">No users match your filters.</p>
          </div>
        ) : (
          /* User Table */
          <div className="bg-surface rounded-xl border border-border overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-gray-50/60">
                    <th className="text-left px-5 py-3.5 font-semibold text-gray-500 text-xs uppercase tracking-wider">User</th>
                    <th className="text-left px-5 py-3.5 font-semibold text-gray-500 text-xs uppercase tracking-wider">Role</th>
                    <th className="text-left px-5 py-3.5 font-semibold text-gray-500 text-xs uppercase tracking-wider">Status</th>
                    <th className="text-left px-5 py-3.5 font-semibold text-gray-500 text-xs uppercase tracking-wider">Created</th>
                    <th className="text-right px-5 py-3.5 font-semibold text-gray-500 text-xs uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredUsers.map((u) => {
                    const isSelf = u.id === currentUser?.id;
                    const initials = u.full_name
                      ? u.full_name
                          .split(" ")
                          .map((w) => w[0])
                          .join("")
                          .substring(0, 2)
                          .toUpperCase()
                      : "?";
                    return (
                      <tr
                        key={u.id}
                        className={`group transition hover:bg-gray-50/80 ${!u.is_active ? "opacity-60" : ""}`}
                      >
                        {/* User info */}
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <div className="h-9 w-9 rounded-full bg-gradient-to-br from-brand-600 to-brand-800 flex items-center justify-center text-white text-xs font-bold shrink-0">
                              {initials}
                            </div>
                            <div className="min-w-0">
                              <p className="font-semibold text-gray-900 truncate">
                                {u.full_name}
                                {isSelf && (
                                  <span className="ml-2 text-[10px] font-bold text-brand-600 bg-brand-600/10 px-1.5 py-0.5 rounded">
                                    YOU
                                  </span>
                                )}
                              </p>
                              <p className="text-xs text-muted truncate flex items-center gap-1">
                                <FiMail size={11} className="shrink-0" />
                                {u.email}
                              </p>
                            </div>
                          </div>
                        </td>

                        {/* Role */}
                        <td className="px-5 py-4">
                          <RoleBadge role={u.role} />
                        </td>

                        {/* Status */}
                        <td className="px-5 py-4">
                          <StatusBadge isActive={u.is_active} />
                        </td>

                        {/* Created */}
                        <td className="px-5 py-4">
                          <span className="text-xs text-muted flex items-center gap-1.5">
                            <FiCalendar size={12} />
                            {formatDate(u.created_at)}
                          </span>
                        </td>

                        {/* Actions */}
                        <td className="px-5 py-4">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleEdit(u)}
                              title="Edit user"
                              className="p-2 rounded-lg text-gray-400 hover:text-brand-600 hover:bg-brand-600/10 transition"
                              id={`edit-user-${u.id}`}
                            >
                              <FiEdit2 size={15} />
                            </button>
                            {!isSelf && (
                              <button
                                onClick={() => handleToggleActive(u)}
                                title={u.is_active ? "Deactivate user" : "Activate user"}
                                className={`p-2 rounded-lg transition ${
                                  u.is_active
                                    ? "text-gray-400 hover:text-red-600 hover:bg-red-50"
                                    : "text-gray-400 hover:text-green-600 hover:bg-green-50"
                                }`}
                                id={`toggle-user-${u.id}`}
                              >
                                {u.is_active ? <FiUserX size={15} /> : <FiUserCheck size={15} />}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Edit Modal */}
      <EditUserModal
        isOpen={editModalOpen}
        onClose={() => {
          setEditModalOpen(false);
          setSelectedUser(null);
        }}
        user={selectedUser}
        onSuccess={handleEditSuccess}
      />

      {/* Confirm Deactivate / Activate Modal */}
      <Modal
        isOpen={confirmModalOpen}
        onClose={() => {
          if (!confirmLoading) {
            setConfirmModalOpen(false);
            setConfirmAction(null);
          }
        }}
        title={confirmAction?.action === "deactivate" ? "Deactivate User" : "Activate User"}
        loading={confirmLoading}
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                setConfirmModalOpen(false);
                setConfirmAction(null);
              }}
              disabled={confirmLoading}
            >
              Cancel
            </Button>
            <Button
              variant={confirmAction?.action === "deactivate" ? "danger" : "primary"}
              onClick={handleConfirmToggle}
              disabled={confirmLoading}
            >
              {confirmLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  Processing…
                </span>
              ) : confirmAction?.action === "deactivate" ? (
                <span className="flex items-center gap-2">
                  <FiUserX size={16} />
                  Deactivate
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <FiUserCheck size={16} />
                  Activate
                </span>
              )}
            </Button>
          </>
        }
      >
        <div className="p-6">
          {confirmAction?.action === "deactivate" ? (
            <p className="text-sm text-gray-600">
              Are you sure you want to deactivate <strong>{confirmAction?.userName}</strong>'s account?
              They will no longer be able to log in until their account is re-activated.
            </p>
          ) : (
            <p className="text-sm text-gray-600">
              Are you sure you want to re-activate <strong>{confirmAction?.userName}</strong>'s account?
              They will be able to log in again.
            </p>
          )}
        </div>
      </Modal>

      {/* Toast */}
      <Toast notification={notification} onClose={() => setNotification(null)} />
    </HrShellLayout>
  );
}
