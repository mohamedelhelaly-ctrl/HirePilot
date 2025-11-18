import InputField from "../components/inputField";
import Button from "../components/button";
import illustration from "../assets/logo-width.jpg";
import { FiUser, FiLock } from "react-icons/fi";
import AuthLayout from "../layouts/AuthLayout";

export default function Login() {
  return (
    <AuthLayout>
      <div className="flex w-full">
        {/* Left Image */}
        <div className="w-1/2 bg-white p-10 flex items-center justify-center">
          <img src={illustration} className="rounded-xl w-full h-full" />
        </div>

        {/* Right Form */}
        <div className="w-1/2 p-12 flex flex-col justify-center border-l border-gray-200">
          <h2 className="text-3xl font-bold mb-2">Sign in to your accoaunt</h2>
          <p className="text-gray-500 mb-8">Welcome to the AI HR Agent.</p>

          <div className="flex flex-col gap-5">
            <InputField
              label="Username"
              placeholder="Enter your username"
              icon={<FiUser size={18} />}
            />

            <InputField
              label="Password"
              type="password"
              placeholder="Enter your password"
              icon={<FiLock size={18} />}
            />

            <div className="flex justify-between items-center mt-2">
              <label className="flex items-center gap-2">
                <input type="checkbox" />
                <span className="text-gray-600">Remember me</span>
              </label>

              <a href="#" className="text-blue-700 text-sm hover:underline">
                Forgot password?
              </a>
            </div>

            <Button title="Login" />
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}
