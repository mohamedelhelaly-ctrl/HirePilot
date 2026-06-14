import Navbar from "../components/navBar";

export default function DashboardLayout({ children, fullHeight = false }) {
  return (
    <div
      className={`flex flex-col bg-canvas ${fullHeight ? "h-screen overflow-hidden" : "min-h-screen"}`}
    >
      <Navbar compact={fullHeight} />
      <main
        className={`flex-1 w-full ${
          fullHeight
            ? "min-h-0 overflow-hidden flex flex-col max-w-none mx-0 px-0"
            : "max-w-[1400px] mx-auto pt-8 pb-16 px-10"
        }`}
      >
        {children}
      </main>
    </div>
  );
}
