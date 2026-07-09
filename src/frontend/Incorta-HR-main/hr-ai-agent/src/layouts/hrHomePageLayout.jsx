import HrShellLayout from "./hrShellLayout";

export default function DashboardLayout({ children, fullHeight = false, hideSidebar = false }) {
  return (
    <HrShellLayout fullHeight={fullHeight} hideSidebar={hideSidebar}>
      {children}
    </HrShellLayout>
  );
}
