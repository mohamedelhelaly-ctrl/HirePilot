/* eslint-disable react-hooks/set-state-in-effect */
import { FiX } from "react-icons/fi";
import { useState, useEffect } from "react";import { inputClasses } from "./inputField";
import Button from "./button";

const fieldLabel =
  "flex flex-col gap-1.5 text-[11px] font-extrabold uppercase tracking-[0.1em] text-gray-900";
const fieldInput = `${inputClasses} text-sm py-2 px-3 bg-surface`;
const fieldError = "text-red-600 text-xs mt-1";

function WizardSteps({ step, isEditMode }) {
  if (isEditMode) return null;

  return (
    <div className="flex items-center w-full pt-3.5 mt-3 border-t border-[#eee]">
      <div
        className={`flex items-center gap-2 px-3.5 text-[13px] whitespace-nowrap ${
          step === 1 ? "font-semibold text-gray-900" : "font-medium text-emerald-600"
        }`}
      >
        <span
          className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-bold leading-none ${
            step === 1
              ? "bg-brand-600 text-white"
              : "bg-emerald-500 text-white"
          }`}
        >
          {step > 1 ? "✓" : "1"}
        </span>
        Details
      </div>

      <div className="flex-1 relative h-0.5 bg-[#d2d2d7] mx-0 rounded-sm">
        <div
          className="absolute inset-y-0 left-0 bg-brand-600 rounded-sm transition-all duration-300"
          style={{ width: step >= 2 ? "100%" : "0%" }}
        />
      </div>

      <div
        className={`flex items-center gap-2 px-3.5 text-[13px] whitespace-nowrap ${
          step === 2 ? "font-semibold text-gray-900" : "text-muted"
        }`}
      >
        <span
          className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-bold leading-none ${
            step === 2 ? "bg-brand-600 text-white" : "bg-[#eee] text-gray-600"
          }`}
        >
          2
        </span>
        Job Description
      </div>
    </div>
  );
}

export default function RequisitionModal({
  isOpen,
  mode,
  requisition,
  onClose,
  onSubmit,
  loading = false,
}) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({    title: "",
    description: "",
    department: "",
    location: "",
  });
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState("");

  const isEditMode = mode === "edit";
  useEffect(() => {
    if (requisition && mode === "edit") {
      setFormData({
        title: requisition.title || "",
        description: requisition.description || "",
        department: requisition.department || "",
        location: requisition.location || "",
      });
      setErrors({});
      setStep(1);
    } else if (mode === "create" && isOpen) {      setFormData({
        title: "",
        description: "",
        department: "",
        location: "",
      });
      setErrors({});
      setStep(1);
    }    setSubmitError("");
  }, [requisition, mode, isOpen]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
    if (submitError) setSubmitError("");
  };

  const validateStep1 = () => {
    const newErrors = {};
    if (!formData.title.trim()) newErrors.title = "Job title is required";
    if (!formData.department.trim()) newErrors.department = "Department is required";
    if (!formData.location.trim()) newErrors.location = "Location is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = () => {
    const newErrors = {};
    if (!formData.description.trim()) {
      newErrors.description = "Job description is required";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = (e) => {
    e.preventDefault();
    if (validateStep1()) {
      setSubmitError("");
      setStep(2);
    }
  };

  const handleBack = () => {
    setSubmitError("");
    setStep(1);
  };

  const validateAll = () => {
    const step1Ok = validateStep1();
    const step2Ok = validateStep2();
    return step1Ok && step2Ok;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validateAll()) return;
    onSubmit(formData);
  };

  if (!isOpen) return null;
  const modalTitle = isEditMode
    ? "Edit Requisition"
    : step === 1
    ? "New Requisition"
    : "Add Job Description";

  return (
    <div
      className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-6"
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-surface rounded-xl shadow-[0_24px_80px_rgb(0_0_0_/_0.2)] max-w-[640px] w-full max-h-[90vh] overflow-y-auto p-6">
        {/* Header */}
        <div className="mb-1">
          <div className="flex items-center justify-between gap-4 pb-3">
            <h2 className="m-0 text-[1.15rem] font-bold text-gray-900">{modalTitle}</h2>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              aria-label="Close"
              className="shrink-0 w-8 h-8 flex items-center justify-center rounded-md text-muted hover:text-gray-900 hover:bg-gray-100 transition disabled:opacity-50"
            >
              <FiX size={18} />
            </button>
          </div>
          <WizardSteps step={step} isEditMode={isEditMode} />
        </div>

        {/* Step 1 — Details */}
        {(step === 1 || isEditMode) && (
          <form
            onSubmit={isEditMode ? handleSubmit : handleNext}
            className="flex flex-col gap-3.5 pt-1"
          >
            <label className={fieldLabel}>
              Job Title *
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                placeholder="e.g. Senior Software Engineer"
                disabled={loading}
                className={`${fieldInput} ${errors.title ? "border-red-500" : ""}`}
              />
              {errors.title && <span className={fieldError}>{errors.title}</span>}
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <label className={fieldLabel}>
                Department *
                <input
                  type="text"
                  name="department"
                  value={formData.department}
                  onChange={handleChange}
                  placeholder="e.g. Engineering"
                  disabled={loading}
                  className={`${fieldInput} ${errors.department ? "border-red-500" : ""}`}
                />
                {errors.department && <span className={fieldError}>{errors.department}</span>}
              </label>

              <label className={fieldLabel}>
                Location *
                <input
                  type="text"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  placeholder="e.g. Cairo, Egypt"
                  disabled={loading}
                  className={`${fieldInput} ${errors.location ? "border-red-500" : ""}`}
                />
                {errors.location && <span className={fieldError}>{errors.location}</span>}
              </label>
            </div>

            {isEditMode && (
              <label className={fieldLabel}>
                Job Description *
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  placeholder="Describe the role, responsibilities, and requirements..."
                  disabled={loading}
                  rows={8}
                  className={`${fieldInput} resize-y min-h-[160px] leading-relaxed ${
                    errors.description ? "border-red-500" : ""
                  }`}
                />
                {errors.description && (
                  <span className={fieldError}>{errors.description}</span>
                )}
              </label>
            )}

            {submitError && <p className="text-red-600 text-sm m-0">{submitError}</p>}

            <div className="flex items-center justify-end gap-2.5 pt-5 mt-1 border-t border-[#eee]">
              <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              {isEditMode ? (
                <Button type="submit" size="sm" disabled={loading}>
                  {loading ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Update Requisition"
                  )}
                </Button>
              ) : (
                <Button type="submit" size="sm" disabled={loading}>
                  Next →
                </Button>
              )}
            </div>
          </form>
        )}

        {/* Step 2 — Job Description (create only) */}
        {step === 2 && !isEditMode && (
          <form onSubmit={handleSubmit} className="flex flex-col gap-3.5 pt-1">
            <label className={fieldLabel}>
              Description *
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="External job description — responsibilities, requirements, and qualifications..."
                disabled={loading}
                rows={10}
                className={`${fieldInput} resize-y min-h-[220px] leading-relaxed ${
                  errors.description ? "border-red-500" : ""
                }`}
              />
              {errors.description && (
                <span className={fieldError}>{errors.description}</span>
              )}
            </label>

            <div className="flex items-center justify-between gap-2.5 pt-5 mt-1 border-t border-[#eee]">              <Button type="button" variant="ghost" size="sm" onClick={handleBack} disabled={loading}>
                ← Back
              </Button>
              <Button type="submit" size="sm" disabled={loading}>
                {loading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  "Create Requisition"
                )}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
