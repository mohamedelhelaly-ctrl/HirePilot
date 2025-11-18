export default function Button({ title, className = "", ...props }) {
  return (
    <button
      className={`w-full bg-blue-700 text-white py-2 rounded-lg font-semibold hover:bg-blue-600 transition ${className}`}
      {...props}
    >
      {title}
    </button>
  );
}
