import { useState } from "react";
import Modal from "./Modal";
import InputField from "./inputField";
import { inputClasses } from "./inputField";
import Button from "./button";
import { createUser } from "../services/authService";
import { FiMail, FiUser, FiUserPlus } from "react-icons/fi";

const ROLES = [
  { value: "hr_manager", label: "HR Manager" },
  { value: "hiring_manager", label: "Hiring Manager" },
];

export default function CreateUserModal({ isOpen, onClose, onSuccess }) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("hiring_manager");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const resetForm = () => {
    setEmail("");
    setFullName("");
    setRole("hiring_manager");
    setError("");
  };

  const handleClose = () => {
    if (!loading) {
      resetForm();
      onClose();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    // Basic validation
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
      const newUser = await createUser(email.trim(), fullName.trim(), role);
      resetForm();
      onSuccess?.(newUser);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to create user.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create New User"
      loading={loading}
      footer={
        <>
          <Button
            variant="ghost"
            onClick={handleClose}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={loading}
          >
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
                Creating…
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <FiUserPlus size={16} />
                Create User
              </span>
            )}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-5">
        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-medium">
            {error}
          </div>
        )}

        {/* Email */}
        <InputField
          label="Email Address"
          placeholder="john.doe@company.com"
          type="email"
          icon={<FiMail size={16} />}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={loading}
          required
          id="create-user-email"
        />

        {/* Full Name */}
        <InputField
          label="Full Name"
          placeholder="John Doe"
          icon={<FiUser size={16} />}
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          disabled={loading}
          required
          id="create-user-fullname"
        />

        {/* Role Dropdown */}
        <div className="flex flex-col">
          <label
            htmlFor="create-user-role"
            className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted mb-1.5"
          >
            Role
          </label>
          <select
            id="create-user-role"
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
