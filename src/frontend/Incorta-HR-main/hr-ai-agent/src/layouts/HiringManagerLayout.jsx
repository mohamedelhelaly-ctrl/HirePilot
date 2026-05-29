import { FiSettings, FiHelpCircle, FiPlus } from "react-icons/fi";
import { MdDashboard, MdWork, MdAnalytics } from "react-icons/md";

export default function HiringManagerLayout({ children }) {
  return (
    <div className="flex h-screen w-full">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-gray-200 bg-white p-4">
        {/* Profile Section */}
        <div className="flex items-center gap-3 mb-8">
          <img
            src="https://i.pravatar.cc/40?u=alexchen"
            alt="Alex Chen"
            className="w-10 h-10 rounded-full"
          />
          <div className="flex flex-col">
            <h1 className="text-base font-medium text-gray-900">Alex Chen</h1>
            <p className="text-sm font-normal text-gray-500">Hiring Manager</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-2">
          <a
            href="/hiring-manager"
            className="flex items-center gap-3 rounded-lg bg-blue-50 px-3 py-2 text-blue-600 border-l-4 border-blue-500"
          >
            <MdWork size={20} />
            <p className="text-sm font-medium">My Open Jobs</p>
          </a>
          <a
            href="/analytics"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-600 hover:bg-gray-100 transition"
          >
            <MdAnalytics size={20} />
            <p className="text-sm font-medium">Analytics</p>
          </a>
        </nav>

        {/* Bottom Section */}
        <div className="mt-auto flex flex-col gap-4">
          <button className="flex items-center justify-center rounded-lg h-10 px-4 bg-blue-600 text-white text-sm font-bold hover:bg-blue-700 transition">
            <FiPlus size={18} className="mr-1" />
            Post a New Job
          </button>
          <div className="flex flex-col gap-1">
            <a
              href="#"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-600 hover:bg-gray-100 transition"
            >
              <FiSettings size={20} />
              <p className="text-sm font-medium">Settings</p>
            </a>
            <a
              href="#"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-600 hover:bg-gray-100 transition"
            >
              <FiHelpCircle size={20} />
              <p className="text-sm font-medium">Help</p>
            </a>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex w-full flex-1 flex-col overflow-y-auto">
        <div className="flex flex-col p-6 lg:p-8">{children}</div>
      </main>
    </div>
  );
}
