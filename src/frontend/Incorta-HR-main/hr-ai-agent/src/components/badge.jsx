const deptColors = {
  Engineering: "bg-blue-100 text-blue-700",
  Finance: "bg-purple-100 text-purple-700",
  Sales: "bg-green-100 text-green-700",
  Marketing: "bg-orange-100 text-orange-700",
  Default: "bg-gray-100 text-gray-600",
};

export default function Badge({ text, color, className = "" }) {
  const colorClass = color || deptColors[text] || deptColors.Default;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${colorClass} ${className}`}
    >
      {text}
    </span>
  );
}
