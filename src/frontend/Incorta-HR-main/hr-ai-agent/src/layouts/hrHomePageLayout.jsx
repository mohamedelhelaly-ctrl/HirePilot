import Navbar from "../components/navBar";

export default function DashboardLayout({ children }) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50 ">
      {/* Top Navigation */}
      <Navbar />

      {/* Page Content - allow full width */}
      <main className="flex-1 p-6 w-full max-w-full">
        {children}
      </main>
    </div>
  );
}
