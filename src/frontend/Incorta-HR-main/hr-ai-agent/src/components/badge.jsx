export default function Badge({ text, color }) {
  const colors = {
    Engineering: "bg-blue-100 text-blue-600",
    Finance: "bg-purple-100 text-purple-600",
    Sales: "bg-green-100 text-green-600",
    Marketing: "bg-orange-100 text-orange-600",
    Default: "bg-gray-100 text-gray-600",
  };

  return (
    <span className={`px-3 py-1 text-sm rounded-full ${colors[text] || colors.Default}`}>
      {text}
    </span>
  );
}