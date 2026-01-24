import InputField from "../components/inputField";
import Button from "../components/button";
import illustration from "../assets/logo-width.jpg";
import { FiUser, FiLock } from "react-icons/fi";
import AuthLayout from "../layouts/AuthLayout";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    
    // Check credentials (username: "hr", password: "hr")
    if (username === "hr" && password === "hr") {
      // Store auth state (optional - you can use localStorage or context)
      localStorage.setItem("isAuthenticated", "true");
      navigate("/hr");
    } else {
      setError("Invalid username or password");
    }
  };

  return (
    <AuthLayout>
      <div className="flex w-full">
        {/* Left Image */}
        <div className="w-1/2 bg-white p-10 flex items-center justify-center">
          <img src={illustration} className="rounded-xl w-full h-full" />
        </div>

        {/* Right Form */}
        <div className="w-1/2 p-12 flex flex-col justify-center border-l border-gray-200">
          <h2 className="text-3xl font-bold mb-2">Sign in to your account</h2>
          <p className="text-gray-500 mb-8">Welcome to the AI HR Agent.</p>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="flex flex-col gap-5">
            <InputField
              label="Username"
              placeholder="Enter your username"
              icon={<FiUser size={18} />}
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setError("");
              }}
            />

            <InputField
              label="Password"
              type="password"
              placeholder="Enter your password"
              icon={<FiLock size={18} />}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError("");
              }}
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
          </form>

          <p className="text-gray-600 text-sm mt-4">
            Demo credentials: <br />
            Username: <strong>hr</strong> <br />
            Password: <strong>hr</strong>
          </p>
        </div>
      </div>
    </AuthLayout>
  );
}
