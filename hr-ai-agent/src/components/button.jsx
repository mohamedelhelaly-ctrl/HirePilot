export default function Button({ title }) {
  return (
    <button className="w-full bg-blue-500 text-white py-2 rounded-lg font-semibold hover:bg-blue-600 transition">
      {title}
    </button>
  );
}
