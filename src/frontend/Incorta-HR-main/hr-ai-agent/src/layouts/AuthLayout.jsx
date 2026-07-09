export default function AuthLayout({ children }) {
  return (
    <div className="min-h-screen w-full bg-canvas flex items-center justify-center p-4 lg:p-8">
      <div className="bg-surface shadow-[0_4px_24px_rgb(0_0_0_/_0.06)] rounded-xl overflow-hidden max-w-5xl w-full">
        {children}
      </div>
    </div>
  );
}
