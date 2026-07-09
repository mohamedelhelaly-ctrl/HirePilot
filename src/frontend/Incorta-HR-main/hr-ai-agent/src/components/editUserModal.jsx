import { useState, useEffect } from "react";
import Modal from "./Modal";
import InputField from "./inputField";
import { inputClasses } from "./inputField";
import Button from "./button";
import { updateUser } from "../services/userService";
import { FiMail, FiUser, FiSave } from "react-icons/fi";

const ROLES = [
  { value: "hr_manager", label: "HR Manager" },
  { value: "hiring_manager", label: "Hiring Manager" },
];

export default function EditUserModal({ isOpen, onClose, user, onSuccess }) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("hiring_manager");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Populate form when user prop changes
  useEffect(() => {
    if (user) {
      setEmail(user.email || "");
      setFullName(user.full_name || "");
      setRole(user.role || "hiring_manager");
      setError("");
    }
  }, [user]);

  const handleClose = () => {
    if (!loading) {
      setError("");
      onClose();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    if (!fullName.trim()) {
      setError("Full name is required.");
      return;
    }

    setLoading(true);
    try {
      const updatedUser = await updateUser(user.id, {
        email: email.trim(),
        full_name: fullName.trim(),
        role,
      });
      onSuccess?.(updatedUser);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to update user.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Edit User"
      loading={loading}
      footer={
        <>
          <Button variant="ghost" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmit} disabled={loading}>
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12" cy="12" r="10"
                    stroke="currentColor" strokeWidth="4" fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                  />
                </svg>
                Saving…
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <FiSave size={16} />
                Save Changes
              </span>
            )}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-5">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-medium">
            {error}
          </div>
        )}

        <InputField
          label="Email Address"
          placeholder="Enter user's email address"
          type="email"
          icon={<FiMail size={16} />}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={loading}
          required
          id="edit-user-email"
        />

        <InputField
          label="Full Name"
          placeholder="First and last name"
          icon={<FiUser size={16} />}
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          disabled={loading}
          required
          id="edit-user-fullname"
        />

        <div className="flex flex-col">
          <label
            htmlFor="edit-user-role"
            className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted mb-1.5"
          >
            Role
          </label>
          <select
            id="edit-user-role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            disabled={loading}
            className={`${inputClasses} px-3 appearance-none bg-white bg-[url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")] bg-[length:16px] bg-[right_12px_center] bg-no-repeat pr-10 cursor-pointer`}
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
      </form>
    </Modal>
  );
}
