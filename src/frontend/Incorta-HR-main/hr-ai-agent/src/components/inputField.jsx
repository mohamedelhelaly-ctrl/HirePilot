const inputClasses =
  "w-full border border-border rounded-[10px] py-2.5 focus:outline-none focus:border-brand-600 focus:ring-[3px] focus:ring-brand-600/18 transition disabled:opacity-50";

export default function InputField({
  label,
  placeholder,
  type = "text",
  icon,
  value,
  onChange,
  className = "",
  ...props
}) {
  return (
    <div className={`flex flex-col ${className}`}>
      {label && (
        <label className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted mb-1.5">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
            {icon}
          </span>
        )}
        <input
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          className={`${inputClasses} ${icon ? "pl-10 pr-3" : "px-3"}`}
          {...props}
        />
      </div>
    </div>
  );
}

export { inputClasses };
