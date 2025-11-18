export default function AuthLayout({ children }) {
  return (
    <div className="h-screen w-full flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow-lg rounded-3xl flex overflow-hidden max-w-6xl w-full">
        {children}
      </div>
    </div>
  );
}
