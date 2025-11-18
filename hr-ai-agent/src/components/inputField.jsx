import React from "react";

export default function InputField({ label, placeholder, type = "text", icon }) {
  return (
    <div className="flex flex-col">
      {label && <label className="text-sm text-gray-700 mb-1">{label}</label>}
      <div className="relative">
        {icon && (
          <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
            {icon}
          </span>
        )}
        <input
          type={type}
          placeholder={placeholder}
          className={`w-full border rounded-lg py-3 ${
            icon ? "pl-10 pr-3" : "px-3"
          } focus:outline-none focus:ring-2 focus:ring-blue-200`}
        />
      </div>
    </div>
  );
}
