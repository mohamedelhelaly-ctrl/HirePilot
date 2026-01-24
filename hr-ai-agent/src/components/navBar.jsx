export default function Navbar() {
  return (
    <nav className="w-full flex items-center justify-between py-4 px-10 bg-white shadow-sm">
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 bg-blue-600 rounded-md"></div>
        <h1 className="text-2xl font-semibold">Incorta</h1>
      </div>

      <div className="flex items-center gap-10 text-gray-600">
        <a className="text-black font-semibold cursor-pointer text-xl">Home</a>
        <a className="hover:text-black cursor-pointer text-xl">Hiring Manager Dashboard</a>
      </div>

      <div>
        <img
          src="https://i.pravatar.cc/40"
          alt="avatar"
          className="w-10 h-10 rounded-full border"
        />
      </div>
    </nav>
  );
}
